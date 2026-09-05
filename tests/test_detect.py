"""
Tests for FYP-26 Pothole Detection API.
Run with: pytest tests/ -v
"""

import io
import json
import zipfile
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from PIL import Image

from app.schemas.detection import (
    DetectionItem,
    BoundingBox,
    Severity,
    VideoFrameSummary,
    LiveIngestionResponse,
)

API_KEY = "dev-key-change-in-production"
HEADERS = {"X-API-Key": API_KEY}
GHANA_LAT, GHANA_LNG = 5.6037, -0.1870


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
        severity=Severity.HIGH,
        bbox=BoundingBox(x1=100, y1=150, x2=400, y2=380),
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
            headers=HEADERS,
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
            LiveIngestionResponse(
                id=None,
                source_mode="live",
                pothole_detected=True,
                severity=Severity.HIGH,
                detections=[
                    DetectionItem(
                        label="Pothole",
                        confidence=0.92,
                        severity=Severity.HIGH,
                        bbox=BoundingBox(x1=10, y1=10, x2=80, y2=80),
                    )
                ],
                coordinates={"lat": GHANA_LAT, "lng": GHANA_LNG},
                device_id="phone-01",
                capture_timestamp="2026-08-20T12:00:00+00:00",
                received_timestamp="2026-08-20T12:00:01+00:00",
            ),
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


def test_batch_sync_deduplicates_nearby_frames_and_persists_the_rest(client):
    """
    Two frames a few meters apart, seconds apart — the slow-driving scenario
    the spatial dedup exists for. Only the first should persist; the second
    should be flagged deduped and never reach save_batch_detections.
    """
    from app.services.ingestion_processor import DecodedBatchFrame
    from app.schemas.detection import IngestionManifestItem

    frame_image = Image.new("RGB", (32, 32), color=(80, 80, 80))
    close_detection = DetectionItem(
        label="Pothole",
        confidence=0.8,
        severity=Severity.LOW,
        bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10),
    )

    decoded_frames = [
        DecodedBatchFrame(
            image=frame_image,
            manifest_item=IngestionManifestItem(
                filename="frame1.jpg",
                lat=GHANA_LAT,
                lng=GHANA_LNG,
                timestamp=datetime.fromisoformat("2026-08-20T12:00:00+00:00"),
                device_id="sd-card-01",
            ),
        ),
        DecodedBatchFrame(
            image=frame_image,
            manifest_item=IngestionManifestItem(
                filename="frame2.jpg",
                lat=GHANA_LAT + 0.00002,  # ~2m north — within the 5m tolerance
                lng=GHANA_LNG,
                timestamp=datetime.fromisoformat("2026-08-20T12:00:05+00:00"),
                device_id="sd-card-01",
            ),
        ),
    ]

    with patch("app.api.v1.endpoints.ingestion.decode_batch_payload") as mock_decode, patch(
        "app.api.v1.endpoints.ingestion.run_batch_inference"
    ) as mock_infer, patch(
        "app.api.v1.endpoints.ingestion.get_dedup_candidate_points"
    ) as mock_pool, patch(
        "app.api.v1.endpoints.ingestion.save_batch_detections"
    ) as mock_save:
        mock_decode.return_value = decoded_frames
        mock_infer.return_value = [[close_detection], [close_detection]]
        mock_pool.return_value = []
        mock_save.return_value = ["batch-row-1"]

        r = client.post(
            "/api/v1/detect/batch-sync",
            headers=HEADERS,
            files={
                "archive": ("batch.zip", _make_image_bytes(), "application/zip"),
                "manifest": ("manifest.json", b"{}", "application/json"),
            },
        )

    assert r.status_code == 200
    body = r.json()
    assert body["persisted_detections"] == 1
    assert body["deduped_detections"] == 1

    # save_batch_detections is called once with only the non-duplicate row.
    mock_save.assert_called_once()
    (inserted_records,), _ = mock_save.call_args
    assert len(inserted_records) == 1
    assert inserted_records[0]["source_mode"] == "batch-sync"

    by_filename = {item["filename"]: item for item in body["results"]}
    assert by_filename["frame1.jpg"]["deduped"] is False
    assert by_filename["frame1.jpg"]["id"] == "batch-row-1"
    assert by_filename["frame2.jpg"]["deduped"] is True
    assert by_filename["frame2.jpg"]["id"] is None


# ── Reporting & Export ────────────────────────────────────────────────────────

def test_report_requires_api_key(client):
    r = client.get("/api/v1/report")
    assert r.status_code == 422


def test_report_groups_by_region_and_severity(client):
    r = client.get("/api/v1/report", headers=HEADERS)
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
    r = client.get("/api/v1/detections/export?format=csv", headers=HEADERS)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    header = r.text.splitlines()[0]
    for col in ["id", "device_id", "lat", "lng", "confidence", "severity", "region"]:
        assert col in header


def test_export_geojson_is_valid_feature_collection(client):
    r = client.get("/api/v1/detections/export?format=geojson", headers=HEADERS)
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
    r = client.get("/api/v1/detections/export?format=shapefile", headers=HEADERS)
    assert r.status_code == 422
