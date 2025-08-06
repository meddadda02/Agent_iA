from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import engine, Base
import Routers.user_route as user_route
import Routers.analyzer_route as analyzer_route
import Models.analyzer_model as Analyzer
import Models.user_model as User
from Routers.image_router import router as image_router  # ✅ <-- Ajout route image
import Routers.audio_route as audio_route # Import du routeur audio
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

# ✅ Créer les tables dans la base de données
User.Base.metadata.create_all(bind=engine)
Analyzer.Base.metadata.create_all(bind=engine)

# ✅ Enregistrer les routers
app.include_router(user_route.router)
app.include_router(analyzer_route.router)
app.include_router(image_router)  # <-- Ajout image_router
app.include_router(audio_route.router)  # Ajout du routeur audio
# ✅ Dossier pour stocker les fichiers uploadés

from Routers import video_route
app.include_router(video_route.router)



from Routers import audio_route
app.include_router(audio_route.router)


uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

# ✅ Monter les fichiers statiques (pour voir les images via /images/nom_image.jpg)
app.mount("/images", StaticFiles(directory=uploads_dir), name="images")

app.mount("/audio", StaticFiles(directory=uploads_dir), name="audio")

app.include_router(image_router)