from datetime import datetime
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


class VideoFrameSummary(BaseModel):
    frame_index: int
    timestamp_ms: int
    pothole_detected: bool
    severity: Optional[Severity] = None
    detections: list[DetectionItem] = Field(default_factory=list)


class VideoDetectionResponse(BaseModel):
    id: Optional[str] = None
    file_name: str
    duration_ms: Optional[int] = None
    fps: Optional[float] = None
    total_frames: int
    processed_frames: int
    discarded_frames: int
    gps_coordinates: Optional[dict] = None
    frames: list[VideoFrameSummary]
    pothole_detected: bool
    best_severity: Optional[Severity] = None
    best_frame_index: Optional[int] = None


class VideoDetectionRecord(BaseModel):
    id: str
    file_name: str
    duration_ms: Optional[int] = None
    fps: Optional[float] = None
    total_frames: int
    processed_frames: int
    discarded_frames: int
    gps_coordinates: Optional[dict] = None
    pothole_detected: bool
    best_severity: Optional[Severity] = None
    best_frame_index: Optional[int] = None
    frames: list
    created_at: str


class IngestionTelemetry(BaseModel):
    lat: float
    lng: float
    timestamp: datetime
    device_id: str = "manual"
    source_name: Optional[str] = None
    frame_index: Optional[int] = None


class IngestionManifestItem(BaseModel):
    filename: str
    lat: float
    lng: float
    timestamp: datetime
    device_id: str = "manual"
    frame_index: Optional[int] = None


class IngestionManifest(BaseModel):
    items: list[IngestionManifestItem]


class LiveIngestionResponse(BaseModel):
    id: Optional[str] = None
    source_mode: str = "live"
    pothole_detected: bool
    severity: Optional[Severity] = None
    detections: list[DetectionItem]
    coordinates: dict
    device_id: str
    capture_timestamp: datetime
    received_timestamp: datetime


class BatchSyncItemResponse(BaseModel):
    id: Optional[str] = None
    filename: str
    source_mode: str = "batch-sync"
    pothole_detected: bool
    severity: Optional[Severity] = None
    detections: list[DetectionItem]
    coordinates: dict
    device_id: str
    capture_timestamp: datetime
    received_timestamp: datetime
    deduped: bool = False


class BatchSyncResponse(BaseModel):
    source_mode: str = "batch-sync"
    total_files: int
    processed_files: int
    persisted_detections: int
    deduped_detections: int
    results: list[BatchSyncItemResponse]
