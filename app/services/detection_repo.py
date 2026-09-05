"""
Detection repository — all Supabase reads/writes in one place.
Falls back to mock data if credentials are not configured.
"""

import uuid
import random
import re
from datetime import datetime, timezone
from typing import Optional

from app.db.client import get_db
from app.schemas.detection import (
    DetectionItem,
    HeatmapPoint,
    StatsResponse,
    DetectionRecord,
    Severity,
)
from app.core.config import get_settings


def _is_configured() -> bool:
    settings = get_settings()
    key = (settings.supabase_service_key or "").strip()
    url = (settings.supabase_url or "").strip()

    if not url or not key:
        return False

    jwt_pattern = r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$"
    if not re.fullmatch(jwt_pattern, key):
        return False

    placeholder_values = {
        "changeme",
        "replace-me",
        "example",
        "demo",
        "dev-key",
        "test-key",
        "replace_with_supabase_service_role_key",
    }
    normalized = key.lower()
    if any(normalized.startswith(p.lower()) for p in placeholder_values):
        return False

    return True


async def save_detection(
    lat: float,
    lng: float,
    confidence: float,
    severity: Severity,
    detections: list[DetectionItem],
    device_id: str,
) -> Optional[str]:
    if not _is_configured():
        mock_id = str(uuid.uuid4())
        print(f"[DB] Mock save — lat={lat}, lng={lng}, conf={confidence:.2f}, severity={severity}, id={mock_id}")
        return mock_id

    data = {
        "device_id": device_id,
        "lat": lat,
        "lng": lng,
        "confidence": confidence,
        "severity": severity.value,
        "detections": [d.model_dump() for d in detections],
    }

    result = get_db().table("detections").insert(data).execute()
    if result.data:
        return result.data[0]["id"]
    return None


async def save_video_detection(
    file_name: str,
    duration_ms: Optional[int],
    fps: Optional[float],
    total_frames: int,
    processed_frames: int,
    discarded_frames: int,
    gps_coordinates: Optional[dict],
    pothole_detected: bool,
    best_severity: Optional[Severity],
    best_frame_index: Optional[int],
    frames: list,
    device_id: str,
) -> Optional[str]:
    if not _is_configured():
        return str(uuid.uuid4())

    data = {
        "device_id": device_id,
        "file_name": file_name,
        "duration_ms": duration_ms,
        "fps": fps,
        "total_frames": total_frames,
        "processed_frames": processed_frames,
        "discarded_frames": discarded_frames,
        "gps_coordinates": gps_coordinates,
        "pothole_detected": pothole_detected,
        "best_severity": best_severity.value if best_severity else None,
        "best_frame_index": best_frame_index,
        "frames": frames,
    }

    result = get_db().table("video_detections").insert(data).execute()
    if result.data:
        return result.data[0]["id"]
    return None


async def save_live_detection(
    lat: float,
    lng: float,
    confidence: float,
    severity: Severity,
    detections: list[DetectionItem],
    device_id: str,
    capture_timestamp: datetime,
) -> Optional[str]:
    if not _is_configured():
        return str(uuid.uuid4())

    data = {
        "device_id": device_id,
        "lat": lat,
        "lng": lng,
        "confidence": confidence,
        "severity": severity.value,
        "detections": [d.model_dump() for d in detections],
        "source_mode": "live",
        "capture_timestamp": capture_timestamp.isoformat(),
    }

    result = get_db().table("detections").insert(data).execute()
    if result.data:
        return result.data[0]["id"]
    return None


async def is_duplicate_detection(
    lat: float,
    lng: float,
    capture_timestamp: datetime,
    tolerance_meters: float = 5.0,
    time_window_seconds: int = 600,
) -> bool:
    if not _is_configured():
        return False

    if capture_timestamp.tzinfo is None:
        capture_timestamp = capture_timestamp.replace(tzinfo=timezone.utc)
    query = (
        get_db()
        .table("detections")
        .select("id, lat, lng, created_at")
        .order("created_at", desc=True)
        .limit(25)
    )
    result = query.execute()
    rows = result.data or []

    return has_nearby_point(
        lat, lng, capture_timestamp, rows, tolerance_meters, time_window_seconds
    )


def has_nearby_point(
    lat: float,
    lng: float,
    timestamp: datetime,
    candidates: list[dict],
    tolerance_meters: float = 5.0,
    time_window_seconds: int = 600,
) -> bool:
    """Haversine + time-window check against an in-memory pool of {lat, lng, created_at} rows.

    Used by batch-sync to dedupe a whole SD-card sync against one prefetched
    pool (plus points already accepted earlier in the same batch) instead of
    issuing a database round trip per frame.
    """
    for row in candidates:
        row_lat = row.get("lat")
        row_lng = row.get("lng")
        created_at = row.get("created_at")
        if row_lat is None or row_lng is None or created_at is None:
            continue

        if _haversine_meters(lat, lng, float(row_lat), float(row_lng)) <= tolerance_meters:
            if isinstance(created_at, datetime):
                created_dt = created_at
            else:
                try:
                    created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                except Exception:
                    continue
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            delta = abs((timestamp - created_dt).total_seconds())
            if delta <= time_window_seconds:
                return True

    return False


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2

    earth_radius_m = 6371000.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * earth_radius_m * atan2(sqrt(a), sqrt(1 - a))


async def get_dedup_candidate_points(limit: int = 200) -> list[dict]:
    """
    Recent {lat, lng, created_at} rows used as a dedup pool for batch-sync.

    Fetched once per batch (instead of once per frame) so a whole SD-card
    sync stays a handful of round trips instead of N.
    """
    if not _is_configured():
        return []

    result = (
        get_db()
        .table("detections")
        .select("lat, lng, created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


async def save_batch_detections(records: list[dict]) -> list[Optional[str]]:
    """
    Bulk-insert non-duplicate batch-sync detections in a single round trip
    (mirrors the model(image_list) batching used for inference).
    """
    if not records:
        return []

    if not _is_configured():
        return [str(uuid.uuid4()) for _ in records]

    result = get_db().table("detections").insert(records).execute()
    rows = result.data or []
    return [row.get("id") for row in rows]


async def get_heatmap_points(
    limit: int = 500,
    min_confidence: float = 0.4,
    severity_filter: Optional[str] = None,
) -> list[HeatmapPoint]:
    if not _is_configured():
        return _mock_heatmap()

    query = (
        get_db()
        .table("detections")
        .select("lat, lng, confidence, severity")
        .gte("confidence", min_confidence)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if severity_filter:
        query = query.eq("severity", severity_filter)

    result = query.execute()

    return [
        HeatmapPoint(
            lat=r["lat"],
            lng=r["lng"],
            intensity=r["confidence"],
            severity=Severity(r.get("severity", "Low")),
        )
        for r in (result.data or [])
    ]


async def get_detections_list(
    page: int = 1,
    page_size: int = 20,
    severity_filter: Optional[str] = None,
) -> list[DetectionRecord]:
    if not _is_configured():
        return _mock_detections_list()

    offset = (page - 1) * page_size

    query = (
        get_db()
        .table("detections")
        .select("id, lat, lng, confidence, severity, device_id, created_at, detections")
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
    )

    if severity_filter:
        query = query.eq("severity", severity_filter)

    result = query.execute()

    return [
        DetectionRecord(
            id=r["id"],
            lat=r["lat"],
            lng=r["lng"],
            confidence=r["confidence"],
            severity=Severity(r.get("severity", "Low")),
            device_id=r["device_id"],
            created_at=r["created_at"],
            detections=r.get("detections", []),
        )
        for r in (result.data or [])
    ]


async def get_stats() -> StatsResponse:
    if not _is_configured():
        return StatsResponse(
            total_detections=0,
            high_severity=0,
            medium_severity=0,
            low_severity=0,
            avg_confidence=0.0,
            devices_active=0,
            mock_mode=True,
        )

    result = get_db().table("detections").select("confidence, device_id, severity").execute()
    rows = result.data or []
    confs = [r["confidence"] for r in rows]
    devices = set(r["device_id"] for r in rows)

    return StatsResponse(
        total_detections=len(rows),
        high_severity=sum(1 for r in rows if r.get("severity") == "High"),
        medium_severity=sum(1 for r in rows if r.get("severity") == "Medium"),
        low_severity=sum(1 for r in rows if r.get("severity") == "Low"),
        avg_confidence=round(sum(confs) / len(confs), 4) if confs else 0.0,
        devices_active=len(devices),
        mock_mode=False,
    )


async def get_all_detections(
    min_confidence: float = 0.0,
    limit: int = 5000,
) -> list[dict]:
    """Raw detection rows for /report and /detections/export."""
    if not _is_configured():
        return _mock_detections(min_confidence, limit)

    result = (
        get_db()
        .table("detections")
        .select("id, device_id, lat, lng, confidence, detections, created_at")
        .gte("confidence", min_confidence)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


async def delete_detection(detection_id: str) -> bool:
    if not _is_configured():
        return True

    result = (
        get_db()
        .table("detections")
        .delete()
        .eq("id", detection_id)
        .execute()
    )
    return bool(result.data)


def _mock_detections(min_confidence: float, limit: int) -> list[dict]:
    """Dev-only sample data so /report and /detections/export work without real detections."""
    random.seed(42)
    clusters = [
        (5.6037, -0.1870, "esp32-accra"),   # Greater Accra
        (6.6885, -1.6244, "esp32-kumasi"),  # Ashanti
        (9.4008, -0.8393, "esp32-tamale"),  # Northern
    ]
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for base_lat, base_lng, device in clusters:
        for _ in range(12):
            conf = round(random.uniform(0.40, 0.97), 2)
            if conf < min_confidence:
                continue
            rows.append({
                "id": str(uuid.uuid4()),
                "device_id": device,
                "lat": base_lat + random.uniform(-0.05, 0.05),
                "lng": base_lng + random.uniform(-0.05, 0.05),
                "confidence": conf,
                "detections": [{
                    "label": "Pothole",
                    "confidence": conf,
                    "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
                }],
                "created_at": now,
            })
    return rows[:limit]


def _mock_heatmap() -> list[HeatmapPoint]:
    random.seed(42)
    clusters = [
        (5.6037, -0.1870, Severity.HIGH),
        (5.5560, -0.1969, Severity.MEDIUM),
        (5.6500, -0.1800, Severity.LOW),
    ]
    points = []
    for base_lat, base_lng, sev in clusters:
        for _ in range(12):
            points.append(HeatmapPoint(
                lat=base_lat + random.uniform(-0.02, 0.02),
                lng=base_lng + random.uniform(-0.02, 0.02),
                intensity=round(random.uniform(0.45, 0.97), 2),
                severity=sev,
            ))
    return points


def _mock_detections_list() -> list[DetectionRecord]:
    return [
        DetectionRecord(
            id=str(uuid.uuid4()),
            lat=5.6037,
            lng=-0.1870,
            confidence=0.87,
            severity=Severity.HIGH,
            device_id="manual",
            created_at="2025-01-01T00:00:00+00:00",
            detections=[],
        )
    ]
