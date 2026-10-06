"""
Detection repository - handles all reads/writes and image storage.
Loads and saves mock data to uploads/mock_detections.json.
"""

import uuid
import os
import random
import re
import io
import json
from datetime import datetime, timezone
from typing import Optional
from PIL import Image, ImageDraw

from app.db.client import get_db
from app.schemas.detection import DetectionItem, HeatmapPoint, StatsResponse, SubmitResponse
from app.core.config import get_settings

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
MOCK_JSON_PATH = os.path.join(UPLOADS_DIR, "mock_detections.json")

_MOCK_STORE: dict[str, dict] = {}

def _is_configured() -> bool:
    settings = get_settings()
    key = (settings.supabase_service_key or "").strip()
    url = (settings.supabase_url or "").strip()

    if not url or not key:
        return False

    jwt_pattern = r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]*$"
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


def _save_mock_store():
    try:
        with open(MOCK_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(_MOCK_STORE, f, indent=2)
    except Exception as e:
        print(f"[DB] Error saving mock json: {e}")


def _ensure_mock_data():
    global _MOCK_STORE
    if _MOCK_STORE:
        return

    if os.path.exists(MOCK_JSON_PATH):
        try:
            with open(MOCK_JSON_PATH, "r", encoding="utf-8") as f:
                _MOCK_STORE = json.load(f)
                print(f"[DB] Loaded {len(_MOCK_STORE)} records from {MOCK_JSON_PATH}")
                return
        except Exception as e:
            print(f"[DB] Error loading mock json: {e}")

    # Default fallback data if mock_detections.json does not exist
    random.seed(42)
    clusters = [
        (5.6037, -0.1870, "ESP32-CAM-ACCRA-01"),
        (5.6508, -0.1869, "Google Chrome (Android Phone) - #7412"),
        (5.5560, -0.1969, "Safari (iPhone 15 Pro) - #3908"),
    ]
    now = datetime.now(timezone.utc).isoformat()
    statuses = ["pending", "confirmed", "declined", "fixed"]

    for base_lat, base_lng, device in clusters:
        for idx in range(4):
            conf = round(random.uniform(0.60, 0.97), 2)
            rec_id = str(uuid.uuid4())
            st = statuses[idx % len(statuses)]
            item = {
                "id": rec_id,
                "device_id": device,
                "lat": round(base_lat + random.uniform(-0.02, 0.02), 6),
                "lng": round(base_lng + random.uniform(-0.02, 0.02), 6),
                "confidence": conf,
                "detections": [{
                    "label": "Pothole",
                    "confidence": conf,
                    "bbox": {"x1": 100.0, "y1": 100.0, "x2": 300.0, "y2": 250.0},
                }],
                "status": st,
                "image_url": f"/api/v1/images/{rec_id}",
                "created_at": now,
            }
            _MOCK_STORE[rec_id] = item
    _save_mock_store()


def save_image_bytes(rec_id: str, raw_bytes: bytes) -> str:
    path = os.path.join(UPLOADS_DIR, f"{rec_id}.jpg")
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        img.save(path, "JPEG", quality=90)
    except Exception:
        with open(path, "wb") as f:
            f.write(raw_bytes)
    return path


def get_image_file_path(rec_id: str) -> str:
    path = os.path.join(UPLOADS_DIR, f"{rec_id}.jpg")
    if os.path.exists(path):
        return path
    img = Image.new("RGB", (600, 400), color=(70, 80, 95))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 150, 550, 350], fill=(40, 45, 50))
    draw.ellipse([200, 200, 400, 300], fill=(20, 20, 20), outline=(220, 50, 50), width=4)
    draw.text((220, 240), f"Pothole Image\nID: {rec_id[:8]}", fill=(255, 255, 255))
    img.save(path, "JPEG")
    return path


async def save_submission(
    lat: float,
    lng: float,
    device_id: str,
    raw_bytes: bytes,
) -> SubmitResponse:
    rec_id = str(uuid.uuid4())
    save_image_bytes(rec_id, raw_bytes)
    now = datetime.now(timezone.utc).isoformat()
    image_url = f"/api/v1/images/{rec_id}"

    record = {
        "id": rec_id,
        "device_id": device_id or "manual",
        "lat": lat,
        "lng": lng,
        "confidence": 0.0,
        "detections": [],
        "status": "pending",
        "image_url": image_url,
        "created_at": now,
    }

    _ensure_mock_data()
    _MOCK_STORE[rec_id] = record
    _save_mock_store()

    if _is_configured():
        base_data = {
            "id": rec_id,
            "device_id": device_id or "manual",
            "lat": lat,
            "lng": lng,
            "confidence": 0.0,
            "detections": [],
        }
        full_data = {**base_data, "status": "pending", "image_url": image_url}
        try:
            get_db().table("detections").insert(full_data).execute()
        except Exception:
            try:
                get_db().table("detections").insert(base_data).execute()
            except Exception as e:
                print(f"[DB] Insert failed: {e}")

    return SubmitResponse(
        id=rec_id,
        message="Pothole report submitted successfully.",
        status="pending",
        device_id=device_id or "manual",
        coordinates={"lat": lat, "lng": lng},
        image_url=image_url,
        timestamp=now,
    )


async def save_detection(
    lat: float,
    lng: float,
    confidence: float,
    detections: list[DetectionItem],
    device_id: str,
    raw_bytes: Optional[bytes] = None,
) -> Optional[str]:
    rec_id = str(uuid.uuid4())
    if raw_bytes:
        save_image_bytes(rec_id, raw_bytes)
    image_url = f"/api/v1/images/{rec_id}"
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "id": rec_id,
        "device_id": device_id or "manual",
        "lat": lat,
        "lng": lng,
        "confidence": confidence,
        "detections": [d.model_dump() for d in detections],
        "status": "confirmed" if confidence >= 0.4 else "pending",
        "image_url": image_url,
        "created_at": now,
    }

    _ensure_mock_data()
    _MOCK_STORE[rec_id] = record
    _save_mock_store()

    if _is_configured():
        base_data = {
            "id": rec_id,
            "device_id": device_id or "manual",
            "lat": lat,
            "lng": lng,
            "confidence": confidence,
            "detections": [d.model_dump() for d in detections],
        }
        full_data = {**base_data, "status": record["status"], "image_url": image_url}
        try:
            get_db().table("detections").insert(full_data).execute()
        except Exception:
            try:
                get_db().table("detections").insert(base_data).execute()
            except Exception as e:
                print(f"[DB] save_detection error: {e}")

    return rec_id


async def get_detection_by_id(rec_id: str) -> Optional[dict]:
    _ensure_mock_data()
    if rec_id in _MOCK_STORE:
        return _MOCK_STORE[rec_id]
    if _is_configured():
        try:
            res = get_db().table("detections").select("*").eq("id", rec_id).execute()
            if res.data:
                item = res.data[0]
                if "status" not in item:
                    item["status"] = "confirmed" if item.get("confidence", 0) >= 0.4 else "pending"
                if "image_url" not in item:
                    item["image_url"] = f"/api/v1/images/{rec_id}"
                return item
        except Exception:
            pass
    return None


async def update_detection_status(rec_id: str, status: str) -> Optional[dict]:
    valid_statuses = {"pending", "confirmed", "declined", "fixed"}
    if status not in valid_statuses:
        status = "confirmed"

    item = await get_detection_by_id(rec_id)
    if not item:
        return None

    item["status"] = status

    if _is_configured():
        try:
            get_db().table("detections").update({"status": status}).eq("id", rec_id).execute()
        except Exception:
            pass

    _MOCK_STORE[rec_id] = item
    _save_mock_store()
    return item


async def update_detection_results(
    rec_id: str,
    confidence: float,
    detections: list[DetectionItem],
    status: Optional[str] = None,
) -> Optional[dict]:
    item = await get_detection_by_id(rec_id)
    if not item:
        return None

    item["confidence"] = confidence
    item["detections"] = [d.model_dump() for d in detections]
    if status:
        item["status"] = status
    elif confidence >= 0.4:
        item["status"] = "confirmed"

    if _is_configured():
        update_payload = {
            "confidence": confidence,
            "detections": [d.model_dump() for d in detections],
        }
        try:
            full_payload = {**update_payload, "status": item["status"]}
            get_db().table("detections").update(full_payload).eq("id", rec_id).execute()
        except Exception:
            try:
                get_db().table("detections").update(update_payload).eq("id", rec_id).execute()
            except Exception as e:
                print(f"[DB] update error: {e}")

    _MOCK_STORE[rec_id] = item
    _save_mock_store()
    return item


async def get_all_detections(
    min_confidence: float = 0.0,
    limit: int = 5000,
    status: Optional[str] = None,
) -> list[dict]:
    _ensure_mock_data()
    items = list(_MOCK_STORE.values())
    if status and status != "all":
        items = [i for i in items if i.get("status") == status]
    if min_confidence > 0:
        items = [i for i in items if i.get("confidence", 0) >= min_confidence]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:limit]


async def get_heatmap_points(
    limit: int = 500,
    min_confidence: float = 0.4,
) -> list[HeatmapPoint]:
    rows = await get_all_detections(min_confidence=min_confidence, limit=limit)
    return [
        HeatmapPoint(
            id=r.get("id"),
            lat=r["lat"],
            lng=r["lng"],
            intensity=r.get("confidence", 0.5),
            image_url=r.get("image_url") or f"/api/v1/images/{r.get('id')}"
        )
        for r in rows
    ]


async def get_stats() -> StatsResponse:
    rows = await get_all_detections(min_confidence=0.0, limit=5000)
    confs = [r.get("confidence", 0.0) for r in rows if r.get("confidence", 0.0) > 0]
    devices = set(r.get("device_id", "manual") for r in rows)
    return StatsResponse(
        total_detections=len(rows),
        avg_confidence=round(sum(confs) / len(confs), 4) if confs else 0.0,
        devices_active=len(devices),
        mock_mode=not _is_configured(),
    )


async def delete_detection(detection_id: str) -> bool:
    _ensure_mock_data()
    if detection_id in _MOCK_STORE:
        del _MOCK_STORE[detection_id]
        _save_mock_store()

    if _is_configured():
        try:
            get_db().table("detections").delete().eq("id", detection_id).execute()
        except Exception:
            pass

    path = os.path.join(UPLOADS_DIR, f"{detection_id}.jpg")
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

    return True
