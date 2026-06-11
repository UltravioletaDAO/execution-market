# City-as-a-Service — 2 AM Operator Reference Privacy Guard (2026-06-11)

> Scope: Execution Market AAS / City-as-a-Service internal/admin answer-receipt validation only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Safe claim: `internal_admin_aas_2am_operator_reference_privacy_guard_2026_06_11_landed`.
> Status: validator hardening only; no operator answer, approval, answer receipt, customer/public/worker copy, catalog, pricing, quote, route, queue, dispatch, runtime mutation, Acontext write/retrieve, IRC/session-manager mutation, reputation/Worker Skill DNA, payment/production reverification, exact-location/raw-metadata/private-context/PII release, authority claim, worker-copyable doctrine, or stopped-project integration.

## Priority compliance

`DREAM-PRIORITIES.md` was read first and overrides the stale 2 AM cron payload. This pass did **not** pull, inspect, analyze, edit, test, or integrate AutoJob; did **not** expand Frontier Academy; did **not** continue KK v2; and did **not** touch KarmaCadabra v2.

Allowed work performed:

- synced only `projects/execution-market` with `git pull --ff-only`;
- inspected current AAS answer-receipt gate/runbook state;
- hardened the existing answer-receipt validator so future explicit operator references cannot carry obvious private or secret material;
- updated the persisted fixture and focused tests.

Pre-existing untracked `scripts/sign_req.mjs` and `mcp_server/city_ops/tests/` were preserved and not staged.

## Why this was the right 2 AM slice

The 1 AM runbook already concluded that no explicit operator answer exists and the active posture remains:

```text
pause_aas_proof_layering
```

So this pass did not create another no-answer proof wrapper. Instead, it turned one runbook sentence into executable guardrail: a future answer receipt must use an opaque, non-secret, non-doxxing operator reference. That matters because the receipt is the next valid gateway before any AAS movement, and a raw reference could accidentally include private context, exact location, or credentials.

## Implementation

Changed files:

| File | Purpose | SHA-256 |
| --- | --- | --- |
| `mcp_server/city_ops/aas_operator_answer_receipt_gate.py` | Adds explicit operator-reference privacy validation. | `4263c2ea5449a561cc0680d4de8c1663edbc6a7b3e38ee447fcc46e187b08d7b` |
| `mcp_server/city_ops/fixtures/aas_package_ladder/aas_operator_answer_receipt_gate.json` | Regenerated policy fixture with the new privacy contract. | `17b74d97db721588211f2d1924d4cdadabfa10341be957b011104e4bd661caac` |
| `mcp_server/tests/city_ops/test_aas_operator_answer_receipt_gate.py` | Adds regression coverage for private/secret reference rejection. | `141938a6bdec1bfbdbfbfda28dee2f9643e7e5a7cec5a2ccb9be36d7ab1079f4` |

The answer-receipt validation policy now records:

```text
rejects_private_or_secret_operator_reference = true
explicit_operator_reference_max_length = 240
```

The validator rejects obvious raw forms of:

- email addresses;
- phone-number-like strings;
- decimal coordinate pairs;
- GPS/latitude/longitude labels;
- Ethereum private-key-shaped values;
- OpenAI-style secret keys;
- GitHub tokens;
- AWS access keys.

The allowed shape stays intentionally boring: an opaque reference such as an internal receipt/message/decision ID that points to the answer without embedding the answer source's private data.

## Boundaries preserved

This guard does **not** mean an answer exists. It does **not** create an answer receipt. It does **not** approve delivery, runtime, dispatch, customer copy, public copy, worker copy, pricing, reputation, payment, production, or authority claims.

It only makes the future receipt validator fail closed if the explicit operator reference itself tries to carry private data or secrets.

## Verification

Verification passed:

```text
./.venv/bin/pytest mcp_server/tests/city_ops/test_aas_operator_answer_receipt_gate.py -q
# 24 passed

git diff --check && ./.venv/bin/pytest mcp_server/tests/city_ops -q
# 2080 passed
```

## Next valid action

Still exactly one of:

1. if Saúl provides exactly one allowed AAS answer value, create one separate digest-backed answer receipt using an opaque non-secret reference and validate it through the hardened gate;
2. otherwise hold / pause and do not add product, runtime, customer, worker, dispatch, reputation, payment, private-context, exact-location, authority, worker-doctrine, or stopped-project layers.
