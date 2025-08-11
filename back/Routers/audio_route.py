from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import tempfile
import os
from config import get_db
from dependencies import get_current_user
from Models.user_model import User
from Models.analyzer_model import Analyzer
from groq import Groq
from Services.moderation_service import ModerationService
from Shemas.moderation_schemas import ContentCheckResponse, ModerationHistoryResponse, UpdateQuestionInput

router = APIRouter(tags=["Audio Moderation"])

@router.post("/moderation/audio", response_model=ContentCheckResponse)
async def moderate_audio_file(
    file: UploadFile = File(...),
    model: str = "llama3-70b-8192",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith((".mp3", ".wav", ".m4a")):
        raise HTTPException(status_code=400, detail="Seuls les fichiers audio mp3, wav, m4a sont autorisés.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=(file.filename, f.read())
            )
        transcript = transcription.text.strip()

        result = await ModerationService.check_content_comprehensive(
            text=transcript,
            model=model,
            db=db,
            user_id=current_user.id
        )

        return ContentCheckResponse(**result)
    finally:
        os.remove(tmp_path)

@router.get("/moderation/audio/history", response_model=list[ModerationHistoryResponse])
async def get_audio_moderation_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analyses = db.query(Analyzer).filter(
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio"
    ).order_by(Analyzer.date.desc()).all()

    return [
        ModerationHistoryResponse(
            id=a.id,
            question=a.question,
            response=a.response,
            toxic=a.toxic,
            date=a.date.isoformat() if a.date else None
        ) for a in analyses
    ]

@router.get("/moderation/audio/history/search", response_model=list[ModerationHistoryResponse])
async def search_audio_history(
    search_query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not search_query:
        raise HTTPException(status_code=400, detail="Le paramètre 'search_query' est requis.")

    analyses = db.query(Analyzer).filter(
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio",
        (Analyzer.question.ilike(f"%{search_query}%")) |
        (Analyzer.response.ilike(f"%{search_query}%"))
    ).order_by(Analyzer.date.desc()).all()

    return [
        ModerationHistoryResponse(
            id=a.id,
            question=a.question,
            response=a.response,
            toxic=a.toxic,
            date=a.date.isoformat() if a.date else None
        ) for a in analyses
    ]

@router.patch("/moderation/audio/history/{analysis_id}", response_model=ModerationHistoryResponse)
async def update_audio_analysis(
    analysis_id: int,
    update_data: UpdateQuestionInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analyzer).filter(
        Analyzer.id == analysis_id,
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio"
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse audio non trouvée.")

    analysis.question = update_data.question
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return ModerationHistoryResponse(
        id=analysis.id,
        question=analysis.question,
        response=analysis.response,
        toxic=analysis.toxic,
        date=analysis.date.isoformat() if analysis.date else None
    )

@router.delete("/moderation/audio/history/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analyzer).filter(
        Analyzer.id == analysis_id,
        Analyzer.user_id == current_user.id,
        Analyzer.type == "audio"
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse audio non trouvée.")

    db.delete(analysis)
    db.commit()
