from pydantic import BaseModel
from typing import List, Optional

#Représente le texte à modérer	Entrée de /check_content
class TextInput(BaseModel):
    text: str
    model: str = "llama3-8b-8192"
#Résultat complet d’une modération	Sortie de /check_content
class ContentCheckResponse(BaseModel):
    status: str
    bert: dict
    groq: dict
    message: str
    processed_text: str
    violated_rules: List[str]
    confidence_score: float

#Afficher une entrée de l’historique	/history
class ModerationHistoryResponse(BaseModel):
    id: int
    question: str
    response: str
    score: Optional[str] = None
    toxic: Optional[bool] = None
    date: Optional[str] = None

#Afficher les modèles Groq disponibles
class ModelsResponse(BaseModel):
    models: List[str]
