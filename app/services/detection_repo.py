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
from app.schemas.detection import DetectionItem, HeatmapPoint, StatsResponse
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
    detections: list[DetectionItem],
    device_id: str,
) -> Optional[str]:
    if not _is_configured():
        mock_id = str(uuid.uuid4())
        print(f"[DB] Mock save — lat={lat}, lng={lng}, conf={confidence:.2f}, id={mock_id}")
        return mock_id

    data = {
        "device_id": device_id,
        "lat": lat,
        "lng": lng,
        "confidence": confidence,
        "detections": [d.model_dump() for d in detections],
    }

    result = get_db().table("detections").insert(data).execute()
    if result.data:
        return result.data[0]["id"]
    return None


async def get_heatmap_points(
    limit: int = 500,
    min_confidence: float = 0.4,
) -> list[HeatmapPoint]:
    if not _is_configured():
        return _mock_heatmap()

    result = (
        get_db()
        .table("detections")
        .select("lat, lng, confidence")
        .gte("confidence", min_confidence)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [
        HeatmapPoint(lat=r["lat"], lng=r["lng"], intensity=r["confidence"])
        for r in (result.data or [])
    ]


async def get_stats() -> StatsResponse:
    if not _is_configured():
        return StatsResponse(
            total_detections=0,
            avg_confidence=0.0,
            devices_active=0,
            mock_mode=True,
        )

    result = get_db().table("detections").select("confidence, device_id").execute()
    rows = result.data or []
    confs = [r["confidence"] for r in rows]
    devices = set(r["device_id"] for r in rows)

    return StatsResponse(
        total_detections=len(rows),
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
    """Dev-only sample data so the frontend works without real detections."""
    random.seed(42)
    clusters = [
        (5.6037, -0.1870),  # Accra — swap for your city
        (5.5560, -0.1969),
        (5.6500, -0.1800),
    ]
    points = []
    for base_lat, base_lng in clusters:
        for _ in range(12):
            points.append(HeatmapPoint(
                lat=base_lat + random.uniform(-0.02, 0.02),
                lng=base_lng + random.uniform(-0.02, 0.02),
                intensity=round(random.uniform(0.45, 0.97), 2),
            ))
    return points
