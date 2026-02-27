---
date: 2026-02-26
tags:
  - type/moc
  - domain/testing
status: active
aliases:
  - Testing MOC
  - Verification MOC
  - QA MOC
---

# Testing & Verification

> Test suites, E2E acceptance tests, CI pipeline, and quality assurance processes for the Execution Market platform.

---

## Definitive Acceptance Test

- [[golden-flow]] — **If it passes, the platform is healthy.**
  - Script: `scripts/e2e_golden_flow.py`
  - Full lifecycle tested end-to-end on production:
    1. Health check
    2. Task creation (balance check)
    3. Worker registration
    4. ERC-8004 identity verification
    5. Task application
    6. Assignment (escrow lock in Fase 5)
    7. Evidence submission (S3/CloudFront presigned upload)
    8. Approval + payment (direct release or platform release)
    9. Bidirectional reputation (agent rates worker, worker rates agent)
    10. On-chain verification
  - Reports: `docs/reports/GOLDEN_FLOW_REPORT.md` (EN), `docs/reports/GOLDEN_FLOW_REPORT.es.md` (ES)

---

## Multichain Testing

- [[multichain-golden-flow]] — Validates payment and escrow across all 8 supported chains
  - Script: `scripts/e2e_golden_flow_multichain.py`
  - **7/8 PASS consolidated**, **8/8 PASS individually**
  - Chains: Base, Ethereum, Polygon, Arbitrum, Avalanche, Monad, Celo, Optimism
  - Ethereum L1 times out in batch runs (>900s) but passes solo (~130s)
  - Reputation PASS bidirectional: 16 on-chain TXs verified (2026-02-21)
  - Known: intermittent TxWatcher timeouts affect any chain randomly (Facilitator TX propagation, not a code bug)
  - Reports: `docs/reports/PAYMENT_FLOW_REPORT.md`, `docs/reports/ERC8004_FLOW_REPORT.md`

---

## Backend Test Suite

**~1,027 total tests** (950 original + 77 added in H2A/A2A audit)

### Test Profiles (pytest markers)

- [[test-profiles-markers]] — Selective execution via `pytest -m <marker>`

| Marker | Tests | Coverage |
|--------|-------|----------|
| `core` | 276 | Routes, MCP tools, auth, reputation, workers, platform config, architecture |
| `payments` | 251 | PaymentDispatcher, escrow, fees, multichain, protocol fee |
| `erc8004` | 177 | Scoring, side effects, auto-registration, rejection, reputation tools, ERC-8128 |
| `security` | 61 | Fraud detection, GPS antispoofing |
| `infrastructure` | 77 | Webhooks, WebSocket, A2A, timestamps |
| *(unmarked)* | 153 | A2A protocol, gas dust, prepare feedback, task transactions |

```bash
# Run specific profiles
cd mcp_server
pytest -m core                    # Core business logic
pytest -m payments                # Payment flows
pytest -m "core or erc8004"       # Combine profiles
pytest                            # All tests (~5-7 min)
```

- Marker definitions: `mcp_server/pytest.ini`
- See: `docs/reports/TEST_SUITE_DESIGN_2026-02-18.md` for gap analysis (95 test gaps identified)

---

## Task Factory

- [[task-factory]] — Create test tasks on production
  - Script: `scripts/task-factory.ts`
  - Usage: `cd scripts && npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10`
  - E2E lifecycle script: `python scripts/e2e_mcp_api.py` (full lifecycle through REST API)
  - **Bounties ALWAYS < $0.20** for testing
  - `TEST_BOUNTY = 0.10` (used by E2E scripts)
  - Deadlines: 5-15 minutes for test tasks

---

## CI Pipeline

- [[ci-pipeline]] — Automated checks on every push

```
cd mcp_server && ruff check . && ruff format --check .
cd mcp_server && mypy models.py api/admin.py api/reputation.py websocket/server.py \
  --ignore-missing-imports --follow-imports=skip
cd mcp_server && TESTING=true pytest
cd dashboard && npx tsc --noEmit && npm run lint
```

| Stage | Tool | What it checks |
|-------|------|----------------|
| Lint | ruff check | Python code quality rules |
| Format | ruff format --check | Python formatting (ruff 0.15.0+ required) |
| Types (Python) | mypy | Static type analysis on key modules |
| Tests (Python) | pytest | All 1,027 backend tests |
| Types (TS) | tsc --noEmit | TypeScript compilation without emit |
| Lint (TS) | npm run lint | ESLint on dashboard code |

---

## Dashboard Tests

- [[dashboard-tests]] — Frontend testing stack
  - **Unit tests**: Vitest (`npm run test` in `dashboard/`)
  - **E2E tests**: Playwright (`npm run e2e` in `dashboard/`)
  - Lint: ESLint (`npm run lint`)
  - Type check: TypeScript compiler (`npx tsc --noEmit`)

---

## Test Budget

- [[test-budget]] — Financial constraints for production testing
  - ~**$5 USDC per chain** must last through all testing cycles
  - Production wallet: `0xD3868E1eD738CED6945A574a7c769433BeD5d474` (funded on all 8 chains)
  - Test worker wallet: `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` (key in AWS SM `em/test-worker`)
  - Test bounty amount: **$0.10** (E2E default)
  - **NEVER exceed $0.20** per test task

---

## KK Scenario Tests

- [[kk-scenario-tests]] — Karma Kadabra V2 integration tests
  - 84 KK scenario tests: 82 pass, 2 xfail
  - Tests agent-to-agent task delegation, swarm behavior, self-application prevention

---

## Reports & Documentation

| Path | Purpose |
|------|---------|
| `docs/reports/GOLDEN_FLOW_REPORT.md` | Golden Flow results (English) |
| `docs/reports/GOLDEN_FLOW_REPORT.es.md` | Golden Flow results (Spanish) |
| `docs/reports/PAYMENT_FLOW_REPORT.md` | Payment flow verification |
| `docs/reports/ERC8004_FLOW_REPORT.md` | ERC-8004 identity/reputation verification |
| `docs/reports/TEST_SUITE_DESIGN_2026-02-18.md` | Test gap analysis (95 gaps identified) |
| `docs/reports/AUDIT_*_2026-02-18.md` | Security and code audit reports (4 reports) |

---

## Key Test Files

| Path | Purpose |
|------|---------|
| `scripts/e2e_golden_flow.py` | Single-chain Golden Flow E2E |
| `scripts/e2e_golden_flow_multichain.py` | Multichain Golden Flow (8 chains) |
| `scripts/e2e_mcp_api.py` | REST API lifecycle E2E |
| `scripts/task-factory.ts` | Test task creation utility |
| `mcp_server/pytest.ini` | Pytest marker definitions |
| `mcp_server/tests/` | All backend unit/integration tests |
| `dashboard/src/**/*.test.ts` | Dashboard unit tests (Vitest) |
| `e2e/` | Playwright E2E tests |

---

## Cross-links

- [[moc-payments]] — Golden Flow validates the entire payment pipeline
- [[moc-infrastructure]] — CI/CD pipeline runs all tests before deploy
- [[moc-agents]] — KK scenario tests validate multi-agent swarm behavior
- [[moc-identity]] — ERC-8004 flow tested in Golden Flow steps 3-4, 9-10
