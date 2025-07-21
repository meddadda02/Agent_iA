from typing import Optional
from pydantic import BaseModel

#stocker dans la base de données
class AnalyzerCreate(BaseModel):
    question: str
    response: str
    score: Optional[str] = None
    toxic: Optional[bool] = None
#Retourner une analyse avec ID et date	/history
class AnalyzerOut(BaseModel):
    id: int
    question: str
    response: str
    score: Optional[str] = None
    toxic: Optional[bool] = None
    date: Optional[str] = None

    class Config:
        from_attributes = True