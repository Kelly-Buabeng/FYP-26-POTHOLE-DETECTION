# ml/weights/

`best.pt` in this directory is currently **not a trained pothole model** — it
is byte-identical to the stock `yolov8n.pt` COCO checkpoint (verify with
`md5sum yolov8n.pt ml/weights/best.pt`). No fine-tuning has actually been run
against the Potpot dataset yet, so this checkpoint has no `pothole` class and
cannot detect potholes.

`app/services/detector.py` checks the loaded model's class names at startup
and refuses to run detections (`/api/v1/detect` returns `503`) when the
`pothole` class isn't present, instead of silently reporting "no pothole" for
every image.

## To get a real pothole model

1. Download the dataset images (they are gitignored, not committed) from
   https://universe.roboflow.com/fyp-pothole-k4loh/potpot-fpp/dataset/1
   into `dataset/train`, `dataset/valid`, `dataset/test`.
2. `python ml/train.py`
3. `cp runs/detect/pothole_v1/weights/best.pt ml/weights/best.pt`
4. Restart the API — `/health` should report `"pothole_model_ready": true`.
