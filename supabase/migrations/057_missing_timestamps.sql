-- Migration 057: Add Missing updated_at to gas_dust_events
-- Source: DB Optimization Audit 2026-03-15 (Phase 4, Task 4.2)
-- gas_dust_events only has created_at but no updated_at, making it
-- impossible to track when a gas dust event status was last changed.
-- Applied to production: pending.

-- Add updated_at column (backfill with created_at for existing rows)
ALTER TABLE gas_dust_events ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
UPDATE gas_dust_events SET updated_at = created_at WHERE updated_at IS NULL;

-- Auto-update trigger (reuses the existing update_updated_at() function from 001)
CREATE TRIGGER gas_dust_events_updated_at
    BEFORE UPDATE ON gas_dust_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
