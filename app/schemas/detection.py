from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionItem(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox


class DetectionRequest(BaseModel):
    """Used when submitting via JSON (not multipart). For IoT/ESP32-CAM use the /detect endpoint."""
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    device_id: str = "manual"


class DetectionResponse(BaseModel):
    id: Optional[str]
    pothole_detected: bool
    detections: list[DetectionItem]
    coordinates: dict
    device_id: str
    timestamp: str


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    intensity: float = Field(ge=0.0, le=1.0)


class StatsResponse(BaseModel):
    total_detections: int
    avg_confidence: float
    devices_active: int
    mock_mode: bool
