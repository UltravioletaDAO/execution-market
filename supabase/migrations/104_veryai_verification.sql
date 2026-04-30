-- 104: VeryAI palm-print verification support (mid-tier human KYC)
-- Mirrors 084_world_id_verification.sql shape exactly.
-- Stores OIDC-linked palm verifications and enforces sub-uniqueness (anti-sybil).
-- See: docs/planning/MASTER_PLAN_VERYAI_INTEGRATION.md Phase 1.1

-- Add VeryAI columns to executors
ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS veryai_verified boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS veryai_level text DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS veryai_sub text DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS veryai_verified_at timestamptz DEFAULT NULL;

-- Create VeryAI verifications table
CREATE TABLE IF NOT EXISTS veryai_verifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  executor_id uuid NOT NULL REFERENCES executors(id) ON DELETE CASCADE,
  veryai_sub text NOT NULL,
  verification_level text NOT NULL CHECK (verification_level IN ('palm_single', 'palm_dual')),
  oidc_id_token text NOT NULL,
  solana_attestation_signature text DEFAULT NULL,
  verified_at timestamptz DEFAULT now(),
  expires_at timestamptz DEFAULT NULL,
  CONSTRAINT uq_veryai_sub UNIQUE (veryai_sub),
  CONSTRAINT uq_veryai_executor UNIQUE (executor_id)
);

-- Index for fast lookup by executor
CREATE INDEX IF NOT EXISTS idx_veryai_verifications_executor
  ON veryai_verifications(executor_id);

-- Index for sub uniqueness checks (anti-sybil fast path)
CREATE INDEX IF NOT EXISTS idx_veryai_verifications_sub
  ON veryai_verifications(veryai_sub);

-- Index on executors for filtering verified workers
CREATE INDEX IF NOT EXISTS idx_executors_veryai_verified
  ON executors(veryai_verified)
  WHERE veryai_verified = true;

COMMENT ON TABLE veryai_verifications IS
  'VeryAI palm-print verifications (Veros Inc. OIDC). '
  'Each veryai_sub is unique (1 human = 1 palm = 1 account). '
  'Linked to executor for anti-sybil enforcement on T1 ($50-$500) tier tasks.';

COMMENT ON COLUMN veryai_verifications.veryai_sub IS
  'OIDC subject from VeryAI userinfo endpoint. '
  'Stable identifier per palm enrollment — prevents multi-accounting at the palm level.';

COMMENT ON COLUMN veryai_verifications.verification_level IS
  'palm_single = one palm enrolled. palm_dual = two palms enrolled (higher confidence).';

COMMENT ON COLUMN veryai_verifications.solana_attestation_signature IS
  'Optional: signature of the Solana on-chain attestation tx (Light Protocol). '
  'NULL for OAuth2-only flow; populated when native SDK with Solana verification ships (Phase 7).';

COMMENT ON COLUMN executors.veryai_level IS
  'palm_single | palm_dual | NULL. Mirrors world_id_level pattern.';
