from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import tempfile
import os
from config import get_db
from dependencies import get_current_user
from Models.user_model import User
from Models.analyzer_model import Analyzer
from groq import Groq
from Services.moderation_service import ModerationService
from Services.acrcloud_service import ACRCloudService
from Services.copyright_service import CopyrightService
from Shemas.moderation_schemas import (
    ContentCheckResponse,
    ModerationHistoryResponse,
    UpdateQuestionInput,
    MinimalAudioModerationResponse,
    CombinedAudioModerationResponse,
)

router = APIRouter(tags=["Audio Moderation"])

@router.post("/moderation/audio", response_model=CombinedAudioModerationResponse)
async def moderate_audio_file(
    file: UploadFile = File(...),
    model: str = "llama3-70b-8192",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith((".mp3", ".wav", ".m4a")):
        raise HTTPException(status_code=400, detail="Seuls les fichiers audio mp3, wav, m4a sont autorisés.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    import httpx
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    acrcloud_service = ACRCloudService()
    copyright_service = CopyrightService()
    
    try:
        print("🔍 Vérification du copyright avec ACRCloud...")
        acrcloud_result = None
        copyright_detection_failed = False
        
        try:
            acrcloud_result = await acrcloud_service.recognize_audio(tmp_path)
            print(f" ACRCloud result status: {acrcloud_result.get('status')}")
            print(f" Music detected: {acrcloud_result.get('music_detected')}")
            
            if acrcloud_result.get("status") == "error":
                print(f"⚠️ Erreur ACRCloud: {acrcloud_result.get('recommendation')}")
                copyright_detection_failed = True
            
        except Exception as copyright_error:
            print(f"⚠️ Exception service ACRCloud: {type(copyright_error).__name__}: {copyright_error}")
            copyright_detection_failed = True
            acrcloud_result = None
        
        transcript = ""
        detected_language = "unknown"
        try:
            with open(tmp_path, "rb") as f:
                files = {
                    "file": (file.filename, f, file.content_type or "audio/mpeg"),
                }
                data = {
                    "model": "whisper-large-v3",
                    "response_format": "verbose_json",
                    "temperature": 0.0
                }
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                }
                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                    response = await client.post(GROQ_AUDIO_URL, data=data, files=files, headers=headers)
                
                if response.status_code != 200:
                    print(f"⚠️ Erreur Groq API: {response.status_code} - {response.text}")
                    transcript = "[Transcription indisponible - erreur API]"
                else:
                    response_data = response.json()
                    transcript = response_data.get("text", "").strip()
                    whisper_language = response_data.get("language", "unknown")
                    
                    language_mapping = {
                        "en": "English",
                        "fr": "French", 
                        "es": "Spanish",
                        "ar": "Arabic",
                        "de": "German",
                        "it": "Italian",
                        "pt": "Portuguese",
                        "ru": "Russian",
                        "ja": "Japanese",
                        "ko": "Korean",
                        "zh": "Chinese"
                    }
                    
                    detected_language = language_mapping.get(whisper_language, whisper_language)
                    print(f" Langue détectée par Whisper: {detected_language} ({whisper_language})")
                    print(f" Transcription: {transcript[:100]}...")
                    
        except Exception as groq_error:
            print(f"⚠️ Erreur Groq générale: {groq_error}")
            transcript = "[Transcription indisponible - erreur service]"
        
        copyright_analysis_result = {
            "status": "success",
            "music_detected": False,
            "title": None,
            "artist": None,
            "album": None,
            "release_date": None,
            "label": None,
            "copyright_protected": False,
            "platforms": {}
        }
        
        # Try ACRCloud first for audio analysis
        if acrcloud_result and acrcloud_result.get("status") == "success":
            copyright_analysis_result = acrcloud_result
        # If ACRCloud fails but we have transcript, analyze text for lyrics
        elif transcript and not transcript.startswith("[Transcription indisponible"):
            try:
                text_analysis = await copyright_service.analyze_text_for_music(transcript)
                # Some implementations wrap details under 'copyright_analysis'
                ca_candidate = text_analysis.get("copyright_analysis") or text_analysis
                pm = ca_candidate.get("potential_matches") or []
                originality = ca_candidate.get("lyrics_originality_score")
                inferred_lyrics = bool(pm) or (isinstance(originality, (int, float)) and originality < 0.6)
                has_music = bool(ca_candidate.get("music_detected"))
                has_lyrics_copy = bool(ca_candidate.get("lyrics_copyrighted") or inferred_lyrics)
                if has_music or has_lyrics_copy:
                    # Promote lyrics-detected copyright as music detection proxy for moderation
                    if has_lyrics_copy and not has_music:
                        ca_candidate["music_detected"] = True
                    copyright_analysis_result = ca_candidate
            except Exception as e:
                print(f"⚠️ Erreur analyse texte copyright: {e}")
        
        content_type = "speech"
        is_likely_music = copyright_analysis_result.get("music_detected", False)
        
        if is_likely_music:
            content_type = "music"
            print(f" Music detected: {copyright_analysis_result.get('artist')} - {copyright_analysis_result.get('title')}")
        
        if content_type == "music" and copyright_analysis_result.get("copyright_protected"):
            music_info = {
                "artist": copyright_analysis_result.get("artist") or "Unknown Artist",
                "title": copyright_analysis_result.get("title") or "Unknown Title",
                "album": copyright_analysis_result.get("album") or "Unknown Album",
                "release_date": copyright_analysis_result.get("release_date") or "Unknown Date",
                "label": copyright_analysis_result.get("label") or "Unknown Label"
            }
            
            platforms_count = len(copyright_analysis_result.get("platforms", {}))
            
            minimal_blocked = {
                "status": "blocked",
                "can_publish": False,
                "message": "🚫 PUBLICATION BLOQUÉE: Contenu non conforme détecté dans l'audio.",
                "violated_rules": ["Violation de droits d'auteur"],
                "lyrics_analysis": {
                    "status": "allowed",
                    "toxic": False,
                    "categories": [],
                    "confidence": 0.0,
                    "flagged_text": "",
                    "recommendation": "Aucune action requise"
                },
                "copyright_analysis": {
                    "music_detected": True,
                    "title": music_info["title"],
                    "artist": music_info["artist"],
                    "album": music_info["album"],
                    "release_date": music_info["release_date"],
                    "copyright_protected": True,
                    "confidence_score": copyright_analysis_result.get("confidence_score", 1.0),
                    "strike_risk_level": copyright_analysis_result.get("strike_risk_level", "high"),
                    "recommendation": copyright_analysis_result.get("recommendation", "Remplacer la musique ou obtenir une licence.")
                },
                "automatic_action": "block"
            }
            return MinimalAudioModerationResponse(**minimal_blocked)
        
        if not transcript or transcript.startswith("[Transcription indisponible"):
            result = {
                "status": "erreur_transcription",
                "bert": {"label": "unknown", "confidence": 0.0},
                "groq": {"status": "erreur", "reasoning": "Impossible de transcrire l'audio", "category": "erreur_technique"},
                "message": f"Erreur de transcription audio. {transcript}",
                "processed_text": transcript,
                "violated_rules": [],
                "conflict_detected": False,
                "detected_language": detected_language,
                "requires_manual_review": True,
                "copyright_analysis": copyright_analysis_result,
                "youtube_report": None,
                "automatic_action": "manual_review",
                "can_publish": False,
                "copyright_strike_risk": False
            }
        else:
            normalized_transcript = transcript.strip().lower()
            while normalized_transcript and normalized_transcript[-1] in ".!?":
                normalized_transcript = normalized_transcript[:-1]
            normalized_transcript = normalized_transcript.strip()

            neutral_expressions = [
                "what the fuck", "wtf", "oh fuck", "fuck it", "what the hell", "damn", "shit", "no way"
            ]
            is_neutral_expression = any(expr in normalized_transcript for expr in neutral_expressions)
            is_insulting = any(word in normalized_transcript for word in ["suck", "idiot", "stupid", "hate", "kill"])

            if is_neutral_expression and not is_insulting:
                print("😅 Expression familière/humoristique détectée dans l'audio - considérée comme conforme")
                result = {
                    "status": "conforme",
                    "bert": {"label": "safe", "confidence": 1.0},
                    "groq": {"status": "conforme", "reasoning": "Expression familière/humoristique détectée (ex: 'what the fuck') dans un contexte non insultant.", "category": "aucun", "is_insult": False},
                    "message": f"Expression familière/humoristique détectée (Langue: {detected_language}) : le texte audio est conforme.",
                    "processed_text": normalized_transcript,
                    "violated_rules": [],
                    "conflict_detected": False,
                    "detected_language": detected_language,
                    "copyright_analysis": copyright_analysis_result,
                    "youtube_report": None,
                    "automatic_action": "allow",
                    "can_publish": True,
                    "copyright_strike_risk": False
                }
            else:
                # Obtenir le résultat de la modération du contenu
                result = await ModerationService.check_content_comprehensive(
                    text=normalized_transcript,
                    model=model,
                    db=db,
                    user_id=current_user.id,
                    entry_type="audio"
                )
                
                # Mettre à jour les informations de langue détectée
                result["detected_language"] = detected_language
                
                # Mettre à jour l'analyse des droits d'auteur
                result["copyright_analysis"] = copyright_analysis_result
                
                # Mettre à jour le rapport YouTube si nécessaire
                if "youtube_report" not in result or not result["youtube_report"]:
                    result["youtube_report"] = {
                        "message": "Aucune violation de droits d'auteur détectée",
                        "risk_level": "low"
                    }
                
                # Mettre à jour les champs audio_analysis avec les informations de copyright
                if "audio_analysis" not in result:
                    result["audio_analysis"] = {}
                
                # Mettre à jour les champs spécifiques de l'analyse audio
                audio_analysis = result["audio_analysis"]
                
                # Mettre à jour les informations de détection de musique
                audio_analysis["music_detected"] = copyright_analysis_result.get("music_detected", False)
                audio_analysis["music_confidence"] = copyright_analysis_result.get("confidence_score", 0.0)
                
                # Mettre à jour les informations de droits d'auteur
                audio_analysis["is_copyrighted"] = copyright_analysis_result.get("copyright_protected", False)
                audio_analysis["copyright_status"] = "copyrighted" if copyright_analysis_result.get("copyright_protected") else "copyright_free"
                audio_analysis["copyright_confidence"] = copyright_analysis_result.get("confidence_score", 0.0)
                
                # Mettre à jour les genres détectés et le statut de domaine public
                audio_analysis["detected_genres"] = copyright_analysis_result.get("genres", [])
                audio_analysis["is_public_domain"] = copyright_analysis_result.get("is_public_domain", False)
                
                # Mettre à jour les champs de refrain et d'autotune s'ils sont disponibles
                if "refrain_detected" in copyright_analysis_result:
                    audio_analysis["refrain_detected"] = copyright_analysis_result["refrain_detected"]
                    audio_analysis["refrain_confidence"] = copyright_analysis_result.get("refrain_confidence", 0.0)
                    audio_analysis["refrain_patterns"] = copyright_analysis_result.get("refrain_patterns", [])
                
                if "autotune_detected" in copyright_analysis_result:
                    audio_analysis["autotune_detected"] = copyright_analysis_result["autotune_detected"]
                    audio_analysis["autotune_confidence"] = copyright_analysis_result.get("autotune_confidence", 0.0)
                    audio_analysis["autotune_artifacts"] = copyright_analysis_result.get("autotune_artifacts", [])
                
                # Mettre à jour les actions automatiques en fonction des droits d'auteur
                result["automatic_action"] = "block" if copyright_analysis_result.get("copyright_protected") else result.get("automatic_action", "allow")
                result["can_publish"] = not copyright_analysis_result.get("copyright_protected", False) and result.get("can_publish", True)
                result["copyright_strike_risk"] = copyright_analysis_result.get("copyright_protected", False)

        if "youtube_report" not in result:
            result["youtube_report"] = None
        elif result["youtube_report"] and isinstance(result["youtube_report"], str):
            # Convert string youtube_report to proper dict format
            result["youtube_report"] = {
                "message": result["youtube_report"],
                "risk_level": "medium",
                "detected_content": copyright_analysis_result.get("title", "Unknown")
            }
        
        if "automatic_action" not in result:
            result["automatic_action"] = "block" if copyright_analysis_result.get("copyright_protected") else "allow"
        if "can_publish" not in result:
            result["can_publish"] = not copyright_analysis_result.get("copyright_protected", False)
        if "copyright_strike_risk" not in result:
            result["copyright_strike_risk"] = copyright_analysis_result.get("copyright_protected", False)

        try:
            last_entry = db.query(Analyzer).filter(Analyzer.user_id == current_user.id).order_by(Analyzer.id.desc()).first()
            if last_entry and transcript and last_entry.question == transcript[:1000]:
                last_entry.type = "audio"
                db.add(last_entry)
                db.commit()
        except Exception as e:
            print(f"⚠️ Impossible de taguer l'entrée Analyzer comme audio : {e}")

        # Construire une réponse minimale, claire et visible
        lyrics_analysis = result.get("lyrics_analysis") or {}
        # Mapper des champs éventuels en cas de structure différente
        la_status = lyrics_analysis.get("status") or ("blocked" if lyrics_analysis.get("toxic") else "allowed") if lyrics_analysis else "allowed"
        la = {
            "status": la_status,
            "toxic": bool(lyrics_analysis.get("toxic", False)),
            "categories": lyrics_analysis.get("categories", []),
            "confidence": lyrics_analysis.get("confidence", lyrics_analysis.get("lyrics_confidence", 0.0)),
            "flagged_text": lyrics_analysis.get("flagged_text", ""),
            "recommendation": lyrics_analysis.get("recommendation", "Aucune action requise")
        }

        ca_source = result.get("copyright_analysis") or {}
        ca = {
            "music_detected": bool(ca_source.get("music_detected", False)),
            "title": ca_source.get("title"),
            "artist": ca_source.get("artist"),
            "album": ca_source.get("album"),
            "release_date": ca_source.get("release_date"),
            "copyright_protected": bool(ca_source.get("copyright_protected", False)),
            "confidence_score": ca_source.get("confidence_score", 0.0),
            "strike_risk_level": ca_source.get("strike_risk_level", "low"),
            "recommendation": ca_source.get("recommendation", "Aucune action requise.")
        }

        # Prise en compte du cas où le LLM détecte des paroles protégées (déduction robuste)
        potential_matches = ca_source.get("potential_matches") or []
        originality = ca_source.get("lyrics_originality_score", None)
        inferred_lyrics_copy = bool(potential_matches) or (isinstance(originality, (int, float)) and originality < 0.6)
        lyrics_copyrighted = bool(ca_source.get("lyrics_copyrighted", False) or inferred_lyrics_copy)
        if lyrics_copyrighted:
            la["status"] = "blocked"
            la.setdefault("categories", [])
            if "copyright_lyrics" not in la["categories"]:
                la["categories"].append("copyright_lyrics")
            la["confidence"] = la.get("confidence", ca_source.get("lyrics_confidence", 0.0))
            # Préférer la recommandation spécifique du LLM si disponible
            la["recommendation"] = ca_source.get(
                "recommendation",
                la.get("recommendation", "Supprimer ou réécrire les paroles protégées.")
            )

        # Forcer le blocage si la musique est protégée par le droit d'auteur ou si le risque est élevé/critique
        strike = str(ca.get("strike_risk_level", "")).lower()
        conf = ca.get("confidence_score", 0.0) or 0.0
        reco_text = str(ca.get("recommendation", "")).lower()
        implies_protection = any(kw in reco_text for kw in ["protégée", "copyright", "droits d'auteur", "licensed", "obtenir une licence", "obtenir des licences"]) 
        high_risk_music = bool(
            ca.get("music_detected") and (
                ca.get("copyright_protected")
                or strike in {"high", "critical"}
                or conf >= 0.9
                or implies_protection
            )
        )
        # Forcer blocage musique si l'un des critères ci-dessus est vrai
        force_block_copyright = high_risk_music
        force_block_lyrics = lyrics_copyrighted

        is_blocked = (
            force_block_copyright
            or force_block_lyrics
            or result.get("automatic_action") == "block"
            or not result.get("can_publish", True)
            or la.get("status") == "blocked"
        )

        # Construire/compléter la liste des règles violées
        violated_rules = list(result.get("violated_rules", []))
        if force_block_copyright and "Violation de droits d'auteur" not in violated_rules:
            violated_rules.append("Violation de droits d'auteur")
        if force_block_lyrics and "Paroles protégées par droits d'auteur" not in violated_rules:
            violated_rules.append("Paroles protégées par droits d'auteur")

        # Choisir un message explicite selon la source du blocage
        if force_block_copyright and force_block_lyrics:
            block_msg = "🚫 PUBLICATION BLOQUÉE: Musique et paroles protégées détectées."
        elif force_block_copyright:
            block_msg = "🚫 PUBLICATION BLOQUÉE: Musique protégée par droits d'auteur détectée."
        elif force_block_lyrics:
            block_msg = "🚫 PUBLICATION BLOQUÉE: Paroles protégées par droits d'auteur détectées."
        else:
            block_msg = "🚫 PUBLICATION BLOQUÉE: Contenu non conforme détecté dans l'audio."

        # Calcul du segment temporel s'il y a un offset fourni (ACRCloud)
        seg = None
        try:
            offset_ms = None
            duration_ms = None
            # offset peut venir soit du copyright_analysis (ACR) soit du résultat brut
            if "play_offset_ms" in ca_source and isinstance(ca_source.get("play_offset_ms"), (int, float)):
                offset_ms = int(ca_source.get("play_offset_ms") or 0)
            elif "play_offset_ms" in result and isinstance(result.get("play_offset_ms"), (int, float)):
                offset_ms = int(result.get("play_offset_ms") or 0)
            elif isinstance(ca.get("play_offset_ms"), (int, float)):
                offset_ms = int(ca.get("play_offset_ms") or 0)

            # récupérer la durée si disponible
            if "duration_ms" in ca_source and isinstance(ca_source.get("duration_ms"), (int, float)):
                duration_ms = int(ca_source.get("duration_ms") or 0)
            elif "duration_ms" in result and isinstance(result.get("duration_ms"), (int, float)):
                duration_ms = int(result.get("duration_ms") or 0)
            elif isinstance(ca.get("duration_ms"), (int, float)):
                duration_ms = int(ca.get("duration_ms") or 0)

            if offset_ms is not None and offset_ms >= 0:
                # fenêtre +/- 15s autour de l'offset
                window = 15000
                # si offset dépasse la durée connue, le borner à la fin - 1s
                if isinstance(duration_ms, int) and duration_ms > 0 and offset_ms > duration_ms:
                    offset_ms = max(0, duration_ms - 1000)

                start_ms = max(0, offset_ms - window)
                end_ms = offset_ms + window
                if isinstance(duration_ms, int) and duration_ms > 0:
                    end_ms = min(end_ms, duration_ms)
                    # s'assurer d'une fenêtre raisonnable si proche de la fin
                    if start_ms >= end_ms:
                        start_ms = max(0, end_ms - (2 * window))
                minute_index = offset_ms // 60000
                def fmt(ms: int) -> str:
                    s = ms // 1000
                    return f"{s//60:02d}:{s%60:02d}"
                seg = {
                    "minute_index": int(minute_index),
                    "offset_ms": int(offset_ms),
                    "start_ms": int(start_ms),
                    "end_ms": int(end_ms),
                    "start_time": fmt(start_ms),
                    "end_time": fmt(end_ms)
                }
        except Exception:
            seg = None

        minimal = {
            "status": "blocked" if is_blocked else "allowed",
            "can_publish": not is_blocked,
            "message": (block_msg if is_blocked else "✅ Contenu approuvé pour publication"),
            "violated_rules": violated_rules,
            "lyrics_analysis": la,
            "copyright_analysis": ca,
            "automatic_action": "block" if is_blocked else "allow",
            "copyrighted_segment": seg,
        }

        # Construire le bloc content_moderation minimal demandé
        groq_block = result.get("groq") or {}
        content_moderation = {
            "status": groq_block.get("status") or result.get("status", "conforme"),
            "bert": result.get("bert", {}),
            "groq": {
                "status": groq_block.get("status", "conforme"),
                "category": groq_block.get("category", "aucun"),
                "reasoning": groq_block.get("reasoning", result.get("message", "")),
                "is_insult": groq_block.get("is_insult", False),
            },
        }

        return CombinedAudioModerationResponse(
            content_moderation=content_moderation,
            audio_moderation=MinimalAudioModerationResponse(**minimal)
        )
    finally:
        os.remove(tmp_path)

@router.get("/moderation/audio/history", response_model=list[ModerationHistoryResponse])
async def get_audio_moderation_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analyses = db.query(Analyzer).filter(
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio"
    ).order_by(Analyzer.date.desc()).all()

    return [
        ModerationHistoryResponse(
            id=a.id,
            question=a.question,
            response=a.response,
            toxic=a.toxic,
            date=a.date.isoformat() if a.date else None
        ) for a in analyses
    ]

@router.get("/moderation/audio/history/search", response_model=list[ModerationHistoryResponse])
async def search_audio_history(
    search_query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not search_query:
        raise HTTPException(status_code=400, detail="Le paramètre 'search_query' est requis.")

    analyses = db.query(Analyzer).filter(
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio",
        (Analyzer.question.ilike(f"%{search_query}%")) |
        (Analyzer.response.ilike(f"%{search_query}%"))
    ).order_by(Analyzer.date.desc()).all()

    return [
        ModerationHistoryResponse(
            id=a.id,
            question=a.question,
            response=a.response,
            toxic=a.toxic,
            date=a.date.isoformat() if a.date else None
        ) for a in analyses
    ]

@router.patch("/moderation/audio/history/{analysis_id}", response_model=ModerationHistoryResponse)
async def update_audio_analysis(
    analysis_id: int,
    update_data: UpdateQuestionInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analyzer).filter(
        Analyzer.id == analysis_id,
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio"
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse audio non trouvée.")

    analysis.question = update_data.question
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return ModerationHistoryResponse(
        id=analysis.id,
        question=analysis.question,
        response=analysis.response,
        toxic=analysis.toxic,
        date=analysis.date.isoformat() if analysis.date else None
    )

@router.delete("/moderation/audio/history/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analyzer).filter(
        Analyzer.id == analysis_id,
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio"
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse audio non trouvée.")

    db.delete(analysis)
    db.commit()
