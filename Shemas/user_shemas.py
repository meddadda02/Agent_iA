from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    confirm_password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None

class UserOut(UserBase):
    id: int
    photo: Optional[str] = None
    created_at: Optional[str] = None
    role: str 

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ResponseSchema(BaseModel):
    code: str
    status: str
    message: str
    result: Optional[dict] = None
