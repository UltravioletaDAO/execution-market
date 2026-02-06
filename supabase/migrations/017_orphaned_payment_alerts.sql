-- Migration 017: Add alerting view/function for submissions accepted without payment_tx
-- Flags submissions where agent_verdict='accepted' but no on-chain tx evidence exists

-- View: orphaned accepted submissions (accepted/completed without payment proof)
CREATE OR REPLACE VIEW v_orphaned_payments AS
SELECT
    s.id AS submission_id,
    s.task_id,
    s.executor_id,
    s.agent_verdict,
    s.payment_tx,
    s.created_at AS submitted_at,
    s.updated_at AS verdict_at,
    t.title AS task_title,
    t.bounty_usd,
    t.agent_id,
    t.status AS task_status,
    EXTRACT(EPOCH FROM (NOW() - s.updated_at)) / 3600 AS hours_since_verdict
FROM submissions s
JOIN tasks t ON t.id = s.task_id
WHERE s.agent_verdict IN ('accepted', 'approved')
  AND (s.payment_tx IS NULL OR s.payment_tx = '')
ORDER BY s.updated_at ASC;

-- Function: get orphaned payment count (for health checks / alerting)
CREATE OR REPLACE FUNCTION get_orphaned_payment_count()
RETURNS INTEGER
LANGUAGE sql
STABLE
AS $$
    SELECT COUNT(*)::INTEGER
    FROM submissions
    WHERE agent_verdict IN ('accepted', 'approved')
      AND (payment_tx IS NULL OR payment_tx = '');
$$;

-- Grant access
GRANT SELECT ON v_orphaned_payments TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_orphaned_payment_count() TO anon, authenticated, service_role;
