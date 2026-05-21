"""
Detection repository — all Supabase reads/writes in one place.
Falls back to mock data if credentials are not configured.
"""

import uuid
import random
from typing import Optional

from app.db.client import get_db
from app.schemas.detection import DetectionItem, HeatmapPoint, StatsResponse, DetectionRecord, Severity
from app.core.config import get_settings


def _is_configured() -> bool:
    settings = get_settings()
    return (
        settings.supabase_url != ""
        and settings.supabase_service_key != "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJkZWNka2x0ZnZ3dG9lcXV0Zmx0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODk1NjA1MiwiZXhwIjoyMDk0NTMyMDUyfQ.a2HEog9W5uZvSpzHSz98iafqwxDBlu13XvYEPa-BFe8"
    )


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
