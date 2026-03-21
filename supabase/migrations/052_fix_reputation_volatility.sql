-- Migration 052: Fix calculate_bayesian_reputation Volatility
-- Source: DB Optimization Audit 2026-03-15 (Phase 2, Task 2.3)
-- The function was marked STABLE but reads from mutable tables (ratings)
-- and uses NOW() for time decay — both violate STABLE contract.
-- PostgreSQL may cache STABLE function results within a transaction,
-- returning stale values if ratings change mid-transaction.
-- Fix: Change to VOLATILE (correct behavior, slight perf trade-off).
-- Applied to production: pending.

CREATE OR REPLACE FUNCTION calculate_bayesian_reputation(
    p_executor_id UUID
)
RETURNS DECIMAL
LANGUAGE plpgsql
VOLATILE  -- Changed from STABLE: reads mutable ratings table + uses NOW()
AS $$
DECLARE
    -- Bayesian parameters
    v_C DECIMAL := 15.0;        -- Confidence parameter
    v_m DECIMAL := 50.0;        -- Prior mean
    v_decay DECIMAL := 0.9;     -- Monthly decay factor

    -- Calculation variables
    v_weighted_sum DECIMAL := 0;
    v_total_weight DECIMAL := 0;
    v_record RECORD;
    v_weight DECIMAL;
    v_months_old DECIMAL;
    v_decay_factor DECIMAL;
    v_result DECIMAL;
BEGIN
    -- Calculate weighted average from ratings
    FOR v_record IN
        SELECT
            r.rating,
            r.task_value_usdc,
            r.created_at
        FROM ratings r
        WHERE r.executor_id = p_executor_id
    LOOP
        -- Weight based on task value (log scale to prevent extreme weighting)
        v_weight := LN(GREATEST(v_record.task_value_usdc, 1) + 1);

        -- Calculate months since rating
        v_months_old := EXTRACT(EPOCH FROM (NOW() - v_record.created_at)) / (30 * 24 * 60 * 60);

        -- Apply time decay
        v_decay_factor := POWER(v_decay, GREATEST(0, v_months_old));

        -- Accumulate
        v_weighted_sum := v_weighted_sum + (v_record.rating * v_weight * v_decay_factor);
        v_total_weight := v_total_weight + (v_weight * v_decay_factor);
    END LOOP;

    -- Calculate Bayesian average
    v_result := (v_C * v_m + v_weighted_sum) / (v_C + v_total_weight);

    -- Clamp to 0-100
    RETURN GREATEST(0, LEAST(100, v_result));
END;
$$;
