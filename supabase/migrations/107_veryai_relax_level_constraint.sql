-- 107: Relax veryai_verifications.verification_level CHECK constraint.
--
-- Per Very's official docs (docs.very.org/developers/oauth2-integration and
-- /developers/api-reference, captured 2026-05-04), `GET /userinfo` returns
-- ONLY a `sub` field. There is no `verification_level`, `palm_single`, or
-- `palm_dual` exposed by the public API today.
--
-- The OAuth2 flow itself guarantees palm verification: Very only issues the
-- authorization `code` after the user completes a palm scan via the mobile
-- app, so the existence of a valid access token (and therefore a valid
-- `sub`) IS the palm-verified signal. Migration 104 prematurely encoded
-- internal labels (`palm_single`, `palm_dual`) that turn out not to be a
-- real API contract.
--
-- This migration:
--   1. Drops the strict CHECK that rejected anything other than the legacy
--      labels — production was hitting `not_palm_verified` because the API
--      never returned them.
--   2. Adds a relaxed CHECK that allows the canonical label `'palm'` (what
--      the client now defaults to when `sub` is present), plus the legacy
--      labels for forward-compat if Very later extends /userinfo.
--   3. Updates column comments to reflect the real contract.

ALTER TABLE veryai_verifications
  DROP CONSTRAINT IF EXISTS veryai_verifications_verification_level_check;

ALTER TABLE veryai_verifications
  ADD CONSTRAINT veryai_verifications_verification_level_check
  CHECK (verification_level IN ('palm', 'palm_single', 'palm_dual'));

COMMENT ON COLUMN veryai_verifications.verification_level IS
  'Internal label for the palm-verification level. '
  'Canonical value is ''palm'' — Very''s public /userinfo endpoint only '
  'returns `sub`, and a valid sub == palm-verified per their OAuth2 flow. '
  'Legacy values palm_single / palm_dual retained for forward-compat in '
  'case Very later extends /userinfo with a richer level field.';

COMMENT ON COLUMN executors.veryai_level IS
  'Mirror of veryai_verifications.verification_level. '
  'Canonical: ''palm''. Legacy: palm_single | palm_dual | NULL.';
