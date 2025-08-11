from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from Models.user_model import User  # adapte selon ton projet
from config import DATABASE_URL  # ou ta config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def create_admin():
    hashed_password = pwd_context.hash("123")
    admin = User(
        username="admin",
        email="admin@gmail.com",
        password_hash=hashed_password,
        Confirm_password_hash=hashed_password,
        role="admin"
    )
    db.add(admin)
    db.commit()
    db.close()

if __name__ == "__main__":
    create_admin()
    print("Admin created successfully.")
