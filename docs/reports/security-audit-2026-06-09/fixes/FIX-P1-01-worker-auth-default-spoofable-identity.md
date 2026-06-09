---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-01
---
# FIX-P1-01 — Worker authentication disabled by default: request-body-spoofable executor identity across all soft-auth endpoints

## Summary
`verify_worker_auth()` is gated by `EM_REQUIRE_WORKER_AUTH`, which defaults to `"false"` (`mcp_server/api/auth.py:798-800`). When false and no/invalid Bearer JWT is present, the dependency returns `None` and `_enforce_worker_identity()` trusts the attacker-controlled `executor_id` supplied in the request body/query (`auth.py:956-963`). The flag is **absent from the live production task definition** (`em-production-mcp-server` rev 535, us-east-2) and from `infrastructure/terraform/ecs.tf`, so the code default `"false"` governs production and the entire worker-authentication tier is effectively disabled. An unauthenticated caller can act as any executor on every soft-auth endpoint. This fix makes worker auth fail-closed by default, adds an authenticated agent path so legitimate H2H flows still work, hardens two per-endpoint checks that are flag-independently weak, sets the Terraform env var, and adds a production boot assertion to prevent silent regression.

## Severity & Impact (why P1)
Complete bypass of worker-side authentication. With the flag unset (current prod state), an attacker with **no Authorization header at all** can:
- **Unauthenticated IDOR read of any worker's private evidence** — the strongest primitive, needing no victim ID. `get_submission_detail` (`workers.py:284-296`) gates access only `if worker_auth and worker_auth.executor_id:` and otherwise logs `"Soft auth ... but allow"` and returns the full submission including evidence S3 keys. `presign-download` (`evidence.py:244`) runs its ownership 403 only `if _key_task_id and worker_auth:`, so with no JWT the check is skipped and a presigned download URL is minted for **any** key. Physical-presence / human-authority tasks store photos, GPS and ID documents — PII exposure.
- **Forge applications and worker→agent feedback** as arbitrary workers (`apply_to_task` `workers.py:349`; `rate_agent` `reputation.py:1104`).
- **Impersonate the assigned worker during submission** (`submit_work` `workers.py:676`) → reputation sabotage.

**Not P0 (verified, no overclaim):** this does **not** yield fund theft or payout redirection. `submit_work` enforces `executor_id == task.executor_id` at the DB layer, the payout wallet is bound to the agent-assigned executor, and no body-fallback endpoint rewrites `executors.wallet_address` (profile writes go through Supabase RLS). Impact is auth bypass + confidential-data IDOR + data-integrity forgery, not escrow drain. Hence P1, not P0.

## Affected code (exact file:line references)

**Core defect — `mcp_server/api/auth.py`:**
```python
# auth.py:798-800  — insecure default
_REQUIRE_WORKER_AUTH = (
    os.environ.get("EM_REQUIRE_WORKER_AUTH", "false").lower() == "true"
)

# auth.py:839-851  — returns None instead of 401 when flag off and no token
if not authorization or not authorization.startswith("Bearer "):
    if _REQUIRE_WORKER_AUTH:
        raise HTTPException(status_code=401, ...)
    logger.warning("... EM_REQUIRE_WORKER_AUTH=false, allowing")
    return None

# auth.py:956-963  — body fallback (the spoof)
if worker_auth is None:
    logger.warning("... action=worker_auth.body_fallback ...")
    return body_executor_id
```

**Flag-independent weak per-endpoint checks (must also be hardened):**
```python
# workers.py:284-296  get_submission_detail
if worker_auth and worker_auth.executor_id:
    if worker_auth.executor_id != sub_executor_id:
        raise HTTPException(status_code=403, ...)
else:
    # Soft auth: log warning but allow   <-- leaks evidence to anon callers
    logger.warning("... action=submission_detail.no_auth ...")

# evidence.py:244-263  presign_download
if _key_task_id and worker_auth:        # <-- skipped entirely when worker_auth is None
    ...
    if not is_executor:
        raise HTTPException(status_code=403, ...)
```

**Infra — `infrastructure/terraform/ecs.tf:290-291`** defines `EM_REQUIRE_ERC8004` / `EM_REQUIRE_ERC8004_WORKER` but never `EM_REQUIRE_WORKER_AUTH`. Live task def `em-production-mcp-server` rev 535 (us-east-2) has 30 env vars, `ENVIRONMENT=production`, but **no** `EM_REQUIRE_WORKER_AUTH` (neither `environment` nor `secrets`).

**All 22 call sites of `verify_worker_auth`** (audited):
- **Body-fallback / soft (vulnerable):** `workers.py` apply(:342) / submit(:667) / get_my_submission(:212) / get_submission_detail(:266); `evidence.py` presign-upload(:113) / presign-download(:232); `reputation.py` rate_agent(:1104) and the three other worker endpoints(:649,:1403,:1533); `worldid.py` verify(:199); `ens.py`(:236,:317); `clawkey.py`(:135); `veryai.py`(:105,:311).
- **Already hard-require (NOT affected — they 401 when `worker_auth is None`):** `workers.py` social-links(:1073); `account.py`(:37,:88,:201); `moderation.py`(:108,:243,:296,:337). Pattern: `if not worker_auth or not worker_auth.executor_id: raise HTTPException(401, ...)`.

## Root cause
Two independent defects compound:
1. **Insecure default.** The security control is opt-in (`default "false"`) instead of fail-closed. Production never set the opt-in, so the control was silently off. The code never consults the existing `ENVIRONMENT=production` var for this gate (unlike `EM_REQUIRE_ERC8004`, which has a boot assertion at `main.py:301-330`).
2. **Body-supplied identity treated as authoritative.** `_enforce_worker_identity()` returns `body_executor_id` whenever the verified principal is absent. Identity should always derive from the verified JWT principal; the body value must only be a non-authoritative hint that is *checked against* the principal, never a fallback source of truth.

A secondary defect: two endpoints (`get_submission_detail`, `presign-download`) make their access-control 403 conditional on `worker_auth` being truthy, so they fail **open** independent of the flag.

## Exploit scenario (concrete)
1. Attacker observes that worker endpoints accept requests with no Bearer token (current prod behavior).
2. **Strongest path (no victim ID needed):** `GET /api/v1/evidence/presign-download?key=tasks/<any-task>/submissions/<any-exec>/<file>` with no `Authorization` header → `worker_auth=None` → `if _key_task_id and worker_auth:` is false → ownership check skipped → presigned S3 GET URL minted → attacker downloads any worker's evidence (photos/GPS/ID). Same for `GET /api/v1/submissions/{id}` → full submission body incl. evidence keys.
3. **Identity-spoof path:** Attacker reads a victim `executor_id` (UUID) from any public path (`/tasks/{id}/applications`, leaderboard, showcase), then `POST /api/v1/tasks/{id}/apply` (or `/submit`, or `rate_agent`) with no `Authorization` header and `executor_id=<victim>` in the body → `_enforce_worker_identity` returns the victim id (`auth.py:962`) → action executes as the victim. No signature, JWT, or wallet proof required.

## The Fix (precise, code-level)

Strategy: (A) flip the default to fail-closed and make the JWT principal authoritative; (B) **add an authenticated agent path** (ERC-8128) so H2H "agent acts as worker" flows keep working — without this, flipping the flag hard-401s legitimate agent-driven apply/submit because those endpoints have no agent-auth dependency and agents have no Supabase JWT; (C) harden the two flag-independent weak checks; (D) set Terraform env var + boot assertion; (E) fix the web client that omits the Bearer token. Roll out staged behind the existing env var so prod can be validated before the code default changes.

### Change 1 — `mcp_server/api/auth.py`: secure default + agent-authorized worker identity

**1a. Flip the default (line 798-800):**
```python
# Worker auth is REQUIRED by default (fail-closed). Set
# EM_REQUIRE_WORKER_AUTH=false ONLY for local dev / isolated tests.
_REQUIRE_WORKER_AUTH = (
    os.environ.get("EM_REQUIRE_WORKER_AUTH", "true").lower() == "true"
)
```

**1b. Add an agent-authorized worker-identity resolver.** Insert a new helper next to `_enforce_worker_identity` that lets a request authenticated via ERC-8128 (the agent path already implemented in `_verify_agent_auth_impl`) act for a body `executor_id` when that agent is authorized — i.e. the agent is the publisher of the task, or owns/created the executor. This is the path H2H needs. Keep it conservative: only the **task-publishing agent** is allowed to act for a worker, resolved from the task row.

Add to `auth.py`:
```python
async def resolve_worker_identity(
    request: Request,
    worker_auth: Optional[WorkerAuth],
    body_executor_id: str,
    *,
    task_id: Optional[str] = None,
) -> str:
    """Authoritative executor_id resolution (fail-closed).

    Order of trust:
      1. Worker JWT principal — must equal body_executor_id (or body omitted).
      2. ERC-8128 agent principal that PUBLISHED task_id — may act for the
         task's assigned executor (H2H "agent acts as worker").
      3. Otherwise → 401/403. The body value is NEVER authoritative on its own.
    """
    # Path 1: verified worker JWT.
    if worker_auth is not None:
        if body_executor_id and worker_auth.executor_id != body_executor_id:
            logger.warning(
                "SECURITY_AUDIT action=worker_auth.mismatch jwt=%s body=%s path=%s",
                worker_auth.executor_id[:8], body_executor_id[:8], request.url.path,
            )
            raise HTTPException(
                status_code=403,
                detail="Executor ID in request does not match authenticated identity",
            )
        return worker_auth.executor_id

    # Path 2: ERC-8128 agent that owns the task may act for its worker.
    sig = request.headers.get("signature")
    sig_input = request.headers.get("signature-input")
    if sig and sig_input and task_id:
        try:
            agent = await verify_agent_auth_write(request)  # raises 401 if invalid
        except HTTPException:
            raise
        if agent.auth_method == "erc8128" and await verify_agent_owns_task(
            agent.agent_id, task_id
        ):
            from supabase_client import get_task
            task = await get_task(task_id)
            assigned = (task or {}).get("executor_id")
            if assigned and (not body_executor_id or body_executor_id == assigned):
                logger.info(
                    "SECURITY_AUDIT action=worker_auth.agent_for_worker "
                    "agent=%s task=%s executor=%s",
                    agent.agent_id[:10], task_id, str(assigned)[:8],
                )
                return str(assigned)
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.agent_not_authorized "
            "agent=%s task=%s path=%s",
            agent.agent_id[:10], task_id, request.url.path,
        )
        raise HTTPException(
            status_code=403,
            detail="Agent is not authorized to act for this worker",
        )

    # Path 3: no verified principal → reject (fail-closed).
    logger.warning(
        "SECURITY_AUDIT action=worker_auth.rejected path=%s reason=no_principal",
        request.url.path,
    )
    raise HTTPException(
        status_code=401,
        detail="Authentication required (Bearer <supabase_jwt> or ERC-8128 signature)",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

**1c. Make `_enforce_worker_identity` fail-closed too** (defense-in-depth for call sites that don't pass `task_id`). Remove the body-fallback branch at `auth.py:956-963` and the `_REQUIRE_WORKER_AUTH=false` "allow body value" branch at `auth.py:978-986`:
```python
def _enforce_worker_identity(
    worker_auth: Optional[WorkerAuth],
    body_executor_id: str,
    request_path: str,
) -> str:
    """Return the authoritative executor_id from the verified JWT principal.

    Fail-closed: a missing principal or a body/JWT mismatch is always rejected.
    The body value is only a hint that must match the verified identity.
    """
    if worker_auth is None:
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.rejected path=%s reason=no_jwt",
            request_path,
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication required (Bearer <supabase_jwt>)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if body_executor_id and worker_auth.executor_id != body_executor_id:
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.mismatch jwt=%s body=%s path=%s",
            worker_auth.executor_id[:8], body_executor_id[:8], request_path,
        )
        raise HTTPException(
            status_code=403,
            detail="Executor ID in request does not match authenticated identity",
        )
    return worker_auth.executor_id
```

**Call-site migration:** the two endpoints that legitimately need the H2H agent path — `apply_to_task` (`workers.py:349`) and `submit_work` (`workers.py:676`) — must switch from `_enforce_worker_identity(...)` to `await resolve_worker_identity(raw_request, worker_auth, request.executor_id, task_id=task_id)`. All other call sites (`get_my_submission`, `worldid.verify`, `ens`, `clawkey`, `veryai`, `presign-upload`) keep `_enforce_worker_identity` — they are worker-only flows with no legitimate agent-acts-as-worker semantics, so the stricter helper is correct. `rate_agent` (`reputation.py`) does not call `_enforce_worker_identity`; it must add `if worker_auth is None: raise HTTPException(401, ...)` at the top of `rate_agent_endpoint` before the existing `if worker_auth is not None:` mismatch block (lines following `reputation.py:1177`), so an anon caller is rejected rather than silently skipping the executor check.

### Change 2 — `mcp_server/api/routers/workers.py`: close the `get_submission_detail` open branch
Replace the `else: # Soft auth ... allow` at lines 290-296 with a hard reject:
```python
sub_executor_id = submission.get("executor_id")
if not (worker_auth and worker_auth.executor_id):
    logger.warning(
        "SECURITY_AUDIT action=submission_detail.no_auth submission_id=%s path=%s",
        submission_id[:8], raw_request.url.path,
    )
    raise HTTPException(status_code=401, detail="Authentication required")
if worker_auth.executor_id != sub_executor_id:
    # Allow the task's publishing agent to view (ERC-8128). Workers only see their own.
    raise HTTPException(
        status_code=403,
        detail="You are not authorized to view this submission",
    )
```

### Change 3 — `mcp_server/api/routers/evidence.py`: close the `presign-download` open path
The ownership 403 currently runs only `if _key_task_id and worker_auth:` (line 244). Make it fail-closed: require an authenticated principal, and require the key to be parseable.
```python
if not _key_task_id:
    raise HTTPException(status_code=400, detail="Unrecognized evidence key")
if not worker_auth:
    logger.warning(
        "SECURITY_AUDIT action=evidence.download_no_auth key_task=%s", _key_task_id,
    )
    raise HTTPException(status_code=401, detail="Authentication required")
try:
    import supabase_client as db
    task = await db.get_task(_key_task_id)
    is_executor = bool(task) and task.get("executor_id") == worker_auth.executor_id
    if not is_executor:
        logger.warning(
            "SECURITY_AUDIT action=evidence.download_denied task=%s executor=%s",
            _key_task_id, worker_auth.executor_id[:8],
        )
        raise HTTPException(status_code=403, detail="You do not have access to this evidence")
except HTTPException:
    raise
except Exception as e:
    # Fail closed on lookup error — do NOT mint a URL we couldn't authorize.
    logger.warning("Evidence download authz lookup failed: %s", e)
    raise HTTPException(status_code=403, detail="Could not verify evidence access")
```
> Note: the publishing-agent download path uses `verify_agent_auth` separately and is out of scope for this worker dependency; this change only ensures the worker path cannot mint URLs without a verified worker principal.

### Change 4 — Infra: set `EM_REQUIRE_WORKER_AUTH=true`

**Terraform diff (`infrastructure/terraform/ecs.tf`, in the `environment = concat([...])` block, next to lines 290-291):**
```hcl
        { name = "EM_REQUIRE_ERC8004", value = "true" },
        { name = "EM_REQUIRE_ERC8004_WORKER", value = "true" },
+       { name = "EM_REQUIRE_WORKER_AUTH", value = "true" },
```

**Manual aws CLI fallback** (only if not redeploying via Terraform): register a new task-def revision adding the env var, then update the service. Do **not** hand-edit a live revision.
```bash
MSYS_NO_PATHCONV=1 aws ecs describe-task-definition \
  --task-definition em-production-mcp-server --region us-east-2 \
  --query 'taskDefinition' > /tmp/td.json
# add { "name":"EM_REQUIRE_WORKER_AUTH", "value":"true" } to
# .containerDefinitions[0].environment, strip the read-only fields
# (taskDefinitionArn, revision, status, requiresAttributes,
#  compatibilities, registeredAt, registeredBy), then:
MSYS_NO_PATHCONV=1 aws ecs register-task-definition \
  --cli-input-json file:///tmp/td.json --region us-east-2
MSYS_NO_PATHCONV=1 aws ecs update-service --cluster <YOUR_ECS_CLUSTER> \
  --service em-production-mcp-server --force-new-deployment --region us-east-2
```

### Change 5 — `mcp_server/main.py`: production boot assertion
Mirror the existing `_assert_erc8004_required_in_production()` (lines 301-330). Add:
```python
def _assert_worker_auth_required_in_production() -> None:
    """Refuse to boot if worker auth is disabled in production (FIX-P1-01)."""
    if os.environ.get("ENVIRONMENT", "development").lower() != "production":
        return
    if os.environ.get("EM_REQUIRE_WORKER_AUTH", "true").lower() != "true":
        raise RuntimeError(
            "CRITICAL: worker authentication disabled in production "
            "(EM_REQUIRE_WORKER_AUTH != 'true'). Refusing to start — "
            "body-supplied executor_id would be spoofable. See FIX-P1-01."
        )
```
And register it in the boot block (lines 327-330):
```python
if _BOOT_ASSERTIONS_ENABLED and not _BOOT_IS_TESTING:
    _assert_jwt_secret_not_default()
    _assert_settlement_not_treasury()
    _assert_erc8004_required_in_production()
    _assert_worker_auth_required_in_production()
```
Note the default in the assertion is `"true"` so an explicitly-set `false` in production is what's rejected, consistent with Change 1a.

### Change 6 — Web client: attach the Supabase JWT on evidence presign (backward-compat)
`dashboard/src/services/evidence.ts:89` calls `fetch(.../presign-upload?...)` with **no** Authorization header — flipping the flag would break web evidence uploads. Fix:
```ts
import { buildAuthHeaders } from '../lib/auth'
// ...
const headers = await buildAuthHeaders()
const res = await fetch(`${EVIDENCE_API_URL}/presign-upload?${qs.toString()}`, { headers })
```
Apply the same to any `presign-download` fetch in `evidence.ts`. `tasks.ts applyToTask`, `submissions.ts submitWork`, `reputation.ts`, `disputes.ts` already use `buildAuthHeaders`, and `api.ts getHeaders()` already attaches the Bearer token — so apply/submit/rate are already compatible. **Audit `em-mobile/` and the XMTP bot the same way before flipping.**

## Backward-compatibility risk & safe rollout
- **Could this lock out legitimate agents/workers?** Yes, two cases:
  1. **Web evidence upload** omits the Bearer token today (Change 6 fixes it).
  2. **H2H "agent acts as worker"** apply/submit has no agent-auth dependency; a naive flag flip 401s it. Change 1b adds the ERC-8128 agent path so the publishing agent can still act for its assigned executor. **Do not delete the body-fallback before Change 1b is merged**, or H2H breaks.
- **Staged rollout (flag-gated, reversible):**
  1. Ship Changes 1-3, 5, 6 with the env var **still unset in prod** (code default flips to `true`, but deploy the Terraform/env change in the same release so behavior is intentional). For an extra-safe staging, set `EM_REQUIRE_WORKER_AUTH=false` explicitly in prod for one deploy, confirm clients send tokens via the `worker_auth.missing` / `worker_auth.body_fallback` audit-log volume dropping to ~0, then remove the override (Change 4) so the secure default governs.
  2. Watch CloudWatch for `SECURITY_AUDIT action=worker_auth.rejected` and `action=worker_auth.agent_not_authorized` spikes — these indicate a client not sending credentials. Roll forward client fixes; do not re-disable the flag.
  3. The boot assertion (Change 5) is the backstop: once shipped, prod literally cannot start with the control off.

## Test plan

### Unit/integration tests to add (`mcp_server/tests/test_auth_security.py` + new file)
Existing `test_auth_security.py` patches `sys.modules["api.auth"]._REQUIRE_WORKER_AUTH`. Reuse that pattern. **Update the three existing tests** that assert body-fallback (`test_mismatch_logs_warning_when_not_required`, the `*_when_not_required` variants) — under the new fail-closed `_enforce_worker_identity` there is no "allow body value" path, so these should be rewritten to assert rejection or removed.

New tests (name → assertion):
1. `test_enforce_worker_identity_no_auth_raises_401` — `_enforce_worker_identity(None, "exec-x", path)` raises `HTTPException(401)` (reproduces the bug: previously returned `"exec-x"`).
2. `test_enforce_worker_identity_mismatch_raises_403` — JWT `exec-a`, body `exec-b` → 403, regardless of flag value.
3. `test_enforce_worker_identity_match_passes` — JWT `exec-a`, body `exec-a` → returns `exec-a`.
4. `test_resolve_worker_identity_jwt_authoritative` — with `worker_auth` set and matching body → returns JWT executor_id.
5. `test_resolve_worker_identity_anon_no_sig_raises_401` — no worker_auth, no signature headers → 401.
6. `test_resolve_worker_identity_agent_owns_task_allowed` — mock `verify_agent_auth_write` → `AgentAuth(auth_method="erc8128", agent_id=A)`, mock `verify_agent_owns_task(A, task)=True`, mock `get_task` returns `executor_id=E` → returns `E` (H2H path works).
7. `test_resolve_worker_identity_agent_not_owner_403` — `verify_agent_owns_task=False` → 403.
8. **End-to-end soft-endpoint sweep** (new `test_worker_auth_required_endpoints.py`): build the FastAPI app with the real `verify_worker_auth` (not overridden) and `_REQUIRE_WORKER_AUTH=True`; for each of `POST /tasks/{id}/apply`, `POST /tasks/{id}/submit`, `GET /workers/tasks/{id}/my-submission`, `GET /submissions/{id}`, `GET /evidence/presign-download?key=...`, `GET /evidence/presign-upload?...`, `POST` rate_agent — assert **no `Authorization` header → 401** (reproduces: today these return 200). Then with a valid mocked JWT principal matching the body → assert non-401.
9. `test_presign_download_no_auth_401` / `test_get_submission_detail_no_auth_401` — specifically assert the previously open branches now 401 even when `_REQUIRE_WORKER_AUTH` is patched **False** (they must be flag-independent — Changes 2 & 3).
10. **Update `tests/test_h2h_executor_type.py`:** it overrides `verify_worker_auth -> None` and posts a body `executor_id`. After the fix, `apply_to_task` calls `resolve_worker_identity` (which 401s a None principal with no signature). Adjust the override to supply a `WorkerAuth(executor_id=EXECUTOR_ID, auth_method="jwt")` so the executor-type gate (the actual subject under test) is still exercised, OR override `resolve_worker_identity` to return `EXECUTOR_ID`. Keep the three executor-type assertions intact.
11. `test_boot_assert_worker_auth_required` — set `ENVIRONMENT=production`, `EM_REQUIRE_WORKER_AUTH=false` → `_assert_worker_auth_required_in_production()` raises `RuntimeError`; with `true` or non-production → no raise.

Run: `cd mcp_server && pytest -m security tests/test_auth_security.py tests/test_worker_auth_required_endpoints.py tests/test_h2h_executor_type.py`.

### Manual / E2E verification (against staging, then prod post-deploy)
1. `curl -s -o /dev/null -w "%{http_code}" "https://api.execution.market/api/v1/evidence/presign-download?key=tasks/<known-task>/submissions/<exec>/x.jpg"` → expect **401** (was 200 + presigned URL).
2. `curl ... -X POST .../api/v1/tasks/<id>/apply -d '{"executor_id":"<victim>"}'` with no auth → expect **401** (was 200).
3. Same calls **with** a valid Supabase Bearer token whose executor matches → expect 2xx.
4. H2H: publishing agent signs an ERC-8128 request to `/submit` for its task's assigned executor → expect 2xx.
5. Web: log in on `execution.market`, upload evidence on an assigned task → upload succeeds (Change 6 verified).
6. Confirm boot assertion: deploy a task-def with `EM_REQUIRE_WORKER_AUTH=false` + `ENVIRONMENT=production` to a throwaway service → container fails health check / logs the CRITICAL. Then revert.

## Rollback plan
- **Fast mitigation if legitimate traffic breaks:** set `EM_REQUIRE_WORKER_AUTH=false` via Terraform (or a task-def revision) **only if the boot assertion (Change 5) is not yet deployed.** Once Change 5 ships, the var cannot be false in production — so rollback = redeploy the **previous image tag** (the pre-fix task-def revision) via `aws ecs update-service --task-definition <prev-rev>`. Note the prior image is the vulnerable one; treat re-disable as an emergency-only stopgap and re-roll-forward with client fixes ASAP.
- Code is additive and behind the env default; reverting the four PR commits restores prior behavior. No DB migration is involved, so there is nothing to migrate down.

## DB migration
**None required.** This is a pure auth/identity-resolution and config fix; no schema or data change. (For reference, the next free Supabase migration number is `111` — `supabase/migrations/` currently ends at `110_moonpay_onramp_attempts.sql` — but no migration is added by this fix.)

## Verification checklist
- [ ] `auth.py:798` default changed to `"true"`.
- [ ] `_enforce_worker_identity` raises 401 on `None` principal and 403 on mismatch; body-fallback branch removed.
- [ ] `resolve_worker_identity` added; `apply_to_task` and `submit_work` migrated to it with `task_id`.
- [ ] `rate_agent_endpoint` rejects `worker_auth is None` with 401.
- [ ] `get_submission_detail` (workers.py) rejects anon with 401 (no "log but allow").
- [ ] `presign_download` (evidence.py) rejects anon/unparseable-key and fails closed on lookup error.
- [ ] `ecs.tf` adds `{ name = "EM_REQUIRE_WORKER_AUTH", value = "true" }`; applied → new task-def revision carries it.
- [ ] `_assert_worker_auth_required_in_production()` added to `main.py` and registered in the boot block.
- [ ] `dashboard/src/services/evidence.ts` presign calls send `buildAuthHeaders()`; `em-mobile/` + XMTP bot audited for the same.
- [ ] New tests 1-11 added and passing under `pytest -m security`; `test_h2h_executor_type.py` updated and green.
- [ ] Manual curl checks return 401 unauthenticated, 2xx authenticated; web evidence upload works.
- [ ] CloudWatch `SECURITY_AUDIT action=worker_auth.rejected` rate stable (no legitimate-client breakage) after prod deploy.
