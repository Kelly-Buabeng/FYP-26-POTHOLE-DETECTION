# ml/weights/

`best.pt` in this directory is a real trained pothole model — fine-tuned on
the [potholes-y1qi8](https://universe.roboflow.com/roadtrain-puq8q/potholes-y1qi8/dataset/1)
Roboflow dataset (569 images, classes `Pothole` and `other`; see
`dataset/data.yaml`). `GET /health` should report `"pothole_model_ready": true`.

`app/services/detector.py` checks the loaded model's class names at startup
and refuses to run detections (`/api/v1/detect` returns `503`) when the
`pothole` class isn't present, instead of silently reporting "no pothole" for
every image — this is what would happen if `best.pt` were ever replaced with
an untrained or mislabeled checkpoint.

## Retraining on a larger dataset (planned)

569 images is a small dataset. The plan is to switch to a larger pothole
dataset and retrain before relying on this in the field:

1. Download the dataset images (gitignored, not committed) into
   `dataset/train`, `dataset/valid`, `dataset/test`, and update
   `dataset/data.yaml` to point at the new dataset.
2. `python ml/train.py`
3. `cp runs/detect/pothole_v1/weights/best.pt ml/weights/best.pt`
4. Restart the API — `/health` should report `"pothole_model_ready": true`,
   and confirm the class names in the log line still include `Pothole`.
