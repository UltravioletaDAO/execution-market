-- 087: ENS Integration — name resolution + subname registry
--
-- Adds ENS identity fields to executors:
--   ens_name:        auto-resolved ENS name (e.g., alice.eth) via reverse resolution
--   ens_avatar:      ENS avatar URL from text records
--   ens_subname:     claimed subname under execution-market.eth (e.g., alice.execution-market.eth)
--   ens_resolved_at: timestamp of last ENS resolution

ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS ens_name text,
  ADD COLUMN IF NOT EXISTS ens_avatar text,
  ADD COLUMN IF NOT EXISTS ens_subname text,
  ADD COLUMN IF NOT EXISTS ens_resolved_at timestamptz;

-- Fast lookup by ENS name (for displaying badges)
CREATE INDEX IF NOT EXISTS idx_executors_ens_name
  ON executors(ens_name) WHERE ens_name IS NOT NULL;

-- Unique constraint on subnames (one subname per executor, no duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS idx_executors_ens_subname
  ON executors(ens_subname) WHERE ens_subname IS NOT NULL;
