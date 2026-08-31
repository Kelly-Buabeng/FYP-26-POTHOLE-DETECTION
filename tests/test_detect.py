"""
Tests for FYP-26 Pothole Detection API.
Run with: pytest tests/ -v
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from PIL import Image

from app.schemas.detection import DetectionItem, BoundingBox


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
        bbox=BoundingBox(x1=100, y1=150, x2=300, y2=280),
    )
    with patch("app.services.detector.detector") as mock_detector:
        mock_detector.is_loaded = True
        mock_detector.load = MagicMock()
        mock_detector.predict = MagicMock(return_value=[mock_detection])
        from app.main import app
        with TestClient(app) as c:
            yield c


def test_load_falls_back_to_builtin_model_when_custom_weights_are_invalid():
    from app.services import detector as detector_module

    class DummyModel:
        names = {0: "Pothole"}

    def fake_yolo(path):
        if path.endswith("ml/weights/best.pt"):
            raise RuntimeError("weights_only incompatibility")
        return DummyModel()

    original_yolo = detector_module.YOLO
    detector_module.YOLO = fake_yolo
    try:
        detector = detector_module.PotholeDetector()
        detector.load()
        assert detector.is_loaded is True
    finally:
        detector_module.YOLO = original_yolo


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["project"] == "FYP-26 Pothole Detection"


def test_detect_returns_pothole(client):
    r = client.post(
        "/api/v1/detect",
        data={"lat": "5.6037", "lng": "-0.1870", "device_id": "test-device"},
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["pothole_detected"] is True
    assert len(body["detections"]) == 1
    assert body["detections"][0]["label"] == "Pothole"
    assert body["detections"][0]["confidence"] == 0.87
    assert body["coordinates"] == {"lat": 5.6037, "lng": -0.187}
    assert body["device_id"] == "test-device"
    assert "timestamp" in body


def test_detect_rejects_non_image(client):
    r = client.post(
        "/api/v1/detect",
        data={"lat": "5.6037", "lng": "-0.1870"},
        files={"image": ("file.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400


def test_detect_requires_coordinates(client):
    r = client.post(
        "/api/v1/detect",
        files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 422


def test_heatmap_returns_list(client):
    r = client.get("/api/v1/heatmap")
    assert r.status_code == 200
    points = r.json()
    assert isinstance(points, list)
    assert len(points) > 0
    assert all({"lat", "lng", "intensity"}.issubset(p.keys()) for p in points)


def test_heatmap_respects_min_confidence(client):
    r = client.get("/api/v1/heatmap?min_confidence=0.9")
    assert r.status_code == 200


def test_stats_shape(client):
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_detections" in body
    assert "avg_confidence" in body
    assert "devices_active" in body
    assert "mock_mode" in body
