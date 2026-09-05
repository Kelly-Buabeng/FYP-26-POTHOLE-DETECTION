from fastapi import APIRouter
from app.api.v1.endpoints import detect, heatmap, video, ingestion, report

router = APIRouter(prefix="/api/v1")
router.include_router(detect.router, tags=["Detection"])
router.include_router(video.router, tags=["Video Detection"])
router.include_router(ingestion.router, tags=["Dual Ingestion"])
router.include_router(heatmap.router, tags=["Heatmap"])
router.include_router(report.router, tags=["Reporting"])
