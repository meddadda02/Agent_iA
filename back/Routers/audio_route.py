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
from Shemas.moderation_schemas import ContentCheckResponse, ModerationHistoryResponse, UpdateQuestionInput

router = APIRouter(tags=["Audio Moderation"])

@router.post("/moderation/audio", response_model=ContentCheckResponse)
async def moderate_audio_file(
    file: UploadFile = File(...),
    model: str = "llama3-70b-8192",
    langue: str = "",

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
    try:
        with open(tmp_path, "rb") as f:
            files = {
                "file": (file.filename, f, file.content_type or "audio/mpeg"),
            }
            data = {
                "model": "whisper-large-v3"
            }
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}"
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(GROQ_AUDIO_URL, data=data, files=files, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Erreur Groq Whisper: {response.status_code} - {response.text}")
            transcript = response.json().get("text", "").strip()
            # Normalisation stricte pour garantir cohérence audio/texte
            normalized_transcript = transcript.strip().lower()
            while normalized_transcript and normalized_transcript[-1] in ".!?":
                normalized_transcript = normalized_transcript[:-1]
            normalized_transcript = normalized_transcript.strip()

        # Utiliser la langue détectée ou choisie (paramètre 'langue')
        language = langue if langue else "fr"
        # Enregistrer la transcription dans l'historique comme question (pour cohérence avec l'analyse texte)

        # Ajout logique expressions familières/humoristiques
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
                "groq": {"status": "conforme", "reasoning": "Expression familière/humoristique détectée (ex: 'what the fuck') dans un contexte non insultant.", "category": "aucun"},
                "message": "Expression familière/humoristique détectée : le texte audio est conforme.",
                "processed_text": normalized_transcript,
                "violated_rules": [],
                "conflict_detected": False,
                "detected_language": language,
            }
        else:
            result = await ModerationService.check_content_comprehensive(
                text=normalized_transcript,
                model=model,
                db=db,
                user_id=current_user.id,
                language=language,
                entry_type="audio"
            )

        # Mettre à jour la dernière entrée Analyzer pour y ajouter le type 'audio' si besoin
        try:
            last_entry = db.query(Analyzer).filter(Analyzer.user_id == current_user.id).order_by(Analyzer.id.desc()).first()
            if last_entry and last_entry.question == transcript[:1000]:
                last_entry.type = "audio"
                db.add(last_entry)
                db.commit()
        except Exception as e:
            print(f"⚠️ Impossible de taguer l'entrée Analyzer comme audio : {e}")

        return ContentCheckResponse(**result)
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