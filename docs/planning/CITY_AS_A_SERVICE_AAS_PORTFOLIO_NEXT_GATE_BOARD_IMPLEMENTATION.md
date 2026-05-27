# City as a Service — AAS Portfolio Next-Gate Board Implementation

> Date: 2026-05-27 01:00 America/New_York
> Status: implemented and verified
> Scope: Execution Market AAS / City-as-a-Service internal-admin proof seam only

## What landed

`mcp_server/city_ops/aas_portfolio_next_gate_board.py` adds the read-only continuation after the portfolio promotion ledger.

The board consumes only:

- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_portfolio_promotion_ledger.json`

and persists:

- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_portfolio_next_gate_board.json`

Safe claim earned:

- `admin_aas_portfolio_next_gate_board_landed`

## Why this exists

The midnight ledger made five AAS family boundaries comparable, but it intentionally did not choose or approve a promotion path. The new board turns that ledger into an operator decision menu while keeping the approval boundary explicit:

1. **Retail Reality as a Service** — rank 1, because a selected boundary is already pending human review.
2. **Compliance Desk as a Service** — rank 2, because an internal label boundary is approved but no delivery path exists.
3. **Document / Handoff Logistics as a Service** — internal prerequisite only.
4. **Incident Verification as a Service** — internal prerequisite only.
5. **Local Data Collection as a Service** — internal prerequisite only.

Default decision if no separate authorization exists:

> do not promote any family; keep the portfolio ledger read-only.

## Guardrails preserved

The board is not a human approval record and does not approve any selected boundary.

It keeps all of these false/blocked:

- customer copy
- customer delivery
- publication
- public/catalog routes
- public prices or customer quotes
- queue launch or dispatch
- ERC-8004 reputation attachment
- live Acontext/runtime parity
- payment/production reverification
- exact GPS/raw metadata release
- private operator context release
- legal/regulator/emergency/safety/repair/insurance authority claims
- dataset or analytics publication
- worker Skill DNA / worker-copyable doctrine

## Tests

Focused verification:

```bash
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_portfolio_next_gate_board.py
# 10 passed

.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1366 passed
```

The tests cover:

- persisted artifact parity and loader parity
- ranked next-gate order
- blocked customer/public/dispatch/runtime/reputation/GPS/worker-doctrine claims
- write/load contract
- fail-closed source ledger summary promotion
- fail-closed source row promotion
- fail-closed source forbidden safe claim
- fail-closed board summary and row promotion

## Next safe slice

If human review is available, create exactly one separate approval artifact for either:

1. Retail Reality selected-boundary approval record, or
2. Compliance Desk delivery/publication gate with an exact delivery path.

If human review is not available, stay internal/admin-only: either improve the next-gate read surface, add proof parity around the board, or keep Acontext repair isolated without inferring customer readiness.
