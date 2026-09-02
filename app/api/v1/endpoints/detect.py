import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from app.core.config import get_settings
from app.schemas.detection import DetectionResponse
from app.services.detector import detector
from app.services.detection_repo import save_detection

router = APIRouter()


@router.post("/detect", response_model=DetectionResponse, summary="Run pothole detection on an image")
async def detect(
    image: UploadFile = File(..., description="Road image (JPEG/PNG)"),
    lat: float = Form(..., description="Latitude"),
    lng: float = Form(..., description="Longitude"),
    device_id: Optional[str] = Form(default="manual", description="Sender device ID"),
):
    """
    Accepts a road image + GPS coordinates and runs YOLOv8 pothole detection.

    - Returns all detected objects with confidence scores and bounding boxes.
    - Persists confirmed pothole detections to Supabase.
    - ESP32-CAM will POST here with multipart form data once hardware is ready.
    - Coordinates outside Ghana are rejected with a 400 before the image is processed.
    """
    settings = get_settings()
    if not (settings.ghana_lat_min <= lat <= settings.ghana_lat_max) or not (
        settings.ghana_lng_min <= lng <= settings.ghana_lng_max
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Coordinates ({lat}, {lng}) are outside Ghana's bounding box "
                f"(lat {settings.ghana_lat_min}–{settings.ghana_lat_max}, "
                f"lng {settings.ghana_lng_min}–{settings.ghana_lng_max}). "
                "This service only accepts detections within Ghana."
            ),
        )

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG or PNG).")

    raw = await image.read()

    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large. Max size is 10MB.")

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=422, detail="Could not decode image.")

    if not detector.is_pothole_capable:
        raise HTTPException(
            status_code=503,
            detail=(
                "Pothole detection model is not available: the loaded weights have no "
                "'pothole' class (untrained/placeholder weights). Train ml/train.py on "
                "the pothole dataset and set MODEL_PATH to the resulting best.pt."
            ),
        )

    detections = await run_in_threadpool(detector.predict, img)

    pothole_detected = any(
        d.label.lower() == "pothole" and d.confidence >= 0.4
        for d in detections
    )

    record_id = None
    if pothole_detected:
        max_conf = max(d.confidence for d in detections)
        record_id = await save_detection(
            lat=lat,
            lng=lng,
            confidence=max_conf,
            detections=detections,
            device_id=device_id or "manual",
        )

    return DetectionResponse(
        id=record_id,
        pothole_detected=pothole_detected,
        detections=detections,
        coordinates={"lat": lat, "lng": lng},
        device_id=device_id or "manual",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
