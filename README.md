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

```bash
python ml/train.py
# Weights saved to: runs/detect/pothole_v1/weights/best.pt
cp runs/detect/pothole_v1/weights/best.pt ml/weights/best.pt
# Update .env: MODEL_PATH=ml/weights/best.pt
# Restart server
```

## Testing

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/detect` | Run YOLOv8 on image + GPS coords |
| POST | `/api/v1/detect/video` | Upload a video, sample frames, and detect potholes |
| GET | `/api/v1/heatmap` | Pothole GPS points for frontend map |
| GET | `/api/v1/stats` | Dashboard summary |
| DELETE | `/api/v1/detections/{id}` | Remove a false positive |
| GET | `/health` | Health check |

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
