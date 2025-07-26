from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
import os
import json
from datetime import datetime

from Services.yolo_service import analyze_with_yolo
from Services.llm_service import check_youtube_compatibility

from dependencies import get_current_user
from config import get_db
from Models.user_model import User
from Models.analyzer_model import Analyzer
from Shemas.moderation_schemas import ModerationHistoryResponse, UpdateQuestionInput
from Services.llm_service import LLMService


import asyncio
from Shemas.moderation_schemas import SupportedModelsResponse

router = APIRouter(tags=["Image Moderation"])


@router.get("/moderation/models-list", response_model=SupportedModelsResponse)
async def list_models(current_user: User = Depends(get_current_user)):
    """
    Récupère les modèles disponibles pour l'analyse - Authentification requise
    """
    return LLMService.get_available_models()

@router.post("/image/moderation/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyse une image et enregistre le résultat lié à l'utilisateur"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image.")

    image_bytes = await file.read()

    # Sauvegarde locale de l'image
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, filename)

    try:
        with open(file_path, "wb") as image_file:
            image_file.write(image_bytes)

        detections = analyze_with_yolo(image_bytes)
        compatibility_phrase = check_youtube_compatibility(detections)

        # Convertir la réponse en JSON string pour stockage
        compatibility_json = json.dumps(compatibility_phrase)

        new_analysis = Analyzer(
            user_id=current_user.id,
            question=filename,
            response=compatibility_json,
            toxic=False,
            type="image"
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

        return {
            "youtube_compatibility": compatibility_phrase,
            "analysis_id": new_analysis.id,
            "date": new_analysis.date.isoformat() if new_analysis.date else None,
            "filename": filename
        }

    except Exception as e:
        print(f"Erreur analyse image : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse de l'image")


@router.get("/image/moderation/history", response_model=List[ModerationHistoryResponse])
async def get_image_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'historique des analyses d'images de l'utilisateur"""
    analyses = db.query(Analyzer).filter(
        Analyzer.user_id == current_user.id,
        Analyzer.type == "image"
    ).order_by(Analyzer.date.desc()).all()

    return [
        ModerationHistoryResponse(
            id=a.id,
            question=a.question,
            response=json.loads(a.response) if a.response else None,
            toxic=a.toxic,
            date=a.date.isoformat() if a.date else None
        ) for a in analyses
    ]


@router.patch("/image/moderation/history/{analysis_id}", response_model=ModerationHistoryResponse)
async def update_image_analysis(
    analysis_id: int,
    update_data: UpdateQuestionInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met à jour la question d’une analyse d’image (authentifié et propriétaire)"""
    analysis = db.query(Analyzer).filter(
        Analyzer.id == analysis_id,
        Analyzer.user_id == current_user.id,
        Analyzer.type == "image"
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse non trouvée.")

    analysis.question = update_data.question
    db.commit()
    db.refresh(analysis)

    return ModerationHistoryResponse(
        id=analysis.id,
        question=analysis.question,
        response=json.loads(analysis.response) if analysis.response else None,
        toxic=analysis.toxic,
        date=analysis.date.isoformat() if analysis.date else None
    )


@router.delete("/image/moderation/history/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime une analyse d'image spécifique"""
    analysis = db.query(Analyzer).filter(
        Analyzer.id == analysis_id,
        Analyzer.user_id == current_user.id,
        Analyzer.type == "image"
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse non trouvée.")

    db.delete(analysis)
    db.commit()
    return {"message": "Analyse image supprimée avec succès"}
