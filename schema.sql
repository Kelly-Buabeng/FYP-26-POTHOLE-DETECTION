

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS detections (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   TEXT NOT NULL DEFAULT 'manual',
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    location    GEOGRAPHY(Point, 4326),
    confidence  DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    detections  JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_detections_location  ON detections USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_detections_created   ON detections(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_detections_confidence ON detections(confidence);

-- Auto-populate the PostGIS geography column from lat/lng on every insert
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

-- Verify
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'detections' ORDER BY ordinal_position;
