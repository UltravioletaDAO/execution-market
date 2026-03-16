-- Migration 061: Balance Reconciliation Function
-- Source: DB Optimization Audit 2026-03-15 (Phase 5, Task 5.5)
-- Compares stored executor balances against calculated balances from
-- payments and withdrawals tables. Returns rows with drift (mismatch).
-- Run monthly or on-demand via admin endpoint.
-- Applied to production: pending.

CREATE OR REPLACE FUNCTION reconcile_executor_balances()
RETURNS TABLE(
    executor_id UUID,
    display_name VARCHAR,
    stored_balance NUMERIC,
    earned NUMERIC,
    withdrawn NUMERIC,
    calculated_balance NUMERIC,
    drift NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id AS executor_id,
        e.display_name,
        e.balance_usdc AS stored_balance,
        COALESCE(p_earned.total, 0) AS earned,
        COALESCE(w_withdrawn.total, 0) AS withdrawn,
        COALESCE(p_earned.total, 0) - COALESCE(w_withdrawn.total, 0) AS calculated_balance,
        e.balance_usdc - (COALESCE(p_earned.total, 0) - COALESCE(w_withdrawn.total, 0)) AS drift
    FROM executors e
    LEFT JOIN (
        SELECT p.executor_id, SUM(p.amount_usdc - p.fee_usdc) AS total
        FROM payments p
        WHERE p.status = 'completed'
        GROUP BY p.executor_id
    ) p_earned ON p_earned.executor_id = e.id
    LEFT JOIN (
        SELECT w.executor_id, SUM(w.amount_usdc) AS total
        FROM withdrawals w
        WHERE w.status = 'completed'
        GROUP BY w.executor_id
    ) w_withdrawn ON w_withdrawn.executor_id = e.id
    WHERE e.balance_usdc != (COALESCE(p_earned.total, 0) - COALESCE(w_withdrawn.total, 0))
    ORDER BY ABS(e.balance_usdc - (COALESCE(p_earned.total, 0) - COALESCE(w_withdrawn.total, 0))) DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
