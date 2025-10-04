# back/Routers/suggestion_route.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from Models.user_model import User
from dependencies import get_current_user
from Services.suggestion_service import generate_suggestions

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])

class SuggestRequest(BaseModel):
    rule_id: str
    rule_title: str
    violated_text: str
    language: str = "fr"

@router.post("/for-violation")
async def get_suggestions(req: SuggestRequest, current_user: User = Depends(get_current_user)):
    result = generate_suggestions(
        rule_id=req.rule_id,
        rule_title=req.rule_title,
        violated_text=req.violated_text,
        language=req.language,
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
