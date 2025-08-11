from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import engine, Base
import Models.analyzer_model as Analyzer
import Models.user_model as User
# import Models.admin_model as Admin  # <-- supprimer

# Import des routeurs
from Routers.user_route import router as user_router
from Routers.admin_router import router as admin_router  # <-- supprimer
from Routers.analyzer_route import router as analyzer_router
from Routers.image_router import router as image_router
from Routers.audio_route import router as audio_router
from Routers.video_route import router as video_router

app = FastAPI(
    title="User & Admin Management API",
    description="API for user and admin authentication, file processing, and media handling",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer les tables dans la base de données
User.Base.metadata.create_all(bind=engine)
Analyzer.Base.metadata.create_all(bind=engine)
# Admin.Base.metadata.create_all(bind=engine)  # <-- supprimer


# Enregistrer les routeurs
app.include_router(user_router)
app.include_router(admin_router)  # <-- supprimer
app.include_router(analyzer_router)
app.include_router(image_router)
app.include_router(audio_router)
app.include_router(video_router)

uploads_dir = "uploads"
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)

app.mount("/images", StaticFiles(directory=uploads_dir), name="images")
app.mount("/audio", StaticFiles(directory=uploads_dir), name="audio")
app.mount("/video", StaticFiles(directory=uploads_dir), name="video")
