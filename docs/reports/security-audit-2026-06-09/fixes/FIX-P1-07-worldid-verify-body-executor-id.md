---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-07
---
# FIX-P1-07 — World ID `/verify` trusts a body-supplied `executor_id` with no authenticated-identity check (IDOR / anti-sybil bypass)

## Summary
`POST /api/v1/world-id/verify` marks an executor as World ID verified using the `executor_id` taken **directly from the request body**, with no proof that the caller owns that account. The identity guard (`_enforce_worker_identity`) is a no-op in production because `EM_REQUIRE_WORKER_AUTH` is unset (defaults `false`) on task definition `em-production-mcp-server:535`, so `verify_worker_auth` returns `None` and the body value is used verbatim. A second defect in the same handler stores the **client-supplied** `nullifier_hash` instead of the Cloud-API-returned value, so an attacker who holds one valid proof can choose **both** `executor_id` and `nullifier_hash` per call. The fix hardens the endpoint locally: require an authenticated worker, derive `executor_id` exclusively from `worker_auth.executor_id`, and use the Cloud-API `result.nullifier_hash` for the uniqueness check and DB insert.

## Severity & Impact (why P1)
This is a missing-authorization (CWE-862) / IDOR (CWE-639) defect on the platform's **anti-sybil foundation**. World ID gates high-value bounties: tasks with bounty `>= $500` require Orb-level verification (`worldid.min_bounty_for_orb_usd`, `EM_WORLD_ID_ENABLED` default `true`).

What's at risk:
- **Mass sybil fraud (fund-relevant).** Because the handler trusts `request.nullifier_hash` (worldid.py:229, 275) instead of the Cloud-API value, a single valid device-level proof (obtainable by anyone with the World App) lets an attacker fabricate a fresh nullifier per call and mark **any number** of sybil accounts as `world_id_verified=true`, defeating the `$500` Orb gate on high-value bounties.
- **Targeted griefing / permanent lockout.** An attacker can bind their own valid proof to a **victim's** `executor_id`. The victim then collides on `uq_world_id_executor` / `uq_world_id_nullifier` and can **never** register their own real World ID, while their account silently carries the attacker's verification.
- **Bypasses RLS** — the handler writes via the service-role Supabase client (`db.get_client()`), so row-level security is not a backstop.

Not P0: there is no direct escrow drain. But the auth gap ties directly to fund-relevant fraud (high-value bounty gate), so P1 is correct.

## Affected code (exact file:line references)

**`mcp_server/api/routers/worldid.py`**
- `:42-52` — `VerifyWorldIdRequest` accepts `executor_id` and `nullifier_hash` as fully client-controlled fields.
- `:196-205` — handler signature + identity resolution. `worker_auth` is **optional**, and `executor_id` is resolved through the body value:
  ```python
  worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
  ...
  executor_id = _enforce_worker_identity(
      worker_auth, request.executor_id, raw_request.url.path
  )
  ```
- `:229` — nullifier uniqueness check uses the **body** value: `.eq("nullifier_hash", request.nullifier_hash)`.
- `:275` — DB insert stores the **body** value: `"nullifier_hash": request.nullifier_hash`.
- `:302-310` — writes `world_id_verified=True` / `world_id_level` to whatever `executor_id` was resolved.

**`mcp_server/api/auth.py`**
- `:798-800` — `_REQUIRE_WORKER_AUTH = os.environ.get("EM_REQUIRE_WORKER_AUTH", "false").lower() == "true"` (default **false**).
- `:839-851` — when flag is false and no/invalid `Authorization`, `verify_worker_auth` returns `None` (does not raise).
- `:956-963` — `_enforce_worker_identity(None, body_executor_id, ...)` returns the **body** value unchanged.
- `:978-986` — even on a JWT/body **mismatch**, when the flag is false it returns the body value.

**`mcp_server/integrations/worldid/client.py`**
- `:250, 273-277` — Cloud API returns the authoritative `nullifier` and the function packs it into `VerificationResult.nullifier_hash`, but the handler **discards** it and uses the body value instead.

**Infra**
- `ECS em-production-mcp-server:535` — env does **not** contain `EM_REQUIRE_WORKER_AUTH` → defaults `false` in prod. World ID secrets present (`WORLD_ID_APP_ID`, `WORLD_ID_RP_ID`, `WORLD_ID_SIGNING_KEY`); `EM_WORLD_ID_ENABLED` unset = enabled.

Router mount: `mcp_server/api/routes.py:27` (import) and `:54` (`include_router`). No global auth/ERC-8128 middleware gates this path — `api/middleware.py` only early-rejects unauthenticated `/a2a/` paths; `/api/v1/world-id/verify` gets generic IP rate-limiting only.

## Root cause
Two distinct defects in one handler:
1. **Optional-auth on an identity-critical write.** The endpoint depends on `verify_worker_auth` (which is globally flag-gated and returns `None` when off) and then routes through `_enforce_worker_identity`, whose "body fallback" branch is designed for low-risk worker endpoints where a missing Supabase JWT is tolerable. World ID verification is **not** low-risk: trusting a body `executor_id` here is a direct authorization bypass. The endpoint must enforce auth **locally**, independent of the global flag.
2. **Trusting client nullifier.** The handler uses `request.nullifier_hash` for both the uniqueness gate and the stored record instead of the Cloud-API-returned `result.nullifier_hash`. This breaks the anti-sybil invariant even for an authenticated caller, because the nullifier (the per-person uniqueness key) is attacker-chosen rather than cryptographically derived.

## Exploit scenario (current, unpatched)
1. Attacker obtains one valid World ID proof (device-level proofs are obtainable by anyone with the World App).
2. `POST /api/v1/world-id/verify` with **no** `Authorization` header, `executor_id` set to a sybil (or victim) account, a chosen `nullifier_hash`, and the valid `responses` array.
3. `EM_REQUIRE_WORKER_AUTH` is unset in prod → `worker_auth` is `None` → `_enforce_worker_identity` returns the attacker-chosen `executor_id`. The Cloud API verifies the proof (`result.success=True`), but the handler stores `request.nullifier_hash` (attacker-chosen), so the uniqueness gate passes.
4. The endpoint writes `world_id_verified=true` / `world_id_level` to the arbitrary executor.
5. Repeat with a new `executor_id` and a new `nullifier_hash` each call to mass-verify sybil accounts, defeating the `$500` Orb gate.

## The Fix (code-level)

Two source files change; **no DB migration and no schema change** is required. One env-var/ECS note and a frontend change (web) are included because hardening the endpoint will otherwise break the live dashboard flow.

### Change 1 — `mcp_server/api/routers/worldid.py`: require auth locally + use Cloud-API nullifier

Add a module-level local enforcement flag (independent of the global `EM_REQUIRE_WORKER_AUTH`), default **on**, so the fix is safe-by-default but still flag-gateable for a staged rollout. Then:
- raise **401** if `worker_auth is None`,
- derive `executor_id` **exclusively** from `worker_auth.executor_id` (ignore `request.executor_id`),
- use `result.nullifier_hash` for the uniqueness check and the DB insert.

**a) Add the local flag near the top of the module (after `router = APIRouter(...)`, ~line 22):**
```python
import os

# Local, endpoint-specific auth enforcement for World ID verification.
# Independent of the global EM_REQUIRE_WORKER_AUTH so this identity-critical
# write is hardened by default even when the global worker-auth flag is off.
# Set EM_WORLDID_REQUIRE_AUTH=false ONLY for a controlled rollback (see runbook).
_WORLDID_REQUIRE_AUTH = (
    os.environ.get("EM_WORLDID_REQUIRE_AUTH", "true").lower() == "true"
)
```

**b) Replace the identity-resolution block in `verify_world_id` (current worldid.py:201-205):**

_Old:_
```python
    """Verify World ID proof and store verification."""
    # Enforce identity: caller must be the executor they claim
    executor_id = _enforce_worker_identity(
        worker_auth, request.executor_id, raw_request.url.path
    )
```

_New:_
```python
    """Verify World ID proof and store verification."""
    # SECURITY (FIX-P1-07): World ID verification is identity-critical and must
    # NOT trust a body-supplied executor_id. Require an authenticated worker and
    # derive the executor_id exclusively from the verified identity. The body
    # field request.executor_id is now advisory only and is ignored.
    if _WORLDID_REQUIRE_AUTH and worker_auth is None:
        logger.warning(
            "SECURITY_AUDIT action=worldid.verify.unauthenticated path=%s "
            "body_executor=%s (rejected)",
            raw_request.url.path,
            (request.executor_id or "none")[:8],
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication required to verify World ID (Bearer <supabase_jwt>)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if worker_auth is not None:
        # Authoritative identity from the verified JWT — never the body value.
        if request.executor_id and request.executor_id != worker_auth.executor_id:
            logger.warning(
                "SECURITY_AUDIT action=worldid.verify.executor_mismatch "
                "jwt_executor=%s body_executor=%s path=%s (using jwt value)",
                worker_auth.executor_id[:8],
                request.executor_id[:8],
                raw_request.url.path,
            )
        executor_id = worker_auth.executor_id
    else:
        # Only reachable when _WORLDID_REQUIRE_AUTH is explicitly disabled
        # (controlled rollback). Fall back to the body value with a loud audit log.
        logger.warning(
            "SECURITY_AUDIT action=worldid.verify.body_fallback executor_id=%s "
            "path=%s (EM_WORLDID_REQUIRE_AUTH=false)",
            (request.executor_id or "none")[:8],
            raw_request.url.path,
        )
        executor_id = request.executor_id
```

> Note: `_enforce_worker_identity` is no longer called here. Leave its import in place only if used elsewhere in the file; it is not, so remove it from the import on **worldid.py:18**:
> ```python
> from ..auth import verify_worker_auth, WorkerAuth   # drop _enforce_worker_identity
> ```
> (`_enforce_worker_identity` remains exported from `auth.py` and used by other routers — do not delete it there.)

**c) Use the Cloud-API nullifier, not the body value.** The Cloud API call at worldid.py:251-261 already returns `result.nullifier_hash`. Move the proof verification **before** the nullifier-uniqueness check, then use `result.nullifier_hash` everywhere. Concretely:

- The "already verified" check (worldid.py:207-223) stays where it is (keyed on `executor_id`).
- **Move** the proof verification (current steps 3, worldid.py:248-267) to run **before** the nullifier-uniqueness check (current step 2, worldid.py:225-246). After this reorder, introduce a single authoritative variable and use it for the gate and the insert:

```python
    # 2. Verify proof via Cloud API FIRST (so we use the API-returned nullifier)
    from integrations.worldid.client import verify_world_id_proof

    result = await verify_world_id_proof(
        nullifier_hash=request.nullifier_hash,
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

    # SECURITY (FIX-P1-07): trust the Cloud-API-returned nullifier, never the body.
    nullifier_hash = result.nullifier_hash
    if not nullifier_hash:
        logger.error(
            "World ID Cloud API returned success with no nullifier (executor=%s)",
            executor_id[:8],
        )
        raise HTTPException(
            status_code=502,
            detail="World ID verification returned no nullifier",
        )

    # 3. Check nullifier uniqueness (anti-sybil) using the API value
    nullifier_check = (
        client.table("world_id_verifications")
        .select("id, executor_id")
        .eq("nullifier_hash", nullifier_hash)
        .limit(1)
        .execute()
    )

    if nullifier_check.data:
        logger.warning(
            "SYBIL_ATTEMPT: nullifier %s...%s already used by executor %s, "
            "attempted reuse by executor %s",
            nullifier_hash[:10],
            nullifier_hash[-6:],
            nullifier_check.data[0].get("executor_id", "?")[:8],
            executor_id[:8],
        )
        raise HTTPException(
            status_code=409,
            detail="This World ID has already been used to verify another account",
        )
```

Then in the **DB insert** (worldid.py:272-282) replace `request.nullifier_hash` with the `nullifier_hash` variable:
```python
            {
                "executor_id": executor_id,
                "nullifier_hash": nullifier_hash,          # was request.nullifier_hash
                "merkle_root": request.merkle_root,
                "verification_level": result.verification_level
                or request.verification_level,
                "proof": request.proof,
                "verified_at": now,
            }
```

And update the two log statements that reference `request.nullifier_hash` (worldid.py:236-239 already handled above; worldid.py:331-332) to use the `nullifier_hash` variable.

> The "already verified" early-return (step 1) intentionally stays first so a re-verify by the same authenticated executor short-circuits before the Cloud API call — unchanged behavior.

### Change 2 — `dashboard/src/components/WorldIdVerification.tsx`: attach the Supabase Bearer JWT

**Backward-compatibility risk (critical):** the live dashboard currently POSTs to `/verify` with only `Content-Type: application/json` (WorldIdVerification.tsx:124-128) and **no** `Authorization` header. After Change 1 the endpoint returns **401** for that request, breaking real verification. The dashboard user is already a Supabase-authenticated worker (there is an `executor` in `useAuth()`), so a session token is available via `src/lib/auth.ts`.

Add the import and attach the header:
```tsx
import { buildAuthHeaders } from '../lib/auth'
```
Replace the fetch at WorldIdVerification.tsx:124-128:
```tsx
      const resp = await fetch(`${API_BASE}/api/v1/world-id/verify`, {
        method: 'POST',
        headers: await buildAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      })
```
`buildAuthHeaders` reads `supabase.auth.getSession()` and adds `Authorization: Bearer <access_token>` when a session exists. The `executor_id` in the body is now ignored server-side but is harmless to keep (the backend derives identity from the JWT, whose `sub` resolves to `executors.user_id`).

> em-mobile: a repo search found **no** mobile World ID verify flow (`grep -rln "world-id/verify" em-mobile` → empty). No mobile change is required now. When a mobile World ID flow is added, it MUST attach the Dynamic/Supabase Bearer JWT.

### Env var / ECS task-definition

| Var | Safe default | Purpose |
|-----|-------------|---------|
| `EM_WORLDID_REQUIRE_AUTH` | `true` (code default) | Local enforcement for `/verify`. Leave **unset** in ECS to get the secure default. Set to `false` ONLY for a controlled rollback. |

No ECS change is required to ship the fix (code default is secure). Do **not** rely on flipping the global `EM_REQUIRE_WORKER_AUTH=true` — per the verifier, that flips behavior at ~10 `verify_worker_auth` call sites at once and the platform auth model is ERC-8128 wallet signing (not Supabase JWT), so some flows may legitimately lack a Supabase JWT and would start 401-ing. This fix is intentionally scoped to the World ID endpoint only.

Rollback (if legitimate verification breaks unexpectedly), set on `em-production-mcp-server` task def:
```jsonc
{ "name": "EM_WORLDID_REQUIRE_AUTH", "value": "false" }
```
then `aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment --region us-east-2`. (Note: the nullifier-source fix in Change 1c remains active even when rolled back — only the auth requirement is toggled.)

### Safe rollout plan
1. Ship **Change 2 (frontend)** first (or in the same release) so the dashboard sends the Bearer JWT. The endpoint still accepts unauthenticated requests until Change 1 is deployed, so there is no window where the web flow is broken.
2. Deploy **Change 1 (backend)** with `EM_WORLDID_REQUIRE_AUTH` unset (default `true`). Verify the dashboard flow end-to-end on production with a real signed-in worker.
3. If any legitimate client is found to lack a token, set `EM_WORLDID_REQUIRE_AUTH=false` temporarily (the nullifier fix stays in force), patch the client, then remove the override.

## Test plan

### Backend regression tests — add to `mcp_server/tests/test_worldid_enforcement.py`
Use FastAPI `TestClient` against the worldid router with `app.dependency_overrides[verify_worker_auth]` to simulate authenticated / unauthenticated callers, and patch `verify_world_id_proof` + `supabase_client.get_client`. Mark `@pytest.mark.worldid`.

1. `test_verify_rejects_unauthenticated_even_when_global_flag_off`
   - Override `verify_worker_auth` → `None` (simulates `EM_REQUIRE_WORKER_AUTH=false`, no JWT). Ensure `EM_WORLDID_REQUIRE_AUTH` is unset/`true`.
   - POST `/api/v1/world-id/verify` with a body `executor_id` and a valid-looking proof.
   - **Asserts:** HTTP **401**; `verify_world_id_proof` was **not** awaited; no DB insert/update occurred. *(This test fails on the current code, which returns 200 — it reproduces the bug, then passes after the fix.)*

2. `test_verify_uses_jwt_executor_not_body`
   - Override `verify_worker_auth` → `WorkerAuth(executor_id="JWT-EXEC", ...)`.
   - POST with body `executor_id="ATTACKER-EXEC"`, mock proof success with `result.nullifier_hash="0xAPI"`.
   - **Asserts:** the `world_id_verifications` insert and the `executors` update are keyed on `JWT-EXEC`, never `ATTACKER-EXEC`. *(Reproduces the IDOR.)*

3. `test_verify_stores_api_nullifier_not_body`
   - Override `verify_worker_auth` → authenticated. Body `nullifier_hash="0xCLIENTCHOSEN"`, mock `verify_world_id_proof` to return `nullifier_hash="0xAPIDERIVED"`.
   - **Asserts:** the nullifier-uniqueness `.eq("nullifier_hash", ...)` query and the inserted row both use `0xAPIDERIVED`, never `0xCLIENTCHOSEN`. *(Reproduces the nullifier defect.)*

4. `test_verify_502_when_api_returns_no_nullifier`
   - Authenticated; `verify_world_id_proof` returns `success=True, nullifier_hash=None`.
   - **Asserts:** HTTP **502**, no DB write.

5. `test_verify_body_fallback_when_flag_explicitly_off`
   - Set `EM_WORLDID_REQUIRE_AUTH=false` (reload module), override `verify_worker_auth` → `None`.
   - **Asserts:** HTTP **200** using body `executor_id` (confirms the rollback path still works and is loud in logs). Then restore the env var.

Run: `cd mcp_server && pytest -m worldid -q` (must stay green; expect the 8 existing worldid tests + 5 new = 13).

### Manual / E2E verification (production-like)
- Signed-in dashboard worker → "Verify with World ID" → complete Orb/device proof → request carries `Authorization: Bearer <jwt>` (confirm in Network tab) → 200, badge appears.
- `curl -X POST https://api.execution.market/api/v1/world-id/verify -H 'Content-Type: application/json' -d '{"executor_id":"<any-uuid>","nullifier_hash":"0xdead","verification_level":"device","responses":[...]}'` with **no** Authorization → expect **401** (was 200).
- Repeat the curl with a valid Bearer JWT for executor A but `executor_id` = executor B in the body → confirm only executor **A** gets verified (check `world_id_verifications.executor_id`).

## Rollback plan
- Fastest: set `EM_WORLDID_REQUIRE_AUTH=false` on `em-production-mcp-server` and force a new deployment (restores body-fallback auth; nullifier-source fix stays). Use only if legitimate verification is broken.
- Full revert: `git revert` the backend commit (restores `_enforce_worker_identity` call + body nullifier). Revert the frontend commit only if it causes a build/regression. Note that reverting the backend re-opens the IDOR — prefer the env-var rollback while patching clients.
- No DB migration is involved, so there is no schema rollback.

## Verification checklist
- [ ] `worldid.py:18` import no longer pulls `_enforce_worker_identity`; it remains intact in `auth.py` for other routers.
- [ ] `_WORLDID_REQUIRE_AUTH` flag added, default `true`.
- [ ] `/verify` raises **401** when `worker_auth is None` and the flag is on.
- [ ] `executor_id` is derived **only** from `worker_auth.executor_id`; body `request.executor_id` is ignored (mismatch is logged, not honored).
- [ ] Proof verification runs **before** the nullifier-uniqueness check; uniqueness gate + DB insert both use `result.nullifier_hash` (not `request.nullifier_hash`); log lines updated.
- [ ] 502 path added when the Cloud API returns success with no nullifier.
- [ ] Dashboard `WorldIdVerification.tsx` attaches `Authorization: Bearer <supabase_jwt>` via `buildAuthHeaders`.
- [ ] 5 new tests added to `test_worldid_enforcement.py`; `pytest -m worldid` green; test #1 confirmed to FAIL on pre-fix code (bug reproduced) and PASS after.
- [ ] Production rollout order followed (frontend ships before/with backend); manual unauthenticated curl returns 401 on prod.
- [ ] `EM_WORLDID_REQUIRE_AUTH` intentionally left **unset** in ECS (secure default); rollback procedure documented and understood.
- [ ] No secret values printed in logs or this doc.
