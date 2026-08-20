import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image

from app.core.dependencies import verify_api_key
from app.schemas.detection import (
    IngestionTelemetry,
    BatchSyncResponse,
    LiveIngestionResponse,
    BatchSyncItemResponse,
)
from app.services.detection_repo import save_live_detection, is_duplicate_detection, save_batch_sync_results
from app.services.ingestion_processor import process_live_frame, decode_batch_payload, run_batch_inference

router = APIRouter()


@router.post(
    "/detect/live",
    response_model=LiveIngestionResponse,
    summary="Ingest a single live frame with telemetry",
    dependencies=[Depends(verify_api_key)],
)
async def detect_live(
    image: UploadFile = File(..., description="Single live frame (JPEG/PNG)"),
    lat: float = Form(...),
    lng: float = Form(...),
    timestamp: datetime = Form(...),
    device_id: str = Form(default="manual"),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    raw = await image.read()
    telemetry = IngestionTelemetry(lat=lat, lng=lng, timestamp=timestamp, device_id=device_id)
    response, detections = process_live_frame(raw, telemetry)

    if response.pothole_detected:
        duplicate = await is_duplicate_detection(lat, lng, timestamp)
        if not duplicate:
            if response.severity is None:
                raise HTTPException(status_code=422, detail="Could not determine pothole severity.")
            record_id = await save_live_detection(
                lat=lat,
                lng=lng,
                confidence=max(d.confidence for d in detections),
                severity=response.severity,
                detections=detections,
                device_id=device_id,
                capture_timestamp=timestamp,
            )
            response.id = record_id

    return response


@router.post(
    "/detect/batch-sync",
    response_model=BatchSyncResponse,
    summary="Sync buffered SD card payloads in bulk",
    dependencies=[Depends(verify_api_key)],
)
async def detect_batch_sync(
    archive: UploadFile = File(..., description="ZIP archive of JPEG frames"),
    manifest: UploadFile = File(..., description="JSON manifest with telemetry per frame"),
):
    if not archive.content_type or "zip" not in archive.content_type:
        raise HTTPException(status_code=400, detail="archive must be a ZIP file")
    if not manifest.content_type or not manifest.content_type.endswith("json"):
        raise HTTPException(status_code=400, detail="manifest must be JSON")

    archive_bytes = await archive.read()
    manifest_bytes = await manifest.read()

    try:
        decoded_frames = decode_batch_payload(archive_bytes, manifest_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not decode batch payload: {exc}") from exc

    if not decoded_frames:
        return BatchSyncResponse(total_files=0, processed_files=0, persisted_detections=0, deduped_detections=0, results=[])

    detections_by_frame = run_batch_inference(decoded_frames)

    results: list[BatchSyncItemResponse] = []
    persisted = 0
    deduped = 0

    for decoded_frame, detections in zip(decoded_frames, detections_by_frame):
        pothole_detected = any(d.label.lower() == "pothole" and d.confidence >= 0.4 for d in detections)
        severity = None
        if pothole_detected:
            severity = max(detections, key=lambda d: {"Low": 1, "Medium": 2, "High": 3}[d.severity.value]).severity

        duplicate = False
        if pothole_detected:
            duplicate = await is_duplicate_detection(
                decoded_frame.manifest_item.lat,
                decoded_frame.manifest_item.lng,
                decoded_frame.manifest_item.timestamp,
            )
            if not duplicate:
                persisted += 1
            else:
                deduped += 1

        results.append(
            BatchSyncItemResponse(
                filename=decoded_frame.manifest_item.filename,
                pothole_detected=pothole_detected,
                severity=severity,
                detections=detections,
                coordinates={"lat": decoded_frame.manifest_item.lat, "lng": decoded_frame.manifest_item.lng},
                device_id=decoded_frame.manifest_item.device_id,
                capture_timestamp=decoded_frame.manifest_item.timestamp,
                received_timestamp=datetime.now(timezone.utc),
                deduped=duplicate,
            )
        )

    await save_batch_sync_results(results, persisted, deduped)
    return BatchSyncResponse(
        total_files=len(decoded_frames),
        processed_files=len(decoded_frames),
        persisted_detections=persisted,
        deduped_detections=deduped,
        results=results,
    )