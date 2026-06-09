---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-08
---
# FIX-P1-08 — Dispute resolution lets a single conflicted arbiter unilaterally redirect escrowed funds

## Summary

`POST /api/v1/disputes/{id}/resolve` (`mcp_server/api/routers/disputes.py:650`) authorizes a resolver as **either** the task owner **or** any executor who passes a generic eligibility bar (`reputation_score >= 80` AND `tasks_completed >= 10`), then immediately drives a real escrow payout (`release` → pays the worker-of-record, `refund` → refunds the agent). There is **no recusal check** (the resolver is never compared against `dispute.executor_id` or `dispute.agent_id`), **no assignment/claim requirement**, and **no multi-arbiter consensus** — a single verdict is final. This contradicts the DB consensus design in migration `004_disputes.sql` (`submit_arbitration_vote` requires a pre-assigned `arbitration_votes` row; `check_arbitration_complete` requires ≥2 votes + majority) which the REST path bypasses entirely.

## Severity & Impact (why P1)

- **Funds at risk**: the per-dispute contested escrow (the full bounty for the disputed task). Not the whole platform balance, which is why this is P1 and not P0.
- **WHO can authorize the release/refund of contested escrow is the broken control.** The idempotent settle path (`_helpers.py:1318-1335`) prevents *double*-payment, and the escrow-releasable-state check (`_helpers.py:1432-1448`) and worker≠agent self-payment block (`_helpers.py:1382-1392`) already exist — but none of them validate *who* authorized the release or whether that party is conflicted.
- **Strongest theft vector (worker self-deal)**: a worker who is the executor on a disputed submission and is an established account (rep ≥ 80, 10+ completed tasks — a low bar) calls `/resolve` with `verdict='release'` on **their own** dispute and pays themselves the full bounty for work the publisher disputed as fraudulent. Requires an established account, not an anonymous attacker — hence P1.
- **Collusion vector**: any single eligible executor can resolve *any* open dispute (no assignment requirement) `release`/`refund` to a colluding party for a kickback.
- **Publisher self-judge**: the task owner can resolve their own dispute `refund` to reclaim 100% after a worker completed a real-world task. (Weakest of the three — overlaps the publisher's existing reject/refund power in the normal approval flow — but the dispute path was supposed to be the worker's neutral recourse.)

## Affected code

`mcp_server/api/routers/disputes.py` — `resolve_dispute` authorization branch (lines 710-760). No recusal, no assignment, no consensus:

```python
# disputes.py:718-724 — task-owner branch: publisher can resolve their OWN dispute
dispute_agent_id = (dispute.get("agent_id") or "").lower()
is_task_owner = dispute_agent_id and dispute_agent_id in (caller_wallet, caller_agent_id)
if not is_task_owner:
    # disputes.py:724-760 — arbiter branch: resolves caller's executor_id by wallet
    #   and checks ONLY generic eligibility. NEVER compares executor_id to
    #   dispute["executor_id"]; NEVER checks an assignment row.
    executor_id = exec_query.data[0]["id"]
    eligible = await _check_human_arbiter_eligibility(executor_id, category)
    if not eligible:
        raise HTTPException(status_code=403, detail="Not eligible: ...")
# ...verdict is written directly (disputes.py:802) and payment dispatched (806-811)
```

`mcp_server/api/routers/disputes.py:228-263` — `_check_human_arbiter_eligibility`. Category specialty is explicitly **non-mandatory** (`_ = category in specialties`, lines 258-259); the bar is purely rep≥80 + 10 tasks. It never receives or checks the dispute's parties.

`mcp_server/api/routers/disputes.py:856-932` — `_trigger_resolution_payment`. `release` → `_settle_submission_payment` (pays `executor.wallet_address`); `refund` → `dispatcher.refund_trustless_escrow` (refunds the agent). Real funds move.

`supabase/migrations/004_disputes.sql:527-578` (`submit_arbitration_vote`, rejects unassigned arbiters: *"Not assigned to this dispute"*), `:581-670` (`check_arbitration_complete`, requires `v_votes_count < 2 → RETURN FALSE`), `:672-736` (`resolve_dispute`, labelled *"Manually resolve dispute (admin)"*). The REST path calls **none** of these.

`mcp_server/api/routes.py:33` registers `disputes_router` — endpoint is live in production. Its only auth dependency is `verify_agent_auth_write` (`auth.py:690`), which admits any ERC-8128-signed wallet — no admin gate.

## Root cause

The REST `resolve_dispute` endpoint reimplements dispute resolution as a **single direct table write** that replaces the migration-004 consensus model, and its authorization logic was written to answer "is this caller a plausible resolver?" instead of "is this caller a *neutral, authorized* resolver for *this* dispute?". Specifically it omits:

1. **Recusal** — the resolving party is never checked against the dispute's two parties (`executor_id`, `agent_id`).
2. **Neutrality of the eligibility gate** — `_check_human_arbiter_eligibility` is generic (rep + count) and does not exclude the task's own executor/publisher.
3. **Assignment** — any eligible executor can resolve any dispute; the DB-level "must hold an `arbitration_votes` row" guard is bypassed.
4. **Consensus** — one verdict is final; the ≥2-vote majority requirement is bypassed.

The backend uses the Supabase service-role key, so the DB-level guards in migration 004 are **never invoked** by this path — these Python checks are the only barrier, and they are insufficient.

## Exploit scenario (concrete attacker steps)

**Worker self-deal:**
1. Attacker is `executor_id = E` on a submission for task `T` (bounty `$B`, escrow locked at assignment). They are an established worker: `reputation_score >= 80`, `tasks_completed >= 10`.
2. Publisher opens a dispute `D` against the submission (`reason='fake_evidence'`). `D.executor_id = E`, `D.agent_id = publisher_wallet`, `D.status='open'`.
3. Attacker (wallet for `E`) signs an ERC-8128 request and calls `POST /api/v1/disputes/{D}/resolve` with `{"verdict":"release","reason":"my work is valid"}`.
4. `is_task_owner` is False (caller wallet ≠ `D.agent_id`). The arbiter branch resolves the caller's `executor_id` by wallet → `E`, runs `_check_human_arbiter_eligibility(E, category)` → True. **No recusal** → passes.
5. `_trigger_resolution_payment(verdict='release')` calls `_settle_submission_payment`, which (escrow is releasable, worker≠agent) pays `$B` to `E.wallet_address`. Attacker is paid for work the publisher disputed as fraudulent.

**Collusion:** attacker `A` (any eligible executor, *not* a party) and worker `W` agree on a kickback. `A` calls `/resolve` on `W`'s open dispute with `verdict='release'`. No assignment requirement, no second arbiter → `W` is paid, `A` takes a cut.

## The Fix (PRECISE, code-level)

**Strategy (matches verifier's "ship first" recommendation):** restore the migration-004 intent that unilateral resolution is **admin-only**, and add hard **recusal** so neither party can ever resolve their own dispute, while leaving a flag-gated path to the (future) assigned-arbiter consensus flow. This is the minimum that closes all three exploit vectors today.

Three layers, all in `mcp_server/api/routers/disputes.py`:

1. **Recusal (always on, no flag)** — reject any resolver who is a party to the dispute.
2. **Admin bypass (header `X-Admin-Key`)** — an authenticated admin may resolve (the legitimate operator path, mirroring migration-004's "admin" function). Admins are still subject to recusal is not required since the admin is a neutral operator — admin bypasses the *eligibility/assignment* requirement but the recusal check below is keyed on dispute parties, and the admin key is not a party, so it passes naturally.
3. **Unilateral human-arbiter resolution gated behind a feature flag** — default **OFF**. When OFF, a non-admin, non-owner eligible arbiter is rejected (must go through admin or the future consensus flow). When ON (transitional), the arbiter must (a) pass recusal, (b) be **assigned** (hold an `arbitration_votes` row, mirroring the DB guard), and (c) pass the tightened eligibility check.

### File 1 — `mcp_server/api/routers/disputes.py`

#### 1a. New env flag + admin import (top of file, after existing imports ~line 37)

```python
import os  # add near the top imports

from ..admin import verify_admin_key  # reuse the existing constant-time admin gate
```

Add a module-level helper (near `OPEN_STATUSES`, ~line 159):

```python
# FIX-P1-08: Unilateral human-arbiter dispute resolution is OFF by default.
# When false, only an admin (X-Admin-Key) or the future assigned-arbiter
# consensus flow may resolve a dispute. A single eligible executor can NOT.
def _arbiter_unilateral_resolution_enabled() -> bool:
    return (
        os.environ.get("EM_ARBITER_UNILATERAL_RESOLUTION", "false")
        .strip()
        .lower()
        == "true"
    )
```

#### 1b. Recusal helper (add near `_check_human_arbiter_eligibility`, ~line 264)

```python
def _is_party_to_dispute(
    dispute: Dict[str, Any],
    caller_wallet: str,
    caller_executor_id: Optional[str],
) -> bool:
    """True if the caller is the publisher (agent_id) OR the executor of THIS dispute.

    A party must never resolve their own dispute (recusal). Wallet comparison is
    lowercased; executor comparison is by id (the executor row resolved from the
    caller's wallet vs. dispute.executor_id).
    """
    dispute_agent_id = (dispute.get("agent_id") or "").lower()
    if caller_wallet and dispute_agent_id and caller_wallet == dispute_agent_id:
        return True
    dispute_executor_id = dispute.get("executor_id")
    if (
        caller_executor_id
        and dispute_executor_id
        and str(caller_executor_id) == str(dispute_executor_id)
    ):
        return True
    return False
```

#### 1c. Tighten `_check_human_arbiter_eligibility` to exclude parties (lines 228-263)

Add the dispute parties as parameters and reject a resolver who is a party (defense in depth — the recusal check below is primary, but the eligibility helper should never green-light a party):

```python
async def _check_human_arbiter_eligibility(
    executor_id: str,
    category: str,
    dispute: Optional[Dict[str, Any]] = None,
) -> bool:
    ...
    # FIX-P1-08: an arbiter must not be a party to the dispute.
    if dispute is not None:
        dispute_executor_id = dispute.get("executor_id")
        if dispute_executor_id and str(dispute_executor_id) == str(executor_id):
            return False
    ...
    # Category specialty: now MANDATORY when a category is provided (verifier note).
    if category and category != "general" and category not in specialties:
        return False
    return True
```

> Backward-compat note: making category specialty mandatory narrows who can arbitrate. Because the whole unilateral path is now **flag-gated OFF by default**, this stricter rule only takes effect when an operator explicitly enables `EM_ARBITER_UNILATERAL_RESOLUTION=true`, so it cannot lock out anyone on the default config.

#### 1d. Rewrite the authorization block in `resolve_dispute` (replace lines 710-760)

Add an optional admin dependency to the signature (line 654) so the endpoint can detect an admin caller without making it mandatory:

```python
@router.post("/{dispute_id}/resolve", response_model=ResolveDisputeResponse)
async def resolve_dispute(
    dispute_id: str,
    body: ResolveDisputeRequest,
    request: Request,
    auth: AgentAuth = Depends(verify_agent_auth_write),
) -> ResolveDisputeResponse:
```

Detect admin from the raw header (so a missing/invalid admin key does NOT 503 the whole endpoint — admin is optional here):

```python
        # FIX-P1-08: optional admin path. A valid X-Admin-Key bypasses the
        # eligibility/assignment requirement but is still subject to recusal
        # (the admin key is not a dispute party, so it passes recusal naturally).
        is_admin = False
        provided_admin = request.headers.get("X-Admin-Key") or ""
        expected_admin = os.environ.get("EM_ADMIN_KEY", "").strip()
        if provided_admin and expected_admin:
            import secrets as _secrets
            is_admin = _secrets.compare_digest(
                provided_admin.strip().encode(), expected_admin.encode()
            )
```

Then replace the authorization branch (currently lines 710-760) with:

```python
        # 3. Authorization (FIX-P1-08): recusal + neutral-resolver enforcement.
        caller_wallet = (auth.wallet_address or "").lower()
        caller_agent_id = (auth.agent_id or "").lower()

        # Resolve the caller's executor_id (if any) up front for recusal + eligibility.
        caller_executor_id: Optional[str] = None
        exec_query = (
            client.table("executors")
            .select("id")
            .eq("wallet_address", caller_wallet)
            .limit(1)
            .execute()
        )
        if exec_query.data:
            caller_executor_id = exec_query.data[0]["id"]

        # 3a. RECUSAL — a party to the dispute may NEVER resolve it (always on).
        #     Admins are exempt only insofar as they are not a party; the admin
        #     key holder is the platform operator, not the agent/executor.
        if not is_admin and _is_party_to_dispute(
            dispute, caller_wallet, caller_executor_id
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Recusal: a party to the dispute (publisher or executor) "
                    "cannot resolve it. Resolution requires a neutral arbiter or admin."
                ),
            )

        # 3b. Admin short-circuit — neutral operator path (mirrors migration-004
        #     'Manually resolve dispute (admin)').
        if not is_admin:
            # 3c. Non-admin: unilateral human-arbiter resolution is flag-gated OFF.
            if not _arbiter_unilateral_resolution_enabled():
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Dispute resolution requires admin authority "
                        "(X-Admin-Key) or assigned-arbiter consensus. "
                        "Unilateral arbiter resolution is disabled."
                    ),
                )

            # 3d. Flag ON (transitional): caller must be a registered executor,
            #     ASSIGNED to this dispute, and pass tightened eligibility.
            if not caller_executor_id:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized: not a registered executor",
                )

            # Assignment guard — mirror the DB rule (arbitration_votes row must
            # exist for this dispute + this arbiter). Resolve arbitrator_id from
            # the executor's wallet.
            arb_query = (
                client.table("arbitrators")
                .select("id")
                .eq("wallet_address", caller_wallet)
                .limit(1)
                .execute()
            )
            arbitrator_id = arb_query.data[0]["id"] if arb_query.data else None
            assigned = False
            if arbitrator_id:
                vote_query = (
                    client.table("arbitration_votes")
                    .select("id")
                    .eq("dispute_id", dispute_id)
                    .eq("arbitrator_id", arbitrator_id)
                    .limit(1)
                    .execute()
                )
                assigned = bool(vote_query.data)
            if not assigned:
                raise HTTPException(
                    status_code=403,
                    detail="Not assigned to this dispute",
                )

            # Tightened eligibility (excludes parties, category-matched).
            task_query = (
                client.table("tasks")
                .select("category")
                .eq("id", dispute.get("task_id"))
                .limit(1)
                .execute()
            )
            category = (
                task_query.data[0].get("category", "general")
                if task_query.data
                else "general"
            )
            eligible = await _check_human_arbiter_eligibility(
                caller_executor_id, category, dispute=dispute
            )
            if not eligible:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Not eligible: arbiter must be unrelated to the task, "
                        "category-matched, reputation>=80, 10+ completed tasks"
                    ),
                )

        # 4. Submission/dispute state precondition before any payout (FIX-P1-08).
        #    Do NOT re-implement escrow checks (handled in _settle_submission_payment,
        #    ESCROW-004). Just ensure the dispute is actually in an open state and
        #    the linked submission is not already terminal.
        if body.verdict == "release" and dispute.get("submission_id"):
            sub_state = (
                client.table("submissions")
                .select("status")
                .eq("id", dispute["submission_id"])
                .limit(1)
                .execute()
            )
            if sub_state.data:
                ss = (sub_state.data[0].get("status") or "").lower()
                if ss in {"paid", "released", "completed", "rated", "refunded"}:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Submission already {ss}; cannot release",
                    )
```

> The existing `OPEN_STATUSES` / `already_resolved` guard at lines 698-708 already blocks resolving a terminal dispute; keep it.

> Note on the previous "task owner" branch: it is **removed**. The publisher (task owner) is now caught by recusal (3a) — they are a party (`agent_id`) and cannot self-resolve. If product wants to keep the harmless "concede against oneself" case (publisher choosing `release`, worker choosing `refund`), that is a deliberate future relaxation; ship the strict version first.

### File 2 — DB migration (defense in depth, audit trail)

The Python path is the live barrier, but add a migration to (a) record the new `resolved_by` semantics and (b) provide an idempotent production guard documenting the admin/recusal expectation. Next free sequential number is **111**.

Create `supabase/migrations/111_dispute_resolution_recusal_guard.sql`:

```sql
-- ============================================================================
-- Migration: 111_dispute_resolution_recusal_guard.sql
-- FIX-P1-08: Defense-in-depth guard for dispute resolution recusal.
-- The REST resolve path enforces recusal in Python (service-role bypasses RLS),
-- so this migration adds an audit-friendly DB function that rejects a
-- party-as-resolver, callable from any future non-service path, plus a
-- comment documenting the control.
-- ============================================================================

-- Trigger-enforced recusal: a dispute may not be marked resolved with
-- resolved_by equal to either party (publisher agent_id or the executor's wallet).
CREATE OR REPLACE FUNCTION enforce_dispute_resolver_recusal()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_executor_wallet TEXT;
BEGIN
    -- Only check on transition INTO a resolved state with a resolver set.
    IF NEW.status IN (
        'resolved_for_agent', 'resolved_for_executor', 'settled'
    ) AND NEW.resolved_by IS NOT NULL
      AND COALESCE(OLD.status, '') NOT IN (
        'resolved_for_agent', 'resolved_for_executor', 'settled', 'closed'
    ) THEN
        -- Publisher (agent_id) may not be the resolver.
        IF lower(NEW.resolved_by) = lower(COALESCE(NEW.agent_id, '')) THEN
            RAISE EXCEPTION
                'Recusal: dispute publisher (%) cannot resolve their own dispute',
                NEW.agent_id;
        END IF;
        -- Executor wallet may not be the resolver.
        IF NEW.executor_id IS NOT NULL THEN
            SELECT lower(wallet_address) INTO v_executor_wallet
            FROM executors WHERE id = NEW.executor_id;
            IF v_executor_wallet IS NOT NULL
               AND lower(NEW.resolved_by) = v_executor_wallet THEN
                RAISE EXCEPTION
                    'Recusal: dispute executor cannot resolve their own dispute';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_dispute_resolver_recusal ON disputes;
CREATE TRIGGER trg_dispute_resolver_recusal
    BEFORE UPDATE ON disputes
    FOR EACH ROW
    EXECUTE FUNCTION enforce_dispute_resolver_recusal();

COMMENT ON FUNCTION enforce_dispute_resolver_recusal() IS
    'FIX-P1-08: rejects a dispute resolution where resolved_by is a party '
    '(publisher agent_id or executor wallet). Recusal enforcement.';
```

**Standalone idempotent production hotfix** (paste into Supabase SQL editor — same content, fully re-runnable):

```sql
-- FIX-P1-08 production hotfix: dispute resolver recusal trigger (idempotent).
CREATE OR REPLACE FUNCTION enforce_dispute_resolver_recusal()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE v_executor_wallet TEXT;
BEGIN
    IF NEW.status IN ('resolved_for_agent','resolved_for_executor','settled')
       AND NEW.resolved_by IS NOT NULL
       AND COALESCE(OLD.status,'') NOT IN
           ('resolved_for_agent','resolved_for_executor','settled','closed') THEN
        IF lower(NEW.resolved_by) = lower(COALESCE(NEW.agent_id,'')) THEN
            RAISE EXCEPTION 'Recusal: publisher (%) cannot resolve own dispute', NEW.agent_id;
        END IF;
        IF NEW.executor_id IS NOT NULL THEN
            SELECT lower(wallet_address) INTO v_executor_wallet
            FROM executors WHERE id = NEW.executor_id;
            IF v_executor_wallet IS NOT NULL
               AND lower(NEW.resolved_by) = v_executor_wallet THEN
                RAISE EXCEPTION 'Recusal: executor cannot resolve own dispute';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS trg_dispute_resolver_recusal ON disputes;
CREATE TRIGGER trg_dispute_resolver_recusal
    BEFORE UPDATE ON disputes FOR EACH ROW
    EXECUTE FUNCTION enforce_dispute_resolver_recusal();
```

> Backward-compat risk of the trigger: legitimate "concede against oneself" updates (if ever added) and any admin resolution where the operator passes `resolved_by = <a party wallet>` would be blocked. The Python path sets `resolved_by` to `caller_wallet or caller_agent_id` (the resolver's own identity), and after this fix a party can never reach the update, so the trigger never fires on legitimate flows. For admin resolutions, `resolved_by` should be the admin actor (set `resolved_by` to the admin actor id, not a party wallet) — see the executor note in the test plan.

### Feature flag / env var

| Name | Default (safe) | Effect |
|------|----------------|--------|
| `EM_ARBITER_UNILATERAL_RESOLUTION` | `false` | When `false`, only admin (`X-Admin-Key`) or assigned-arbiter consensus may resolve; a single eligible arbiter is rejected. Set `true` only after the assignment/consensus flow is wired. |

`EM_ADMIN_KEY` already exists in the ECS task definition (used by `admin.py`); no new secret needed. **ECS task-def update**: add `EM_ARBITER_UNILATERAL_RESOLUTION=false` to the MCP service env (or omit — the code defaults to `false`). No new secret.

### Backward-compatibility & safe rollout

- **Does this lock out legitimate resolvers?** On default config it makes `/resolve` admin-only. Today there is **no UI flow** that has non-admin executors resolving disputes through a vetted assignment process, so the default-OFF flag is the correct fail-closed posture. The admin dashboard (which already sends `X-Admin-Key`) continues to work.
- **Staged rollout**: (1) Deploy code + migration with `EM_ARBITER_UNILATERAL_RESOLUTION` unset (→ admin-only + recusal). (2) Verify admin dashboard resolution still works and self-resolution is rejected. (3) Only later, when the assigned-arbiter consensus path is built, flip the flag in a canary.
- **No data migration of existing disputes** required; the trigger only fires on future resolving updates.

## Test plan

### Unit/integration tests to add

Add to `mcp_server/tests/test_security_phase1_api_hardening.py` in a new `class TestDisputeRecusal` (marker `security`), following the existing direct-invocation + mocked `supabase_client.get_client` pattern. Build the dispute mock so `select(...).eq("id", dispute_id).limit(1).execute().data` returns one open dispute with known `executor_id`/`agent_id`, and the `executors` lookup returns the caller's executor id.

1. **`test_executor_party_release_rejected`** (reproduces the bug) — caller wallet maps to an executor whose id == `dispute["executor_id"]`; `verdict='release'`; expect `HTTPException` **403** with `"Recusal"` in detail. (Before the fix this would pass auth and trigger payment.)
2. **`test_publisher_party_refund_rejected`** — caller wallet == `dispute["agent_id"]`; `verdict='refund'`; expect **403** `"Recusal"`. (Replaces the old self-judge path.)
3. **`test_non_admin_unilateral_disabled`** — neutral eligible executor (not a party), flag unset (`EM_ARBITER_UNILATERAL_RESOLUTION` absent); expect **403** `"requires admin authority"`.
4. **`test_unassigned_arbiter_rejected_when_flag_on`** — set `EM_ARBITER_UNILATERAL_RESOLUTION=true` (monkeypatch env), neutral eligible executor with **no** `arbitration_votes` row; expect **403** `"Not assigned to this dispute"`.
5. **`test_admin_resolution_allowed`** — pass a `Request` whose `headers` contains a valid `X-Admin-Key` (monkeypatch `EM_ADMIN_KEY`); neutral verdict; mock `_trigger_resolution_payment` to a no-op; expect **200** and that the dispute update was attempted. Use `resolved_by` = admin actor.
6. **`test_settle_payment_not_called_on_recusal`** — patch `api.routers.disputes._trigger_resolution_payment` with an `AsyncMock`; run test 1; assert the mock was **never awaited** (proves no funds move on a recused caller).

Because `resolve_dispute` now takes a `request` parameter, update the **existing** `TestDisputeResolveHardened` tests (lines 110-155) to pass a `MagicMock()` (or a minimal object with `.headers = {}`) as `request=`. The three existing assertions (API-003: reject api_key, reject missing wallet, ERC-8128 → 404) must still pass.

DB-trigger test (optional, requires a live/branch Supabase): update a `disputes` row to `resolved_for_executor` with `resolved_by` = the executor's wallet → expect a `RAISE EXCEPTION` / error; with `resolved_by` = a neutral admin id → succeeds.

### Manual / E2E verification

1. As an established worker who is the executor on an open dispute, sign ERC-8128 and `POST /api/v1/disputes/{id}/resolve {"verdict":"release","reason":"x"}` → expect **403** "Recusal". Confirm no `dispute.resolved` event and no payout in `payment_events`.
2. As a neutral eligible executor (not a party), same call with default flag → **403** "requires admin authority".
3. As admin (`X-Admin-Key`) → **200**, dispute resolves, payout dispatched. Confirm `disputes.resolved_by` is the admin actor (not a party wallet) so the recusal trigger does not fire.
4. Confirm the existing admin dashboard "resolve dispute" button still works end-to-end.

## Rollback plan

- **Code**: revert the commit touching `disputes.py` (`resolve_dispute`, the two new helpers, the import). The endpoint reverts to prior behavior. Low risk because the change is contained to one router.
- **Migration**: `DROP TRIGGER IF EXISTS trg_dispute_resolver_recusal ON disputes; DROP FUNCTION IF EXISTS enforce_dispute_resolver_recusal();`
- **Flag**: removing `EM_ARBITER_UNILATERAL_RESOLUTION` from ECS keeps the safe default; setting it `true` re-enables the (now hardened, assignment-gated) arbiter path.
- Rollback restores the vulnerability, so only roll back if the fix breaks the admin resolution path; prefer a forward-fix.

## Verification checklist

- [ ] Confirmed `resolve_dispute` rejects (403, "Recusal") a caller whose executor_id == `dispute.executor_id` on `verdict='release'`.
- [ ] Confirmed `resolve_dispute` rejects (403, "Recusal") a caller whose wallet == `dispute.agent_id` on `verdict='refund'`.
- [ ] Confirmed a neutral eligible executor is rejected (403) when `EM_ARBITER_UNILATERAL_RESOLUTION` is unset/false.
- [ ] Confirmed an unassigned eligible arbiter is rejected (403, "Not assigned") when the flag is true.
- [ ] Confirmed an admin (`X-Admin-Key`) resolution returns 200 and dispatches payment.
- [ ] Confirmed `_trigger_resolution_payment` is NOT invoked on any recused/unauthorized caller.
- [ ] Existing `TestDisputeResolveHardened` (API-003) tests updated for the new `request` param and still pass.
- [ ] Migration `111_dispute_resolution_recusal_guard.sql` applies cleanly; idempotent hotfix re-runs without error.
- [ ] DB recusal trigger raises on a party-as-`resolved_by` update and allows a neutral resolver.
- [ ] `EM_ARBITER_UNILATERAL_RESOLUTION=false` present (or absent) in the deployed ECS task definition.
- [ ] Admin dashboard "resolve dispute" flow verified end-to-end against the deployed build.
- [ ] `pytest -m security` green; no regressions in `pytest -m arbiter`.
