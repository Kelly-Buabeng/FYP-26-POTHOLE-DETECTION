# FYP-26 Pothole Detection — REST API Documentation

**Version:** `1.0.0`  
**Base URL:** `http://localhost:8000` (or your deployed server domain)  
**Interactive Docs:**  
- Swagger UI: `http://localhost:8000/docs`  
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Overview & Architecture

The **FYP-26 Pothole Detection API** is a FastAPI-powered backend providing real-time computer vision inference (via Ultralytics YOLOv8) and geospatial data persistence (via Supabase / PostGIS).

### Key Features
- **Real-Time Inference:** Fast inference on road imagery sent from mobile clients or IoT hardware (ESP32-CAM).
- **Geospatial Storage:** Confirmed detections ($\text{confidence} \ge 0.40$) are automatically stored in PostgreSQL with PostGIS Geography coordinates.
- **Heatmap Layer Support:** Aggregated coordinate endpoints optimized for mapping libraries (Leaflet, Mapbox, Google Maps).
- **Graceful Fallback / Mock Mode:** Built-in mock responses if Supabase credentials are not yet configured during development.

---

## 2. Global Headers & Conventions

| Header | Description | Required |
|--------|-------------|----------|
| `Content-Type` | `multipart/form-data` for file uploads, `application/json` for standard requests | Yes (per endpoint) |
| `Accept` | `application/json` | Optional (default) |

### CORS Configuration
- **Allowed Origins:** `*` (All origins permitted for mobile and web frontends)
- **Allowed Methods:** `*`
- **Allowed Headers:** `*`

---

## 3. Endpoints

```
├── Health & Meta
│   ├── GET  /                          # Service info & doc links
│   └── GET  /health                    # Model & service health check
│
└── API v1 (/api/v1)
    ├── POST   /api/v1/detect           # Image upload + YOLOv8 inference
    ├── GET    /api/v1/heatmap          # GPS points for heatmap visualization
    ├── GET    /api/v1/stats            # System statistics & dashboard metrics
    └── DELETE /api/v1/detections/{id}  # Remove false positive detection
```

---

### 3.1 Health & Meta Endpoints

#### `GET /` — Root Information
Returns basic service metadata and links.

- **Request:** `GET /`
- **Success Response (`200 OK`):**
```json
{
  "project": "FYP-26 Pothole Detection",
  "status": "online",
  "model_loaded": true,
  "docs": "/docs"
}
```

---

#### `GET /health` — Health Check
Used by monitoring tools, load balancers, and client apps to check readiness.

- **Request:** `GET /health`
- **Success Response (`200 OK`):**
```json
{
  "status": "ok",
  "model_loaded": true
}
```

---

### 3.2 Detection Endpoint

#### `POST /api/v1/detect` — Run Pothole Detection
Accepts an image file and geographical coordinates (from GPS/device), executes YOLOv8 object detection, and saves confirmed detections to the database.

- **Content-Type:** `multipart/form-data`
- **Request Parameters (Form Data):**

| Parameter | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `image` | `file` (binary) | **Yes** | Road image in JPEG or PNG format | Max size: `10 MB` |
| `lat` | `float` | **Yes** | Latitude coordinate | `-90.0` to `90.0` |
| `lng` | `float` | **Yes** | Longitude coordinate | `-180.0` to `180.0` |
| `device_id`| `string` | No | Identifier for the submitting device / client | Default: `"manual"` |

- **Detection & Persistence Logic:**
  1. Decodes image into RGB.
  2. Runs YOLOv8 inference with the configured threshold (`CONFIDENCE_THRESHOLD=0.35`).
  3. Checks if any detection has `label == "pothole"` with `confidence >= 0.40`.
  4. If a pothole is found, records are inserted into Supabase (`detections` table).
  5. Returns detection results, bounding boxes, and DB record ID (if saved).

- **Success Response (`200 OK`):**
```json
{
  "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "pothole_detected": true,
  "detections": [
    {
      "label": "pothole",
      "confidence": 0.8742,
      "bbox": {
        "x1": 124.50,
        "y1": 340.10,
        "x2": 260.80,
        "y2": 450.30
      }
    }
  ],
  "coordinates": {
    "lat": 5.6037,
    "lng": -0.1870
  },
  "device_id": "esp32_cam_01",
  "timestamp": "2026-08-21T01:00:00.000000+00:00"
}
```

> **Note:** If no pothole is detected (`pothole_detected: false`), `id` will be `null` and `detections` will either be empty or contain non-pothole detected objects.

- **Error Responses:**
  - `400 Bad Request`: `{"detail": "File must be an image (JPEG or PNG)."}`
  - `413 Payload Too Large`: `{"detail": "Image too large. Max size is 10MB."}`
  - `422 Unprocessable Entity`: `{"detail": "Could not decode image."}` or validation errors on missing/invalid `lat`/`lng`.

---

### 3.3 Geospatial & Analytics Endpoints

#### `GET /api/v1/heatmap` — Get Heatmap Points
Retrieves geographical coordinates with confidence/intensity weights for rendering density heatmaps on client maps.

- **Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | `integer` | No | `500` | Max number of points (maximum: `2000`) |
| `min_confidence` | `float` | No | `0.4` | Minimum detection confidence (`0.0` to `1.0`) |

- **Success Response (`200 OK`):**
```json
[
  {
    "lat": 5.603712,
    "lng": -0.187045,
    "intensity": 0.89
  },
  {
    "lat": 5.556023,
    "lng": -0.196891,
    "intensity": 0.74
  }
]
```

---

#### `GET /api/v1/stats` — Dashboard Statistics
Returns aggregated system metrics including total detections, average confidence score, and active devices.

- **Success Response (`200 OK`):**
```json
{
  "total_detections": 142,
  "avg_confidence": 0.8125,
  "devices_active": 4,
  "mock_mode": false
}
```

---

#### `DELETE /api/v1/detections/{detection_id}` — Delete False Positive
Deletes a detection record by its UUID.

- **Path Parameters:**
  - `detection_id` (`string`, UUID): The ID of the detection record.

- **Success Response (`200 OK`):**
```json
{
  "deleted": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
}
```

- **Error Response:**
  - `404 Not Found`: `{"detail": "Detection not found."}`

---

## 4. Schemas & Data Models

### BoundingBox
| Field | Type | Description |
|---|---|---|
| `x1` | `float` | Top-left X pixel coordinate |
| `y1` | `float` | Top-left Y pixel coordinate |
| `x2` | `float` | Bottom-right X pixel coordinate |
| `y2` | `float` | Bottom-right Y pixel coordinate |

### DetectionItem
| Field | Type | Description |
|---|---|---|
| `label` | `string` | Detected class name (e.g., `"pothole"`) |
| `confidence` | `float` | Detection confidence between `0.0` and `1.0` |
| `bbox` | `BoundingBox` | Bounding box coordinates |

### DetectionResponse
| Field | Type | Description |
|---|---|---|
| `id` | `string \| null` | UUID generated in Supabase database |
| `pothole_detected` | `boolean` | `true` if any pothole with conf $\ge 0.40$ was found |
| `detections` | `DetectionItem[]` | List of all detected objects |
| `coordinates` | `object` | `{ "lat": float, "lng": float }` |
| `device_id` | `string` | Device identifier |
| `timestamp` | `string` | ISO 8601 UTC timestamp |

### HeatmapPoint
| Field | Type | Description |
|---|---|---|
| `lat` | `float` | Latitude coordinate |
| `lng` | `float` | Longitude coordinate |
| `intensity` | `float` | Intensity / confidence (`0.0` to `1.0`) |

### StatsResponse
| Field | Type | Description |
|---|---|---|
| `total_detections` | `integer` | Total stored pothole detections |
| `avg_confidence` | `float` | Average confidence across stored detections |
| `devices_active` | `integer` | Count of unique device IDs |
| `mock_mode` | `boolean` | `true` if operating without Supabase connection |

---

## 5. Client Integration Code Examples

### 5.1 cURL

#### Run Detection:
```bash
curl -X POST "http://localhost:8000/api/v1/detect" \
  -F "image=@/path/to/road_sample.jpg" \
  -F "lat=5.6037" \
  -F "lng=-0.1870" \
  -F "device_id=esp32_cam_01"
```

#### Fetch Heatmap Data:
```bash
curl -X GET "http://localhost:8000/api/v1/heatmap?limit=100&min_confidence=0.5"
```

#### Fetch Stats:
```bash
curl -X GET "http://localhost:8000/api/v1/stats"
```

#### Delete Detection:
```bash
curl -X DELETE "http://localhost:8000/api/v1/detections/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
```

---

### 5.2 Python (`requests` / `httpx`)

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Post Detection
def upload_road_image(file_path: str, lat: float, lng: float, device_id: str = "mobile_app"):
    url = f"{BASE_URL}/api/v1/detect"
    with open(file_path, "rb") as img:
        files = {"image": ("road.jpg", img, "image/jpeg")}
        data = {"lat": lat, "lng": lng, "device_id": device_id}
        response = requests.post(url, files=files, data=data)
        return response.json()

# 2. Get Heatmap
def get_heatmap(min_confidence: float = 0.4):
    url = f"{BASE_URL}/api/v1/heatmap"
    response = requests.get(url, params={"min_confidence": min_confidence})
    return response.json()

# Example usage:
# result = upload_road_image("test_road.jpg", lat=5.6037, lng=-0.1870)
# print(result)
```

---

### 5.3 JavaScript / TypeScript (`fetch` for Web & React Native)

```javascript
const BASE_URL = 'http://localhost:8000';

// 1. Post Detection (Multipart Form)
async function sendDetection(imageBlob, lat, lng, deviceId = 'web_client') {
  const formData = new FormData();
  formData.append('image', imageBlob, 'capture.jpg');
  formData.append('lat', lat.toString());
  formData.append('lng', lng.toString());
  formData.append('device_id', deviceId);

  const res = await fetch(`${BASE_URL}/api/v1/detect`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Detection error: ${res.statusText}`);
  }

  return await res.json();
}

// 2. Fetch Heatmap Points
async function fetchHeatmapPoints(minConfidence = 0.4) {
  const res = await fetch(`${BASE_URL}/api/v1/heatmap?min_confidence=${minConfidence}`);
  return await res.json();
}
```

---

### 5.4 ESP32-CAM / C++ (Arduino HTTPClient)

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

void sendDetection(uint8_t *imageBuffer, size_t imageLen, float lat, float lng, const char* deviceId) {
  HTTPClient http;
  http.begin("http://<YOUR_SERVER_IP>:8000/api/v1/detect");
  
  String boundary = "----ESP32Boundary";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  // Construct multipart body including lat, lng, device_id, and JPEG stream
  // Send via http.POST(...)
  http.end();
}
```

---

## 6. Environment Configuration

The API reads settings from the `.env` file (configured in [`app/core/config.py`](file:///c:/Users/USER/Desktop/FYP-26-POTHOLE-DETECTION/app/core/config.py)):

```ini
# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here

# ML Model Configuration
MODEL_PATH=yolov8n.pt              # Base or fine-tuned weights (e.g. ml/weights/best.pt)
CONFIDENCE_THRESHOLD=0.35          # Minimum threshold for model inference

# App Runtime
APP_ENV=development
APP_PORT=8000
```
