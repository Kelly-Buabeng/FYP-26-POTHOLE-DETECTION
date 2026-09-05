"""
Dual-mode ingestion helpers for live and batch-sync flows.

Live mode processes a single frame with a matching telemetry envelope.
Batch mode opens a ZIP or multipart JPEG bundle, pairs each image with its
manifest entry, and performs batched YOLO inference across the decoded frames.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image

from app.schemas.detection import (
    DetectionItem,
    Severity,
    IngestionManifest,
    IngestionManifestItem,
    IngestionTelemetry,
    LiveIngestionResponse,
    BatchSyncItemResponse,
)
from app.services.detector import detector


# Bounds for the batch-sync ZIP so an oversized or maliciously-crafted
# archive (a "zip bomb": a tiny compressed file that expands to gigabytes)
# can't exhaust memory/CPU before inference even starts.
MAX_ARCHIVE_BYTES = 150 * 1024 * 1024
MAX_FRAME_BYTES = 20 * 1024 * 1024
MAX_TOTAL_DECOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_FRAMES_PER_BATCH = 500


@dataclass
class DecodedBatchFrame:
    image: Image.Image
    manifest_item: IngestionManifestItem


def _worst_severity(detections: list[DetectionItem]) -> Optional[Severity]:
    if not detections:
        return None
    order = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}
    return max(detections, key=lambda d: order[d.severity]).severity


def process_live_frame(image_bytes: bytes, telemetry: IngestionTelemetry) -> tuple[LiveIngestionResponse, list[DetectionItem]]:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    detections = detector.predict(image)
    pothole_detected = any(d.label.lower() == "pothole" and d.confidence >= 0.4 for d in detections)
    worst = _worst_severity(detections) if pothole_detected else None
    received_timestamp = datetime.now(timezone.utc)

    return (
        LiveIngestionResponse(
            pothole_detected=pothole_detected,
            severity=worst,
            detections=detections,
            coordinates={"lat": telemetry.lat, "lng": telemetry.lng},
            device_id=telemetry.device_id,
            capture_timestamp=telemetry.timestamp,
            received_timestamp=received_timestamp,
        ),
        detections,
    )


def _load_manifest_from_json(manifest_bytes: bytes) -> IngestionManifest:
    payload = json.loads(manifest_bytes.decode("utf-8"))
    return IngestionManifest.model_validate(payload)


def _decode_zip_frames(zip_bytes: bytes, manifest: IngestionManifest) -> list[DecodedBatchFrame]:
    if len(manifest.items) > MAX_FRAMES_PER_BATCH:
        raise ValueError(f"Batch has {len(manifest.items)} frames, exceeding the limit of {MAX_FRAMES_PER_BATCH}.")

    decoded: list[DecodedBatchFrame] = []
    total_decompressed_bytes = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as bundle:
        infos_by_name = {Path(info.filename).name: info for info in bundle.infolist() if not info.is_dir()}
        for item in manifest.items:
            info = infos_by_name.get(Path(item.filename).name)
            if not info:
                continue

            if info.file_size > MAX_FRAME_BYTES:
                raise ValueError(
                    f"Frame '{item.filename}' is {info.file_size} bytes uncompressed, "
                    f"exceeding the per-frame limit of {MAX_FRAME_BYTES} bytes."
                )
            total_decompressed_bytes += info.file_size
            if total_decompressed_bytes > MAX_TOTAL_DECOMPRESSED_BYTES:
                raise ValueError(
                    f"Batch exceeds the total decompressed size limit of {MAX_TOTAL_DECOMPRESSED_BYTES} bytes."
                )

            raw = bundle.read(info)
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            decoded.append(DecodedBatchFrame(image=image, manifest_item=item))
    return decoded


def decode_batch_payload(zip_bytes: bytes, manifest_bytes: bytes) -> list[DecodedBatchFrame]:
    if len(zip_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError(f"Archive is {len(zip_bytes)} bytes, exceeding the limit of {MAX_ARCHIVE_BYTES} bytes.")

    manifest = _load_manifest_from_json(manifest_bytes)
    return _decode_zip_frames(zip_bytes, manifest)


def run_batch_inference(frames: list[DecodedBatchFrame]) -> list[list[DetectionItem]]:
    images = [frame.image for frame in frames]
    return detector.predict_batch(images)
