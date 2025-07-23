from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, File, UploadFile, Request
from sqlalchemy.orm import Session
import os

from Shemas.user_shemas import UserOut, Token, ResponseSchema
from config import get_db
from Services.user_services import UserService, JWTService, FileService
from dependencies import get_current_user
from Models.user_model import User


router = APIRouter(tags=["Authentication"])

@router.post("/signup", response_model=ResponseSchema)
async def signup(
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    email: str = Form(...),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        # Sauvegarder l'image si elle existe
        photo_path = None
        if photo and photo.filename:
            photo_path = FileService.save_image(photo)
        
        # Créer l'utilisateur
        user = UserService.create_user(
            db=db,
            username=username,
            email=email,
            password=password,
            confirm_password=confirm_password,
            photo_path=photo_path
        )
        
        return ResponseSchema(
            code="200",
            status="success",
            message="User successfully registered",
            result={"user_id": user.id}
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Authentifier l'utilisateur
        user = UserService.authenticate_user(db, username, password)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )
        
        # Créer le token JWT
        access_token = JWTService.create_access_token(data={"sub": user.username})
        
        # Sauvegarder le token dans la base de données
        user.jwt_token = access_token
        db.commit()
        
        return Token(access_token=access_token, token_type="bearer")
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/users/me", response_model=UserOut)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    try:
        # Construire l'URL publique pour la photo
        photo_url = None
        if current_user.photo:
            base_url = str(request.base_url) if request else "http://localhost:8000/"
            photo_filename = os.path.basename(current_user.photo)
            photo_url = f"{base_url}images/{photo_filename}"
        
        return UserOut(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            photo=photo_url,
            created_at=current_user.created_at.isoformat() if current_user.created_at else None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/users/me", response_model=UserOut)
def update_current_user(
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None), # Added confirm_password to form
    photo: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    try:
        update_data = {}
        
        if username:
            update_data["username"] = username
        if email:
            update_data["email"] = email
        
        # Pass password and confirm_password separately to the service for validation
        # The service will handle the matching logic
        
        if photo and photo.filename:
            photo_path = FileService.save_image(photo)
            update_data["photo"] = photo_path
        
        # Mettre à jour l'utilisateur
        updated_user = UserService.update_user(
            db, 
            current_user, 
            password=password, 
            confirm_password=confirm_password, 
            **update_data
        )
        
        # Construire l'URL publique pour la photo
        photo_url = None
        if updated_user.photo:
            base_url = str(request.base_url) if request else "http://localhost:8000/"
            photo_filename = os.path.basename(updated_user.photo)
            photo_url = f"{base_url}images/{photo_filename}"
        
        return UserOut(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            photo=photo_url,
            created_at=updated_user.created_at.isoformat() if updated_user.created_at else None
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/users/me", response_model=ResponseSchema)
def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Supprimer la photo si elle existe
        if current_user.photo and os.path.exists(current_user.photo):
            os.remove(current_user.photo)
        
        # Supprimer l'utilisateur
        db.delete(current_user)
        db.commit()
        
        return ResponseSchema(
            code="200",
            status="success",
            message="User deleted successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
