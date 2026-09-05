from fastapi import APIRouter, Depends, Query
from app.core.security import require_api_key
from app.schemas.detection import HeatmapPoint, StatsResponse
from app.services.detection_repo import get_heatmap_points, get_stats, delete_detection
from fastapi import HTTPException

router = APIRouter()


@router.get("/heatmap", response_model=list[HeatmapPoint], summary="Get pothole locations for the heatmap")
async def heatmap(
    limit: int = Query(default=500, le=2000),
    min_confidence: float = Query(default=0.4, ge=0.0, le=1.0),
):
    """
    Returns pothole GPS coordinates with intensity values.
    Consumed by the frontend heatmap layer.
    Format: [{lat, lng, intensity}]
    """
    return await get_heatmap_points(limit=limit, min_confidence=min_confidence)


@router.get("/stats", response_model=StatsResponse, summary="Dashboard summary statistics")
async def stats():
    """Returns total detections, average confidence, and active device count."""
    return await get_stats()


@router.delete("/detections/{detection_id}", summary="Remove a false positive", dependencies=[Depends(require_api_key)])
async def remove_detection(detection_id: str):
    deleted = await delete_detection(detection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Detection not found.")
    return {"deleted": detection_id}
