from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.security import _PLACEHOLDER_KEYS
from app.services.detector import detector


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Loading YOLOv8 model...")
    detector.load()
    if get_settings().api_key.strip() in _PLACEHOLDER_KEYS:
        print(
            "[Startup] WARNING: API_KEY is not configured (or is still the "
            ".env.example placeholder) — /detect, /detections/export, and "
            "DELETE /detections/{id} are unauthenticated. Set a real API_KEY "
            "before deploying."
        )
    print("[Startup] Ready.")
    yield
    print("[Shutdown] Done.")


app = FastAPI(
    title="FYP-26 Pothole Detection API",
    description="YOLOv8-powered road hazard detection with geospatial heatmap support.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"])
def root():
    return {
        "project": "FYP-26 Pothole Detection",
        "status": "online",
        "model_loaded": detector.is_loaded,
        "pothole_model_ready": detector.is_pothole_capable,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "model_loaded": detector.is_loaded,
        "pothole_model_ready": detector.is_pothole_capable,
    }
