"""
Pothole detector service — wraps YOLOv8.

Severity is calculated from bounding box area as a percentage of the image:
  - Low    : bbox covers < 5% of image area
  - Medium : bbox covers 5% – 15% of image area  
  - High   : bbox covers > 15% of image area

These thresholds are based on visual inspection of the Potpot dataset
and can be tuned after field testing.
"""

import os
from pathlib import Path

from PIL import Image

os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

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
        self._pothole_capable: bool = False

    def load(self):
        settings = get_settings()
        model_candidates = []
        configured_path = settings.model_path.strip()

        if configured_path:
            model_candidates.append(configured_path)

        root_model = str(Path(__file__).resolve().parents[2] / "yolov8n.pt")
        if root_model not in model_candidates:
            model_candidates.append(root_model)

        if "yolov8n.pt" not in model_candidates:
            model_candidates.append("yolov8n.pt")

        last_error: Exception | None = None

        for candidate in model_candidates:
            try:
                print(f"[Detector] Loading model: {candidate}")
                model = YOLO(candidate)
                pothole_capable = any(
                    str(name).strip().lower() == "pothole"
                    for name in model.names.values()
                )
                print(f"[Detector] Ready. Classes: {model.names}")
                if not pothole_capable:
                    print(
                        f"[Detector] WARNING: '{candidate}' has no 'pothole' class "
                        f"(classes: {list(model.names.values())}). This is not a "
                        "pothole-trained model — the /detect endpoint will refuse to run "
                        "detections until real trained weights are provided. Run "
                        "ml/train.py on the pothole dataset and set MODEL_PATH to the "
                        "resulting best.pt."
                    )
                self._model = model
                self._pothole_capable = pothole_capable
                return
            except Exception as exc:  # pragma: no cover - depends on runtime artifact
                last_error = exc
                print(f"[Detector] Failed to load {candidate}: {exc}")

        raise RuntimeError(
            "Unable to load a valid YOLO model. Please verify the trained weights or restore a valid default checkpoint."
        ) from last_error

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def is_pothole_capable(self) -> bool:
        """True only if the loaded model's classes actually include 'pothole'."""
        return self._pothole_capable

    def predict(self, image: Image.Image) -> list[DetectionItem]:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded.")
        if not self._pothole_capable:
            raise RuntimeError(
                "Loaded model has no 'pothole' class — it cannot detect potholes. "
                "The configured weights are untrained/placeholder weights. Train "
                "ml/train.py on the pothole dataset and point MODEL_PATH to the "
                "resulting best.pt."
            )

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
                
                # Filter: Only keep pothole detections
                if label.lower() != "pothole":
                    continue
                    
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

    def predict_batch(self, images: list[Image.Image]) -> list[list[DetectionItem]]:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded.")
        if not self._pothole_capable:
            raise RuntimeError(
                "Loaded model has no 'pothole' class — it cannot detect potholes. "
                "The configured weights are untrained/placeholder weights. Train "
                "ml/train.py on the pothole dataset and point MODEL_PATH to the "
                "resulting best.pt."
            )

        settings = get_settings()
        results = self._model.predict(
            source=images,
            conf=settings.confidence_threshold,
            verbose=False,
        )

        batch_detections: list[list[DetectionItem]] = []
        for image, result in zip(images, results):
            img_width, img_height = image.size
            detections: list[DetectionItem] = []
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = self._model.names[cls_id]

                # Filter: Only keep pothole detections
                if label.lower() != "pothole":
                    continue

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
            batch_detections.append(detections)

        return batch_detections


# Singleton
detector = PotholeDetector()
