from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import get_db
from dependencies import get_current_user
from Models.user_model import User
from Models.analyzer_model import Analyzer

from Services.moderation_service import ModerationService
from Shemas.moderation_schemas import TextInput, ContentCheckResponse, ModerationHistoryResponse, ModelsResponse
from sqlalchemy import select

router = APIRouter(tags=["Moderation"])

@router.get("/moderation/models", response_model=ModelsResponse)
async def get_available_models(current_user: User = Depends(get_current_user)):
  """Récupère les modèles disponibles pour l'analyse - Authentification requise"""
  return ModerationService.get_available_models()

@router.get("/moderation/rules")
async def get_moderation_rules(current_user: User = Depends(get_current_user)):
  """Endpoint pour consulter les règles de modération - Authentification requise"""
  return ModerationService.get_rules()

@router.get("/moderation/history")
async def get_moderation_history(
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  """Récupère l'historique des analyses de modération pour l'utilisateur actuel - Authentification requise"""
  try:
      # Attempt to query the database
      try:
          analyses = db.query(Analyzer).filter(Analyzer.user_id == current_user.id).order_by(Analyzer.date.desc()).all()
          print(f"Found {len(analyses)} analyses for user {current_user.id}")
      except Exception as db_e:
          print(f"❌ Erreur lors de l'exécution de la requête de base de données pour l'historique: {type(db_e).__name__}: {db_e}")
          raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'historique (problème de base de données)")

      response_data = []
      for analysis in analyses:
          try:
              response_data.append(
                  ModerationHistoryResponse(
                      id=analysis.id,
                      question=analysis.question,
                      response=analysis.response,
                      score=analysis.score,
                      toxic=analysis.toxic,
                      date=analysis.date.isoformat() if analysis.date else None
                  )
              )
          except Exception as inner_e:
              print(f"⚠️ Erreur lors du traitement de l'analyse ID {analysis.id} pour l'utilisateur {current_user.id}: {type(inner_e).__name__}: {inner_e}")
              # Continue to next analysis if one fails, rather than crashing the whole request
              continue 

      return response_data
  except HTTPException:
      # Re-raise HTTPException if it was already raised by the inner try-except
      raise
  except Exception as e:
      # Catch any other unexpected errors
      print(f"❌ Erreur inattendue lors de la récupération de l'historique: {type(e).__name__}: {e}")
      raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'historique")

@router.post("/moderation/check", response_model=ContentCheckResponse)
async def check_content(
  input_data: TextInput,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db)
):
  """Analyse le contenu pour détecter les violations des règles de modération - Authentification requise"""
  try:
      result = await ModerationService.check_content_comprehensive(
          text=input_data.text,
          model=input_data.model,
          db=db,
          user_id=current_user.id
      )

      return ContentCheckResponse(
          status=result["status"],
          bert=result["bert"],
          groq=result["groq"],
          message=result["message"],
          processed_text=result["processed_text"],
          violated_rules=result["violated_rules"],
          confidence_score=result["confidence_score"]
      )

  except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
      print(f"Erreur lors de l'analyse de contenu: {e}")
      raise HTTPException(status_code=500, detail="Erreur lors de l'analyse de contenu")
