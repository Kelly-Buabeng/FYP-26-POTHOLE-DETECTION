-- ============================================
-- FYP-26 Pothole Detection — Supabase Schema
-- Run in: Supabase Dashboard > SQL Editor
-- ============================================

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS detections (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   TEXT NOT NULL DEFAULT 'manual',
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    location    GEOGRAPHY(Point, 4326),
    confidence  DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    severity    TEXT NOT NULL DEFAULT 'Low' CHECK (severity IN ('Low', 'Medium', 'High')),
    detections  JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_detections_location   ON detections USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_detections_created    ON detections(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_detections_confidence ON detections(confidence);
CREATE INDEX IF NOT EXISTS idx_detections_severity   ON detections(severity);

CREATE TABLE IF NOT EXISTS video_detections (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id         TEXT NOT NULL DEFAULT 'manual',
    file_name         TEXT NOT NULL,
    duration_ms       INTEGER,
    fps               DOUBLE PRECISION,
    total_frames      INTEGER NOT NULL DEFAULT 0,
    processed_frames  INTEGER NOT NULL DEFAULT 0,
    discarded_frames  INTEGER NOT NULL DEFAULT 0,
    gps_coordinates   JSONB,
    pothole_detected  BOOLEAN NOT NULL DEFAULT FALSE,
    best_severity     TEXT CHECK (best_severity IN ('Low', 'Medium', 'High')),
    best_frame_index  INTEGER,
    frames            JSONB NOT NULL DEFAULT '[]',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_detections_created    ON video_detections(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_video_detections_pothole    ON video_detections(pothole_detected);

-- Auto-populate PostGIS geography from lat/lng
CREATE OR REPLACE FUNCTION set_detection_location()
RETURNS TRIGGER AS $$
BEGIN
    NEW.location = ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326)::GEOGRAPHY;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_location ON detections;
CREATE TRIGGER trg_set_location
    BEFORE INSERT OR UPDATE ON detections
    FOR EACH ROW EXECUTE FUNCTION set_detection_location();

-- If you already ran the old schema, just add the severity column:
-- ALTER TABLE detections ADD COLUMN IF NOT EXISTS severity TEXT NOT NULL DEFAULT 'Low' CHECK (severity IN ('Low', 'Medium', 'High'));
-- CREATE INDEX IF NOT EXISTS idx_detections_severity ON detections(severity);

-- Verify
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name IN ('detections', 'video_detections') ORDER BY table_name, ordinal_position;
