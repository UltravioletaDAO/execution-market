-- Migration 058: Escrow Expiry Validation
-- Source: DB Optimization Audit 2026-03-15 (Phase 4, Task 4.3)
-- The existing set_escrow_expiry() trigger auto-calculates expires_at
-- but does NOT validate that timeout_hours is positive or that
-- expires_at is in the future. This migration adds those guards.
-- Applied to production: pending.

CREATE OR REPLACE FUNCTION set_escrow_expiry()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate timeout_hours is positive
    IF NEW.timeout_hours IS NOT NULL AND NEW.timeout_hours <= 0 THEN
        RAISE EXCEPTION 'timeout_hours must be positive (got %)', NEW.timeout_hours;
    END IF;

    -- Auto-calculate expires_at from timeout_hours if not provided
    IF NEW.expires_at IS NULL AND NEW.timeout_hours IS NOT NULL THEN
        NEW.expires_at = NOW() + (NEW.timeout_hours * INTERVAL '1 hour');
    END IF;

    -- Validate expires_at is in the future (only on INSERT)
    IF TG_OP = 'INSERT' AND NEW.expires_at IS NOT NULL AND NEW.expires_at <= NOW() THEN
        RAISE EXCEPTION 'expires_at must be in the future (got %)', NEW.expires_at;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- The existing trigger escrows_set_expiry already fires BEFORE INSERT,
-- and now calls this updated function with validation.
-- No need to recreate the trigger — CREATE OR REPLACE on the function is enough.
