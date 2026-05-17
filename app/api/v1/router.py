from fastapi import APIRouter
from app.api.v1.endpoints import detect, heatmap

router = APIRouter(prefix="/api/v1")
router.include_router(detect.router, tags=["Detection"])
router.include_router(heatmap.router, tags=["Heatmap"])
