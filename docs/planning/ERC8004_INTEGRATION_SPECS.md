# ERC-8004 Full Integration Specs (Hardened)

> Date: February 11, 2026  
> Status: Pre-implementation (hardened for production rollout)  
> Scope: Backend API, MCP tools, dashboard UI, Supabase schema  
> Goal: Complete ERC-8004 identity + bidirectional reputation integration without breaking payment finality, idempotency, or abuse controls

---

## 1) Why this revision

The prior spec identified the right gaps but left production-risky ambiguity in five areas:

1. Missing hard invariants (what can never break).
2. Ambiguous idempotency and dedup behavior.
3. No reliable retry path for fire-and-forget failures.
4. No feature-flagged rollout/rollback plan.
5. No acceptance gates that prove correctness end-to-end.

This version defines explicit contracts, failure semantics, and release gates.

---

## 2) Non-negotiable invariants

These are mandatory:

1. Payment finality first: never mark a submission `accepted` unless a payment tx hash exists.
2. ERC-8004 side effects never block payment or approval success.
3. Each ERC-8004 side effect is idempotent and deduplicated per submission/direction.
4. Approval/rejection authorization checks remain unchanged (ownership checks stay mandatory).
5. All new behavior is behind feature flags with immediate kill switches.
6. Every emitted on-chain action has audit evidence in DB (tx hash or explicit error).

---

## 3) Verified current state (from code)

| Area | Verified behavior | Evidence |
|---|---|---|
| Agent->worker rating on approval | `_send_reputation_feedback()` submits `rate_worker()` with hardcoded score `80` after payment settlement | `mcp_server/api/routes.py` |
| Payment gating | `approve_submission` fails with `502` if no `payment_tx`, then updates submission only after tx exists | `mcp_server/api/routes.py` |
| Worker identity registration flow | API exists for check + unsigned tx + confirm; uses wallet-signed tx path | `mcp_server/api/routes.py` (`/executors/{id}/identity`, `/register-identity`, `/confirm-identity`) |
| Gasless worker registration helper | `register_worker_gasless()` exists but is not wired into lifecycle | `mcp_server/integrations/erc8004/identity.py` |
| Worker->agent public rating API | Endpoint exists and verifies rated `agent_id` ownership against task agent address | `mcp_server/api/reputation.py` (`/api/v1/reputation/agents/rate`) |
| Task ERC-8004 column | `tasks.erc8004_agent_id` exists | `supabase/migrations/020_tasks_erc8004_agent_id.sql` |
| Submission reputation tx tracking | `submissions.reputation_tx` exists (agent->worker path) | `supabase/migrations/021_add_reputation_tx_to_submissions.sql` |
| MCP reputation tools | No dedicated reputation tools file is registered | `mcp_server/tools`, `mcp_server/server.py` |

Critical current limitation to address:

- `verify_agent_identity()` resolves numeric IDs only; wallet-like agent identifiers are treated as not-resolvable. This can leave `tasks.erc8004_agent_id` unset for wallet-based agents.  
  Evidence: `mcp_server/integrations/erc8004/identity.py`.

---

## 4) Target architecture (production-safe)

### 4.1 Blocking path (unchanged principle)

1. Settle payment.
2. Require `payment_tx` for approval success.
3. Update submission/task status.

### 4.2 Non-blocking side-effect path (new)

After successful settlement, enqueue side effects and execute best-effort immediately:

- `register_worker_identity`
- `rate_worker_from_agent` (existing behavior, but dynamic scoring)
- `rate_agent_from_worker` (new)

Failures are persisted and retried asynchronously.

### 4.3 Outbox table (required)

Add a durable side-effect ledger to guarantee dedup + retry:

```sql
CREATE TABLE IF NOT EXISTS erc8004_side_effects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
  effect_type TEXT NOT NULL CHECK (effect_type IN (
    'register_worker_identity',
    'rate_worker_from_agent',
    'rate_agent_from_worker',
    'rate_worker_on_rejection'
  )),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed', 'skipped')),
  attempts INTEGER NOT NULL DEFAULT 0,
  tx_hash TEXT,
  score INTEGER CHECK (score >= 0 AND score <= 100),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (submission_id, effect_type)
);
```

Why this is required:

- `fire-and-forget` alone loses failed operations.
- One `submissions.reputation_tx` column cannot track all directions.
- Idempotent retries need a canonical key.

---

## 5) Workstream specs

## WS-1) Worker auto-registration after first paid completion

Objective:

- Auto-register workers on ERC-8004 after their first successful payout.

Hook:

- Success branch of `_settle_submission_payment()` (covers both manual approval and instant payout path).

Algorithm:

1. Guard by feature flag `feature.erc8004_auto_register_worker_enabled`.
2. Skip if worker wallet invalid or missing.
3. Skip if executor already has `erc8004_agent_id`.
4. Enqueue `register_worker_identity` side-effect row (dedup by unique key).
5. Best-effort immediate attempt:
   - call `register_worker_gasless(wallet, network=task.payment_network or "base")`
   - if success and `agent_id`, call `update_executor_identity(executor_id, agent_id)`
   - mark side effect `success` with tx metadata
6. On failure mark `failed` with `last_error`; do not affect approval response.

Idempotency:

- DB dedup: unique `(submission_id, effect_type)`.
- Domain dedup: skip when `executors.erc8004_agent_id` already set.
- Facilitator-level duplicate registration errors are treated as recoverable; fallback to `check_worker_identity()` and persist if found.

Files:

- `mcp_server/api/routes.py` (enqueue + invoke non-blocking side effects)
- `mcp_server/integrations/erc8004/identity.py` (reuse existing helpers)
- `supabase/migrations/*` (add side-effect table)

Tests:

- Missing wallet -> `skipped`, approval succeeds.
- Already registered worker -> no external call, `skipped`.
- Facilitator success -> executor identity updated.
- Facilitator failure -> `failed` side-effect row, approval still succeeds.

---

## WS-2) Worker -> agent auto-rating after payment

Objective:

- Close the bidirectional reputation loop automatically once worker is paid.

Precondition:

- Need reliable agent ERC-8004 ID resolution.

Resolution order (strict):

1. Use `task.erc8004_agent_id` if numeric.
2. Else if `task.agent_id` is numeric, use it.
3. Else optional lookup in new mapping table (`agent_identity_map`), if implemented.
4. Else mark side effect as `skipped` with reason `missing_agent_erc8004_id`.

Algorithm:

1. Guard by flag `feature.erc8004_auto_rate_agent_enabled`.
2. Enqueue `rate_agent_from_worker` side effect.
3. Calculate score (default from dynamic scoring module; fallback `85`).
4. Call `rate_agent(agent_id, task_id, score, proof_tx=payment_tx)`.
5. Persist tx hash and status in side-effect row.

Important:

- Do not reuse `submissions.reputation_tx` for reverse direction.
- Keep old `reputation_tx` for backward compatibility (agent->worker only).

Tests:

- Task with valid `erc8004_agent_id` -> on-chain feedback submitted.
- Wallet-only agent without mapping -> `skipped`, no exception.
- Idempotent retry call -> single on-chain submission due outbox dedup.

---

## WS-3) Rejection feedback policy (major/minor)

Objective:

- Support optional on-chain negative feedback without creating automatic abuse vectors.

API contract change:

- Extend `RejectionRequest` in `mcp_server/api/routes.py`:
  - `severity: "minor" | "major" = "minor"`
  - `reputation_score: Optional[int]` constrained to `0..50` for `major` only

Policy:

1. `minor` (default): local rejection only, no on-chain write.
2. `major`: enqueue `rate_worker_on_rejection` side effect with capped score.
3. If dispute overturns rejection, call facilitator `revoke_feedback` and mark side effect as reversed.

Abuse controls:

- Existing task ownership checks stay mandatory.
- Rate-limit major rejection writes (max 3 per agent per 24h).
- Require non-empty notes (already required).
- Security audit log on every major rejection submission.

Tests:

- Minor rejection -> no side-effect row for on-chain write.
- Major rejection with score -> side-effect created and submitted.
- Major rejection without score -> default score `30`.
- Non-owner rejection attempt -> `403`.
- Rate limit exceeded -> `429`.

---

## WS-4) MCP reputation tools

Objective:

- Expose reputation and identity operations in MCP with proper read/write hints and ownership semantics.

New file:

- `mcp_server/tools/reputation_tools.py`

Tools:

1. `em_rate_worker` (write)
2. `em_rate_agent` (write)
3. `em_get_reputation` (read)
4. `em_check_identity` (read)
5. `em_register_identity` (write; explicit mode required: `wallet_signed` vs `gasless`)

Integration:

- Export in `mcp_server/tools/__init__.py`
- Register in `mcp_server/server.py`

Additional MCP enhancement:

- Add optional `rating_score` to `ApproveSubmissionInput` (`mcp_server/models.py`) and forward to dynamic scoring override.

Tests:

- Extend `mcp_server/tests/test_mcp_tools.py` for each new tool.
- Validate ownership/authorization and error surface consistency.

---

## WS-5) Dashboard reputation and identity UX

Objective:

- Surface identity/reputation actions and results without introducing auth abuse or broken UX on partial outages.

Required behavior:

1. Add register CTA in `IdentitySection` (`dashboard/src/pages/Profile.tsx`).
2. Default registration path uses existing wallet-signed flow from `useIdentity`:
   - `prepareRegistration` -> wallet send -> `confirmRegistration`.
3. Gasless registration (if desired later) must be behind authenticated backend control + rate limit; do not call public register endpoint directly from UI.
4. Show local + on-chain reputation when available.
5. Add worker->agent rating modal after completed tasks.
6. Add agent self-reputation card in `AgentDashboard`.

Data/source behavior:

- Local score source: Supabase (`useReputation`).
- On-chain score source: `/api/v1/reputation/agents/{id}`.
- If on-chain read fails, keep UI functional with local score and degraded badge state.

Files:

- `dashboard/src/pages/Profile.tsx`
- `dashboard/src/hooks/useIdentity.ts` (button wiring only; preserve existing flow)
- `dashboard/src/hooks/useProfile.ts` (on-chain overlay fetch)
- `dashboard/src/services/reputation.ts` (agent rating + identity helpers)
- `dashboard/src/pages/AgentDashboard.tsx`
- i18n files in `dashboard/src/i18n/locales/`

Tests:

- Add/extend component tests and service mock tests.
- Verify no broken state when on-chain endpoint returns `404/503`.

---

## WS-6) Dynamic scoring engine (replace hardcoded 80)

Objective:

- Replace fixed score with deterministic scoring derived from submission/task quality signals, with optional agent override.

New module:

- `mcp_server/reputation/scoring.py`

Primary function:

```python
def calculate_dynamic_score(
    task: dict,
    submission: dict,
    executor: dict,
    override_score: int | None = None,
) -> int:
    ...
```

Scoring model (v1):

- Speed: 0-30
- Evidence completeness: 0-30
- AI verification quality: 0-25
- Forensic metadata quality: 0-15
- Clamp final score to `0..100`

Rules:

1. If `override_score` is provided, use it (after validation).
2. Missing dimensions use neutral defaults, not zeros.
3. Deterministic output for same inputs.
4. Persist assigned score and source (`override|dynamic|fallback`) in side-effect payload.

Integrations:

- Update `_send_reputation_feedback()` signature to accept submission/executor/override.
- Extend `ApprovalRequest` (REST) and `ApproveSubmissionInput` (MCP) with optional score override.

Tests:

- Fast + complete + high AI -> high score.
- Slow + incomplete + weak AI -> low score.
- Override provided -> exact override used.
- Missing data -> stable neutral score.

---

## 6) Cross-cutting requirements

### 6.1 Feature flags (mandatory)

Add config keys (default `false` until staged rollout):

- `feature.erc8004_auto_register_worker_enabled`
- `feature.erc8004_auto_rate_agent_enabled`
- `feature.erc8004_rejection_feedback_enabled`
- `feature.erc8004_dynamic_scoring_enabled`
- `feature.erc8004_mcp_tools_enabled`

Implementation should use existing `PlatformConfig.is_feature_enabled(...)`.

### 6.2 Observability

Structured logs for each side effect:

- `event=erc8004_side_effect`
- `submission_id`
- `task_id`
- `effect_type`
- `status`
- `attempt`
- `tx_hash` (if any)
- `error` (if any)

Operational alerts:

- >5% failure rate over 15m for any effect type.
- Retry queue age > 30m for `pending/failed` items.

### 6.3 Retry strategy

- Retry schedule: 1m, 5m, 15m, 60m, 6h, 24h.
- Max attempts: 6.
- After max attempts -> status `failed` + alert.

### 6.4 Backward compatibility

- Do not remove or repurpose `submissions.reputation_tx`.
- Old flows continue to work when new flags are off.
- No API breaking changes; only additive request fields.

---

## 7) Rollout plan

1. Deploy schema migrations (outbox + optional helper columns).
2. Deploy code with all new ERC-8004 flags disabled.
3. Enable dynamic scoring only.
4. Enable auto worker registration.
5. Enable auto worker->agent rating.
6. Enable major rejection on-chain feedback.
7. Enable MCP reputation tools.
8. Enable dashboard UI features.

Rollback:

- Disable the corresponding feature flag immediately.
- Blocking payment/approval flow is unaffected by rollback of side effects.

---

## 8) Test plan and acceptance gates

Required suites:

1. `mcp_server/tests/test_p0_routes_idempotency.py`
2. `mcp_server/tests/test_reputation_ownership.py`
3. New unit tests for `mcp_server/reputation/scoring.py`
4. Extended `mcp_server/tests/test_mcp_tools.py`
5. Relevant e2e reputation and lifecycle tests in `mcp_server/tests/e2e/`
6. Dashboard component/service tests for identity/reputation UX

Must-pass acceptance criteria:

1. Approvals still require `payment_tx`.
2. Side-effect failures never flip approval success to failure.
3. No duplicate on-chain writes for same submission/effect type.
4. Worker identity auto-registration works and is idempotent.
5. Worker->agent auto-rating works when agent ERC-8004 ID is resolvable.
6. Missing agent ERC-8004 ID yields `skipped` state, not exception.
7. Rejection major/minor policy behaves exactly as specified.
8. All new behavior can be disabled live via feature flags.
9. Audit evidence exists for every side-effect attempt.

---

## 9) Recommended implementation order

| Step | Workstream | Why first | Est. effort |
|---|---|---|---|
| 1 | Outbox + feature flags + observability scaffolding | Foundation for safe retries and rollout | 3h |
| 2 | WS-6 Dynamic scoring | Replaces hardcoded scoring baseline | 2h |
| 3 | WS-1 Auto worker registration | Highest user impact, low coupling | 1.5h |
| 4 | WS-2 Auto worker->agent rating | Completes bidirectional loop | 2h |
| 5 | WS-3 Rejection policy | Safety feature with abuse controls | 2h |
| 6 | WS-4 MCP tools | Agent-facing operability | 2.5h |
| 7 | WS-5 Dashboard UX | Surface finalized backend capability | 4h |

Total estimated engineering effort: ~17 hours (excluding QA signoff and production monitoring window).

---

## 10) Open risks to track

1. Agent ID resolution gap for wallet-based agent identifiers (must be explicitly handled).
2. Environment schema drift between Supabase instances (run preflight schema checks before enabling flags).
3. Facilitator partial outages (retry queue and UI degradation behavior must be validated).
4. Abuse risk if gasless registration is exposed without auth/rate limits.

This spec is now implementation-ready with explicit safety rails and operational controls.
