# FYP-26 Pothole Detection — System Diagrams

All diagrams are generated from the backend source (`app/`, `schema.sql`, `ml/`).
Editable Mermaid sources live in [`src/`](src); rendered images in [`png/`](png) (report-ready, 2×) and [`svg/`](svg).
Re-render: `npx -p @mermaid-js/mermaid-cli mmdc -i src/X.mmd -o png/X.png -s 2 -b white`.

## 1. Concept in one paragraph

A road image plus GPS coordinates arrives from an **ESP32-CAM** (`POST /detect`, API-key protected, inference runs immediately) or a **citizen's browser** (`POST /submit`, public, stored as *pending* and analysed later via `POST /detections/{id}/analyze`). The FastAPI service validates that the point lies inside Ghana's bounding box (lat 4.5–11.5, lng −3.5–1.5) and that the file is an image ≤ 10 MB, then runs the fine-tuned **YOLOv8** model (classes `Pothole`, `other`; only `Pothole` boxes are kept). The highest box confidence becomes the record's `confidence`; ≥ 0.4 marks it *confirmed*. Records are written to a local JSON store + JPEG file **and** mirrored to **Supabase/PostGIS** when credentials are valid. Administrators review records (list, image, status → confirmed/declined/fixed, delete), the frontend draws a **heatmap** and **stats**, and the Ghana Highway Authority gets a **regional severity report** (nearest of 16 regional capitals by haversine; high ≥ 0.75, medium ≥ 0.5, else low) and **CSV/GeoJSON exports** for QGIS/ArcGIS.

## 2. Diagram index

| # | Diagram | Type | What it shows |
|---|---------|------|---------------|
| 01 | [use case](png/01-use-case.png) | Use case | 5 primary actors, 2 secondary actors, 17 use cases with «include»/«extend» |
| 02 | [architecture](png/02-architecture.png) | Component | Clients → middleware → routers → services → storage |
| 03 | [startup](png/03-seq-startup.png) | Sequence | Model loading fallback chain + production safety checks |
| 04 | [detect](png/04-seq-detect.png) | Sequence | `POST /detect` end-to-end incl. every error branch |
| 05 | [submit & analyze](png/05-seq-submit-analyze.png) | Sequence | Two-phase citizen report → deferred ML analysis |
| 06 | [moderation](png/06-seq-moderation.png) | Sequence | List, view image, PATCH status, DELETE |
| 07 | [dashboard & report](png/07-seq-dashboard-report.png) | Sequence | Heatmap, stats, GHA report, CSV/GeoJSON export |
| 08 | [DFD level 0](png/08-dfd-level0.png) | Data flow | Context diagram |
| 09 | [DFD level 1](png/09-dfd-level1.png) | Data flow | 8 processes, 4 data stores (D1–D4) |
| 10 | [status lifecycle](png/10-state-lifecycle.png) | State machine | pending / confirmed / declined / fixed |
| 11 | [current ER](png/11-er-current.png) | ER | The real `detections` table + JSONB items + image file |
| 12 | [proposed ER](png/12-er-proposed.png) | ER | Normalised sample schema → [`sample_schema.sql`](sample_schema.sql) |
| 13 | [schemas](png/13-class-schemas.png) | Class | Pydantic request/response models, detector, settings |

## 3. Endpoint ↔ use case map

| Endpoint | Auth | Use case | Repo function |
|---|---|---|---|
| `POST /api/v1/detect` | X-API-Key | UC1 | `save_detection` |
| `POST /api/v1/submit` | public | UC2 | `save_submission` |
| `POST /api/v1/detections/{id}/analyze` | public | UC3 | `update_detection_results` |
| `GET /api/v1/heatmap` | public | UC7 | `get_heatmap_points` |
| `GET /api/v1/stats` | public | UC8 | `get_stats` |
| `GET /api/v1/detections`, `/detections/{id}` | public | UC9 | `get_all_detections`, `get_detection_by_id` |
| `GET /api/v1/images/{id}` | public | UC10 | `get_image_file_path` |
| `PATCH /api/v1/detections/{id}/status` | public | UC11 | `update_detection_status` |
| `DELETE /api/v1/detections/{id}` | X-API-Key | UC12 | `delete_detection` |
| `GET /api/v1/report` | public | UC13 | `get_all_detections` + `geo.py` |
| `GET /api/v1/detections/export` | X-API-Key | UC14 | `get_all_detections` + `geo.py` |
| `GET /health`, `/` | public | UC15 | `detector.is_loaded / is_pothole_capable` |

## 4. Things the diagrams surfaced (worth knowing for the write-up)

1. **Reads never come from Supabase.** `get_all_detections` (list, heatmap, stats, report, export) reads only the local `_MOCK_STORE` / `mock_detections.json`. Supabase is a write-mirror; only `get_detection_by_id` falls back to it. On Render/Railway the local disk is ephemeral, so data shown after a restart is whatever JSON was committed.
2. **`schema.sql` lacks `status` and `image_url`.** The repo tries a full insert, then silently retries without those columns — so Supabase never stores status. The sample schema adds them.
3. **Silent mock detections.** If the model isn't pothole-capable, `/detect` and `/analyze` return a hard-coded pothole (conf 0.88 / 0.85) instead of the `503` the README/`ml/weights/README.md` describe. Same when Ultralytics fails to import ("fallback" model).
4. **Unauthenticated mutations.** `/submit`, `/analyze` and `PATCH /status` have no API-key check (only `/detect`, `DELETE`, `/export` do).
5. **Invalid status is coerced** to `confirmed` rather than rejected (`update_detection_status`).
6. **Duplicate route:** `DELETE /detections/{id}` is defined in both `detect.py` and `heatmap.py`; the `detect.py` one wins (registered first). `delete_detection` always returns `True`, so the 404 branch is unreachable.
7. **`GET /images/{id}` fabricates a placeholder JPEG** (and saves it to disk) for any unknown id.
8. `CONFIDENCE_THRESHOLD` defaults to 0.02 in code (0.35 in `.env.example`); the 0.4 "pothole_detected/confirmed" cut-off is hard-coded separately.
