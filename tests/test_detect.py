"""
Tests for FYP-26 Pothole Detection API.
Run with: pytest tests/ -v
"""

import io
import json
import zipfile
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from PIL import Image

from app.schemas.detection import DetectionItem, BoundingBox, Severity, VideoFrameSummary

API_KEY = "dev-key-change-in-production"
HEADERS = {"X-API-Key": API_KEY}
GHANA_LAT, GHANA_LNG = 5.6037, -0.1870


def _make_image_bytes(width=640, height=480) -> bytes:
    img = Image.new("RGB", (width, height), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def client():
    mock_detection = DetectionItem(
        label="Pothole",
        confidence=0.87,
        severity=Severity.HIGH,
        bbox=BoundingBox(x1=100, y1=150, x2=400, y2=380),
    )
    with patch("app.services.detector.detector") as mock_detector:
        mock_detector.is_loaded = True
        mock_detector.load = MagicMock()
        mock_detector.predict = MagicMock(return_value=[mock_detection])
        from app.main import app
        with TestClient(app) as c:
            yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200


# ── Authentication ────────────────────────────────────────────────────────────

def test_detect_requires_api_key(client):
    r = client.post(
        "/api/v1/detect",
        data={"lat": str(GHANA_LAT), "lng": str(GHANA_LNG)},
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 422  # missing header


def test_detect_rejects_wrong_api_key(client):
    r = client.post(
        "/api/v1/detect",
        headers={"X-API-Key": "wrong-key"},
        data={"lat": str(GHANA_LAT), "lng": str(GHANA_LNG)},
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 401


# ── Ghana Coordinate Validation ───────────────────────────────────────────────

def test_detect_rejects_coords_outside_ghana(client):
    # London coordinates
    r = client.post(
        "/api/v1/detect",
        headers=HEADERS,
        data={"lat": "51.5074", "lng": "-0.1278"},
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 422
    assert "Ghana" in r.json()["detail"]


def test_detect_rejects_atlantic_ocean(client):
    r = client.post(
        "/api/v1/detect",
        headers=HEADERS,
        data={"lat": "0.0", "lng": "-20.0"},
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 422


# ── Detection ─────────────────────────────────────────────────────────────────

def test_detect_valid(client):
    r = client.post(
        "/api/v1/detect",
        headers=HEADERS,
        data={"lat": str(GHANA_LAT), "lng": str(GHANA_LNG), "device_id": "test-01"},
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["pothole_detected"] is True
    assert body["severity"] == "High"
    assert body["detections"][0]["severity"] == "High"
    assert body["coordinates"] == {"lat": GHANA_LAT, "lng": GHANA_LNG}


def test_detect_rejects_non_image(client):
    r = client.post(
        "/api/v1/detect",
        headers=HEADERS,
        data={"lat": str(GHANA_LAT), "lng": str(GHANA_LNG)},
        files={"image": ("file.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400


def test_detect_requires_coordinates(client):
    r = client.post(
        "/api/v1/detect",
        headers=HEADERS,
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 422


# ── Heatmap & Stats ───────────────────────────────────────────────────────────

def test_heatmap_requires_api_key(client):
    r = client.get("/api/v1/heatmap")
    assert r.status_code == 422


def test_heatmap_returns_points_with_severity(client):
    r = client.get("/api/v1/heatmap", headers=HEADERS)
    assert r.status_code == 200
    points = r.json()
    assert isinstance(points, list)
    assert len(points) > 0
    assert all({"lat", "lng", "intensity", "severity"}.issubset(p.keys()) for p in points)


def test_heatmap_severity_filter(client):
    r = client.get("/api/v1/heatmap?severity=High", headers=HEADERS)
    assert r.status_code == 200


def test_stats_shape(client):
    r = client.get("/api/v1/stats", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "total_detections" in body
    assert "high_severity" in body
    assert "medium_severity" in body
    assert "low_severity" in body
    assert "avg_confidence" in body
    assert "mock_mode" in body


def test_detections_list(client):
    r = client.get("/api/v1/detections", headers=HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_detections_list_pagination(client):
    r = client.get("/api/v1/detections?page=1&page_size=5", headers=HEADERS)
    assert r.status_code == 200


def test_video_endpoint_rejects_non_video(client):
    r = client.post(
        "/api/v1/detect/video",
        headers=HEADERS,
        files={"video": ("clip.txt", b"not a video", "text/plain")},
    )
    assert r.status_code == 400


def test_video_endpoint_returns_summary(client):
    with patch("app.api.v1.endpoints.video.process_video_upload") as mock_process, patch(
        "app.api.v1.endpoints.video.save_video_detection"
    ) as mock_save:
        mock_process.return_value = (
            [
                VideoFrameSummary(
                    frame_index=0,
                    timestamp_ms=0,
                    pothole_detected=True,
                    severity=Severity.HIGH,
                    detections=[
                        DetectionItem(
                            label="Pothole",
                            confidence=0.91,
                            severity=Severity.HIGH,
                            bbox=BoundingBox(x1=10, y1=10, x2=50, y2=50),
                        )
                    ],
                )
            ],
            {"lat": 5.6, "lng": -0.18},
            {
                "duration_ms": 1000,
                "fps": 30.0,
                "total_frames": 60,
                "processed_frames": 1,
                "discarded_frames": 1,
                "pothole_detected": True,
                "best_severity": "High",
                "best_frame_index": 0,
                "file_name": "clip.mp4",
            },
        )
        mock_save.return_value = "video-123"

        r = client.post(
            "/api/v1/detect/video",
            headers=HEADERS,
            files={"video": ("clip.mp4", b"video-bytes", "video/mp4")},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "video-123"
    assert body["pothole_detected"] is True
    assert body["best_severity"] == "High"
    assert body["gps_coordinates"] == {"lat": 5.6, "lng": -0.18}


def test_live_endpoint_returns_ingestion_response(client):
    with patch("app.api.v1.endpoints.ingestion.process_live_frame") as mock_process, patch(
        "app.api.v1.endpoints.ingestion.is_duplicate_detection"
    ) as mock_duplicate, patch("app.api.v1.endpoints.ingestion.save_live_detection") as mock_save:
        mock_process.return_value = (
            {
                "id": None,
                "source_mode": "live",
                "pothole_detected": True,
                "severity": Severity.HIGH,
                "detections": [
                    DetectionItem(
                        label="Pothole",
                        confidence=0.92,
                        severity=Severity.HIGH,
                        bbox=BoundingBox(x1=10, y1=10, x2=80, y2=80),
                    )
                ],
                "coordinates": {"lat": GHANA_LAT, "lng": GHANA_LNG},
                "device_id": "phone-01",
                "capture_timestamp": "2026-08-20T12:00:00+00:00",
                "received_timestamp": "2026-08-20T12:00:01+00:00",
            },
            [
                DetectionItem(
                    label="Pothole",
                    confidence=0.92,
                    severity=Severity.HIGH,
                    bbox=BoundingBox(x1=10, y1=10, x2=80, y2=80),
                )
            ],
        )
        mock_duplicate.return_value = False
        mock_save.return_value = "live-123"

        r = client.post(
            "/api/v1/detect/live",
            headers=HEADERS,
            data={
                "lat": str(GHANA_LAT),
                "lng": str(GHANA_LNG),
                "timestamp": "2026-08-20T12:00:00+00:00",
                "device_id": "phone-01",
            },
            files={"image": ("frame.jpg", _make_image_bytes(), "image/jpeg")},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["source_mode"] == "live"
    assert body["id"] == "live-123"


def test_batch_sync_endpoint_accepts_zip_and_manifest(client):
    archive_buf = io.BytesIO()
    with zipfile.ZipFile(archive_buf, "w") as zf:
        zf.writestr("frame1.jpg", _make_image_bytes())

    manifest_payload = {
        "items": [
            {
                "filename": "frame1.jpg",
                "lat": GHANA_LAT,
                "lng": GHANA_LNG,
                "timestamp": "2026-08-20T12:00:00+00:00",
                "device_id": "sd-card-01",
            }
        ]
    }

    with patch("app.api.v1.endpoints.ingestion.decode_batch_payload") as mock_decode, patch(
        "app.api.v1.endpoints.ingestion.run_batch_inference"
    ) as mock_infer, patch("app.api.v1.endpoints.ingestion.is_duplicate_detection") as mock_duplicate:
        mock_decode.return_value = []
        mock_infer.return_value = []
        mock_duplicate.return_value = False

        r = client.post(
            "/api/v1/detect/batch-sync",
            headers=HEADERS,
            files={
                "archive": ("batch.zip", archive_buf.getvalue(), "application/zip"),
                "manifest": ("manifest.json", json.dumps(manifest_payload).encode("utf-8"), "application/json"),
            },
        )

    assert r.status_code == 200
    assert r.json()["source_mode"] == "batch-sync"
