from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Variables d'environnement avec debug
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# Debug: afficher les variables (à supprimer en production)
print(f"DATABASE_URL loaded: {DATABASE_URL}")
print(f"SECRET_KEY loaded: {'***' if SECRET_KEY else 'None'}")

# Vérifier que DATABASE_URL est définie
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL n'est pas définie. "
        "Veuillez vérifier votre fichier .env"
    )

try:
    # Configuration de la base de données
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    print("✅ Connexion à la base de données configurée avec succès")
except Exception as e:
    print(f"❌ Erreur de configuration de la base de données: {e}")
    raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
