# City as a Service — Decision Support Matrix Card Implementation

> Status: 04:00 dream implementation note  
> Scope: Execution Market AAS / City-as-a-Service only  
> Related source: `CITY_AS_A_SERVICE_MORNING_BRIEF_2026_05_09.md`

## What landed

The 03:00 handoff said the next smallest safe step was to render the decision-support readiness matrix as an internal/admin-only four-axis card, preserving safe/blocked claim adjacency and refusing readiness promotion until live Acontext write/retrieve parity exists.

That step now exists.

Code changes:

- `mcp_server/city_ops/decision_support_matrix_card.py`
  - adds `build_decision_support_matrix_card()`
  - adds `write_decision_support_matrix_card_fixture()`
  - adds `load_decision_support_matrix_card()`
  - consumes only `decision_support_readiness_matrix.json`
  - renders the four matrix axes as pass-through cards without semantic reinterpretation
  - keeps `safe_to_claim[]` and `do_not_claim_yet[]` as adjacent claim cards
  - rejects promoted matrix readiness, public route drift, access-policy drift, interpretation drift, raw transcript replay, live-sink writes, and blocked-safe-claim drift
- `mcp_server/city_ops/__init__.py`
  - exports the matrix-card builder/writer/loader
- `mcp_server/tests/city_ops/test_decision_support_matrix_card.py`
  - verifies matrix-only consumption
  - verifies four-axis pass-through rendering
  - verifies persisted fixture parity
  - verifies adjacent safe/blocked claim cards
  - verifies external/product claims remain blocked
  - verifies live transport may become attemptable without becoming ready
  - verifies readiness, interpretation, and access drift rejections
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_matrix_card.json`
  - persisted deterministic card payload

## Render contract

The card is deliberately not a real route yet. It is an internal/admin-only data contract that can later be mounted behind an authenticated boundary.

Suggested internal path:

```text
/internal/admin/city-ops/decision-support-matrix
```

The route is **not** registered by this slice. The payload declares:

- `network_route_registered=false`
- `audience=internal_admin_only`
- `requires_admin_context=true`
- `allowed_interpretation=pass_through_matrix_fields_only`
- no customer visibility
- no worker visibility
- no dispatch enablement
- no live Acontext writes
- no municipal memory writes
- no reputation receipts
- no GPS/metadata exposure
- no worker doctrine publication

## Four-axis card output

The card preserves the existing decision-support axes from the matrix:

1. `memory_system_to_acontext_bridge`
   - blocked or attemptable-not-ready
   - never sink-ready until one live write/retrieve parity pass exists
2. `irc_session_management`
   - compact ID handoff active
   - useful for handoff by invariant IDs rather than raw chat replay
3. `cross_project_decision_support`
   - bounded verdict reusable for operator-only EM AAS planning
   - blocked from broad doctrine until another reviewed municipal case confirms repeatability
4. `agent_observability_success_metrics`
   - proof-block metrics landed
   - useful for checking whether future agents preserve claim boundaries and IDs

The card adds display status only as a UI hint:

- `ready_for_operator_planning` when the source axis is already `ready_now=true`
- `blocked_or_attemptable_not_ready` when the source axis is `ready_now=false`

It does not alter source axis state, readiness, evidence, safe use, or blocker text.

## Safe to claim

- `decision_support_matrix_card_landed`
- the decision-support readiness matrix now has a persisted internal/admin-only four-axis card payload
- the card consumes only `decision_support_readiness_matrix.json`
- matrix fields are rendered as pass-through cards without reinterpretation
- safe and blocked claims remain visible together
- live Acontext can be displayed as attemptable, but not as ready

## Still blocked / not safe to claim

- public route readiness
- customer-visible catalog readiness
- customer copy readiness
- polished operator console readiness
- operator UI readiness beyond a generated internal/admin payload contract
- dispatch routing readiness
- dispatch automation readiness
- live Acontext readiness
- Acontext sink readiness
- runtime parity
- ERC-8004 reputation readiness
- worker Skill DNA readiness
- legal sufficiency or regulator acceptance
- exact GPS/metadata exposure
- worker-copyable municipal doctrine

## Why this matters for the AAS strategy

The useful pattern is no longer just “generate a proof artifact.” The pattern is now:

```text
reviewed proof artifact
-> read-only intelligence matrix
-> internal/admin card
-> authenticated route later
```

That is the scaling shape for Execution Market AAS packages: agents can coordinate across memory, IRC-style handoffs, metrics, and Acontext readiness without reopening raw transcripts or overstating readiness. The UI surface becomes a conservative carrier for reviewed truth, not a place where claims get rewritten.

This is the same operating principle CaaS needs before adjacent AAS concepts are promoted: operator-visible before customer-visible; proof-preserving before automation; blocked claims beside safe claims; live transport only after parity.

## Verification

Passed:

```bash
python3 -m py_compile mcp_server/city_ops/decision_support_matrix_card.py mcp_server/tests/city_ops/test_decision_support_matrix_card.py
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops/test_decision_support_matrix_card.py -q
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Result: focused gate `9 passed, 1 existing pytest config warning`; full city-ops gate `186 passed, 1 existing pytest config warning`.

## Next smallest safe step

Either:

1. mount the persisted card behind a real authenticated internal/admin route once an admin auth boundary exists, returning the payload as-is; or
2. if route/auth remains blocked, add a tiny route-readiness preflight that fails closed unless admin auth, matrix-card parity, and no-interpretation response rules are all present.

Do not add customer copy, public catalog, dispatch routing, live Acontext writes, ERC-8004 reputation updates, worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or worker-copyable doctrine in the next slice.
