from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionItem(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    bbox: BoundingBox


class DetectionResponse(BaseModel):
    id: Optional[str]
    pothole_detected: bool
    severity: Optional[Severity]       # worst severity in this frame
    detections: list[DetectionItem]
    coordinates: dict
    device_id: str
    timestamp: str


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    intensity: float = Field(ge=0.0, le=1.0)
    severity: Severity = Severity.LOW


class StatsResponse(BaseModel):
    total_detections: int
    high_severity: int
    medium_severity: int
    low_severity: int
    avg_confidence: float
    devices_active: int
    mock_mode: bool


class DetectionRecord(BaseModel):
    """Single row returned by GET /detections"""
    id: str
    lat: float
    lng: float
    confidence: float
    severity: Severity
    device_id: str
    created_at: str
    detections: list
