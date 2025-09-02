import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
import os
import json
from datetime import datetime
from PIL import Image, ImageEnhance
from Services.yolo_service import analyze_with_yolo, ocr_extract_text, moderate_text
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

    try:
        # 1️⃣ Lire et sauvegarder l'image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, filename)
        image.save(file_path)

        # 2️⃣ Détection d'objets avec YOLO
        detections = analyze_with_yolo(image_bytes) or []

        # 3️⃣ OCR global + OCR sur chaque objet
        ocr_texts = []
        full_text = ocr_extract_text(image_bytes)
        if full_text:
            ocr_texts.append(full_text)

        for det in detections:
            try:
                x1, y1, x2, y2 = map(int, det["bbox"])
                cropped = image.crop((x1, y1, x2, y2))
                buf = io.BytesIO()
                cropped.save(buf, format="JPEG")
                crop_bytes = buf.getvalue()
                text_crop = ocr_extract_text(crop_bytes)
                if text_crop:
                    ocr_texts.append(text_crop)
            except Exception as crop_err:
                print(f"Erreur OCR sur crop: {crop_err}")

        combined_text = " ".join(ocr_texts).strip()
        print("Texte détecté par OCR :", combined_text or "Aucun texte détecté")

        # 4️⃣ Modération texte
        text_moderation = await moderate_text(combined_text or "")

        # 5️⃣ Vérification compatibilité YouTube via LLM
        youtube_compatibility = check_youtube_compatibility(
            detections=detections,
            ocr_text=combined_text
        )

        if not isinstance(youtube_compatibility, dict):
            youtube_compatibility = {
                "compatible": None,
                "commentaire": "Erreur LLM ou réponse invalide"
            }

        # 6️⃣ Fusion compatibilité finale
        if (youtube_compatibility.get("compatible") is False or
            text_moderation.get("compatible") is False):
            youtube_compatibility["compatible"] = False
            youtube_compatibility["commentaire"] = (
                youtube_compatibility.get("commentaire", "")
                + " / Texte ou objet non conforme"
            )

        # 7️⃣ Sauvegarde en base
        new_analysis = Analyzer(
            user_id=current_user.id,
            question=filename,
            response=json.dumps({
                "objects": detections,
                "ocr_text": combined_text,
                "text_moderation": text_moderation,
                "youtube_compatibility": youtube_compatibility
            }, ensure_ascii=False),
            toxic=False,
            type="image"
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

        # 8️⃣ Réponse finale
        return {
            "objects": detections,
            "ocr_text": combined_text,
            "text_moderation": text_moderation,
            "youtube_compatibility": youtube_compatibility,
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


@router.get("/image/moderation/history/{analysis_id}", response_model=ModerationHistoryResponse)
async def get_image_analysis_by_id(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupère une analyse d’image par ID (authentifié et propriétaire)"""
    analysis = db.query(Analyzer).filter(
        Analyzer.id == analysis_id,
        Analyzer.user_id == current_user.id,
        Analyzer.type == "image"
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse non trouvée.")

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