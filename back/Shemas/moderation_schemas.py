from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any

# Représente le texte à modérer	Entrée de /check_content
class TextInput(BaseModel):
    text: str
    model: str = "llama3-70b-8192"
    language: str = "fr"  # Ajout du champ facultatif pour la langue ("fr", "en", "ar", "dialecte")

# Résultat complet d’une modération	Sortie de /check_content
class ContentCheckResponse(BaseModel):
    status: str
    bert: dict
    groq: dict
    message: str
    processed_text: str
    violated_rules: List[str]
    conflict_detected: Optional[bool] = False  # Nouveau champ pour indiquer les conflits

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
