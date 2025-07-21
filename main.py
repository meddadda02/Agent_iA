from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import engine, Base
import Routers.user_route as user_route
import Routers.analyzer_route as analyzer_route
import Models.analyzer_model as Analyzer
import Models.user_model as User

# Créer l'application FastAPI
app = FastAPI(
    title="User Management API",
    description="API for user authentication and management",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer les tables dans la base de données
User.Base.metadata.create_all(bind=engine)
app.include_router(user_route.router)
Analyzer.Base.metadata.create_all(bind=engine)
app.include_router(analyzer_route.router)

# Servir les fichiers statiques (images)
uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

app.mount("/images", StaticFiles(directory=uploads_dir), name="images")
