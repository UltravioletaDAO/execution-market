-- 084: World ID 4.0 verification support
-- Stores proof data and enforces nullifier uniqueness (anti-sybil)

-- Add World ID columns to executors
ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS world_id_verified boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS world_id_level text DEFAULT NULL;

-- Create World ID verifications table
CREATE TABLE IF NOT EXISTS world_id_verifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  executor_id uuid NOT NULL REFERENCES executors(id) ON DELETE CASCADE,
  nullifier_hash text NOT NULL,
  merkle_root text NOT NULL,
  verification_level text NOT NULL CHECK (verification_level IN ('orb', 'device')),
  proof text NOT NULL,
  verified_at timestamptz DEFAULT now(),
  CONSTRAINT uq_world_id_nullifier UNIQUE (nullifier_hash),
  CONSTRAINT uq_world_id_executor UNIQUE (executor_id)
);

-- Index for fast lookup by executor
CREATE INDEX IF NOT EXISTS idx_world_id_verifications_executor
  ON world_id_verifications(executor_id);

-- Index for nullifier uniqueness checks (anti-sybil fast path)
CREATE INDEX IF NOT EXISTS idx_world_id_verifications_nullifier
  ON world_id_verifications(nullifier_hash);

-- Index on executors for filtering verified workers
CREATE INDEX IF NOT EXISTS idx_executors_world_id_verified
  ON executors(world_id_verified)
  WHERE world_id_verified = true;

COMMENT ON TABLE world_id_verifications IS
  'World ID 4.0 proof-of-unique-humanity verifications. '
  'Each nullifier_hash is unique (1 human = 1 account). '
  'Linked to executor for anti-sybil enforcement.';

COMMENT ON COLUMN world_id_verifications.nullifier_hash IS
  'Deterministic hash = f(person_identity, app_id, action). '
  'Unique per person per application — prevents multi-accounting.';
