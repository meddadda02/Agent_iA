from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
import os, json, shutil
from datetime import datetime

from Services.video_service import analyze_video_full
from dependencies import get_current_user
from config import get_db
from Models.user_model import User
from Models.analyzer_model import Analyzer
from Shemas.moderation_schemas import ModerationHistoryResponse, UpdateQuestionInput

router = APIRouter(prefix="/video/moderation", tags=["Video Moderation"])

@router.post("/analyze")
async def analyze_video_route(
    file: UploadFile = File(...),
    model: str = "llama3-70b-8192",
    langue: str = "",  # "", "fr", "en", "ar", "auto"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze video: frames (YOLO), audio (Whisper→moderation), subtitles (ffmpeg→moderation)."""
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une vidéo.")

    # Persist upload to disk (temp)
    os.makedirs("uploads", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    path = os.path.join("uploads", filename)

    with open(path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        # Full multimodal analysis
        report = await analyze_video_full(
            video_path=path,
            db=db,
            user_id=current_user.id,
            model=model,
            interval_ms=200,
            language_hint=langue
        )

        # Toxicity from text moderation (visual can be integrated in the future rule mapping)
        is_toxic = bool(report.get("summary", {}).get("toxic"))

        # Store in DB (Analyzer.response = JSON string)
        record = Analyzer(
            user_id=current_user.id,
            question=filename,                       # keep filename as "question"
            response=json.dumps(report, ensure_ascii=False),
            toxic=is_toxic,
            type="video"
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "analysis_id": record.id,
            "date": record.date.isoformat() if record.date else None,
            "filename": filename,
            "youtube_compatibility": None,  # kept for backward compat; you can compute from report if desired
            "report": report
        }
    finally:
        # Cleanup
        try:
            os.remove(path)
        except Exception:
            pass


@router.get("/history", response_model=List[ModerationHistoryResponse])
async def get_video_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
