---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-06
---
# FIX-P1-06 — World ID anti-sybil bypass: uniqueness check and storage use the client-supplied nullifier, not the proof-verified one

## Summary (2-3 sentences)
`POST /api/v1/world-id/verify` runs its anti-sybil nullifier-uniqueness check and persists the verification record using `request.nullifier_hash` — a value the client controls in the request body — instead of the cryptographically-bound nullifier returned by World's Cloud API. The proof is verified correctly (and the real nullifier is returned in `VerificationResult.nullifier_hash`), but that verified value is logged and then discarded. As a result the `UNIQUE(nullifier_hash)` constraint guards a fully attacker-controlled field, so one human holding a single valid Orb proof can mint unlimited "Orb-verified" sybil accounts by replaying the same `responses` payload with a fresh random `nullifier_hash` each time.

## Severity & Impact (why P1; what funds/data are at risk)
- **P1, not P0**: This is an identity-integrity / anti-sybil defense bypass, not direct fund theft. No private key or escrow is drained by this bug alone.
- **What it defeats**: The platform's "1 human = 1 account" guarantee (the entire point of the World ID integration). The `>= $500` bounty gate (`EM_WORLD_ID_ENABLED`, Tier T2, `worldid.min_bounty_for_orb_usd`) requires an Orb-level World ID. A single human can occupy many "unique verified human" slots, claim multiple high-value bounties, and inflate reputation across N sybil executors.
- **Verified tier is NOT fakeable** (CRY-002 already trusts `data.verification_level` from the API), so an attacker cannot upgrade `device` → `orb`. But they fully control the *identity-binding key* (the nullifier), which is the field the whole anti-sybil control hinges on.
- **Blast-radius caveat**: The *number* of sybil accounts achievable is ultimately capped by the World action's `max_verifications` portal setting (external, not in repo). However, the application-layer sybil control — which was meant to enforce uniqueness independently — is broken unconditionally regardless of that setting. We must not rely on an external portal toggle for our own anti-sybil invariant.

## Affected code (exact file:line references, with short redacted quotes)

**`mcp_server/api/routers/worldid.py:226-246`** — uniqueness check filters on the client value:
```python
nullifier_check = (
    client.table("world_id_verifications")
    .select("id, executor_id")
    .eq("nullifier_hash", request.nullifier_hash)   # <-- client-controlled
    .limit(1)
    .execute()
)
```

**`mcp_server/api/routers/worldid.py:248-261`** — proof verified AFTER the uniqueness check (wrong order); the verified nullifier comes back in `result` but is never consumed:
```python
result = await verify_world_id_proof(
    nullifier_hash=request.nullifier_hash,   # passed in, used only as a fallback
    ...
)
```

**`mcp_server/api/routers/worldid.py:269-282`** — record stored with the client value:
```python
client.table("world_id_verifications").insert(
    {
        "executor_id": executor_id,
        "nullifier_hash": request.nullifier_hash,   # <-- client-controlled, not result.nullifier_hash
        "merkle_root": request.merkle_root,
        "verification_level": result.verification_level or request.verification_level,
        ...
    }
).execute()
```
Confirmed by grep: `result.` is only read for `result.success`, `result.error`, `result.verification_level` (lines 263, 277, 293, 307, 319). `result.nullifier_hash` is **never** consumed anywhere in the endpoint.

**`mcp_server/integrations/worldid/client.py:248-277`** — the API DOES return the real nullifier, but the fallback re-introduces the client value:
```python
if data.get("success"):
    # v4 response uses "nullifier" (not "nullifier_hash")
    resp_nullifier = data.get("nullifier", nullifier_hash)   # <-- falls back to CLIENT value
    ...
    return VerificationResult(
        success=True,
        nullifier_hash=resp_nullifier,   # logged then discarded by caller
        verification_level=actual_level,
    )
```

**`mcp_server/integrations/worldid/client.py:222-227`** — the v4 payload sent to World's Cloud API contains only `protocol_version`, `nonce`, `action`, `responses[]`. The client's claimed `nullifier_hash` is **never sent** to the API, so the API cannot detect or reject a mismatch between the claimed nullifier and the proof.

**`supabase/migrations/084_world_id_verification.sql:13-19`** — the `UNIQUE` constraint that is supposed to enforce anti-sybil:
```sql
nullifier_hash text NOT NULL,
...
CONSTRAINT uq_world_id_nullifier UNIQUE (nullifier_hash),
```
This constraint is correct; it just guards an attacker-controlled column today.

**Correct-pattern reference (sibling flow, NOT buggy):** `mcp_server/api/routers/veryai.py:201-219` binds its sybil check to the **server-verified** `info.sub`, never to a client field. This is the pattern World ID must match.

## Root cause (the real underlying defect)
Two compounding defects:

1. **Trust boundary violation in `worldid.py`**: The endpoint treats `request.nullifier_hash` (client-supplied) as the identity key for both the uniqueness check and storage, instead of the server-verified nullifier returned by the Cloud API. The proof verification and the uniqueness/storage are also in the wrong order (uniqueness runs *before* verification), so even the structure invites using the unverified value.

2. **Unsafe fallback in `client.py:250`**: `data.get("nullifier", nullifier_hash)` silently falls back to the **client-supplied** `nullifier_hash` whenever the Cloud API response omits a `"nullifier"` field. This means even a corrected `worldid.py` that uses `result.nullifier_hash` could still end up using the attacker's value. The verified nullifier must come *only* from the API; a missing API nullifier must be a hard verification failure, not a silent passthrough of client input.

## Exploit scenario (concrete attacker steps)
1. Attacker completes **one** legitimate World ID Orb verification in their own wallet and captures the IDKit `responses` payload (a valid proof) plus `protocol_version`, `nonce`, `action`.
2. Attacker opens N sybil executor accounts `A1..AN` (registration is open; each is the attacker's own executor, so `_enforce_worker_identity` is satisfied for each).
3. For each `Ai`, the attacker calls:
   `POST /api/v1/world-id/verify`
   `{ executor_id: Ai, nullifier_hash: <fresh random hex, different each time>, verification_level: "orb", protocol_version, nonce, action, responses: <the ONE valid proof> }`
4. **Uniqueness check (worldid.py:229) passes** — the fresh random nullifier is unique in the table.
   **Cloud API call (worldid.py:251) passes** — the real proof validates; the API returns the real nullifier, which is ignored.
   **Insert (worldid.py:272) writes the random nullifier** with `world_id_verified=true`, `world_id_level="orb"`.
5. Result: N Orb-verified sybil accounts from a single human, defeating the `>= $500` Orb gate and inflating reputation.

## The Fix (PRECISE, code-level)

The fix has three parts: (A) make the client never the source of the nullifier in `client.py`; (B) reorder + rebind `worldid.py` to use the verified nullifier; (C) a data-integrity migration plus a production-hotfix SQL block to flag/quarantine any records written during the vulnerable window. No infra, env-var, or ECS task-definition change is required.

### A. `mcp_server/integrations/worldid/client.py` — remove the client fallback (lines 248-281)

Replace the success branch so the nullifier comes **only** from the API, and a missing/empty API nullifier is a hard failure.

Change:
```python
            if data.get("success"):
                # v4 response uses "nullifier" (not "nullifier_hash")
                resp_nullifier = data.get("nullifier", nullifier_hash)
```
to:
```python
            if data.get("success"):
                # v4 response uses "nullifier" (not "nullifier_hash").
                # SECURITY (FIX-P1-06): take the nullifier ONLY from the API
                # response. NEVER fall back to the client-supplied value —
                # that is the attacker-controlled field and using it defeats
                # the anti-sybil 1-human-1-account invariant.
                resp_nullifier = data.get("nullifier")
                if not resp_nullifier:
                    logger.error(
                        "World ID Cloud API returned success without a nullifier "
                        "— rejecting verification (FIX-P1-06)"
                    )
                    return VerificationResult(
                        success=False,
                        error="World ID response missing verified nullifier",
                    )
```
Leave lines 252-277 (CRY-002 level handling, logging, the `VerificationResult(success=True, nullifier_hash=resp_nullifier, ...)` return) unchanged — `resp_nullifier` is now guaranteed non-empty and API-sourced.

> Note on the v2 legacy fallback (`client.py:228-240`): that path forwards `nullifier_hash` to the v2 API, where the API *does* validate it against the proof. We are **not** removing `nullifier_hash` from the function signature or from `VerifyWorldIdRequest`, precisely to keep the v2 path working. We are only removing the *response* fallback. This is the deliberate, documented decision called out by the verifier.

### B. `mcp_server/api/routers/worldid.py` — verify first, then bind uniqueness + storage to the verified nullifier (lines 225-333)

**B1. Move proof verification BEFORE the uniqueness check, and bind the uniqueness check to `result.nullifier_hash`.** Replace the current step-2/step-3 block (lines 225-267) with:

```python
    # 2. Verify proof via Cloud API FIRST (FIX-P1-06).
    # The uniqueness check and storage MUST use the cryptographically-bound
    # nullifier returned by World, NEVER the client-supplied request value.
    from integrations.worldid.client import verify_world_id_proof

    result = await verify_world_id_proof(
        nullifier_hash=request.nullifier_hash,  # used only by the v2 legacy path
        verification_level=request.verification_level,
        protocol_version=request.protocol_version,
        nonce=request.nonce,
        responses=request.responses,
        proof=request.proof,
        merkle_root=request.merkle_root,
        action=request.action,
        signal=request.signal,
    )

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error or "World ID proof verification failed",
        )

    # Defense in depth: client.py already rejects an empty API nullifier, but
    # never proceed without a verified one.
    verified_nullifier = result.nullifier_hash
    if not verified_nullifier:
        raise HTTPException(
            status_code=400,
            detail="World ID verification did not return a nullifier",
        )

    # 3. Check nullifier uniqueness (anti-sybil) using the VERIFIED nullifier.
    nullifier_check = (
        client.table("world_id_verifications")
        .select("id, executor_id")
        .eq("nullifier_hash", verified_nullifier)
        .limit(1)
        .execute()
    )

    if nullifier_check.data:
        prior_executor = nullifier_check.data[0].get("executor_id", "?")
        # Idempotent re-verify by the same executor is success, not a sybil hit.
        if prior_executor == executor_id:
            return VerifyWorldIdResponse(
                verified=True,
                verification_level=result.verification_level,
                message="Already verified",
            )
        logger.warning(
            "SYBIL_ATTEMPT: nullifier %s...%s already used by executor %s, "
            "attempted reuse by executor %s",
            verified_nullifier[:10],
            verified_nullifier[-6:],
            str(prior_executor)[:8],
            executor_id[:8],
        )
        raise HTTPException(
            status_code=409,
            detail="This World ID has already been used to verify another account",
        )
```

> Note: step 1 (the per-executor "already verified" short-circuit at lines 207-223) stays exactly where it is, before this block. It does not touch the nullifier.

**B2. Use the verified nullifier in the insert (lines 272-282).** Change:
```python
                "nullifier_hash": request.nullifier_hash,
```
to:
```python
                "nullifier_hash": verified_nullifier,
```
Keep `"merkle_root": request.merkle_root` as-is — `merkle_root` is stored for audit only and is not a security control (cosmetic). Keep the post-insert `uq_world_id_nullifier` / `uq_world_id_executor` catch (lines 283-300) as the race backstop.

**B3. Fix the final log line (lines 327-333)** to log the verified nullifier rather than the client one:
```python
    logger.info(
        "World ID verified: executor=%s, level=%s, nullifier=%s...%s",
        executor_id[:8],
        level,
        verified_nullifier[:10],
        verified_nullifier[-6:],
    )
```

No other lines change. `result.verification_level or request.verification_level` fallbacks at lines 277-278 / 307-309 / 319 are unrelated to this finding and stay.

### C. Database migration + production hotfix (data already poisoned during the vulnerable window)

Because pre-fix records may already contain client-controlled nullifiers, we cannot trust existing `world_id_verifications` rows. We add a column to mark provenance going forward and quarantine rows that cannot be re-attested. **The next free migration number is `111`** (latest is `110_moonpay_onramp_attempts.sql`).

**New migration file:** `supabase/migrations/111_worldid_nullifier_provenance.sql`
```sql
-- 111: FIX-P1-06 — track nullifier provenance and quarantine pre-fix records
--
-- Before this fix, world_id_verifications.nullifier_hash could be set from a
-- CLIENT-supplied value rather than the World Cloud API's verified nullifier.
-- Such rows provide ZERO anti-sybil value. We:
--   (a) add a provenance flag so all NEW rows are explicitly api-verified;
--   (b) flag all EXISTING rows as unverified-provenance so ops can force
--       re-verification of those executors instead of trusting stale data.

ALTER TABLE world_id_verifications
  ADD COLUMN IF NOT EXISTS nullifier_provenance text NOT NULL DEFAULT 'api_verified'
    CHECK (nullifier_provenance IN ('api_verified', 'legacy_unverified'));

-- Everything that existed before this migration predates the fix → untrusted.
-- (New inserts default to 'api_verified' via the column default above.)
UPDATE world_id_verifications
  SET nullifier_provenance = 'legacy_unverified'
  WHERE verified_at < now();

-- Also drop the executor verified flag for legacy rows so the >=$500 Orb gate
-- re-challenges them. They keep their reputation but must re-attest World ID.
UPDATE executors e
  SET world_id_verified = false
  FROM world_id_verifications w
  WHERE w.executor_id = e.id
    AND w.nullifier_provenance = 'legacy_unverified';

COMMENT ON COLUMN world_id_verifications.nullifier_provenance IS
  'api_verified = nullifier came from World Cloud API response (post FIX-P1-06). '
  'legacy_unverified = nullifier may be client-supplied (pre-fix) — do not trust for anti-sybil.';
```

**Standalone idempotent production hotfix** (paste into the Supabase SQL editor; safe to re-run):
```sql
-- FIX-P1-06 production hotfix — idempotent
BEGIN;

ALTER TABLE world_id_verifications
  ADD COLUMN IF NOT EXISTS nullifier_provenance text NOT NULL DEFAULT 'api_verified';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'world_id_verifications_nullifier_provenance_check'
  ) THEN
    ALTER TABLE world_id_verifications
      ADD CONSTRAINT world_id_verifications_nullifier_provenance_check
      CHECK (nullifier_provenance IN ('api_verified', 'legacy_unverified'));
  END IF;
END $$;

UPDATE world_id_verifications
  SET nullifier_provenance = 'legacy_unverified'
  WHERE verified_at < now()
    AND nullifier_provenance <> 'legacy_unverified';

UPDATE executors e
  SET world_id_verified = false
  FROM world_id_verifications w
  WHERE w.executor_id = e.id
    AND w.nullifier_provenance = 'legacy_unverified'
    AND e.world_id_verified = true;

COMMIT;
```
> The `UPDATE ... WHERE verified_at < now()` runs once at deploy time; re-running it is harmless because the second predicate (`<> 'legacy_unverified'`) makes it a no-op on already-flagged rows. The application code does **not** need to read `nullifier_provenance` — it is an ops/forensics column. (Optional follow-up: have the read paths that gate on `world_id_verified` ignore `legacy_unverified` rows, but flipping `executors.world_id_verified=false` above already achieves the re-challenge with no code change.)

### Feature flag / env var
None required. The fix is a correctness change to an existing, always-on endpoint. `EM_WORLD_ID_ENABLED` already gates whether World ID is enforced on applications; this fix does not alter that flag's behavior.

### Backward-compatibility risk & safe rollout
- **Honest clients are unaffected**: `dashboard/src/components/WorldIdVerification.tsx:113` sets `nullifier_hash` from `response.nullifier` (the same value the API returns), so for legitimate flows `request.nullifier_hash == result.nullifier_hash`. Switching to `result.nullifier_hash` changes nothing for them.
- **Could this lock out legitimate agents?** The migration sets `world_id_verified=false` for all pre-fix verifications and asks those users to re-verify once. This is a one-time re-attestation, not a permanent lockout — re-verifying with their real proof restores the flag and (now correctly) binds to the verified nullifier. This is the correct, conservative posture because pre-fix rows are untrustworthy.
- **`max_verifications` interaction**: If the World action's `max_verifications` is set to 1, a legitimate user who was verified pre-fix may be unable to re-verify (the proof is now "used"). **Before running the migration**, ops should confirm the action's `max_verifications` allows re-verification (raise it temporarily, or accept that a small number of pre-fix users contact support). Document the count of affected rows first: `SELECT count(*) FROM world_id_verifications WHERE verified_at < now();`
- **Staged rollout**: (1) deploy the code change (parts A+B) — it is strictly more correct and breaks no honest client; (2) run the migration (part C) during a low-traffic window after checking the affected-row count and `max_verifications`. The code change is safe to ship independently of the migration.

## Test plan (how the execution team proves it's fixed)

### Unit/integration tests to add — `mcp_server/tests/test_worldid.py`

1. **`test_verify_rejects_when_api_returns_no_nullifier`** (client.py): mock the Cloud API to return `{"success": True, "verification_level": "orb"}` (no `"nullifier"` key) while passing `nullifier_hash="0xATTACKER"`. Assert `result.success is False` and `"nullifier" in result.error.lower()`. **This reproduces the bug**: pre-fix, `data.get("nullifier", nullifier_hash)` returned `"0xATTACKER"` and `success` stayed True; post-fix it is a hard failure.

2. **`test_verify_uses_api_nullifier_not_client`** (client.py): mock the API to return `{"success": True, "nullifier": "0xREAL", "verification_level": "orb"}` while calling with `nullifier_hash="0xCLIENTFAKE"`. Assert `result.nullifier_hash == "0xREAL"` (never the client value).

### Endpoint test — new file `mcp_server/tests/test_worldid_nullifier_binding.py` (marker `pytest.mark.worldid`)

3. **`test_sybil_replay_with_fresh_fake_nullifier_is_blocked`** (the headline regression test, reproduces the finding end-to-end):
   - Patch `db.get_client()` to a fake/Mock Supabase whose `world_id_verifications` table records inserts in-memory and whose `nullifier_check` query filters on the value actually queried.
   - Patch `verify_world_id_proof` (or `httpx.AsyncClient`) so the Cloud API always returns the **same real nullifier** `0xREAL` regardless of the request body (this models "same valid proof replayed").
   - Patch `_enforce_worker_identity` to return the request's `executor_id` (attacker owns all N executors).
   - **Request 1**: `executor_id="A1"`, `nullifier_hash="0xFAKE1"` → expect `200`, and assert the stored row's `nullifier_hash == "0xREAL"` (NOT `0xFAKE1`).
   - **Request 2**: `executor_id="A2"`, `nullifier_hash="0xFAKE2"` (different fake), same `responses` → expect **`409`** ("already used to verify another account"), because the uniqueness check now runs against `0xREAL`, which is already present.
   - Pre-fix, request 2 returned `200` (the fake nullifier `0xFAKE2` is unique). Post-fix it must be `409`. This is the proof of fix.

4. **`test_honest_client_with_matching_nullifier_succeeds`**: `executor_id="B1"`, `nullifier_hash="0xREAL"` (honest client sends the same value the API returns) → `200`, stored nullifier `0xREAL`, `world_id_verified` set true. Confirms no regression for legitimate users.

5. **`test_same_executor_reverify_is_idempotent_success`**: verify `executor_id="C1"` once (`0xREAL`), then call again with the same executor → `200` "Already verified", not `409`. Confirms the same-executor short-circuit in B1.

Run: `cd mcp_server && pytest -m worldid -q` — all existing `worldid` tests plus the new ones must pass.

### Manual / E2E verification
1. On staging, complete a real World ID Orb verification via the dashboard. Capture the `responses` payload from network dev-tools.
2. Replay `POST /api/v1/world-id/verify` with a **second** executor you own, the same `responses`, and a **random** `nullifier_hash`. Expected: HTTP `409`. (Pre-fix: HTTP `200`.)
3. Query the DB: `SELECT executor_id, nullifier_hash FROM world_id_verifications ORDER BY verified_at DESC LIMIT 5;` — confirm stored `nullifier_hash` equals the value World's API returned, not the random one you sent.
4. Confirm logs show `nullifier=<real>...` in the final "World ID verified" line (part B3), and a `SYBIL_ATTEMPT` warning on the blocked replay.

## Rollback plan
- **Code**: revert the two source edits (`client.py` fallback restore, `worldid.py` reorder/rebind) via `git revert <commit>`; the endpoint returns to prior behavior. No schema dependency in the code, so it can be reverted independently of the migration.
- **Migration**: the column add is additive and harmless to keep. If the re-verification churn is unacceptable, restore the verified flag for legacy rows:
  ```sql
  UPDATE executors e SET world_id_verified = true
  FROM world_id_verifications w
  WHERE w.executor_id = e.id AND w.nullifier_provenance = 'legacy_unverified';
  ```
  (This restores the *prior, insecure* state — only do this as an emergency mitigation, and note it re-trusts unverifiable nullifiers.) To fully drop the column: `ALTER TABLE world_id_verifications DROP COLUMN IF EXISTS nullifier_provenance;`.

## Verification checklist (boxes the executor ticks before marking done)
- [ ] `client.py:250` no longer falls back to the client nullifier; missing API nullifier returns `success=False`.
- [ ] `worldid.py` calls `verify_world_id_proof` **before** the uniqueness check.
- [ ] Uniqueness check (`worldid.py`) filters on `verified_nullifier` (the API value), not `request.nullifier_hash`.
- [ ] Insert (`worldid.py`) writes `verified_nullifier`, not `request.nullifier_hash`.
- [ ] Final "World ID verified" log line uses `verified_nullifier`.
- [ ] Same-executor re-verify returns `200` (idempotent), not `409`.
- [ ] `grep -n "request.nullifier_hash" mcp_server/api/routers/worldid.py` shows it used **only** as the v2-legacy passthrough arg to `verify_world_id_proof` (line ~252), nowhere in the uniqueness query or the insert.
- [ ] New tests `test_verify_rejects_when_api_returns_no_nullifier`, `test_verify_uses_api_nullifier_not_client`, and `test_sybil_replay_with_fresh_fake_nullifier_is_blocked` pass; the last one returns `409` on the second replay.
- [ ] `cd mcp_server && pytest -m worldid` is green (no regressions in existing World ID tests).
- [ ] Migration `111_worldid_nullifier_provenance.sql` added; affected-row count recorded; `max_verifications` checked before running it in prod.
- [ ] Production hotfix SQL executed (or migration applied) and verified idempotent (re-run is a no-op).
- [ ] Manual replay on staging returns `409` and stored nullifier matches the API value.
