"""
Video processing helpers for lightweight frame sampling and GPS extraction.

Uses OpenCV for frame extraction so the API can process uploads without ffmpeg.
GPS metadata extraction is best-effort: if pymediainfo can read the container,
coordinates are returned when present; otherwise the upload still works.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
from PIL import Image

from app.schemas.detection import DetectionItem, Severity, VideoFrameSummary
from app.services.detector import detector

try:
    from pymediainfo import MediaInfo
except Exception:  # pragma: no cover - optional dependency/runtime parser
    MediaInfo = None


@dataclass
class VideoFrameResult:
    frame_index: int
    timestamp_ms: int
    pothole_detected: bool
    severity: Optional[Severity]
    detections: list[DetectionItem]


def _worst_severity(detections: list[DetectionItem]) -> Optional[Severity]:
    if not detections:
        return None
    order = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}
    return max(detections, key=lambda d: order[d.severity]).severity


def _is_useful_frame(image: Image.Image, min_variance: float = 25.0) -> bool:
    gray = image.convert("L")
    histogram = gray.histogram()
    if not histogram:
        return False

    pixel_count = sum(histogram)
    if pixel_count == 0:
        return False

    mean = sum(index * value for index, value in enumerate(histogram)) / pixel_count
    variance = sum(((index - mean) ** 2) * value for index, value in enumerate(histogram)) / pixel_count
    return variance >= min_variance


def _parse_gps(metadata_file: Path) -> Optional[dict]:
    if MediaInfo is None:
        return None

    media_info = MediaInfo.parse(str(metadata_file))
    for track in media_info.tracks:
        latitude = getattr(track, "other_latitude", None) or getattr(track, "latitude", None)
        longitude = getattr(track, "other_longitude", None) or getattr(track, "longitude", None)
        if latitude and longitude:
            try:
                lat_value = float(latitude[0] if isinstance(latitude, list) else latitude)
                lng_value = float(longitude[0] if isinstance(longitude, list) else longitude)
            except (TypeError, ValueError, IndexError):
                continue
            return {"lat": lat_value, "lng": lng_value}
    return None


def process_video_upload(
    file_bytes: bytes,
    file_name: str,
    sample_every_n_frames: int = 12,
    max_frames: int = 180,
) -> tuple[list[VideoFrameSummary], Optional[dict], dict]:
    """
    Extract a bounded subset of frames, run pothole detection, and return
    summary metadata plus optional GPS coordinates.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / file_name
        video_path.write_bytes(file_bytes)

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError("Could not open video file.")

        fps = capture.get(cv2.CAP_PROP_FPS) or None
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration_ms = int((total_frames / fps) * 1000) if fps else None
        gps_coordinates = _parse_gps(video_path)

        frame_results: list[VideoFrameResult] = []
        processed_frames = 0
        discarded_frames = 0
        best_result: Optional[VideoFrameResult] = None

        frame_index = 0
        sampled_index = 0
        severity_rank = {Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3}

        while processed_frames < max_frames:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_index % sample_every_n_frames != 0:
                frame_index += 1
                discarded_frames += 1
                continue

            sampled_index += 1
            frame_index += 1

            if frame is None:
                discarded_frames += 1
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)

            if not _is_useful_frame(pil_image):
                discarded_frames += 1
                continue

            detections = detector.predict(pil_image)
            pothole_detected = any(
                detection.label.lower() == "pothole" and detection.confidence >= 0.4
                for detection in detections
            )
            severity = _worst_severity(detections) if pothole_detected else None
            timestamp_ms = int(((frame_index - 1) / fps) * 1000) if fps else sampled_index * sample_every_n_frames

            result = VideoFrameResult(
                frame_index=frame_index - 1,
                timestamp_ms=timestamp_ms,
                pothole_detected=pothole_detected,
                severity=severity,
                detections=detections,
            )
            frame_results.append(result)
            processed_frames += 1

            if pothole_detected:
                if best_result is None or (severity and best_result.severity and severity_rank[severity] > severity_rank[best_result.severity]):
                    best_result = result

        capture.release()

        return (
            [
                VideoFrameSummary(
                    frame_index=item.frame_index,
                    timestamp_ms=item.timestamp_ms,
                    pothole_detected=item.pothole_detected,
                    severity=item.severity,
                    detections=item.detections,
                )
                for item in frame_results
            ],
            gps_coordinates,
            {
                "duration_ms": duration_ms,
                "fps": fps,
                "total_frames": total_frames,
                "processed_frames": processed_frames,
                "discarded_frames": discarded_frames,
                "pothole_detected": any(item.pothole_detected for item in frame_results),
                "best_severity": best_result.severity if best_result else None,
                "best_frame_index": best_result.frame_index if best_result else None,
                "file_name": file_name,
            },
        )