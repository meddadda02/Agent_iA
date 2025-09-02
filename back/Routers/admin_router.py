from ast import List
from multiprocessing import get_context
import os
from datetime import date, datetime, timedelta
from pyparsing import Dict
from sqlalchemy import cast, Date
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
from Models.Rules_model import Rules
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

@router.get("/stats/users/count")
def get_total_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    return {"total_users": total_users}

@router.get("/moderation/analyses/global-type-distribution")
def get_global_analysis_type_distribution(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Retourne la distribution globale des analyses par type (texte, image, audio, vidéo)
    pour tous les utilisateurs.
    """

    # Fetch distribution from DB
    results = (
        db.query(
            Analyzer.type,
            func.count(Analyzer.id).label("count")
        )
        .group_by(Analyzer.type)
        .order_by(func.count(Analyzer.id).desc())
        .all()
    )

    # Normalize to include all types
    all_types = ["text", "image", "audio", "video"]

    distribution = {t: 0 for t in all_types}
    for r in results:
        distribution[r.type] = r.count

    return {
        "global_type_distribution": [
            {"type": t, "count": distribution[t]} for t in all_types
        ]
    }

@router.get("/moderation/analyses/count/today")
def get_total_analyses_today(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    today = date.today()
    total_analyses = (
        db.query(func.count(Analyzer.id))
        .filter(cast(Analyzer.date, Date) == today)
        .scalar()
        or 0
    )
    return {"total_analyses_today": total_analyses}



@router.get("/moderation/analyses/stats/weekly")
def get_analyses_per_day_this_week(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday of current week

    # Query count of analyses grouped by day
    results = (
        db.query(
            cast(Analyzer.date, Date).label("day"),
            func.count(Analyzer.id).label("analyses")
        )
        .filter(cast(Analyzer.date, Date) >= start_of_week)
        .group_by(cast(Analyzer.date, Date))
        .order_by(cast(Analyzer.date, Date))
        .all()
    )

    # Fill missing days from Monday to today
    stats = []
    days_count = (today - start_of_week).days + 1  # number of days to include
    for i in range(days_count):
        current_day = start_of_week + timedelta(days=i)
        found = next((r for r in results if r.day == current_day), None)
        stats.append({
            "day": current_day.strftime("%A"),  # Day name
            "analyses": found.analyses if found else 0
        })

    return stats


@router.get("/moderation/analyses/toxic-trend/weekly")
def get_weekly_toxic_trend(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Retourne la tendance hebdomadaire du contenu toxique.
    """
    today = datetime.utcnow().date()
    trend: List[Dict] = []

    for i in range(6, -1, -1):  # last 7 days
        day = today - timedelta(days=i)
        
        total_analyses = db.query(func.count(Analyzer.id))\
            .filter(func.date(Analyzer.date) == day)\
            .scalar() or 0

        total_toxic = db.query(func.count(Analyzer.id))\
            .filter(func.date(Analyzer.date) == day, Analyzer.toxic == True)\
            .scalar() or 0

        percent_toxic = (total_toxic / total_analyses * 100) if total_analyses > 0 else 0

        trend.append({
            "day": day.strftime("%Y-%m-%d"),
            "percent_toxic": round(percent_toxic, 2)
        })

    return {"weekly_toxic_trend": trend}

@router.get("/moderation/analyses/toxic-percentage")
def get_toxic_content_percentage(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_analyses = db.query(func.count(Analyzer.id)).scalar() or 0
    total_toxic = db.query(func.count(Analyzer.id)).filter(Analyzer.toxic == True).scalar() or 0
    percent_toxic = (total_toxic / total_analyses * 100) if total_analyses > 0 else 0
    return round(percent_toxic, 2)


@router.get("/users/active/count")
def get_active_users_count(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    active_users = (
        db.query(func.count(func.distinct(Analyzer.user_id)))
        .filter(Analyzer.user_id != None)
        .scalar()
        or 0
    )
    return {"active_users": active_users}


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
    current_admin: User = Depends(get_current_admin), 
    db: Session = Depends(get_db)
):
    """Accès aux règles de modération (admin only)"""
    rules = db.query(Rules).all()
    return rules

@router.get("/moderation/history/{user_id}")
async def admin_get_user_moderation_history(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Accès à l'historique de modération d'un utilisateur spécifique (admin only)
    -> Retourne uniquement l'id et le type (image, texte, video, audio)
    """
    analyses = (
        db.query(Analyzer)
        .filter(Analyzer.user_id == user_id)
        .order_by(Analyzer.date.desc())
        .all()
    )

    response_data = []
    for analysis in analyses:
        response_data.append({
            "id": analysis.id,
            "type": analysis.type  # Assumes Analyzer has a "type" column
        })
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




@router.get("/moderation/volume-by-date")
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

@router.get("/moderation/top-users")
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

@router.get("/moderation/count-by-type")
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

@router.get("/moderation/average-toxicity-by-user")
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
# Create a new rule
@router.post("/moderation/rules", response_model=None)
def create_rule(
    title: str = Form(...),
    content: str = Form(None),
    link: str = Form(None),
    source: str = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    rule = Rules(
        title=title,
        content=content,
        link=link,
        source=source,
        published_at=datetime.utcnow()
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule  # raw SQLAlchemy object
# Update a rule
@router.put("/moderation/rules/{rule_id}", response_model=None)
def update_rule(
    rule_id: int,
    title: str = Form(None),
    content: str = Form(None),
    link: str = Form(None),
    source: str = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    rule = db.query(Rules).filter(Rules.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if title: rule.title = title
    if content: rule.content = content
    if link: rule.link = link
    if source: rule.source = source

    db.commit()
    db.refresh(rule)
    return rule

# Delete a rule
@router.delete("/moderation/rules/{rule_id}", response_model=None)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    rule = db.query(Rules).filter(Rules.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
    return {"detail": "Rule deleted successfully"}

#from Services.rules_refresh import refresh_rules_job
#@router.post("/refresh-rules")
#async def refresh_rules():
#    refresh_rules_job()
#    return {"message": "Rules refreshed successfully"}