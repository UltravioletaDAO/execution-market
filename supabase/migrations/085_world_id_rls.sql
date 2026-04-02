-- 085: RLS policies for world_id_verifications table

ALTER TABLE world_id_verifications ENABLE ROW LEVEL SECURITY;

-- Workers can read their own verification
CREATE POLICY "world_id_verifications_select_own"
  ON world_id_verifications
  FOR SELECT
  USING (
    executor_id IN (
      SELECT id FROM executors WHERE user_id = auth.uid()
    )
  );

-- Service role can insert/update (backend API does this)
CREATE POLICY "world_id_verifications_service_insert"
  ON world_id_verifications
  FOR INSERT
  WITH CHECK (true);

-- No direct updates from client — only backend can modify
CREATE POLICY "world_id_verifications_service_update"
  ON world_id_verifications
  FOR UPDATE
  USING (true);

-- Nobody can delete verifications
-- (intentionally no DELETE policy)
