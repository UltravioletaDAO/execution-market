-- Add explicit lat/lng columns for task location (geofencing)
-- These supplement the PostGIS location column for simpler REST API access
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_lat DOUBLE PRECISION;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_lng DOUBLE PRECISION;

-- Update location_radius_km default to be more generous for text-based locations
ALTER TABLE tasks ALTER COLUMN location_radius_km SET DEFAULT 10.0;

-- Index for spatial queries
CREATE INDEX IF NOT EXISTS idx_tasks_location_coords
ON tasks (location_lat, location_lng)
WHERE location_lat IS NOT NULL AND location_lng IS NOT NULL;
