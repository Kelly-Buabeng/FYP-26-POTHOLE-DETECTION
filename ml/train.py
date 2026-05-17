"""
ml/train.py — Fine-tune YOLOv8n on the Potpot pothole dataset.

Run from the project root:
    python ml/train.py

After training:
    - Best weights saved to: runs/detect/pothole_v1/weights/best.pt
    - Copy to ml/weights/: cp runs/detect/pothole_v1/weights/best.pt ml/weights/best.pt
    - Update .env: MODEL_PATH=ml/weights/best.pt
    - Restart the API server
"""

from pathlib import Path
from ultralytics import YOLO

DATASET_YAML = Path("dataset/data.yaml")
EPOCHS = 50
IMG_SIZE = 640
BATCH = 8           # Reduce to 4 if you run out of VRAM
RUN_NAME = "pothole_v1"


def fix_data_yaml():
    """
    The Roboflow-generated data.yaml uses relative paths like ../train/images.
    We fix them to absolute paths so training works from any working directory.
    """
    import yaml

    yaml_path = DATASET_YAML
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    root = yaml_path.parent.resolve()
    data["train"] = str(root / "train" / "images")
    data["val"] = str(root / "valid" / "images")
    data["test"] = str(root / "test" / "images")
    data["path"] = str(root)

    fixed_path = root / "data_fixed.yaml"
    with open(fixed_path, "w") as f:
        yaml.dump(data, f)

    print(f"[Train] Fixed data.yaml written to: {fixed_path}")
    return str(fixed_path)


def train():
    if not DATASET_YAML.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_YAML}. "
            "Make sure you've extracted the Roboflow zip into dataset/"
        )

    data_yaml = fix_data_yaml()

    print(f"[Train] Starting fine-tune: YOLOv8n → {RUN_NAME}")
    print(f"[Train] Dataset: {data_yaml}")
    print(f"[Train] Epochs: {EPOCHS}, Image size: {IMG_SIZE}, Batch: {BATCH}")

    model = YOLO("yolov8n.pt")

    results = model.train(
        data=data_yaml,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        patience=15,
        project="runs/detect",
        name=RUN_NAME,
        exist_ok=True,
        # Augmentations suited for road/daylight conditions
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.4,
        flipud=0.0,     # Roads don't flip upside-down
        fliplr=0.5,
        mosaic=1.0,
        translate=0.1,
        scale=0.4,
    )

    best = Path(f"runs/detect/{RUN_NAME}/weights/best.pt")
    print(f"\n✅ Training complete.")
    print(f"   Best weights : {best.resolve()}")
    print(f"   mAP50        : {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    print(f"\nNext steps:")
    print(f"   cp {best} ml/weights/best.pt")
    print(f"   Set MODEL_PATH=ml/weights/best.pt in .env")


if __name__ == "__main__":
    train()
