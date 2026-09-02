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
def app_with_mock_detector():
    """
    Patches the detector singleton before app.main is ever imported, so both
    the FastAPI lifespan (which calls detector.load()) and the /detect
    endpoint bind to the same mock — this avoids loading the real YOLO model
    during tests entirely.
    """
    with patch("app.services.detector.detector") as mock_detector:
        mock_detector.is_loaded = True
        mock_detector.is_pothole_capable = True
        mock_detector.load = MagicMock()
        from app.main import app
        yield app, mock_detector


@pytest.fixture(scope="module")
def client(app_with_mock_detector):
    app, mock_detector = app_with_mock_detector
    mock_detection = DetectionItem(
        label="Pothole",
        confidence=0.87,
        bbox=BoundingBox(x1=100, y1=150, x2=300, y2=280),
    )
    mock_detector.is_pothole_capable = True
    mock_detector.predict = MagicMock(return_value=[mock_detection])
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


def test_load_marks_model_without_pothole_class_as_not_capable():
    from app.services import detector as detector_module

    class CocoModel:
        names = {0: "person", 1: "car", 2: "dog"}

    original_yolo = detector_module.YOLO
    detector_module.YOLO = lambda path: CocoModel()
    try:
        detector = detector_module.PotholeDetector()
        detector.load()
        assert detector.is_loaded is True
        assert detector.is_pothole_capable is False
    finally:
        detector_module.YOLO = original_yolo


def test_load_marks_model_with_pothole_class_as_capable():
    from app.services import detector as detector_module

    class PotholeModel:
        names = {0: "Pothole"}

    original_yolo = detector_module.YOLO
    detector_module.YOLO = lambda path: PotholeModel()
    try:
        detector = detector_module.PotholeDetector()
        detector.load()
        assert detector.is_pothole_capable is True
    finally:
        detector_module.YOLO = original_yolo


def test_predict_refuses_when_model_lacks_pothole_class():
    from app.services import detector as detector_module

    class CocoModel:
        names = {0: "person"}

    original_yolo = detector_module.YOLO
    detector_module.YOLO = lambda path: CocoModel()
    try:
        detector = detector_module.PotholeDetector()
        detector.load()
        with pytest.raises(RuntimeError):
            detector.predict(Image.new("RGB", (10, 10)))
    finally:
        detector_module.YOLO = original_yolo


def test_detect_returns_503_when_model_not_pothole_capable(client, app_with_mock_detector):
    _, mock_detector = app_with_mock_detector
    original = mock_detector.is_pothole_capable
    mock_detector.is_pothole_capable = False
    try:
        r = client.post(
            "/api/v1/detect",
            data={"lat": "5.6037", "lng": "-0.1870"},
            files={"image": ("road.jpg", _make_image_bytes(), "image/jpeg")},
        )
    finally:
        mock_detector.is_pothole_capable = original
    assert r.status_code == 503


def test_nearest_region_matches_known_city():
    from app.services.geo import nearest_region

    assert nearest_region(5.6037, -0.1870) == "Greater Accra"
    assert nearest_region(6.6885, -1.6244) == "Ashanti"


def test_severity_bucket_thresholds():
    from app.services.geo import severity_bucket

    assert severity_bucket(0.9) == "high"
    assert severity_bucket(0.75) == "high"
    assert severity_bucket(0.6) == "medium"
    assert severity_bucket(0.5) == "medium"
    assert severity_bucket(0.3) == "low"


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


def test_report_groups_by_region_and_severity(client):
    r = client.get("/api/v1/report")
    assert r.status_code == 200
    body = r.json()
    assert "generated_at" in body
    assert body["total_detections"] > 0
    assert len(body["regions"]) > 0
    for region in body["regions"]:
        assert {"region", "total", "avg_confidence", "severity_breakdown"}.issubset(region.keys())
        breakdown = region["severity_breakdown"]
        assert breakdown["high"] + breakdown["medium"] + breakdown["low"] == region["total"]


def test_export_csv_has_expected_columns(client):
    r = client.get("/api/v1/detections/export?format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    header = r.text.splitlines()[0]
    for col in ["id", "device_id", "lat", "lng", "confidence", "severity", "region"]:
        assert col in header


def test_export_geojson_is_valid_feature_collection(client):
    r = client.get("/api/v1/detections/export?format=geojson")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) > 0
    feature = body["features"][0]
    assert feature["geometry"]["type"] == "Point"
    assert "severity" in feature["properties"]
    assert "region" in feature["properties"]


def test_export_rejects_invalid_format(client):
    r = client.get("/api/v1/detections/export?format=shapefile")
    assert r.status_code == 422
