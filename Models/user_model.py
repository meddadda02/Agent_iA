from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, Text
from config import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    photo = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    Confirm_password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    jwt_token = Column(String, nullable=True)

    analyzers = relationship("Analyzer", back_populates="user", cascade="all, delete-orphan")
