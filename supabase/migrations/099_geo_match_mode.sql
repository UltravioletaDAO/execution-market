-- Migration 099: Geo Matching — geo_match_mode + location_radius_m
-- Part of WS-3 of MASTER_PLAN_GEO_MATCHING_2026_04_16.
--
-- Adds two optional columns to `tasks` that drive the geo-matching pipeline:
--   * geo_match_mode   — how strictly worker location must match the task location.
--                        Allowed: 'strict' | 'city' | 'region' | 'country' | 'any'.
--                        NULL means "not specified" — pipeline will treat as 'any'.
--   * location_radius_m — override for strict-mode radius, in METERS (integer > 0).
--                        NULL means "use default" (500m for strict tasks).
--
-- Notes:
--   * Idempotent: uses `ADD COLUMN IF NOT EXISTS` and guards constraints in DO blocks.
--   * No backfill — pre-existing rows keep NULL and fall through to 'any' in code.
--   * Does NOT touch the legacy `location_radius_km` column (migration 001/044);
--     that one is still used by the geocoder for city-center fallback radii.

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS geo_match_mode TEXT DEFAULT NULL;

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS location_radius_m INTEGER DEFAULT NULL;

-- Enum-style CHECK constraint on geo_match_mode (idempotent).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tasks_geo_match_mode_check'
    ) THEN
        ALTER TABLE tasks
            ADD CONSTRAINT tasks_geo_match_mode_check
            CHECK (
                geo_match_mode IS NULL
                OR geo_match_mode IN ('strict', 'city', 'region', 'country', 'any')
            );
    END IF;
END $$;

-- Positive-integer CHECK on location_radius_m (idempotent).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tasks_location_radius_m_check'
    ) THEN
        ALTER TABLE tasks
            ADD CONSTRAINT tasks_location_radius_m_check
            CHECK (
                location_radius_m IS NULL
                OR location_radius_m > 0
            );
    END IF;
END $$;

COMMENT ON COLUMN tasks.geo_match_mode IS
    'Geo-matching strictness: strict (GPS radius), city, region, country, any. NULL = any.';

COMMENT ON COLUMN tasks.location_radius_m IS
    'Override radius in meters for strict-mode matching. NULL = default (500m).';
