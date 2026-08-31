"""
Pothole detector service — wraps YOLOv8.

Loaded once at startup via lifespan. After training on the Potpot dataset,
set MODEL_PATH=ml/weights/best.pt in .env to switch from the base YOLOv8n
to the fine-tuned pothole model.
"""

import io
from pathlib import Path
from PIL import Image
from ultralytics import YOLO

from app.core.config import get_settings
from app.schemas.detection import DetectionItem, BoundingBox


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
                
                # Filter: Only keep pothole detections
                if label.lower() != "pothole":
                    continue
                    
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append(DetectionItem(
                    label=label,
                    confidence=round(conf, 4),
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
