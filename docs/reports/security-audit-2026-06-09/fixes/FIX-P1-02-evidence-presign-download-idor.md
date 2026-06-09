---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-02
---
# FIX-P1-02 — Unauthenticated IDOR on `GET /presign-download`: access control skipped when no JWT → arbitrary private evidence read

## Summary
`GET /api/v1/evidence/presign-download` wraps its entire ownership check inside `if _key_task_id and worker_auth:` (`evidence.py:244`). Because `EM_REQUIRE_WORKER_AUTH` defaults to `false` in production, `verify_worker_auth` returns `None` (not 401) for any request with no Bearer JWT, so `worker_auth` is `None`, the 403 branch is skipped, and the endpoint mints a working 1-hour S3 presigned GET URL for **any** attacker-supplied `key`. An unauthenticated attacker who harvests an evidence S3 key (trivially obtainable via the public showcase feed, the soft-auth `GET /submissions/{id}`, or Supabase anon-key reads) can download arbitrary workers' private evidence — geotagged photos, faces, proof-of-presence selfies, and ID-like documents. The fix makes the endpoint **deny-by-default**: require an authenticated principal (assigned executor, the task's publishing agent, or admin) and compute `is_authorized` *unconditionally* before signing any URL.

## Severity & Impact (why P1)
- **What's at risk:** Confidential/biometric PII for every worker across the entire evidence bucket — GPS-tagged photos, selfies, faces, PDFs, possible identity documents. GDPR-relevant special-category data.
- **Why P1 (not P2):** A real fail-open access control on a sensitive endpoint, with a complete and currently-live exploit chain in production (taskdef `em-production-mcp-server:535` does **not** set `EM_REQUIRE_WORKER_AUTH`). The presign endpoint *is* the intended access gate — the bucket blocks public access (`evidence.tf` block-public-access = true; OAC-only bucket policy), so this endpoint failing open is the breach, not a redundant control.
- **Why not P0:** Data disclosure, not fund loss or full system auth bypass.
- **Blast radius:** All evidence objects, all workers, all tasks. The minted URL works directly against S3 for 1 hour (`PRESIGN_EXPIRES_DOWNLOAD = 3600`), bypassing CloudFront and the API-Gateway JWT authorizer (which fronts a *separate* Lambda, not this FastAPI endpoint).

## Affected code (exact file:line references)
**`mcp_server/api/routers/evidence.py`** — `presign_download()` (decorator `@router.get("/presign-download")` at line 221, handler at 229):

```python
# evidence.py:244-267  (the defect: ownership check nested under `and worker_auth`)
if _key_task_id and worker_auth:          # <-- worker_auth is None for anon callers
    try:
        task = await db.get_task(_key_task_id)
        if task:
            is_executor = task.get("executor_id") == worker_auth.executor_id
            if not is_executor:
                raise HTTPException(403, "You do not have access to this evidence")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Could not verify evidence download access: %s", e)  # fail-OPEN

# evidence.py:269-282  (reached unconditionally → signs URL for any key)
if not EVIDENCE_BUCKET:
    raise HTTPException(503, "Evidence storage not configured")
key = key.strip().lstrip("/")
if not key or ".." in key:
    raise HTTPException(400, "Invalid key")
download_url = s3.generate_presigned_url("get_object", Params={"Bucket": EVIDENCE_BUCKET, "Key": key}, ExpiresIn=PRESIGN_EXPIRES_DOWNLOAD)
```

Supporting (root enablers, not changed by the primary fix):
- `mcp_server/api/auth.py:798-800` — `_REQUIRE_WORKER_AUTH` defaults `false`.
- `mcp_server/api/auth.py:839-851` — `verify_worker_auth` returns `None` (not 401) when flag off and no token.
- `mcp_server/api/routers/evidence.py:293-294` — when unauthenticated, mints an `authorizer_jwt` with `actor_id = task_id` (a fabricated principal — must be fixed too).

Adjacent same-pattern defect (in scope — covered by Fix step 2):
- `mcp_server/api/routers/evidence.py:104-141` — `presign_upload()` calls `_enforce_worker_identity` (`auth.py:943`) which, with `worker_auth=None`, just **returns the body `executor_id`**; the only block is `task.executor_id != body executor_id` (line 126), and that check is skipped when the task is unassigned (`executor_id` null) → evidence planting/tampering.

## Root cause
The ownership check is **conditional on the presence of `worker_auth`** instead of being an unconditional gate. The design implicitly assumed `verify_worker_auth` would reject unauthenticated callers — but that dependency is configured to **fail open** (`EM_REQUIRE_WORKER_AUTH=false`), returning `None` rather than raising. So "no JWT" silently means "skip access control" rather than "deny". Compounding defects: (a) the `except Exception` at line 266 swallows DB errors and **continues to sign** (fail-open on error); (b) the endpoint never consults agent auth or admin auth, so the only principal it can recognize is a worker JWT — yet it still signs when none is present.

## Exploit scenario (concrete attacker steps)
1. Attacker hits the public showcase feed (`showcase.py` `_primary_image_url`) or `GET /api/v1/submissions/{id}` (soft-auth: returns full `evidence` jsonb when `worker_auth` is None), or reads `submissions` rows via the Supabase anon key (RLS `submissions_select_task_owner` is `USING (true)`), and extracts an evidence object key, e.g. `tasks/<task>/submissions/<victim>/<rand>-selfie.jpg`.
2. Attacker calls — **with no `Authorization` header**:
   `GET https://api.execution.market/api/v1/evidence/presign-download?key=tasks/<task>/submissions/<victim>/<rand>-selfie.jpg`
3. `verify_worker_auth` → `None` → the `if _key_task_id and worker_auth:` block is skipped → execution falls through to line 278.
4. Server returns a valid 1-hour presigned S3 GET URL. Attacker downloads the victim's geotagged selfie. Repeat at scale across harvested keys.

## The Fix (deny-by-default, code-level)

### File 1 (PRIMARY): `mcp_server/api/routers/evidence.py` — rewrite `presign_download()`

Make authorization **unconditional**: resolve the principal from worker JWT **and** agent ERC-8128 signature **and** admin key; compute `is_authorized`; raise `401` when no principal is present and `403` when the principal is not entitled — **before** signing. Fail **closed** on DB error. Reject unparseable / non-`tasks/` keys with `403`. Stop minting a JWT with a fabricated `actor_id`.

Replace the imports near the top of the file (line 19):

```python
# OLD (evidence.py:19)
from ..auth import verify_worker_auth, WorkerAuth, _enforce_worker_identity

# NEW
from ..auth import (
    verify_worker_auth,
    WorkerAuth,
    _enforce_worker_identity,
    verify_agent_auth_read,   # non-raising: returns AgentAuth (erc8128 or anonymous)
    AgentAuth,
)
from ..admin import verify_admin_key
```

Add a small authorization helper above `presign_download` (after the response models, ~line 94). It centralizes the entitlement decision and is independently unit-testable:

```python
def _agent_matches_task(agent_auth: Optional["AgentAuth"], task: dict) -> bool:
    """True iff agent_auth is a real (non-anonymous) ERC-8128 principal that owns the task.

    A task's publishing principal is stored in tasks.agent_id (wallet address OR
    numeric ERC-8004 id). We only trust a *signed* identity here — the anonymous
    Agent #2106 fallback (auth_method="anonymous") must NOT match anything.
    """
    if agent_auth is None or agent_auth.auth_method != "erc8128":
        return False
    task_agent = str(task.get("agent_id") or "").lower()
    if not task_agent:
        return False
    wallet = (agent_auth.wallet_address or "").lower()
    erc_id = str(agent_auth.erc8004_agent_id or "")
    if wallet and wallet == task_agent:
        return True
    if erc_id and erc_id == task_agent:
        return True
    return False
```

Rewrite the handler body. Note: `verify_admin_key` *raises* on a malformed/invalid admin key, and `verify_agent_auth_read` *raises* on a bad ERC-8128 signature — both must be probed defensively so a missing credential degrades to "not admin / anonymous" rather than blowing up. We treat only an **affirmative** admin result or a real signed agent as a principal.

```python
@router.get(
    "/presign-download",
    response_model=PresignDownloadResponse,
    responses={
        400: {"description": "Invalid parameters"},
        401: {"description": "Authentication required"},
        403: {"description": "Not authorized for this evidence"},
        503: {"description": "Evidence storage not configured"},
    },
)
async def presign_download(
    raw_request: Request,
    key: str = Query(..., description="S3 object key"),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> PresignDownloadResponse:
    """Generate a presigned S3 GET URL for evidence download.

    DENY BY DEFAULT. Access control is unconditional: the caller must be the
    task's assigned executor (worker JWT), the task's publishing agent
    (ERC-8128 signature), or an admin (X-Admin-Key). Otherwise 401/403.
    """
    if not EVIDENCE_BUCKET:
        raise HTTPException(503, "Evidence storage not configured")

    # --- Sanitize + parse task_id from the key (fail closed on bad shape) ---
    key = key.strip().lstrip("/")
    if not key or ".." in key:
        raise HTTPException(400, "Invalid key")
    parts = key.split("/")
    if len(parts) < 2 or parts[0] != "tasks" or not parts[1]:
        # Unparseable / non-tasks key → DENY (never "skip the check").
        logger.warning(
            "SECURITY_AUDIT action=evidence.download_denied reason=bad_key_shape"
        )
        raise HTTPException(403, "You do not have access to this evidence")
    task_id = parts[1]

    # --- Probe each principal source defensively (never sign on probe errors) ---
    # 1) Admin (X-Admin-Key / Bearer admin key). verify_admin_key RAISES on
    #    bad/missing key, so only an affirmative dict counts as admin.
    is_admin = False
    try:
        await verify_admin_key(
            authorization=raw_request.headers.get("authorization"),
            x_admin_key=raw_request.headers.get("x-admin-key"),
            x_admin_actor=raw_request.headers.get("x-admin-actor"),
        )
        is_admin = True
    except HTTPException:
        is_admin = False  # not an admin — fall through to other principals

    # 2) Agent ERC-8128 signature (publishing agent). read variant is
    #    non-raising for *anonymous* but RAISES on a *bad* signature.
    agent_auth: Optional[AgentAuth] = None
    try:
        agent_auth = await verify_agent_auth_read(raw_request)
    except HTTPException:
        agent_auth = None  # malformed signature → treat as no agent principal

    # 3) Worker JWT already resolved via Depends(verify_worker_auth) above.

    # --- Did the caller present ANY principal at all? ---
    has_principal = (
        is_admin
        or worker_auth is not None
        or (agent_auth is not None and agent_auth.auth_method == "erc8128")
    )
    if not has_principal:
        logger.warning(
            "SECURITY_AUDIT action=evidence.download_unauth task=%s", task_id
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication required to download evidence",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Resolve the task and decide entitlement. Fail CLOSED on DB error. ---
    if is_admin:
        is_authorized = True
        actor_id = "admin"
    else:
        try:
            import supabase_client as db

            task = await db.get_task(task_id)
        except Exception as e:
            logger.error(
                "evidence.download: task lookup failed (deny) task=%s err=%s",
                task_id,
                e,
            )
            raise HTTPException(503, "Could not verify evidence access")
        if not task:
            raise HTTPException(403, "You do not have access to this evidence")

        is_executor = bool(
            worker_auth and task.get("executor_id") == worker_auth.executor_id
        )
        is_owner_agent = _agent_matches_task(agent_auth, task)
        is_authorized = is_executor or is_owner_agent
        actor_id = (
            worker_auth.executor_id
            if is_executor
            else (agent_auth.agent_id if is_owner_agent else "unknown")
        )

    if not is_authorized:
        logger.warning(
            "SECURITY_AUDIT action=evidence.download_denied task=%s actor=%s",
            task_id,
            actor_id[:8],
        )
        raise HTTPException(403, "You do not have access to this evidence")

    # --- Authorized: sign the URL ---
    s3 = _get_s3()
    download_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": EVIDENCE_BUCKET, "Key": key},
        ExpiresIn=PRESIGN_EXPIRES_DOWNLOAD,
    )

    public_url = (
        f"{EVIDENCE_PUBLIC_BASE_URL}/{key}" if EVIDENCE_PUBLIC_BASE_URL else None
    )

    # Mint the Lambda authorizer JWT with the REAL actor (never task_id).
    authorizer_jwt: Optional[str] = None
    try:
        from integrations.evidence.jwt_helper import mint_evidence_jwt

        authorizer_jwt = mint_evidence_jwt(
            task_id=task_id,
            submission_id=key,
            actor_id=actor_id,
        )
    except RuntimeError as e:
        logger.debug("[Evidence] skipping authorizer JWT (download): %s", e)
    except Exception as e:
        logger.error("[Evidence] failed to mint authorizer JWT (download): %s", e)

    return PresignDownloadResponse(
        download_url=download_url,
        key=key,
        public_url=public_url,
        expires_in=PRESIGN_EXPIRES_DOWNLOAD,
        authorizer_jwt=authorizer_jwt,
    )
```

Key behavioral changes vs. the old code:
- Authorization is **unconditional** — no `and worker_auth` nesting.
- No principal → **401**; wrong principal → **403**; bad key shape → **403** (was: silently signed).
- DB error → **503 deny** (was: `logger.warning` + continue to sign).
- Agent (ERC-8128) and admin principals are now first-class (was: worker JWT only).
- `authorizer_jwt.actor_id` is the real actor (was: `task_id` when unauthenticated).

### File 1 (step 2): harden `presign_upload()` (same file, lines 104-141)

The upload path has the identical fail-open shape via `_enforce_worker_identity`. Tighten it so an unauthenticated caller cannot mint a PUT URL into a victim's submission path or upload to an unassigned task. Replace the executor-verification block:

```python
# OLD (evidence.py:116-141): _enforce_worker_identity returns body executor_id
# when worker_auth is None, then only blocks on task.executor_id mismatch
# (skipped when task is unassigned).

# NEW — require an authenticated principal (worker JWT for the executor,
# OR the publishing agent, OR admin) before issuing an upload URL:
executor_id = _enforce_worker_identity(worker_auth, executor_id, raw_request.url.path)

try:
    import supabase_client as db
    task = await db.get_task(task_id)
except Exception as e:
    logger.error("evidence.upload: task lookup failed (deny): %s", e)
    raise HTTPException(503, "Could not verify upload access")
if not task:
    raise HTTPException(404, "Task not found")

# Probe agent + admin principals (defensive, non-fatal on bad creds).
is_admin = False
try:
    await verify_admin_key(
        authorization=raw_request.headers.get("authorization"),
        x_admin_key=raw_request.headers.get("x-admin-key"),
        x_admin_actor=raw_request.headers.get("x-admin-actor"),
    )
    is_admin = True
except HTTPException:
    is_admin = False
agent_auth: Optional[AgentAuth] = None
try:
    agent_auth = await verify_agent_auth_read(raw_request)
except HTTPException:
    agent_auth = None

is_assigned_executor = bool(
    worker_auth and task.get("executor_id")
    and task["executor_id"] == worker_auth.executor_id
)
is_owner_agent = _agent_matches_task(agent_auth, task)

if not (is_admin or is_assigned_executor or is_owner_agent):
    logger.warning(
        "SECURITY_AUDIT action=evidence.upload_denied task=%s claimed_executor=%s",
        task_id, str(executor_id)[:8],
    )
    raise HTTPException(403, "Not authorized to upload evidence for this task")
```

> Backward-compat note for upload: legitimate workers already authenticate with a Supabase JWT in the dashboard/mobile submit flow, so `worker_auth` is present for them. Agents that publish a task and upload their own reference evidence sign ERC-8128. This change blocks *unauthenticated* upload-URL minting, which has no legitimate caller. If telemetry (the `evidence.upload_denied` log) shows real workers being blocked because their client doesn't send the JWT, gate this stricter upload check behind the same flag as below before requiring it — but the download fix must ship unconditionally.

### No DB migration required
This is purely an access-control code change. `tasks.agent_id`, `tasks.executor_id`, and the joined `executor` (`wallet_address`, `erc8004_agent_id`) already exist and are returned by `db.get_task()` (`supabase_client.py:308-346`). The next free migration number is `111_` — **not used by this fix.** If a future operator wants an audit table for denied evidence reads, that is a separate ticket.

### Infra / env: no required change to ship the primary fix
The primary fix is self-contained in application code and does **not** depend on flipping any flag. The endpoint now fails closed regardless of `EM_REQUIRE_WORKER_AUTH`.

**Optional defense-in-depth (separate, regression-gated ticket — do NOT bundle as the primary fix):** set `EM_REQUIRE_WORKER_AUTH=true` so `verify_worker_auth` fails closed globally. Per the verifier, this flips `_enforce_worker_identity` body-fallback for **every** endpoint (submit_work, presign-upload, etc.) and would 403 MCP/mobile/agent flows that pass `executor_id` in the body without a Supabase JWT. Treat as its own change with a full regression of all body-fallback callers.

If/when adopted, the ECS task-definition update is:
```jsonc
// container "environment" of em-production-mcp-server task def
{ "name": "EM_REQUIRE_WORKER_AUTH", "value": "true" }
```
And the matching Terraform addition in `infrastructure/terraform/ecs.tf` `environment` block:
```hcl
{ name = "EM_REQUIRE_WORKER_AUTH", value = "true" },
```
Manual AWS CLI (staged) — register a new revision, then force-new-deployment:
```bash
# (register new task-def revision with the env var, then)
MSYS_NO_PATHCONV=1 aws ecs update-service --cluster em-production-cluster \
  --service em-production-mcp-server --force-new-deployment --region us-east-2
```

### Out-of-scope but related (file follow-up tickets — verifier flagged)
Fixing `presign_download` alone does **not** fully close evidence leakage. Track separately:
1. `GET /submissions/{id}` (`workers.py:284-296`) soft-auth returns full `evidence` jsonb (incl. `forensic.gps`) to anonymous callers → make fail-closed.
2. Showcase feed embeds full S3 keys in `fileUrl` → minimize / sign.
3. Evidence CloudFront distribution (`evidence.tf:118-126`) has no viewer authorizer / trusted_key_groups → add signed-URL/cookie or a viewer-request authorizer.
4. `EVIDENCE_PUBLIC_BASE_URL` drift to raw S3 host vs intended CloudFront domain.

### Backward-compatibility risk & safe rollout
- **Download fix:** Legitimate downloaders are (a) the assigned worker (dashboard/mobile, authenticated via Supabase JWT → `worker_auth` set), (b) the publishing agent reviewing submitted evidence (ERC-8128 signed), and (c) admins. All three are now explicitly allowed. The only flows that break are *unauthenticated* ones — which is the vulnerability. **Low compat risk.** Roll out by deploying the MCP server (`deploy-mcp` skill) and watching CloudWatch for a spike in `evidence.download_unauth` / `evidence.download_denied` SECURITY_AUDIT logs; a spike from a legitimate client means that client wasn't sending its JWT/signature and needs a client-side fix — not a reason to revert the server.
- **Upload fix:** see the upload note above; if real workers are blocked, flag-gate the stricter upload check while keeping the download fix live.

## Test plan

Add `mcp_server/tests/test_evidence_presign_authz.py` (marker `security`), mounting `evidence.router` on a bare `FastAPI` app with a `TestClient`, mocking `supabase_client.get_task` and the S3 client. Each test asserts the **status code** and that `generate_presigned_url` is/ isn't called.

Tests to add (names + assertions):

1. `test_presign_download_anonymous_is_401_reproduces_bug` — **reproduces the vuln**: no auth headers, valid `tasks/<id>/...` key. Pre-fix this returns 200 with a `download_url`; post-fix it MUST return **401** and `s3.generate_presigned_url` MUST NOT be called.
2. `test_presign_download_wrong_worker_is_403` — `worker_auth` overridden to a non-assigned executor; `get_task` returns a task with a different `executor_id`. Asserts **403**, no URL.
3. `test_presign_download_assigned_executor_ok` — `worker_auth.executor_id == task.executor_id`. Asserts **200**, `download_url` present, S3 called once.
4. `test_presign_download_publishing_agent_ok` — override `verify_agent_auth_read` to return `AgentAuth(auth_method="erc8128", wallet_address="0xAGENT", agent_id="0xAGENT")`; `get_task` returns `agent_id="0xagent"`. Asserts **200** (case-insensitive wallet match).
5. `test_presign_download_anonymous_agent_does_not_match` — `verify_agent_auth_read` returns `AgentAuth(auth_method="anonymous", agent_id="2106")`. Asserts **401** (anonymous platform identity must NOT count as a principal).
6. `test_presign_download_admin_ok` — set `EM_ADMIN_KEY`, send `X-Admin-Key`. Asserts **200** without needing a task match.
7. `test_presign_download_bad_key_shape_is_403` — `key="foo/bar"` (non-`tasks/` prefix) with a valid worker. Asserts **403**, no URL.
8. `test_presign_download_path_traversal_is_400` — `key="tasks/../secret"`. Asserts **400**.
9. `test_presign_download_db_error_fails_closed` — `get_task` raises; authenticated worker. Asserts **503**, no URL (proves fail-closed-on-error).
10. `test_presign_upload_anonymous_is_403` — no auth, valid task_id/executor_id. Asserts **403**, no PUT URL (covers the upload hardening).
11. `test_presign_upload_assigned_executor_ok` — worker JWT matches `task.executor_id`. Asserts **200**, PUT URL present.

Reuse the existing harness style from `tests/test_auth_phase0.py` (dependency overrides via `app.dependency_overrides[verify_worker_auth] = ...`) and patch `verify_agent_auth_read` / `verify_admin_key` with `unittest.mock.patch` on the `api.routers.evidence` namespace.

Run:
```bash
cd mcp_server && pytest tests/test_evidence_presign_authz.py -v
cd mcp_server && pytest -m security
```

### Manual / E2E verification
```bash
# 1) Anonymous download MUST now be rejected (was 200 + URL):
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://api.execution.market/api/v1/evidence/presign-download?key=tasks/<known_task>/submissions/<exec>/<rand>-x.jpg"
# Expect: 401

# 2) Bad key shape:
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://api.execution.market/api/v1/evidence/presign-download?key=foo/bar"
# Expect: 403

# 3) Admin can still download:
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Admin-Key: $EM_ADMIN_KEY" \
  "https://api.execution.market/api/v1/evidence/presign-download?key=tasks/<task>/submissions/<exec>/<rand>-x.jpg"
# Expect: 200
```
(Use the Golden Flow worker JWT to confirm the assigned executor still gets 200.)

## Rollback plan
Single-file application change, no schema/infra coupling. To roll back: `git revert <commit>` and redeploy the MCP server via the `deploy-mcp` skill (ECR build → `aws ecs update-service --force-new-deployment`). No data migration to undo. If the optional `EM_REQUIRE_WORKER_AUTH=true` flag was *also* shipped and causes broad 403s, remove that env var from the task definition and force a new deployment — the code fix stands on its own and does not require the flag.

## Verification checklist
- [ ] Confirmed in current code that `presign_download` nests the 403 under `if _key_task_id and worker_auth:` (`evidence.py:244`) and falls through to sign at `evidence.py:278`.
- [ ] `presign_download` rewritten: authorization is unconditional; 401 (no principal) / 403 (wrong principal or bad key shape) raised **before** `generate_presigned_url`.
- [ ] DB lookup failure now denies (503), not signs (fail-closed).
- [ ] Anonymous Agent #2106 (`auth_method="anonymous"`) does NOT satisfy the principal check.
- [ ] Publishing agent (ERC-8128) and admin (`X-Admin-Key`) paths added and tested.
- [ ] `authorizer_jwt.actor_id` is a real actor (executor/agent/admin), never `task_id`.
- [ ] `presign_upload` hardened to require an authenticated, entitled principal.
- [ ] New test file `test_evidence_presign_authz.py` added; the anonymous-401 test fails on `main` (reproduces the bug) and passes after the fix.
- [ ] `pytest -m security` green; no regressions in `pytest -m core`.
- [ ] Manual curl: anonymous download → 401; bad key → 403; admin → 200; assigned worker → 200.
- [ ] No secret values printed in any log line or test (only truncated/`[:8]` ids).
- [ ] Follow-up tickets filed for `GET /submissions/{id}` soft-auth, showcase key exposure, CloudFront viewer auth, and `EVIDENCE_PUBLIC_BASE_URL` drift.
- [ ] (Optional, separate ticket) `EM_REQUIRE_WORKER_AUTH=true` decision tracked with full body-fallback regression.
