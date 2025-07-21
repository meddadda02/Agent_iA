import os
import shutil
import uuid
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, UploadFile
from config import SECRET_KEY, ALGORITHM
from Models.user_model import User

# Configuration du hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    @staticmethod
    def create_user(db: Session, username: str, email: str, password: str, bio: str = None, photo_path: str = None):
        # Vérifier si l'utilisateur existe déjà
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Hacher le mot de passe
        hashed_password = pwd_context.hash(password)
        
        # Créer l'utilisateur
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            bio=bio,
            photo=photo_path
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str):
        user = db.query(User).filter(User.username == username).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            return False
        return user
    
    @staticmethod
    def update_user(db: Session, user: User, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                if key == "password":
                    setattr(user, "password_hash", pwd_context.hash(value))
                else:
                    setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        return user

class JWTService:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)  # Token valide 24h
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

class FileService:
    @staticmethod
    def save_image(file: UploadFile, directory: str = "uploads") -> str:
        try:
            # Créer le dossier s'il n'existe pas
            os.makedirs(directory, exist_ok=True)
            
            # Vérifier le fichier
            if not file.filename or '.' not in file.filename:
                raise ValueError("Invalid file name")
            
            # Générer un nom unique
            ext = file.filename.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                raise ValueError("Invalid file type")
            
            unique_name = f"{uuid.uuid4()}.{ext}"
            file_path = os.path.join(directory, unique_name)
            
            # Sauvegarder le fichier
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            return file_path
        
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error saving file: {str(e)}")
