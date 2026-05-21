"""
Pothole detector service — wraps YOLOv8.

Severity is calculated from bounding box area as a percentage of the image:
  - Low    : bbox covers < 5% of image area
  - Medium : bbox covers 5% – 15% of image area  
  - High   : bbox covers > 15% of image area

These thresholds are based on visual inspection of the Potpot dataset
and can be tuned after field testing.
"""

from PIL import Image
from ultralytics import YOLO

from app.core.config import get_settings
from app.schemas.detection import DetectionItem, BoundingBox, Severity


def _calculate_severity(x1: float, y1: float, x2: float, y2: float,
                         img_width: int, img_height: int) -> Severity:
    """
    Classify pothole severity by what percentage of the image it occupies.
    Larger bbox = closer to camera = more severe road damage.
    """
    bbox_area = (x2 - x1) * (y2 - y1)
    image_area = img_width * img_height
    ratio = bbox_area / image_area

    if ratio > 0.15:
        return Severity.HIGH
    elif ratio > 0.05:
        return Severity.MEDIUM
    else:
        return Severity.LOW


class PotholeDetector:
    def __init__(self):
        self._model: YOLO | None = None

    def load(self):
        settings = get_settings()
        model_path = settings.model_path
        print(f"[Detector] Loading model: {model_path}")
        self._model = YOLO(model_path)
        print(f"[Detector] Ready. Classes: {self._model.names}")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def predict(self, image: Image.Image) -> list[DetectionItem]:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded.")

        img_width, img_height = image.size
        settings = get_settings()

        results = self._model.predict(
            source=image,
            conf=settings.confidence_threshold,
            verbose=False,
        )

        detections: list[DetectionItem] = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = self._model.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                severity = _calculate_severity(x1, y1, x2, y2, img_width, img_height)

                detections.append(DetectionItem(
                    label=label,
                    confidence=round(conf, 4),
                    severity=severity,
                    bbox=BoundingBox(
                        x1=round(x1, 2),
                        y1=round(y1, 2),
                        x2=round(x2, 2),
                        y2=round(y2, 2),
                    ),
                ))

        return detections


# Singleton
detector = PotholeDetector()
