-- =====================================================================
-- FYP-26 Pothole Detection — SAMPLE / PROPOSED SCHEMA (illustrative)
-- Matches diagram 12-er-proposed. The live schema is ../../schema.sql
-- (single `detections` table). This version adds the columns the code
-- already writes (status, image_url) and normalises the rest.
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TYPE detection_status AS ENUM ('pending', 'confirmed', 'declined', 'fixed');
CREATE TYPE severity_level   AS ENUM ('low', 'medium', 'high');

CREATE TABLE devices (
    id           TEXT PRIMARY KEY,                 -- 'ESP32-CAM-ACCRA-01', 'manual'
    device_type  TEXT NOT NULL DEFAULT 'web',      -- esp32_cam | web | mobile
    description  TEXT,
    last_seen_at TIMESTAMPTZ
);

CREATE TABLE regions (
    id           SERIAL PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,             -- 16 Ghana regions (app/services/geo.py)
    capital      TEXT NOT NULL,
    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_lng DOUBLE PRECISION NOT NULL
);

CREATE TABLE model_versions (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,                    -- 'yolov8s pothole_v1'
    weights_path TEXT NOT NULL,                    -- 'ml/weights/best.pt'
    class_names  JSONB NOT NULL,                   -- ["Pothole","other"]
    trained_at   TIMESTAMPTZ
);

CREATE TABLE app_users (
    id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    role  TEXT NOT NULL CHECK (role IN ('admin', 'gha_analyst'))
);

CREATE TABLE detections (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id        TEXT NOT NULL DEFAULT 'manual' REFERENCES devices(id),
    region_id        INT REFERENCES regions(id),
    model_version_id INT REFERENCES model_versions(id),
    lat              DOUBLE PRECISION NOT NULL CHECK (lat BETWEEN 4.5 AND 11.5),
    lng              DOUBLE PRECISION NOT NULL CHECK (lng BETWEEN -3.5 AND 1.5),
    location         GEOGRAPHY(Point, 4326),
    confidence       DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (confidence BETWEEN 0 AND 1),
    severity         severity_level GENERATED ALWAYS AS (
                        CASE WHEN confidence >= 0.75 THEN 'high'::severity_level
                             WHEN confidence >= 0.5  THEN 'medium'::severity_level
                             ELSE 'low'::severity_level END) STORED,
    status           detection_status NOT NULL DEFAULT 'pending',
    source           TEXT NOT NULL DEFAULT 'detect' CHECK (source IN ('detect', 'submit')),
    image_url        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE detection_objects (               -- replaces the JSONB `detections` array
    id           BIGSERIAL PRIMARY KEY,
    detection_id UUID NOT NULL REFERENCES detections(id) ON DELETE CASCADE,
    label        TEXT NOT NULL,
    confidence   DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    x1 DOUBLE PRECISION NOT NULL, y1 DOUBLE PRECISION NOT NULL,
    x2 DOUBLE PRECISION NOT NULL, y2 DOUBLE PRECISION NOT NULL
);

CREATE TABLE status_history (                  -- audit trail for PATCH /status
    id           BIGSERIAL PRIMARY KEY,
    detection_id UUID NOT NULL REFERENCES detections(id) ON DELETE CASCADE,
    old_status   detection_status,
    new_status   detection_status NOT NULL,
    changed_by   UUID REFERENCES app_users(id),
    changed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_detections_location   ON detections USING GIST(location);
CREATE INDEX idx_detections_created    ON detections(created_at DESC);
CREATE INDEX idx_detections_status     ON detections(status);
CREATE INDEX idx_detections_confidence ON detections(confidence);

CREATE OR REPLACE FUNCTION set_detection_location() RETURNS TRIGGER AS $$
BEGIN
    NEW.location   = ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326)::GEOGRAPHY;
    NEW.updated_at = NOW();
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_location BEFORE INSERT OR UPDATE ON detections
    FOR EACH ROW EXECUTE FUNCTION set_detection_location();

-- ---------------------------------------------------------------------
-- Sample data (values taken from uploads/mock_detections.json)
-- ---------------------------------------------------------------------
INSERT INTO devices (id, device_type, description) VALUES
  ('ESP32-CAM-ACCRA-01', 'esp32_cam', 'Dash-mounted ESP32-CAM + NEO-6M GPS'),
  ('manual',             'web',       'Default when no device_id is sent');

INSERT INTO regions (name, capital, centroid_lat, centroid_lng) VALUES
  ('Greater Accra', 'Accra',  5.6037, -0.1870),
  ('Ashanti',       'Kumasi', 6.6885, -1.6244);

INSERT INTO model_versions (name, weights_path, class_names) VALUES
  ('yolov8s pothole_v1', 'ml/weights/best.pt', '["Pothole","other"]');

INSERT INTO detections (id, device_id, region_id, model_version_id, lat, lng,
                        confidence, status, source, image_url)
VALUES ('a9c5d342-665a-466e-8590-b0a7223eab53', 'ESP32-CAM-ACCRA-01', 1, 1,
        5.6508, -0.1869, 0.94, 'fixed', 'detect',
        '/api/v1/images/a9c5d342-665a-466e-8590-b0a7223eab53');

INSERT INTO detection_objects (detection_id, label, confidence, x1, y1, x2, y2)
VALUES ('a9c5d342-665a-466e-8590-b0a7223eab53', 'Pothole', 0.94, 144, 180, 816, 540);

INSERT INTO status_history (detection_id, old_status, new_status) VALUES
  ('a9c5d342-665a-466e-8590-b0a7223eab53', NULL,        'confirmed'),
  ('a9c5d342-665a-466e-8590-b0a7223eab53', 'confirmed', 'fixed');
