from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.dependencies import verify_api_key
from app.schemas.detection import (
    IngestionTelemetry,
    BatchSyncResponse,
    LiveIngestionResponse,
    BatchSyncItemResponse,
)
from app.services.detection_repo import (
    save_live_detection,
    is_duplicate_detection,
    get_dedup_candidate_points,
    save_batch_detections,
    has_nearby_point,
)
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

    # Process chronologically so intra-batch duplicates (the same pothole caught
    # by several consecutive frames while driving slowly) are caught in order.
    ordered = sorted(zip(decoded_frames, run_batch_inference(decoded_frames)), key=lambda pair: pair[0].manifest_item.timestamp)

    # One prefetch instead of one query per frame; extended in-memory as frames
    # in this batch are accepted, so later frames dedupe against earlier ones
    # in the same sync too.
    dedup_pool = await get_dedup_candidate_points()

    results: list[BatchSyncItemResponse] = []
    pending_inserts: list[dict] = []
    pending_result_indices: list[int] = []
    persisted = 0
    deduped = 0

    for decoded_frame, detections in ordered:
        item = decoded_frame.manifest_item
        pothole_detected = any(d.label.lower() == "pothole" and d.confidence >= 0.4 for d in detections)
        severity = None
        if pothole_detected:
            severity = max(detections, key=lambda d: {"Low": 1, "Medium": 2, "High": 3}[d.severity.value]).severity

        duplicate = False
        if pothole_detected:
            duplicate = has_nearby_point(item.lat, item.lng, item.timestamp, dedup_pool)
            if duplicate:
                deduped += 1

        result = BatchSyncItemResponse(
            filename=item.filename,
            pothole_detected=pothole_detected,
            severity=severity,
            detections=detections,
            coordinates={"lat": item.lat, "lng": item.lng},
            device_id=item.device_id,
            capture_timestamp=item.timestamp,
            received_timestamp=datetime.now(timezone.utc),
            deduped=duplicate,
        )
        results.append(result)

        if pothole_detected and not duplicate:
            dedup_pool.append({"lat": item.lat, "lng": item.lng, "created_at": item.timestamp})
            pending_inserts.append({
                "device_id": item.device_id,
                "lat": item.lat,
                "lng": item.lng,
                "confidence": max(d.confidence for d in detections),
                "severity": severity.value,
                "detections": [d.model_dump() for d in detections],
                "source_mode": "batch-sync",
                "capture_timestamp": item.timestamp.isoformat(),
            })
            pending_result_indices.append(len(results) - 1)
            persisted += 1

    inserted_ids = await save_batch_detections(pending_inserts)
    for result_index, record_id in zip(pending_result_indices, inserted_ids):
        results[result_index].id = record_id

    return BatchSyncResponse(
        total_files=len(decoded_frames),
        processed_files=len(decoded_frames),
        persisted_detections=persisted,
        deduped_detections=deduped,
        results=results,
    )