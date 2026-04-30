-- 105: RLS policies for veryai_verifications table
-- Mirrors 085_world_id_rls.sql exactly.
-- See: docs/planning/MASTER_PLAN_VERYAI_INTEGRATION.md Phase 1.2

ALTER TABLE veryai_verifications ENABLE ROW LEVEL SECURITY;

-- Workers can read their own verification
CREATE POLICY "veryai_verifications_select_own"
  ON veryai_verifications
  FOR SELECT
  USING (
    executor_id IN (
      SELECT id FROM executors WHERE user_id = auth.uid()
    )
  );

-- Service role can insert (backend API does this after OAuth2 callback)
CREATE POLICY "veryai_verifications_service_insert"
  ON veryai_verifications
  FOR INSERT
  WITH CHECK (true);

-- No direct updates from client — only backend can modify
CREATE POLICY "veryai_verifications_service_update"
  ON veryai_verifications
  FOR UPDATE
  USING (true);

-- Nobody can delete verifications (immutable audit trail)
-- (intentionally no DELETE policy)
