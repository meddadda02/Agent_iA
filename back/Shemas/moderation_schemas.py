from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any

# Représente le texte à modérer	Entrée de /check_content
class TextInput(BaseModel):
    text: str
    model: str = "llama3-70b-8192"

class LanguageDetectionInput(BaseModel):
    text: str

class LanguageDetectionResponse(BaseModel):
    language: str
    dialect: str
    confidence_score: float
    detected_patterns: Dict[str, float]
    text_analysis: Dict[str, Any]

# Résultat complet d’une modération	Sortie de /check_content
class AudioAnalysis(BaseModel):
    music_detected: bool = False
    music_confidence: float = 0.0
    is_copyrighted: Optional[bool] = None
    copyright_status: str = "not_applicable"  # not_applicable, copyright_free, copyrighted, public_domain
    copyright_confidence: float = 0.0
    detected_genres: List[str] = []
    is_public_domain: bool = False
    
    # Détection de refrain
    refrain_detected: bool = False
    refrain_confidence: float = 0.0
    refrain_patterns: List[str] = []
    
    # Détection d'autotune
    autotune_detected: bool = False
    autotune_confidence: float = 0.0
    autotune_artifacts: List[Dict[str, Any]] = []
    
    # Analyse des paroles
    lyrics_analysis: Dict[str, Any] = {}
    lyrics_detected: bool = False
    lyrics_confidence: float = 0.0
    lyrics_copyrighted: Optional[bool] = None
    lyrics_copyright_confidence: float = 0.0
    lyrics_matches: List[Dict[str, Any]] = []  # Correspondances trouvées avec des paroles connues
    
    # Détails sur la source des paroles (si connue)
    lyrics_source: Optional[Dict[str, Any]] = None  # Informations sur la chanson originale
    
    class Config:
        json_schema_extra = {
            "example": {
                "music_detected": True,
                "music_confidence": 0.95,
                "is_copyrighted": True,
                "copyright_status": "copyrighted",
                "copyright_confidence": 0.92,
                "detected_genres": ["pop", "dance"],
                "is_public_domain": False,
                "refrain_detected": True,
                "refrain_confidence": 0.88,
                "refrain_patterns": ["chorus"],
                "autotune_detected": True,
                "autotune_confidence": 0.85,
                "autotune_artifacts": [{"type": "pitch_correction", "confidence": 0.9}]
            }
        }

class CombinedAudioModerationResponse(BaseModel):
    """Réponse combinée: modération du contenu (paroles) + modération audio (droits musique)."""
    content_moderation: Dict[str, Any]
    audio_moderation: 'MinimalAudioModerationResponse'

    class Config:
        json_schema_extra = {
            "example": {
                "content_moderation": {
                    "status": "conforme",
                    "bert": {"label": "toxic", "confidence": 0.9956},
                    "groq": {
                        "status": "conforme",
                        "category": "aucun",
                        "reasoning": "Expression familière/humoristique détectée (ex: 'what the fuck') dans un contexte non insultant.",
                        "is_insult": False
                    }
                },
                "audio_moderation": {
                    "status": "allowed",
                    "can_publish": True,
                    "message": "✅ Contenu approuvé pour publication",
                    "violated_rules": [],
                    "lyrics_analysis": {
                        "status": "allowed",
                        "toxic": False,
                        "categories": [],
                        "confidence": 0,
                        "flagged_text": "",
                        "recommendation": "Aucune action requise"
                    },
                    "copyright_analysis": {
                        "music_detected": False,
                        "title": None,
                        "artist": None,
                        "album": None,
                        "release_date": None,
                        "copyright_protected": False,
                        "confidence_score": 0,
                        "strike_risk_level": "low",
                        "recommendation": "Aucune musique protégée détectée par ACRCloud"
                    },
                    "automatic_action": "allow",
                    "copyrighted_segment": None
                }
            }
        }

class AudioModerationResponse(BaseModel):
    """Schéma dédié pour les réponses de modération AUDIO uniquement."""
    status: str = "success"  # success, error, warning
    message: str = ""
    violated_rules: List[str] = []
    automatic_action: str = "allow"  # allow, block, manual_review
    can_publish: bool = True
    youtube_report: Optional[str] = None
    copyright_strike_risk: bool = False
    copyright_analysis: Optional[Dict[str, Any]] = None
    audio_analysis: AudioAnalysis = AudioAnalysis()

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Analyse audio terminée",
                "violated_rules": [],
                "automatic_action": "allow",
                "can_publish": True,
                "youtube_report": None,
                "copyright_strike_risk": False,
                "copyright_analysis": {
                    "music_detected": True,
                    "confidence_score": 0.93,
                    "copyright_protected": False,
                    "title": "Exemple",
                    "artist": "Artiste"
                },
                "audio_analysis": {
                    "music_detected": True,
                    "music_confidence": 0.95,
                    "is_copyrighted": False,
                    "copyright_status": "copyright_free",
                    "copyright_confidence": 0.9,
                    "detected_genres": ["royalty_free"],
                    "is_public_domain": False
                }
            }
        }

class MinimalAudioModerationResponse(BaseModel):
    """Schéma minimal pour réponse de modération AUDIO (clair et visible)."""
    status: str
    can_publish: bool
    message: str
    violated_rules: List[str]
    lyrics_analysis: Dict[str, Any]
    copyright_analysis: Dict[str, Any]
    automatic_action: str
    # Optionnel: segment temporel de la partie potentiellement protégée
    copyrighted_segment: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "blocked",
                "can_publish": False,
                "message": "🚫 PUBLICATION BLOQUÉE: Contenu non conforme détecté dans l'audio.",
                "violated_rules": [
                    "Langage sexuellement explicite",
                    "Violation de droits d'auteur"
                ],
                "lyrics_analysis": {
                    "status": "blocked",
                    "toxic": True,
                    "categories": ["sexual_content", "offensive_language"],
                    "confidence": 0.97,
                    "flagged_text": "what the fuck i will put my dick in you",
                    "recommendation": "Supprimer ou reformuler les paroles."
                },
                "copyright_analysis": {
                    "music_detected": True,
                    "title": "God's Plan",
                    "artist": "Drake",
                    "album": "Scorpion",
                    "release_date": "2018-07-29",
                    "copyright_protected": True,
                    "confidence_score": 0.98,
                    "strike_risk_level": "high",
                    "recommendation": "Remplacer la musique ou obtenir une licence."
                },
                "automatic_action": "block"
            }
        }

# Résoudre les références directes différées (Pydantic v2)
try:
    CombinedAudioModerationResponse.model_rebuild()
except Exception:
    pass

class ContentCheckResponse(BaseModel):
    status: str = "success"  # success, error, warning
    bert: Optional[Dict[str, Any]] = {}
    groq: Optional[Dict[str, Any]] = {}
    message: str = ""
    processed_text: str = ""
    violated_rules: List[str] = []
    conflict_detected: bool = False
    detected_language: Optional[str] = None
    detected_dialect: Optional[str] = None
    # Champs AUDIO au niveau racine pour compatibilité avec ACRCloud et routes existantes
    music_detected: bool = False
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    release_date: Optional[str] = None
    label: Optional[str] = None
    platforms: Dict[str, Any] = {}
    confidence_score: float = 0.0
    strike_risk_level: str = "low"
    recommendation: Optional[str] = None
    is_public_domain: bool = False
    whitelist_match: bool = False
    
    copyright_strike_risk: bool = False
    copyright_analysis: Optional[Dict[str, Any]] = None
    audio_analysis: AudioAnalysis = AudioAnalysis()
    youtube_report: Optional[Dict[str, Any]] = None
    automatic_action: str = "allow"  # allow, block, manual_review
    can_publish: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "bert": {"label": "safe", "confidence": 0.95},
                "groq": {"status": "conforme", "reasoning": "Aucun contenu inapproprié détecté"},
                "message": "Analyse terminée avec succès",
                "detected_language": "fr",
                "detected_dialect": "standard",
                "copyright_strike_risk": False,
                "audio_analysis": {
                    "music_detected": True,
                    "music_confidence": 0.95,
                    "is_copyrighted": False,
                    "copyright_status": "copyright_free",
                    "copyright_confidence": 0.9,
                    "detected_genres": ["royalty_free"],
                    "is_public_domain": False
                },
                "automatic_action": "allow",
                "can_publish": True
            }
        }

class SupportedModelsResponse(BaseModel):
    models: List[str]

# Afficher une entrée de l’historique	/history
class ModerationHistoryResponse(BaseModel):
    id: int
    question: str
    response: Union[str, Dict[str, Any]]  # Accept string or dict
    toxic: Optional[bool] = None
    date: Optional[str] = None

# Afficher les modèles Groq disponibles
class ModelsResponse(BaseModel):
    models: List[str]

class UpdateQuestionInput(BaseModel):
    question: str

class MusicInfo(BaseModel):
    artist: str
    title: str
    album: Optional[str] = None
    release_date: Optional[str] = None
    label: Optional[str] = None
