-- ============================================================================
-- EXECUTION MARKET
-- Migration: 063_escrow_submission_trigger.sql
-- Description: Safety net trigger that prevents submission INSERT when escrow
--              is not funded (fase2+ only). Skipped in fase1 mode.
-- Source: Escrow Validation Master Plan, Task 5.3
-- Date: 2026-03-19
-- ============================================================================

-- ---------------------------------------------------------------------------
-- FUNCTION: fn_validate_escrow_before_submission
--
-- Runs BEFORE INSERT on submissions. Checks:
-- 1. Payment mode from platform_config (key = 'payment_mode')
--    - If missing or 'fase1', skip validation (no escrow by design)
-- 2. If mode is NOT fase1, verify that a funded escrow exists for the task
-- 3. Block the insert if no funded escrow is found
--
-- Accepted escrow statuses: funded, partial_released, deposited, locked, active
-- (covers both x402r naming conventions and future status extensions)
--
-- This is a DB-level safety net. Application code should also validate,
-- but this trigger catches any bypass (direct SQL, RPC, race conditions).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_validate_escrow_before_submission()
RETURNS TRIGGER AS $$
DECLARE
    v_escrow_status TEXT;
    v_payment_mode TEXT;
BEGIN
    -- Check payment mode from platform_config
    -- The value column is JSONB, so we extract the text value
    SELECT value #>> '{}' INTO v_payment_mode
    FROM platform_config
    WHERE key = 'payment_mode';

    -- If payment_mode is not configured or is 'fase1', skip validation
    -- fase1 = no escrow by design (direct EIP-3009 settlement at approval)
    IF v_payment_mode IS NULL OR v_payment_mode = 'fase1' THEN
        RETURN NEW;
    END IF;

    -- For fase2+, check that a funded escrow exists for this task
    SELECT status::TEXT INTO v_escrow_status
    FROM escrows
    WHERE task_id = NEW.task_id
    ORDER BY created_at DESC
    LIMIT 1;

    -- Block submission if no escrow record exists
    IF v_escrow_status IS NULL THEN
        RAISE EXCEPTION 'Cannot create submission: no escrow found for task % (payment_mode: %)',
            NEW.task_id, v_payment_mode;
    END IF;

    -- Block submission if escrow is not in a funded state
    -- Accepted statuses: funded (standard), partial_released (30% already sent),
    -- plus defensive aliases for future/alternative naming
    IF v_escrow_status NOT IN ('funded', 'partial_released', 'deposited', 'locked', 'active') THEN
        RAISE EXCEPTION 'Cannot create submission: escrow not funded (status: %, task: %)',
            v_escrow_status, NEW.task_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- TRIGGER: trg_validate_escrow_before_submission
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_validate_escrow_before_submission ON submissions;
CREATE TRIGGER trg_validate_escrow_before_submission
    BEFORE INSERT ON submissions
    FOR EACH ROW
    EXECUTE FUNCTION fn_validate_escrow_before_submission();

-- ---------------------------------------------------------------------------
-- COMMENTS
-- ---------------------------------------------------------------------------

COMMENT ON FUNCTION fn_validate_escrow_before_submission() IS
    'Safety net: blocks submission creation when escrow is not funded in fase2+ modes. '
    'Skipped when payment_mode is fase1 or not configured. '
    'Checks platform_config key=payment_mode and escrows table status.';
