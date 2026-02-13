# Refactoring Plan: Eliminate "Fase" Naming Convention

## Problem

Method names like `_release_fase2()`, `deployFase3Clean()`, `_authorize_x402r()` are **internal development phase labels** that leaked into production code. They describe *when* something was built, not *what* it does. This violates basic naming principles — a developer reading `_release_fase2()` has zero idea what it does without reading the implementation.

## Guiding Principle

**Names describe behavior, not history.**

- `_release_fase2()` → what does it actually do? Releases funds from on-chain escrow. → `_release_from_escrow()`
- `_authorize_fase1()` → what does it actually do? Checks agent balance. → `_authorize_balance_check()`
- `deployFase4()` → what does it actually do? Deploys operator with secure refund. → `deploySecureRefundOperator()`

---

## Part 1: Payment Modes (EM_PAYMENT_MODE env var)

The env var values are the root of the naming disease. Fix these first, everything else follows.

| Current Value | New Value | What It Actually Does |
|---------------|-----------|----------------------|
| `fase1` | `direct` | Direct EIP-3009 settlement at approval. No escrow. |
| `fase2` | `escrow` | On-chain escrow lock at creation, gasless release at approval. |
| `preauth` | `preauth` | OK — descriptive enough (EIP-3009 pre-authorization). Keep. |
| `x402r` | *(remove)* | Deprecated. Delete all code paths. |

**Migration**: Accept both old and new values during transition:
```python
# payment_dispatcher.py
mode = os.getenv("EM_PAYMENT_MODE", "escrow")
# Backward compat (remove after all ECS task defs updated)
MODE_ALIASES = {"fase1": "direct", "fase2": "escrow"}
mode = MODE_ALIASES.get(mode, mode)
```

**Files to update:**
- `mcp_server/integrations/x402/payment_dispatcher.py` (mode parsing)
- `mcp_server/api/routes.py` (mode checks: `is_fase1`, `is_fase2`, `is_x402r`)
- `infrastructure/terraform/ecs.tf` (env var value)
- `CLAUDE.md` (documentation)
- `.claude/skills/e2e-full-lifecycle/SKILL.md`

---

## Part 2: PaymentDispatcher Methods

### Authorization Methods

| Current Name | New Name | Reason |
|-------------|----------|--------|
| `_authorize_fase1()` | `_authorize_balance_check()` | Only checks balance, no funds move |
| `_authorize_fase2()` | `_authorize_escrow_lock()` | Locks funds in on-chain escrow |
| `_authorize_x402r()` | *(delete)* | Deprecated mode. Remove entirely. |
| `_authorize_preauth()` | `_authorize_signed_header()` | Validates EIP-3009 signed header |

### Release Methods

| Current Name | New Name | Reason |
|-------------|----------|--------|
| `_release_fase1()` | `_release_direct_settlement()` | Signs fresh EIP-3009 auths, settles directly |
| `_release_fase2()` | `_release_from_escrow()` | Releases escrow, then disburses to worker |
| `_release_x402r()` | *(delete)* | Deprecated. Merge any unique logic into `_release_from_escrow()` if needed. |
| `_release_preauth()` | `_release_preauth_settlement()` | Settles stored pre-auth header |

### Refund Methods

| Current Name | New Name | Reason |
|-------------|----------|--------|
| `_refund_fase1()` | `_refund_noop()` | No-op — no auth was signed, nothing to refund |
| `_refund_fase2()` | `_refund_from_escrow()` | Refunds escrowed funds via facilitator |
| `_refund_x402r()` | *(delete)* | Deprecated mode |
| `_refund_preauth()` | `_refund_expired_auth()` | Auth expires naturally, just marks DB |

### Helper Methods

| Current Name | New Name | Reason |
|-------------|----------|--------|
| `_get_fase2_client()` | `_get_escrow_client()` | Returns AdvancedEscrowClient instance |

### Routing Logic

The `authorize_payment()`, `release_payment()`, `refund_payment()` router methods use if/elif chains matching mode strings. Update to match new mode values:

```python
# Before:
if self._mode in ("x402r", "fase2"):
    return await self._authorize_fase2(...)
elif self._mode == "fase1":
    return await self._authorize_fase1(...)

# After:
if self._mode == "escrow":
    return await self._authorize_escrow_lock(...)
elif self._mode == "direct":
    return await self._authorize_balance_check(...)
```

---

## Part 3: Deploy Script (`scripts/deploy-payment-operator.ts`)

### CLI Flags

| Current Flag | New Flag | What It Deploys |
|-------------|----------|-----------------|
| `--fase3` | *(remove)* | Legacy. 1% on-chain fee. No longer needed. |
| `--fase3-clean` | *(remove)* | Legacy. 0% fee but vulnerable refund. |
| `--fase4` | `--secure` | Facilitator-only refund. Current target. |
| *(default)* | `--standard` | Basic operator (original, no special conditions) |

### Functions

| Current Name | New Name | Reason |
|-------------|----------|--------|
| `deployFase3()` | *(delete)* | Legacy deployment, keep in git history |
| `deployFase3Clean()` | *(delete)* | Legacy, vulnerable to payer refund attack |
| `deployFase4()` | `deploySecureOperator()` | Deploys with Facilitator-only refund |

### Simplification

After removing legacy functions, the deploy script becomes much simpler — one deployment mode (`--secure`) with clear configuration:

```typescript
async function deploySecureOperator(wallet, publicClient) {
  // releaseCondition: OR(Payer | Facilitator) — either can release
  // refundCondition: Facilitator-only — prevents payer frontrunning
  // feeCalculator: address(0) — no on-chain operator fee
}
```

---

## Part 4: API Routes (`mcp_server/api/routes.py`)

### Variables in Route Handlers

| Current Name | New Name |
|-------------|----------|
| `is_x402r` | *(delete)* |
| `is_fase1` | `is_direct_mode` |
| `is_fase2` | `is_escrow_mode` |
| `is_fase1_mode` | `is_direct_mode` |
| `is_fase2_mode` | `is_escrow_mode` |

### Mode Checks

```python
# Before:
if dispatcher.get_mode() == "fase2":
    # escrow lock
elif dispatcher.get_mode() == "x402r":
    # settle + lock (deprecated)
elif dispatcher.get_mode() == "fase1":
    # balance check

# After:
if dispatcher.get_mode() == "escrow":
    # escrow lock
elif dispatcher.get_mode() == "direct":
    # balance check
```

---

## Part 5: Test Files

### Test Methods in `test_payment_dispatcher.py`

Rename tests to match new method names. Pattern: `test_<method>_<scenario>`.

| Current Test Name | New Test Name |
|------------------|---------------|
| `test_authorize_x402r_*` | *(delete with mode)* |
| `test_authorize_fase1_*` | `test_authorize_balance_check_*` |
| `test_authorize_fase2_*` | `test_authorize_escrow_lock_*` |
| `test_release_x402r_*` | *(delete with mode)* |
| `test_release_fase1_*` | `test_release_direct_settlement_*` |
| `test_release_fase2_*` | `test_release_from_escrow_*` |
| `test_refund_x402r_*` | *(delete with mode)* |
| `test_refund_fase1_*` | `test_refund_noop_*` |
| `test_refund_fase2_*` | `test_refund_from_escrow_*` |
| `test_mode_selection_*` | Update mode strings to `direct`/`escrow` |

### E2E Test Scripts in `scripts/`

| Current File | Action |
|-------------|--------|
| `test-fase2-escrow.py` | Rename to `test-escrow-e2e.py` or archive |
| `test-fase3-escrow.py` | Archive to `_archive/scripts/` |
| `test-fase3-clean-escrow.py` | Archive to `_archive/scripts/` |

---

## Part 6: Documentation Updates

| File | Changes |
|------|---------|
| `CLAUDE.md` | Replace all `fase1`/`fase2` references with `direct`/`escrow` |
| `docs/planning/PAYMENT_ARCHITECTURE.md` | Update mode names |
| `docs/planning/X402R_REFERENCE.md` | Remove x402r mode references (keep protocol docs) |
| Memory files | Update `payment-architecture.md` |
| `FASE1_E2E_EVIDENCE_*.md` | Keep as historical evidence (file names = timestamps) |
| `FASE2_E2E_EVIDENCE_*.md` | Keep as historical evidence |

---

## Part 7: Delete Dead Code (x402r mode)

The `x402r` payment mode is deprecated. Remove all code paths:

1. `_authorize_x402r()` — ~130 lines
2. `_release_x402r()` — ~130 lines
3. `_refund_x402r()` — ~115 lines
4. All `if self._mode == "x402r"` branches in routers
5. Related test cases in `test_payment_dispatcher.py`
6. `test_a2a.py` serialization tests (99 tests, already marked `redundant`)

**Estimated code reduction**: ~375 lines of dead code removed from payment_dispatcher.py alone.

---

## Execution Order

### Step 1: Mode Values (smallest blast radius, backward compat)
1. Add `MODE_ALIASES` dict for backward compat
2. Change internal references to `"direct"` / `"escrow"`
3. Update ECS task def: `EM_PAYMENT_MODE=escrow`
4. Run full test suite
5. Remove `MODE_ALIASES` after confirming ECS deploys

### Step 2: Method Renames (mechanical, safe with find-replace)
1. Rename all `_*_fase1` → `_*_balance_check` / `_*_direct_settlement` / `_*_noop`
2. Rename all `_*_fase2` → `_*_escrow_lock` / `_*_from_escrow`
3. Rename `_get_fase2_client` → `_get_escrow_client`
4. Update all call sites and tests
5. Run full test suite

### Step 3: Delete x402r Mode (remove dead code)
1. Delete `_authorize_x402r`, `_release_x402r`, `_refund_x402r`
2. Remove x402r routing branches
3. Delete/archive x402r-specific tests
4. Run full test suite

### Step 4: Deploy Script Cleanup
1. Remove `deployFase3()` and `deployFase3Clean()`
2. Rename `deployFase4()` → `deploySecureOperator()`
3. Rename `--fase4` → `--secure`
4. Simplify CLI arg parsing

### Step 5: Documentation Sweep
1. Update CLAUDE.md
2. Update all docs/ references
3. Update memory files
4. Archive old E2E test scripts

---

## Validation Checklist

After each step:
- [ ] `cd mcp_server && ruff format . && ruff check .`
- [ ] `cd mcp_server && set TESTING=true && pytest -m payments -x`
- [ ] `cd mcp_server && set TESTING=true && pytest` (full suite)
- [ ] `cd dashboard && npx tsc --noEmit && npm run lint`
- [ ] `cd mcp_server && mypy models.py api/admin.py api/reputation.py --ignore-missing-imports --follow-imports=skip`

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| ECS uses old mode value | `MODE_ALIASES` backward compat dict |
| Tests break on rename | Mechanical rename, run suite after each file |
| x402r code still needed | Git history preserves everything. Mark removed date. |
| Deploy script breaks | Old flags kept as aliases during transition |
| Third-party references to mode values | Only internal — no external API exposes mode strings |

**Estimated effort**: 2-3 hours for a thorough rename + test validation.
**Lines affected**: ~800+ across 15 files.
**Risk level**: Low — all renames are internal, no external API changes.
