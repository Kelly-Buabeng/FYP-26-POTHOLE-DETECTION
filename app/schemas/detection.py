from pydantic import BaseModel, Field
from typing import Optional, List
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
    image_url: Optional[str] = None
    status: Optional[str] = "pending"


class SubmitResponse(BaseModel):
    id: str
    message: str
    status: str = "pending"
    device_id: str
    coordinates: dict
    image_url: str
    timestamp: str


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Status: pending, confirmed, declined, or fixed")


class HeatmapPoint(BaseModel):
    id: Optional[str] = None
    lat: float
    lng: float
    intensity: float = Field(ge=0.0, le=1.0)
    image_url: Optional[str] = None


class StatsResponse(BaseModel):
    total_detections: int
    avg_confidence: float
    devices_active: int
    mock_mode: bool


class SeverityBreakdown(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0


class RegionReport(BaseModel):
    region: str
    total: int
    avg_confidence: float
    severity_breakdown: SeverityBreakdown


class ReportResponse(BaseModel):
    generated_at: str
    total_detections: int
    regions: list[RegionReport]
