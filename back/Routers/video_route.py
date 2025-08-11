from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
import os, json, shutil, uuid
from datetime import datetime

from Services.video_service import analyze_video
from Services.llm_service import check_youtube_compatibility
from dependencies import get_current_user
from config import get_db
from Models.user_model import User
from Models.analyzer_model import Analyzer
from Shemas.moderation_schemas import ModerationHistoryResponse, UpdateQuestionInput

router = APIRouter(prefix="/video/moderation", tags=["Video Moderation"])

@router.post("/analyze")
async def analyze_video_route(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyse une vidéo, enregistre le rapport et renvoie la compatibilité YouTube"""
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une vidéo.")

    # Sauvegarde locale
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", filename)
    with open(path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # Analyse vidéo + rapport détaillé
    video_report = analyze_video(path)
    # Génère une phrase de compatibilité à partir du rapport
    compatibility_phrase = check_youtube_compatibility(video_report)

    # Stockage en base
    record = Analyzer(
        user_id=current_user.id,
        question=filename,             # on stocke le nom du fichier comme "question"
        response=json.dumps(video_report),
        toxic=False,
        type="video"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Cleanup du fichier uploadé
    os.remove(path)

    return {
        "youtube_compatibility": compatibility_phrase,
        "analysis_id": record.id,
        "date": record.date.isoformat() if record.date else None,
        "filename": filename
    }

@router.get("/history", response_model=List[ModerationHistoryResponse])
async def get_video_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retourne l’historique des analyses vidéo de l’utilisateur"""
    analyses = (
        db.query(Analyzer)
          .filter(Analyzer.user_id == current_user.id, Analyzer.type == "video")
          .order_by(Analyzer.date.desc())
          .all()
    )
    return [
        ModerationHistoryResponse(
            id=a.id,
            question=a.question,
            response=json.loads(a.response) if a.response else None,
            toxic=a.toxic,
            date=a.date.isoformat() if a.date else None
        )
        for a in analyses
    ]

@router.patch("/history/{analysis_id}", response_model=ModerationHistoryResponse)
async def update_video_analysis(
    analysis_id: int,
    update_data: UpdateQuestionInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met à jour le champ question (filename) d’une analyse vidéo existante"""
    analysis = (
        db.query(Analyzer)
          .filter(
              Analyzer.id == analysis_id,
              Analyzer.user_id == current_user.id,
              Analyzer.type == "video"
          )
          .first()
    )
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

@router.delete("/history/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime une analyse vidéo de l’historique"""
    analysis = (
        db.query(Analyzer)
          .filter(
              Analyzer.id == analysis_id,
              Analyzer.user_id == current_user.id,
              Analyzer.type == "video"
          )
          .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse non trouvée.")
    db.delete(analysis)
    db.commit()
    return {"message": "Analyse vidéo supprimée avec succès"}
