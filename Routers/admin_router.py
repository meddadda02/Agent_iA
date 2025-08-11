from multiprocessing import get_context
import os
from fastapi import APIRouter, Depends, HTTPException, Form, Request, UploadFile
from fastapi.params import File
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from Models.analyzer_model import Analyzer
from Services.llm_service import LLMService
from Services.user_services import FileService, UserService
from Shemas.user_shemas import UserOut, ResponseSchema
from Models.user_model import User
from dependencies import get_current_admin, get_db
from passlib.context import CryptContext
from Services.moderation_service import ModerationService
from Shemas.moderation_schemas import ModelsResponse, ModerationHistoryResponse, SupportedModelsResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/users", response_model=ResponseSchema)
async def create_user(
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    email: str = Form(...),
    role: Optional[str] = Form("user"),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    request: Request = None
):
    try:
        # Check password confirmation
        if password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        # Save photo if uploaded
        photo_path = None
        if photo and photo.filename:
            photo_path = FileService.save_image(photo)
        
        # Check if username/email already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        # Create user (hashing password done inside UserService.create_user)
        user = UserService.create_user(
            db=db,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
            role=role,
            photo_path=photo_path
        )
        
        return ResponseSchema(
            code="200",
            status="success",
            message="User successfully created",
            result={"user_id": user.id}
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
# --- Rechercher un utilisateur par ID ---
@router.get("/users/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    request: Request = None
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    photo_url = None
    base_url = str(request.base_url) if request else "http://localhost:8000/"
    if user.photo:
        photo_filename = os.path.basename(user.photo)
        photo_url = f"{base_url}images/{photo_filename}"

    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        photo=photo_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        role=user.role
    )

@router.get("/users", response_model=list[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
    request: Request = None
):
    try:
        users = db.query(User).all()

        result = []
        base_url = str(request.base_url) if request else "http://localhost:8000/"
        for user in users:
            photo_url = None
            if user.photo:
                photo_filename = os.path.basename(user.photo)
                photo_url = f"{base_url}images/{photo_filename}"

            result.append(
                UserOut(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    photo=photo_url,
                    created_at=user.created_at.isoformat() if user.created_at else None,
                    role=user.role
                )
            )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    request: Request = None,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if username:
        user.username = username
    if email:
        user.email = email
    if role:
        if role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role

    db.commit()
    db.refresh(user)

    # Préparer la photo_url
    photo_url = None
    if user.photo:
        base_url = str(request.base_url) if request else "http://localhost:8000/"
        photo_filename = os.path.basename(user.photo)
        photo_url = f"{base_url}images/{photo_filename}"

    # Retourner un UserOut avec conversion explicite de created_at
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        photo=photo_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        role=user.role,
    )

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"detail": "User deleted successfully"}
#TEXTE
@router.get("/moderation/models", response_model=ModelsResponse)
async def admin_get_text_models(
    current_admin: User = Depends(get_current_admin)
):
    """Accès aux modèles de modération (admin only)"""
    return ModerationService.get_available_models()
#IMAGE
@router.get("/moderation/models-list", response_model=SupportedModelsResponse)
async def admin_get_image_models(current_user: User = Depends(get_current_admin)):
    """
    Récupère les modèles disponibles pour l'analyse - Authentification requise
    """
    return LLMService.get_available_models()

@router.get("/moderation/rules")
async def admin_get_rules(
    current_admin: User = Depends(get_current_admin)
):
    """Accès aux règles de modération (admin only)"""
    return ModerationService.get_rules()

@router.get("/moderation/history/{user_id}", response_model=list[ModerationHistoryResponse])
async def admin_get_user_moderation_history(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Accès à l'historique de modération d'un utilisateur spécifique (admin only)"""
    analyses = db.query(Analyzer).filter(Analyzer.user_id == user_id).order_by(Analyzer.date.desc()).all()

    response_data = []
    for analysis in analyses:
        response_data.append(
            ModerationHistoryResponse(
                id=analysis.id,
                question=analysis.question,
                response=analysis.response,
                toxic=analysis.toxic,
                date=analysis.date.isoformat() if analysis.date else None
            )
        )
    return response_data

@router.get("/moderation/history/{user_id}/{analysis_id}", response_model=ModerationHistoryResponse)
async def admin_get_specific_moderation_analysis(
    user_id: int,
    analysis_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Récupère une analyse de modération spécifique d'un utilisateur (admin only)
    """
    try:
        analysis = db.query(Analyzer).filter(
            Analyzer.user_id == user_id,
            Analyzer.id == analysis_id
        ).first()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analyse non trouvée pour cet utilisateur")

        return ModerationHistoryResponse(
            id=analysis.id,
            question=analysis.question,
            response=analysis.response,
            toxic=analysis.toxic,
            date=analysis.date.isoformat() if analysis.date else None
        )
    except Exception as e:
        print(f"Erreur lors de la récupération de l'analyse {analysis_id} pour user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'analyse")




@router.get("/admin/moderation/volume-by-date")
def get_volume_analyses_by_date(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Récupère le nombre total d'analyses effectuées regroupées par date.
    Utile pour visualiser le volume d'activité de modération au fil du temps.
    """
    from sqlalchemy import func, cast, Date
    results = (
        db.query(
            cast(Analyzer.date, Date).label("date"),
            func.count(Analyzer.id).label("count")
        )
        .group_by(cast(Analyzer.date, Date))
        .order_by(cast(Analyzer.date, Date))
        .all()
    )
    return [{"date": r.date.isoformat(), "count": r.count} for r in results]

@router.get("/admin/moderation/top-users")
def get_top_users_by_analysis_count(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Retourne la liste des utilisateurs ayant effectué le plus d'analyses.
    Utile pour identifier les utilisateurs les plus actifs en modération.
    """
    from sqlalchemy import func
    results = (
        db.query(
            User.id,
            User.username,
            func.count(Analyzer.id).label("analysis_count")
        )
        .join(Analyzer, Analyzer.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(Analyzer.id).desc())
        .limit(10)
        .all()
    )
    return [
        {"user_id": r.id, "username": r.username, "analysis_count": r.analysis_count}
        for r in results
    ]

@router.get("/admin/moderation/count-by-type")
def get_analysis_count_by_type(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Récupère la répartition du nombre d'analyses effectuées par type (texte, image, audio, video).
    """
    from sqlalchemy import func

    results = (
        db.query(
            Analyzer.type,
            func.count(Analyzer.id).label("count")
        )
        .group_by(Analyzer.type)
        .order_by(func.count(Analyzer.id).desc())
        .all()
    )
    return [{"type": r.type, "count": r.count} for r in results]

@router.get("/admin/moderation/average-toxicity-by-user")
def get_avg_toxicity_by_user(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Calcule la toxicité moyenne des contenus modérés par utilisateur.
    Permet d'identifier les utilisateurs dont les contenus sont les plus toxiques en moyenne.
    """
    from sqlalchemy import func, cast, Integer

    results = (
        db.query(
            User.id,
            User.username,
            func.avg(cast(Analyzer.toxic, Integer)).label("avg_toxicity")  # cast bool to int for avg
        )
        .join(Analyzer, Analyzer.user_id == User.id)
        .group_by(User.id, User.username)
        .order_by(func.avg(cast(Analyzer.toxic, Integer)).desc())
        .all()
    )

    return [
        {"user_id": r.id, "username": r.username, "average_toxicity": float(r.avg_toxicity or 0)}
        for r in results
    ]
