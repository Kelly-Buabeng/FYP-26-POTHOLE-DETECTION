from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.dependencies import verify_api_key
from app.schemas.detection import HeatmapPoint, StatsResponse, DetectionRecord
from app.services.detection_repo import (
    get_heatmap_points, get_stats, delete_detection, get_detections_list
)

router = APIRouter()


@router.get(
    "/heatmap",
    response_model=list[HeatmapPoint],
    summary="Pothole locations for the heatmap",
    dependencies=[Depends(verify_api_key)],
)
async def heatmap(
    limit: int = Query(default=500, le=2000),
    min_confidence: float = Query(default=0.4, ge=0.0, le=1.0),
    severity: str = Query(default=None, description="Filter by severity: Low, Medium, High"),
):
    """Returns [{lat, lng, intensity, severity}] for the frontend heatmap layer."""
    return await get_heatmap_points(
        limit=limit,
        min_confidence=min_confidence,
        severity_filter=severity,
    )


@router.get(
    "/detections",
    response_model=list[DetectionRecord],
    summary="Paginated list of all detections",
    dependencies=[Depends(verify_api_key)],
)
async def list_detections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    severity: str = Query(default=None, description="Filter by severity: Low, Medium, High"),
):
    """
    Returns a paginated list of detections — useful for building a data table
    or report view in the frontend.
    """
    return await get_detections_list(page=page, page_size=page_size, severity_filter=severity)


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Dashboard summary statistics",
    dependencies=[Depends(verify_api_key)],
)
async def stats():
    """Returns total detections broken down by severity, avg confidence, active devices."""
    return await get_stats()


@router.delete(
    "/detections/{detection_id}",
    summary="Remove a false positive",
    dependencies=[Depends(verify_api_key)],
)
async def remove_detection(detection_id: str):
    deleted = await delete_detection(detection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Detection not found.")
    return {"deleted": detection_id}
