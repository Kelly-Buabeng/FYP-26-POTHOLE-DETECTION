# FYP-26 Pothole Detection — Backend

YOLOv8-powered road hazard detection API with Supabase geospatial storage.

## Project Structure

```
FYP-26-POTHOLE-DETECTION/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── detect.py       # POST /api/v1/detect
│   │   └── heatmap.py      # GET /api/v1/heatmap, /stats
│   ├── core/config.py      # Settings (pydantic-settings)
│   ├── db/client.py        # Supabase client
│   ├── schemas/detection.py # Pydantic models
│   ├── services/
│   │   ├── detector.py     # YOLOv8 wrapper
│   │   └── detection_repo.py # DB read/write
│   └── main.py             # FastAPI app + lifespan
├── ml/
│   ├── train.py            # Fine-tuning script
│   └── weights/            # Trained .pt files (git-ignored)
├── dataset/                # Roboflow YOLOv8 dataset
├── tests/                  # Pytest test suite
├── schema.sql              # Run in Supabase SQL Editor
├── requirements.txt
└── .env.example
```

## Setup

> Recommended runtime: Python 3.11

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in the following values in `.env` (names are case-insensitive):
# - `SUPABASE_URL` (or `supabase_url`)
# - `SUPABASE_SERVICE_KEY` (or `supabase_service_key`)
# - `API_KEY` (or `api_key`) — required for all protected endpoints
# - `MODEL_PATH` (or `model_path`) — defaults to `yolov8n.pt`
# - `CONFIDENCE_THRESHOLD` (or `confidence_threshold`) — default `0.35`
# - `APP_PORT` (or `app_port`) — default `8000`

# 3. Run Supabase schema
# Paste schema.sql into Supabase Dashboard > SQL Editor > Run

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

## Training

The `ml/weights/best.pt` checked into this repo is a real model fine-tuned on
the [potholes-y1qi8](https://universe.roboflow.com/roadtrain-puq8q/potholes-y1qi8/dataset/1)
dataset (569 images). `GET /health` reports `"pothole_model_ready": true`
when the loaded weights actually have a `pothole` class — if you ever swap in
untrained or mislabeled weights, `/api/v1/detect` returns `503` instead of
silently reporting no potholes. See `ml/weights/README.md` for details,
including plans to retrain on a larger dataset.

```bash
# 1. Download the Roboflow dataset images into dataset/train, dataset/valid, dataset/test
#    (see dataset/data.yaml for the current dataset URL — gitignored, not committed)

python ml/train.py
# Weights saved to: runs/detect/pothole_v1/weights/best.pt
cp runs/detect/pothole_v1/weights/best.pt ml/weights/best.pt
# Update .env: MODEL_PATH=ml/weights/best.pt
# Restart server — check GET /health for "pothole_model_ready": true
```

## Testing

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/detect` | Run YOLOv8 on image + GPS coords |
| POST | `/api/v1/detect/live` | Ingest a single live frame with telemetry |
| POST | `/api/v1/detect/batch-sync` | Sync buffered ZIP/manifest payloads from SD card |
| POST | `/api/v1/detect/video` | Upload a video, sample frames, and detect potholes |
| GET | `/api/v1/heatmap` | Pothole GPS points for frontend map |
| GET | `/api/v1/stats` | Dashboard summary |
| GET | `/api/v1/report` | Detections grouped by severity and region, for GHA |
| GET | `/api/v1/detections/export` | Download detections as CSV or GeoJSON (`?format=csv\|geojson`), for QGIS/ArcGIS |
| DELETE | `/api/v1/detections/{id}` | Remove a false positive |
| GET | `/health` | Health check |

## Dual-Mode Ingestion
The backend now supports two ingestion modes for unstable field connectivity:

- `POST /api/v1/detect/live` accepts a single frame plus decoupled GPS telemetry (`lat`, `lng`, `timestamp`, `device_id`) and stores a live detection only when the new point is not spatially close to a recent pothole record.
- `POST /api/v1/detect/batch-sync` accepts a ZIP archive of JPEG frames plus a JSON manifest with telemetry for each frame. The backend decodes the archive, runs YOLOv8 in batch on the decoded frames, and deduplicates detections using a short-distance / recent-time filter.

This keeps live driving responsive while allowing buffered SD-card syncs to be processed efficiently after reconnects.

## ESP32-CAM Integration (Phase 1 — pending)
The `/api/v1/detect` endpoint accepts `multipart/form-data` with:
- `image` — JPEG frame
- `lat` — latitude from NEO-6M GPS
- `lng` — longitude from NEO-6M GPS
- `device_id` — ESP32-CAM unit identifier

Notes and constraints for `/api/v1/detect`:
- Requires header `X-API-Key` with a valid API key (set `API_KEY` in `.env`).
- Accepts common image types (JPEG/PNG) only; server validates `Content-Type`.
- Maximum image size: 10 MB. Large files return HTTP 413.
- Coordinates are validated to fall within Ghana's bounding box by default (lat: 4.5–11.5, lng: -3.5–1.5). Requests outside this box are rejected.
- A detection is considered a pothole only if the model returns a `label` of `pothole` with confidence >= 0.4; the app will persist confirmed detections to Supabase.

## Video Uploads
The `/api/v1/detect/video` endpoint accepts an uploaded road video and processes only a sampled subset of useful frames.

Behavior:
- Frames are sampled with OpenCV instead of decoding every frame.
- Low-information frames are discarded before inference to keep the pipeline lightweight.
- GPS metadata is returned when present in the video container metadata.
- The response contains a compact summary of the frames that were actually analyzed.

Supported inputs depend on the local OpenCV build, but MP4, MOV, and AVI are the intended upload formats.

## Database / Supabase

- The schema in `schema.sql` requires the PostGIS extension and includes a `detections` table with a `location` geography column and a `severity` column (`Low`/`Medium`/`High`).
- The SQL file creates a trigger that auto-populates the `location` geography from `lat`/`lng` on insert/update.
- If you already have an older schema, `schema.sql` includes an `ALTER TABLE` snippet to add the `severity` column if missing.
