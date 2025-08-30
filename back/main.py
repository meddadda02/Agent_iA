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




# Scheduler for rules refresh
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import HTTPException
from Services.rules_refresh import refresh_rules_job

scheduler = BackgroundScheduler()
scheduler.start()

# Auto every 3 days
scheduler.add_job(
    refresh_rules_job,
    IntervalTrigger(days=3),
    id="refresh_rules",
    replace_existing=True
)

@app.post("/rules/refresh")
def manual_refresh(current_user: str = "admin"):  # TODO: replace with real auth
    if current_user != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return refresh_rules_job()

@app.get("/rules/status")
def rules_status():
    jobs = scheduler.get_jobs()
    return {
        "jobs": [job.id for job in jobs],
        "next_run_time": str(jobs[0].next_run_time) if jobs else None
    }

