import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image

from app.core.dependencies import verify_api_key, validate_ghana_coordinates
from app.schemas.detection import DetectionResponse, Severity
from app.services.detector import detector
from app.services.detection_repo import save_detection

router = APIRouter()


def _worst_severity(detections) -> Optional[Severity]:
    """Return the highest severity found in this frame."""
    if not detections:
        return None
    order = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}
    return max(detections, key=lambda d: order[d.severity]).severity


@router.post(
    "/detect",
    response_model=DetectionResponse,
    summary="Run pothole detection on a road image",
    dependencies=[Depends(verify_api_key)],
)
async def detect(
    image: UploadFile = File(..., description="Road image (JPEG/PNG)"),
    lat: float = Form(..., description="Latitude (must be within Ghana)"),
    lng: float = Form(..., description="Longitude (must be within Ghana)"),
    device_id: Optional[str] = Form(default="manual", description="Sender device ID"),
):
    """
    Accepts a road image + GPS coordinates, runs YOLOv8 pothole detection,
    classifies severity, and persists confirmed detections to Supabase.

    Requires header: X-API-Key
    Coordinates must fall within Ghana's geographic bounds.
    """
    # Validate coordinates are within Ghana
    validate_ghana_coordinates(lat, lng)

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG or PNG).")

    raw = await image.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large. Max size is 10MB.")

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=422, detail="Could not decode image.")

    detections = detector.predict(img)

    pothole_detected = any(
        d.label.lower() == "pothole" and d.confidence >= 0.4
        for d in detections
    )

    worst = _worst_severity(detections) if pothole_detected else None
    record_id = None

    if pothole_detected:
        max_conf = max(d.confidence for d in detections)
        record_id = await save_detection(
            lat=lat,
            lng=lng,
            confidence=max_conf,
            severity=worst,
            detections=detections,
            device_id=device_id or "manual",
        )

    return DetectionResponse(
        id=record_id,
        pothole_detected=pothole_detected,
        severity=worst,
        detections=detections,
        coordinates={"lat": lat, "lng": lng},
        device_id=device_id or "manual",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
