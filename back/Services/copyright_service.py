from typing import Dict, List, Any, Optional
from Services.acrcloud_service import ACRCloudService
import asyncio
from enum import Enum
from groq import Groq
import os
import json
import tempfile

class CopyrightAction(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    MUTE_AUDIO = "mute_audio"
    MONETIZE_DISABLE = "monetize_disable"

class CopyrightService:
    def __init__(self):
        self.acrcloud_service = ACRCloudService()
        self.risk_thresholds = {
            "confidence_critical": 0.85,
            "confidence_high": 0.75,
            "confidence_medium": 0.60,
            "confidence_low": 0.45,
            "platforms_critical": 4,
            "platforms_high": 3,
            "platforms_medium": 2,
            "score_minimum": 70,
            "score_warning": 50
        }
        self.youtube_risk_labels = {
            "none": "✅ SÉCURISÉ",
            "low": "⚠️ SURVEILLANCE",
            "medium": "🔶 ATTENTION",
            "high": "🚫 RISQUE ÉLEVÉ",
            "critical": "❌ BLOCAGE"
        }
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def youtube_style_copyright_check(self, file_path: str, file_type: str, user_id: int) -> Dict[str, Any]:
        """Vérifie le copyright dans un style YouTube."""
        print(f"🔍 [YouTube-Protection] Vérification copyright pour {file_type}: {file_path}")
        base_result = await self.comprehensive_copyright_check(file_path, file_type)
        content_type = self._detect_content_type(base_result)
        print(f" Type de contenu détecté: {content_type}")
        action_result = self._determine_youtube_safe_action(base_result, file_type)
        
        # Si ACRCloud échoue mais la transcription est indisponible, tenter une seconde analyse
        if base_result.get("status") == "error" and file_type == "audio":
            print(" Tentative de réanalyse avec un segment différent")
            temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_wav.close()
            try:
                if await self.acrcloud_service._convert_to_wav(file_path, temp_wav.name, duration_limit=15):
                    base_result = await self.acrcloud_service.recognize_audio(temp_wav.name)
                    content_type = self._detect_content_type(base_result)
                    action_result = self._determine_youtube_safe_action(base_result, file_type)
            finally:
                try:
                    os.remove(temp_wav.name)
                except Exception as e:
                    print(f"⚠️ Erreur suppression fichier temporaire {temp_wav.name}: {e}")

        final_report = {
            **base_result,
            "automatic_action": action_result["action"],
            "action_reason": action_result["reason"],
            "user_options": action_result["user_options"],
            "youtube_style_response": action_result["youtube_response"],
            "can_publish": action_result["can_publish"],
            "requires_user_action": action_result["requires_user_action"],
            "content_type": content_type,
            "youtube_safety_score": action_result["safety_score"],
            "strike_prevention": action_result["strike_prevention"]
        }
        
        print(f"✅ [YouTube-Protection] Action: {action_result['action']} - Sécurité: {action_result.get('safety_score', 'N/A')}%")
        return final_report
    
    def _detect_content_type(self, copyright_result: Dict) -> str:
        """Détermine si le contenu est de la musique ou de la parole."""
        if copyright_result.get("status") == "error":
            print(" Erreur dans la détection, type par défaut: speech")
            return "speech"
        
        music_detected = copyright_result.get("music_detected", False)
        confidence = copyright_result.get("confidence_score", 0.0)
        music_info = copyright_result.get("music_info", {})
        platforms = copyright_result.get("platforms", {})

        # Validation renforcée pour éviter les faux négatifs
        if music_detected and confidence >= self.risk_thresholds["confidence_low"]:
            if music_info.get("title") and music_info.get("artist"):
                print(f" Musique détectée avec confiance {confidence:.1%}: {music_info.get('artist')} - {music_info.get('title')}")
                return "music"
            elif confidence >= self.risk_thresholds["confidence_medium"] or len(platforms) >= 2:
                print(f" Probabilité de musique (confiance: {confidence:.1%}, plateformes: {len(platforms)})")
                return "music"
        
        print(" Contenu détecté comme non musical")
        return "speech"

    def _determine_youtube_safe_action(self, copyright_result: Dict, file_type: str) -> Dict[str, Any]:
        """Détermine l'action à prendre pour la sécurité YouTube."""
        if copyright_result.get("status") == "error":
            print(" Vérification incomplète, action par défaut: WARN")
            return {
                "action": CopyrightAction.WARN.value,
                "reason": "Vérification copyright incomplète - surveillance recommandée par précaution",
                "can_publish": True,
                "requires_user_action": False,
                "safety_score": 70,
                "strike_prevention": True,
                "user_options": ["Réessayer la vérification", "Vérification manuelle", "Remplacer le contenu"],
                "youtube_response": "⚠️ Vérification incomplète - Publication autorisée avec surveillance renforcée."
            }
        
        if not copyright_result.get("copyright_detected", False):
            print(" Aucun contenu protégé détecté")
            return {
                "action": CopyrightAction.ALLOW.value,
                "reason": "Aucun contenu protégé détecté - Publication sécurisée",
                "can_publish": True,
                "requires_user_action": False,
                "safety_score": 100,
                "strike_prevention": False,
                "user_options": [],
                "youtube_response": "✅ Contenu libre de droits - Publication sécurisée pour YouTube."
            }
        
        confidence = copyright_result.get("confidence_score", 0.0)
        platforms = copyright_result.get("platforms", [])
        music_info = copyright_result.get("music_info", {})
        
        if confidence >= self.risk_thresholds["confidence_critical"] and len(platforms) >= self.risk_thresholds["platforms_critical"]:
            print(f" Risque critique détecté (confiance: {confidence:.1%}, plateformes: {len(platforms)})")
            return {
                "action": CopyrightAction.BLOCK.value,
                "reason": f"Risque de strike YouTube très élevé - Musique protégée identifiée avec certitude ({confidence:.1%})",
                "can_publish": False,
                "requires_user_action": True,
                "safety_score": 0,
                "strike_prevention": True,
                "user_options": [
                    "Remplacer par de la musique libre de droits",
                    "Obtenir une licence d'utilisation",
                    "Supprimer la partie audio",
                    "Faire appel de cette décision"
                ],
                "youtube_response": f"🚫 PUBLICATION BLOQUÉE: Risque de strike YouTube très élevé. Musique protégée: {music_info.get('artist', 'Artiste inconnu')} - {music_info.get('title', 'Titre inconnu')}"
            }
        
        elif confidence >= self.risk_thresholds["confidence_high"] or len(platforms) >= self.risk_thresholds["platforms_high"]:
            print(f" Risque modéré détecté (confiance: {confidence:.1%}, plateformes: {len(platforms)})")
            return {
                "action": CopyrightAction.WARN.value,
                "reason": f"Risque de strike YouTube modéré - Musique potentiellement protégée ({confidence:.1%})",
                "can_publish": True,
                "requires_user_action": False,
                "safety_score": 30,
                "strike_prevention": True,
                "user_options": [
                    "Publier avec surveillance renforcée",
                    "Remplacer le contenu par précaution",
                    "Demander une vérification manuelle"
                ],
                "youtube_response": f"⚠️ RISQUE MODÉRÉ: Publication autorisée mais surveillée. Confiance: {confidence:.1%}"
            }
        
        elif confidence >= self.risk_thresholds["confidence_medium"]:
            print(f" Risque moyen détecté (confiance: {confidence:.1%})")
            return {
                "action": CopyrightAction.WARN.value,
                "reason": f"Surveillance recommandée - Détection de contenu potentiellement protégé ({confidence:.1%})",
                "can_publish": True,
                "requires_user_action": False,
                "safety_score": 50,
                "strike_prevention": True,
                "user_options": [
                    "Publier avec surveillance",
                    "Remplacer le contenu par précaution"
                ],
                "youtube_response": f"⚠️ Surveillance recommandée: Contenu potentiellement protégé détecté."
            }
        
        else:
            print(f" Risque faible détecté (confiance: {confidence:.1%})")
            return {
                "action": CopyrightAction.ALLOW.value,
                "reason": f"Détection de contenu à faible risque ({confidence:.1%})",
                "can_publish": True,
                "requires_user_action": False,
                "safety_score": 80,
                "strike_prevention": False,
                "user_options": [],
                "youtube_response": "✅ Contenu à faible risque - Publication autorisée."
            }

    def generate_youtube_style_report(self, results: Dict) -> Dict[str, Any]:
        """Génère un rapport style YouTube."""
        safety_score = results.get("youtube_safety_score", 0)
        risk_level = self._calculate_risk_level(safety_score)
        return {
            "risk_level": risk_level,
            "youtube_advice": self._generate_youtube_advice(results),
            "alternatives": self._generate_alternatives(results),
            "details": {
                "confidence": results.get("confidence_score", 0.0),
                "platforms_detected": list(results.get("platforms", {}).keys()),
                "content_type": results.get("content_type", "unknown"),
                "music_info": results.get("music_info", {})
            }
        }

    def _calculate_risk_level(self, safety_score: int) -> str:
        """Calcule le niveau de risque."""
        if safety_score >= 90:
            return "none"
        elif safety_score >= 70:
            return "low"
        elif safety_score >= 40:
            return "medium"
        else:
            return "high"

    def _generate_youtube_advice(self, results: Dict) -> List[str]:
        """Génère des conseils pour YouTube."""
        advice = []
        safety_score = results.get("youtube_safety_score", 0)
        if safety_score < 50:
            advice.extend([
                "🚫 Évitez de publier ce contenu sur YouTube",
                "⚠️ Risque élevé de réclamation de droits d'auteur",
                "📉 Votre chaîne pourrait recevoir un strike"
            ])
        elif safety_score < 80:
            advice.extend([
                "⚠️ Publiez avec prudence sur YouTube",
                "📊 Surveillez les métriques après publication",
                "🔔 Préparez-vous à répondre aux réclamations"
            ])
        else:
            advice.extend([
                "✅ Contenu sûr pour YouTube",
                "🎉 Publication sans restriction",
                "💚 Aucune action supplémentaire requise"
            ])
        return advice

    def _generate_alternatives(self, results: Dict) -> List[str]:
        """Propose des alternatives pour éviter les violations de copyright."""
        return [
            "🎼 YouTube Audio Library (musique libre)",
            "🎵 Epidemic Sound (licence commerciale)",
            "🎤 Enregistrement audio original",
            "🔇 Version sans audio",
            "✂️ Édition pour supprimer la musique"
        ]

    async def comprehensive_copyright_check(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Effectue une vérification complète du copyright."""
        print(f" Début vérification copyright pour {file_type}: {file_path}")
        if file_type == "audio":
            result = await self.acrcloud_service.recognize_audio(file_path)
        else:
            result = await self.acrcloud_service.check_video_copyright(file_path)
        
        # Validation des résultats
        if result.get("status") == "error":
            print(f" Erreur ACRCloud: {result.get('message', 'Erreur inconnue')}")
            return {
                "status": "error",
                "copyright_detected": False,
                "confidence_score": 0.0,
                "music_info": {},
                "platforms": {},
                "message": result.get("message", "Erreur lors de la vérification du copyright"),
                "music_detected": False,
                "title": None,
                "artist": None,
                "album": None,
                "release_date": None,
                "label": None,
                "copyright_protected": False,
                "strike_risk_level": "low",
                "recommendation": "Vérification manuelle recommandée"
            }
        
        # Vérification de la cohérence des métadonnées
        music_detected = result.get("music_detected", False)
        confidence = result.get("confidence_score", 0.0)
        music_info = result.get("music_info", {})
        if music_detected and (not music_info.get("title") or not music_info.get("artist")):
            print(f" Métadonnées incomplètes: {music_info}")
            music_detected = False
            confidence = 0.0
            result["music_detected"] = False
            result["copyright_protected"] = False
            result["strike_risk_level"] = "low"
            result["recommendation"] = "Vérification manuelle recommandée"

        print(f" Résultat vérification: music_detected={music_detected}, confidence={confidence:.1%}")
        
        # Préparer l'objet de réponse
        response = {
            "status": "success",
            "copyright_detected": music_detected and result.get("copyright_protected", False),
            "confidence_score": confidence,
            "music_info": {
                "title": result.get("title"),
                "artist": result.get("artist"),
                "album": result.get("album"),
                "release_date": result.get("release_date"),
                "label": result.get("label")
            },
            "platforms": result.get("platforms", {}),
            "music_detected": music_detected,
            "title": result.get("title"),
            "artist": result.get("artist"),
            "album": result.get("album"),
            "release_date": result.get("release_date"),
            "label": result.get("label"),
            "copyright_protected": result.get("copyright_protected", False),
            "strike_risk_level": result.get("strike_risk_level", "low"),
            "recommendation": result.get("recommendation", "Aucune action requise"),
            "is_public_domain": result.get("is_public_domain", False),
            "whitelist_match": result.get("whitelist_match", False),
            "audio_analysis": {
                "music_detected": music_detected,
                "music_confidence": confidence,
                "is_copyrighted": result.get("copyright_protected", False),
                "copyright_status": "copyrighted" if result.get("copyright_protected") else "copyright_free",
                "copyright_confidence": confidence,
                "detected_genres": result.get("audio_analysis", {}).get("detected_genres", []),
                "is_public_domain": result.get("is_public_domain", False),
                "refrain_detected": result.get("audio_analysis", {}).get("refrain_detected", False),
                "refrain_confidence": result.get("audio_analysis", {}).get("refrain_confidence", 0.0),
                "refrain_patterns": result.get("audio_analysis", {}).get("refrain_patterns", []),
                "autotune_detected": result.get("audio_analysis", {}).get("autotune_detected", False),
                "autotune_confidence": result.get("audio_analysis", {}).get("autotune_confidence", 0.0),
                "autotune_artifacts": result.get("audio_analysis", {}).get("autotune_artifacts", [])
            }
        }
        
        # Si l'analyse audio contient des genres, les ajouter
        if "audio_analysis" in result and "detected_genres" in result["audio_analysis"]:
            response["audio_analysis"]["detected_genres"] = result["audio_analysis"]["detected_genres"]
        
        print(f" Réponse finale avec analyse audio: {json.dumps(response, indent=2, ensure_ascii=False)[:500]}...")
        return response

    async def analyze_text_for_music(self, text: str) -> Dict[str, Any]:
        """
        Analyse le texte pour détecter des paroles de chanson et vérifier leur statut de copyright.
        
        Args:
            text: Texte à analyser (peut être une transcription vocale ou tout autre texte)
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse, y compris la détection de musique,
            les informations sur les droits d'auteur et l'analyse des paroles.
        """
        if not text or not text.strip():
            return {
                "status": "success",
                "music_detected": False,
                "title": None,
                "artist": None,
                "album": None,
                "release_date": None,
                "label": None,
                "copyright_protected": False,
                "platforms": {},
                "confidence_score": 0.0,
                "strike_risk_level": "low",
                "recommendation": "Aucun texte à analyser",
                "lyrics_analysis": {
                    "lyrics_detected": False,
                    "lyrics_confidence": 0.0,
                    "lyrics_copyrighted": False,
                    "lyrics_copyright_confidence": 0.0,
                    "lyrics_matches": [],
                    "lyrics_source": None
                }
            }

        # Nettoyage et préparation du texte
        cleaned_text = text.strip().lower()
        words = cleaned_text.split()
        unique_words = set(words)
        
        # Paramètres pour la détection des paroles
        min_words = 10  # Nombre minimum de mots pour l'analyse
        min_unique_words = 5  # Nombre minimum de mots uniques pour éviter la répétition
        
        # Structure de base de la réponse avec analyse des paroles
        base_response = {
            "status": "success",
            "music_detected": False,
            "title": None,
            "artist": None,
            "album": None,
            "release_date": None,
            "label": None,
            "copyright_protected": False,
            "platforms": {},
            "confidence_score": 0.0,
            "strike_risk_level": "low",
            "recommendation": "Aucune action requise",
            "lyrics_analysis": {
                "lyrics_detected": False,
                "lyrics_confidence": 0.0,
                "lyrics_copyrighted": False,
                "lyrics_copyright_confidence": 0.0,
                "lyrics_matches": [],
                "lyrics_source": None,
                "lyrics_fragments": [],
                "lyrics_originality_score": 0.0
            }
        }
        
        # Vérification de la longueur du texte
        if len(words) < min_words or len(unique_words) < min_unique_words:
            print(f" Texte trop court ou répétitif pour être des paroles ({len(words)} mots, {len(unique_words)} uniques)")
            base_response["lyrics_analysis"]["lyrics_confidence"] = 0.1  # Très faible confiance
            base_response["lyrics_analysis"]["recommendation"] = "Texte trop court pour une analyse fiable des paroles"
            return base_response
        
        # Mots courants qui ne devraient pas déclencher la détection de copyright
        common_words = {
            # Mots de base
            'the', 'and', 'or', 'but', 'if', 'because', 'as', 'until', 'while', 'of', 
            'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in',
            'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
            
            # Salutations et expressions courantes
            'hello', 'hi', 'hey', 'goodbye', 'bye', 'good', 'morning', 'afternoon', 'evening',
            'night', 'day', 'time', 'today', 'yesterday', 'tomorrow', 'now', 'later', 'soon',
            'please', 'thank', 'thanks', 'sorry', 'excuse', 'pardon', 'welcome', 'well',
            
            # Pronoms et déterminants
            'i', 'me', 'my', 'myself', 'we', 'us', 'our', 'ours', 'ourselves', 'you', 'your',
            'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her',
            'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            
            # Verbes courants
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
            'do', 'does', 'did', 'doing', 'can', 'could', 'may', 'might', 'must', 'shall',
            'should', 'will', 'would', 'get', 'got', 'gotten', 'make', 'made', 'take', 'took',
            'taken', 'see', 'saw', 'seen', 'come', 'came', 'go', 'went', 'gone', 'know', 'knew',
            'known', 'think', 'thought', 'want', 'wanted', 'look', 'looked', 'use', 'used', 'find',
            'found', 'give', 'gave', 'given', 'tell', 'told', 'work', 'worked', 'call', 'called',
            'try', 'tried', 'ask', 'asked', 'need', 'needed', 'feel', 'felt', 'become', 'became',
            'leave', 'left', 'put', 'put', 'mean', 'meant', 'keep', 'kept', 'let', 'let', 'begin',
            'began', 'begun', 'seem', 'seemed', 'help', 'helped', 'show', 'showed', 'shown',
            'hear', 'heard', 'play', 'played', 'run', 'ran', 'move', 'moved'
        }
        
        # Calcul du ratio de mots courants et analyse de la structure du texte
        common_word_ratio = sum(1 for word in words if word in common_words) / len(words)
        unique_word_ratio = len(set(words)) / len(words) if words else 0
        
        # Détection de motifs de paroles (vers, refrains, etc.)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        repeated_lines = [line for line in set(lines) if lines.count(line) > 1]
        has_repeated_lines = len(repeated_lines) > 0
        
        # Analyse préliminaire pour déterminer la probabilité de paroles
        is_likely_lyrics = (
            len(words) >= 20 and  # Longueur minimale
            unique_word_ratio > 0.5 and  # Évite les répétitions excessives
            (has_repeated_lines or len(lines) >= 3)  # Structure de chanson ou plusieurs lignes
        )
        
        # Ajustement de la confiance en fonction des caractéristiques du texte
        base_lyrics_confidence = 0.0
        if is_likely_lyrics:
            base_lyrics_confidence = min(0.7, 0.3 + (unique_word_ratio * 0.4))
            if has_repeated_lines:
                base_lyrics_confidence = min(0.9, base_lyrics_confidence + 0.2)
        
        print(f" Analyse préliminaire - Mots uniques: {unique_word_ratio:.1%}, "
              f"Lignes répétées: {len(repeated_lines)}, Confiance: {base_lyrics_confidence:.1f}")
        
        # Si le texte est principalement composé de mots courants, réduire la confiance
        if common_word_ratio > 0.7:
            print(f" Texte composé principalement de mots communs ({common_word_ratio:.1%}), réduction de confiance")
            base_lyrics_confidence = max(0.0, base_lyrics_confidence - 0.3)
        
        # Si la confiance est trop faible, éviter d'appeler l'API inutilement
        if base_lyrics_confidence < 0.3 and len(words) < 30:
            print(" Confiance trop faible, texte probablement pas des paroles")
            base_response["lyrics_analysis"].update({
                "lyrics_detected": False,
                "lyrics_confidence": base_lyrics_confidence,
                "lyrics_copyrighted": False,
                "recommendation": "Contenu probablement pas des paroles de chanson"
            })
            return base_response
        
        print(f"🎵 [Copyright] Analyse de texte pour détection musicale: '{text[:50]}...'")
        
        try:
            # Préparation du prompt pour l'analyse des paroles
            system_prompt = (
                "You are an expert in music lyrics detection and copyright analysis. Your task is to analyze the given text "
                "and determine if it contains song lyrics, and if so, whether they are likely to be copyrighted.\n\n"
                "GUIDELINES:\n"
                "1. LYRIC DETECTION:\n"
                "   - Look for distinctive, creative, and specific lyrical content\n"
                "   - Check for poetic elements, rhyme schemes, or song structure (verse/chorus/bridge)\n"
                "   - Be cautious with generic phrases that could be coincidental\n\n"
                "2. COPYRIGHT ANALYSIS:\n"
                "   - If lyrics are detected, determine if they match known songs\n"
                "   - Consider the uniqueness and distinctiveness of the lyrics\n"
                "   - Common phrases or very short excerpts may not be copyrightable\n\n"
                "3. RESPONSE FORMAT:\n"
                "   - music_detected: boolean (true if lyrics are detected)\n"
                "   - lyrics_confidence: float (0-1, confidence in lyric detection)\n"
                "   - lyrics_copyrighted: boolean (true if lyrics match known copyrighted material)\n"
                "   - lyrics_originality_score: float (0-1, how original/unique the lyrics are)\n"
                "   - potential_matches: array of {title, artist, confidence} (if known songs match)\n"
                "   - recommendation: string (suggested action based on analysis)\n"
                "   - analysis_notes: string (brief explanation of the findings)"
            )
            
            user_prompt = (
                f"TEXT TO ANALYZE:\n{text}\n\n"
                "ANALYSIS REQUESTED:\n"
                "1. Does this text contain song lyrics?\n"
                "2. If yes, are these lyrics likely to be from a known/copyrighted song?\n"
                "3. What is your confidence in this assessment?\n\n"
                "Please provide a detailed analysis in JSON format."
            )
            
            # Appel à l'API Groq pour l'analyse des paroles
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama3-70b-8192",
                response_format={"type": "json_object"},
                temperature=0.3,  # Pour des résultats plus déterministes
                max_tokens=1000
            )
            
            # Traitement de la réponse de l'API
            detected_info = json.loads(response.choices[0].message.content)
            
            # Extraction des informations sur les paroles
            lyrics_detected = detected_info.get("lyrics_detected", False)
            lyrics_confidence = float(detected_info.get("lyrics_confidence", 0.0))
            lyrics_copyrighted = detected_info.get("lyrics_copyrighted", False)
            lyrics_originality = float(detected_info.get("lyrics_originality_score", 0.0))
            potential_matches = detected_info.get("potential_matches", [])
            
            # Déterminer le statut global et l'action automatique
            is_blocked = lyrics_copyrighted  # Bloquer si paroles protégées par copyright
            
            # Préparer l'analyse des paroles détaillée
            lyrics_analysis = {
                "status": "blocked" if lyrics_copyrighted else "allowed",
                "toxic": detected_info.get("is_toxic", False),
                "categories": detected_info.get("toxic_categories", []),
                "confidence": lyrics_confidence,
                "flagged_text": detected_info.get("flagged_text", "") if lyrics_copyrighted else "",
                "recommendation": detected_info.get("recommendation", "Supprimer ou reformuler les paroles." if lyrics_copyrighted else "Aucune action requise")
            }
            
            # Préparer l'analyse des droits d'auteur
            copyright_analysis = {
                "music_detected": lyrics_detected,
                "title": detected_info.get("title"),
                "artist": detected_info.get("artist"),
                "album": detected_info.get("album"),
                "release_date": detected_info.get("release_date"),
                "copyright_protected": lyrics_copyrighted,
                "confidence_score": lyrics_confidence,
                "strike_risk_level": "high" if lyrics_copyrighted else "low",
                "recommendation": detected_info.get("recommendation", "Remplacer la musique ou obtenir une licence." if lyrics_copyrighted else "Aucune action requise.")
            }
            
            # Construire la réponse complète avec analyse des paroles et droits d'auteur
            is_blocked = lyrics_copyrighted or lyrics_analysis.get("toxic", False)
            
            base_response = {
                "status": "blocked" if is_blocked else "allowed",
                "can_publish": not is_blocked,
                "message": "🚫 PUBLICATION BLOQUÉE: Contenu non conforme détecté dans l'audio." if is_blocked 
                          else "✅ Contenu approuvé pour publication",
                "violated_rules": [],
                "lyrics_analysis": lyrics_analysis,
                "copyright_analysis": {
                    "music_detected": lyrics_detected,
                    "title": detected_info.get("title"),
                    "artist": detected_info.get("artist"),
                    "album": detected_info.get("album"),
                    "release_date": detected_info.get("release_date"),
                    "copyright_protected": lyrics_copyrighted,
                    "confidence_score": lyrics_confidence,
                    "strike_risk_level": "high" if lyrics_copyrighted else "low",
                    "recommendation": detected_info.get("recommendation", "Remplacer la musique ou obtenir une licence." if lyrics_copyrighted else "Aucune action requise.")
                },
                "automatic_action": "block" if is_blocked else "allow"
            }
            
            # Ajouter les règles violées
            if lyrics_analysis.get("toxic"):
                category_map = {
                    "sexual_content": "Langage sexuellement explicite",
                    "offensive_language": "Langage offensant",
                    "hate_speech": "Discours haineux",
                    "violence": "Violence",
                    "self_harm": "Incitation à l'automutilation",
                    "drugs": "Promotion de drogues",
                    "harassment": "Harcèlement"
                }
                mapped = [category_map.get(cat, cat) for cat in lyrics_analysis.get("categories", [])]
                base_response["violated_rules"].extend(mapped)
            if lyrics_copyrighted:
                base_response["violated_rules"].append("Violation de droits d'auteur")
            
            # Journalisation des résultats pour le débogage
            print(f" Analyse des paroles terminée - Détecté: {lyrics_detected}, "
                  f"Copyright: {lyrics_copyrighted}, Confiance: {lyrics_confidence:.2f}")
            
            print(f"🎵 [Copyright] Résultat LLM: {detected_info}")
            return base_response
            
        except Exception as e:
            print(f"⚠️ [Copyright] Erreur lors de l'analyse de texte: {e}")
            return {
                "status": "error",
                "music_detected": False,
                "title": None,
                "artist": None,
                "album": None,
                "release_date": None,
                "label": None,
                "copyright_protected": False,
                "platforms": {},
                "confidence_score": 0.0,
                "strike_risk_level": "low",
                "recommendation": "Vérification manuelle recommandée"
            }
