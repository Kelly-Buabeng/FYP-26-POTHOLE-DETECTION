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

    settings = get_settings()
    is_production = settings.app_env.strip().lower() == "production"
    api_key_unconfigured = settings.api_key.strip() in _PLACEHOLDER_KEYS
    cors_wide_open = "*" in settings.cors_origin_list

    if api_key_unconfigured:
        message = (
            "API_KEY is not configured (or is still the .env.example "
            "placeholder) — /detect, /detections/export, and DELETE "
            "/detections/{id} are unauthenticated."
        )
        if is_production:
            raise RuntimeError(f"[Startup] {message} Refusing to start in production.")
        print(f"[Startup] WARNING: {message} Set a real API_KEY before deploying.")

    if cors_wide_open and is_production:
        raise RuntimeError(
            "[Startup] CORS_ORIGINS includes '*' — refusing to start in production. "
            "Set CORS_ORIGINS to the deployed frontend's exact origin(s)."
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
    allow_origins=get_settings().cors_origin_list,
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
