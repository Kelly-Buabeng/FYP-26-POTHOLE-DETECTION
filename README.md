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
# Fill in SUPABASE_URL and SUPABASE_SERVICE_KEY

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
