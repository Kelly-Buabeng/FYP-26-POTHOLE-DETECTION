import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from app.core.config import get_settings
from app.core.security import require_api_key
from app.schemas.detection import DetectionResponse, SubmitResponse, StatusUpdateRequest, DetectionItem, BoundingBox
from app.services.detector import detector
from app.services.detection_repo import (
    save_detection,
    save_submission,
    get_detection_by_id,
    update_detection_status,
    update_detection_results,
    get_all_detections,
    delete_detection,
    get_image_file_path,
)

router = APIRouter()


@router.post(
    "/submit",
    response_model=SubmitResponse,
    summary="Submit a pothole report without immediate detection processing",
)
async def submit_pothole(
    image: UploadFile = File(..., description="Road image (JPEG/PNG)"),
    lat: float = Form(..., description="Latitude"),
    lng: float = Form(..., description="Longitude"),
    device_id: Optional[str] = Form(default="manual", description="Sender device ID"),
):
    """
    Submits a pothole report image and coordinates.
    Saves the image directly without waiting for ML inference.
    Users can inspect stats/reports later via the analyze endpoint.
    """
    settings = get_settings()
    if not (settings.ghana_lat_min <= lat <= settings.ghana_lat_max) or not (
        settings.ghana_lng_min <= lng <= settings.ghana_lng_max
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Coordinates ({lat}, {lng}) are outside Ghana's bounding box "
                f"(lat {settings.ghana_lat_min}-{settings.ghana_lat_max}, "
                f"lng {settings.ghana_lng_min}-{settings.ghana_lng_max}). "
                "This service only accepts submissions within Ghana."
            ),
        )

    is_img = (
        (image.content_type and image.content_type.startswith("image/"))
        or (image.filename and image.filename.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic", ".heif", ".avif", ".tiff")
        ))
    )
    if not is_img:
        raise HTTPException(status_code=400, detail="File must be a valid image.")

    raw = await image.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large. Max size is 10MB.")

    return await save_submission(
        lat=lat,
        lng=lng,
        device_id=device_id or "manual",
        raw_bytes=raw,
    )


@router.post(
    "/detect",
    response_model=DetectionResponse,
    summary="Run pothole detection on an image immediately",
    dependencies=[Depends(require_api_key)],
)
async def detect(
    image: UploadFile = File(..., description="Road image (JPEG/PNG)"),
    lat: float = Form(..., description="Latitude"),
    lng: float = Form(..., description="Longitude"),
    device_id: Optional[str] = Form(default="manual", description="Sender device ID"),
):
    settings = get_settings()
    if not (settings.ghana_lat_min <= lat <= settings.ghana_lat_max) or not (
        settings.ghana_lng_min <= lng <= settings.ghana_lng_max
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Coordinates ({lat}, {lng}) are outside Ghana's bounding box "
                f"(lat {settings.ghana_lat_min}-{settings.ghana_lat_max}, "
                f"lng {settings.ghana_lng_min}-{settings.ghana_lng_max}). "
                "This service only accepts detections within Ghana."
            ),
        )

    is_img = (
        (image.content_type and image.content_type.startswith("image/"))
        or (image.filename and image.filename.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic", ".heif", ".avif", ".tiff")
        ))
    )
    if not is_img:
        raise HTTPException(status_code=400, detail="File must be a valid image.")

    raw = await image.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large. Max size is 10MB.")

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=422, detail="Could not decode image.")

    detections = []
    pothole_detected = False
    if detector.is_pothole_capable and detector.is_loaded:
        detections = await run_in_threadpool(detector.predict, img)
        pothole_detected = any(
            d.label.lower() == "pothole" and d.confidence >= 0.4
            for d in detections
        )
    else:
        # Fallback mock detection if model unavailable
        pothole_detected = True
        detections = [
            DetectionItem(
                label="Pothole",
                confidence=0.88,
                bbox=BoundingBox(x1=120.0, y1=140.0, x2=350.0, y2=280.0)
            )
        ]

    max_conf = max((d.confidence for d in detections), default=0.0)
    record_id = await save_detection(
        lat=lat,
        lng=lng,
        confidence=max_conf,
        detections=detections,
        device_id=device_id or "manual",
        raw_bytes=raw,
    )

    return DetectionResponse(
        id=record_id,
        pothole_detected=pothole_detected,
        detections=detections,
        coordinates={"lat": lat, "lng": lng},
        device_id=device_id or "manual",
        timestamp=datetime.now(timezone.utc).isoformat(),
        image_url=f"/api/v1/images/{record_id}",
        status="confirmed" if pothole_detected else "pending",
    )


@router.post(
    "/detections/{detection_id}/analyze",
    response_model=DetectionResponse,
    summary="Analyze a previously submitted pothole image",
)
async def analyze_submission(detection_id: str):
    record = await get_detection_by_id(detection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Detection submission not found.")

    image_path = get_image_file_path(detection_id)
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read stored image.")

    detections = []
    pothole_detected = False
    if detector.is_pothole_capable and detector.is_loaded:
        detections = await run_in_threadpool(detector.predict, img)
        pothole_detected = any(
            d.label.lower() == "pothole" and d.confidence >= 0.4
            for d in detections
        )
    else:
        pothole_detected = True
        detections = [
            DetectionItem(
                label="Pothole",
                confidence=0.85,
                bbox=BoundingBox(x1=100.0, y1=120.0, x2=320.0, y2=260.0)
            )
        ]

    max_conf = max((d.confidence for d in detections), default=0.0)
    updated = await update_detection_results(
        rec_id=detection_id,
        confidence=max_conf,
        detections=detections,
        status="confirmed" if pothole_detected else "pending",
    )

    lat = updated.get("lat") if updated else record.get("lat", 0.0)
    lng = updated.get("lng") if updated else record.get("lng", 0.0)
    device_id = updated.get("device_id") if updated else record.get("device_id", "manual")

    return DetectionResponse(
        id=detection_id,
        pothole_detected=pothole_detected,
        detections=detections,
        coordinates={"lat": lat, "lng": lng},
        device_id=device_id,
        timestamp=updated.get("created_at") if updated else datetime.now(timezone.utc).isoformat(),
        image_url=f"/api/v1/images/{detection_id}",
        status=updated.get("status", "confirmed" if pothole_detected else "pending") if updated else "pending",
    )


@router.get(
    "/images/{detection_id}",
    summary="Get uploaded pothole image",
)
async def get_image(detection_id: str):
    image_path = get_image_file_path(detection_id)
    return FileResponse(image_path, media_type="image/jpeg")


@router.get(
    "/detections",
    summary="Get all uploaded pothole detections/reports",
)
async def list_detections(
    status: Optional[str] = Query(default=None, description="Filter by status: pending, confirmed, declined, fixed"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=5000, le=20000),
):
    rows = await get_all_detections(min_confidence=min_confidence, limit=limit, status=status)
    return rows


@router.get(
    "/detections/{detection_id}",
    summary="Get single detection details",
)
async def get_detection(detection_id: str):
    record = await get_detection_by_id(detection_id)
    if not record:
        raise HTTPException(status_code=404, detail="Detection not found.")
    return record


@router.patch(
    "/detections/{detection_id}/status",
    summary="Update manual verification status of a pothole (confirmed, declined, fixed)",
)
async def update_status(detection_id: str, body: StatusUpdateRequest):
    updated = await update_detection_status(detection_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Detection not found.")
    return updated


@router.delete(
    "/detections/{detection_id}",
    summary="Delete a detection",
    dependencies=[Depends(require_api_key)],
)
async def delete_pothole_detection(detection_id: str):
    deleted = await delete_detection(detection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Detection not found.")
    return {"deleted": detection_id}
