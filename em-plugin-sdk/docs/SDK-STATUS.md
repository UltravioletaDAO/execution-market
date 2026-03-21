---
date: 2026-03-21
tags:
  - type/report
  - domain/integrations
status: active
related-files:
  - em-plugin-sdk/em_plugin_sdk/client.py
  - em-plugin-sdk/em_plugin_sdk/resources/
  - em-plugin-sdk/em_plugin_sdk/realtime/
---

# em-plugin-sdk — Status Report

> Python SDK for the [[Execution Market]] REST API.
> Branch: `feat/plugin-sdk` (merged to `main` 2026-03-21)
> Package: `em-plugin-sdk/` (standalone, ready for own repo)

## Summary

| Metric | Value |
|--------|-------|
| Version | 0.4.0 |
| Phases completed | 6 / 6 |
| Commits | 7 feature + 1 merge |
| Files | 43 |
| Lines of code | ~4,400 |
| Tests | **142 passing** |
| Resource namespaces | 11 |
| API methods | ~75 |
| API coverage | **82%** (75 of ~92 endpoints) |
| Pydantic models | 24 |
| Networks | 9 EVM + Solana |
| Fee categories | 21 |
| Examples | 4 |

---

## Architecture

```
em-plugin-sdk/
├── em_plugin_sdk/
│   ├── client.py                    # EMClient — entry point, 11 resource namespaces
│   ├── models.py                    # 24 Pydantic v2 models
│   ├── exceptions.py                # EMError → EMAuthError, EMNotFoundError, EMValidationError, EMServerError
│   │
│   ├── resources/                   # Stripe-pattern resource namespaces
│   │   ├── tasks.py                 # client.tasks.*          (11 methods)
│   │   ├── submissions.py           # client.submissions.*    (5 methods)
│   │   ├── workers.py               # client.workers.*        (4 methods)
│   │   ├── reputation.py            # client.reputation.*     (13 methods)
│   │   ├── evidence.py              # client.evidence.*       (4 methods)
│   │   ├── payments.py              # client.payments.*       (4 methods)
│   │   ├── webhooks.py              # client.webhooks.*       (8 methods)
│   │   ├── h2a.py                   # client.h2a.*            (7 methods)
│   │   │                            # client.agents.*         (2 methods)
│   │   ├── swarm.py                 # client.swarm.*          (13 methods)
│   │   └── relay.py                 # client.relay.*          (4 methods)
│   │
│   ├── realtime/                    # WebSocket event system
│   │   ├── ws_client.py             # EMEventClient (auto-reconnect, rooms, handlers)
│   │   └── event_types.py           # 22 event type constants + room helpers
│   │
│   ├── networks.py                  # Static network/token registry (no server calls)
│   ├── fees.py                      # Fee calculator (no server calls)
│   ├── retry.py                     # Exponential backoff + jitter
│   ├── pagination.py                # Auto-paginating async iterator
│   │
│   ├── testing/                     # Consumer test helpers
│   │   └── mock_client.py           # MockEMClient (drop-in, no network)
│   │
│   └── py.typed                     # PEP 561
│
├── examples/
│   ├── quick_start.py               # Full lifecycle: publish → assign → approve
│   ├── worker_agent.py              # Worker-side: register → browse → apply → submit
│   ├── fee_calculator.py            # Offline fee computation + network validation
│   └── webhook_server.py            # FastAPI webhook receiver + HMAC verification
│
├── tests/                           # 142 tests
│   ├── test_client.py               # 33 (core, retry, pagination, errors, lifecycle)
│   ├── test_mock_client.py          # 19 (MockEMClient mirrors real API)
│   ├── test_reputation.py           # 13 (read + write, ERC-8004)
│   ├── test_fees.py                 # 12 (rates, reverse calc, edge cases)
│   ├── test_networks.py             # 11 (registry, chain IDs, token validation)
│   ├── test_realtime.py             # 10 (event types, rooms, import guard)
│   ├── test_webhooks.py             #  9 (CRUD + HMAC signature)
│   ├── test_h2a.py                  #  9 (H2A + agent directory)
│   ├── test_swarm.py                # 17 (13 swarm + 4 relay)
│   ├── test_payments.py             #  5 (balance, events, timeline)
│   └── test_evidence.py             #  4 (presign, verify)
│
├── pyproject.toml                   # hatchling build, httpx + pydantic deps
└── README.md                        # Quick start + API coverage table
```

---

## Phase History

### Phase 1 — Foundation (commit `a2fd5d2`)
- Package scaffold with `pyproject.toml`, `py.typed`
- `EMClient` with flat async methods (httpx)
- Basic models: Task, Submission, Application, Executor
- Custom exception hierarchy (5 levels)
- 27 tests

### Phase 2 — Resource Namespaces + Infrastructure (commit `d84a374`)
- **Stripe-pattern refactor**: `client.tasks.create()` instead of `client.create_task()`
- Automatic retry with exponential backoff + jitter (429, 5xx)
- `PageIterator` for auto-paginating list endpoints
- Open-access mode (API key now optional)
- `networks.py`: static registry of 9 EVM chains + Solana with token addresses
- `fees.py`: `calculate_fee()`, `calculate_reverse_fee()`, 21 category rates
- New models: PaymentEvent, PaymentTimeline, PlatformConfig
- New endpoints: assign, batch_create, available_tasks, get_payment, get_transactions
- 56 tests

### Phase 3 — Reputation, Evidence, Payments (commit `e8c8763`)
- `client.reputation`: 13 methods covering all ERC-8004 endpoints
  - Read: get_agent, get_agent_identity, leaderboard, info, networks, em_reputation, em_identity, get_feedback
  - Write: rate_worker, rate_agent, register, prepare_feedback, confirm_feedback
- `client.evidence`: presign_upload, presign_download, upload (convenience), verify (AI-powered)
- `client.payments`: balance (multichain), events, task_payment, task_transactions
- New models: AgentReputation, AgentIdentity, EvidenceUploadInfo, EvidenceVerifyResult
- 78 tests

### Phase 4 — Webhooks, H2A, Agents (commit `242dca4`)
- `client.webhooks`: full CRUD (create/list/get/update/delete) + rotate_secret, test, `verify_signature()` (HMAC-SHA256)
- `client.h2a`: publish, list, get, submissions, approve, reject, cancel (Human-to-Agent marketplace)
- `client.agents`: directory, register_executor
- New models: Webhook, WebhookList
- 96 tests

### Phase 5 — WebSocket, Swarm, Relay (commits `43ca096`, `46b30e2`)
- `EMEventClient` (realtime/ws_client.py): WebSocket client with auto-reconnect, room subscriptions, typed event handlers, async iteration, ping/latency
- `EventType`: 22 event constants (TaskCreated, SubmissionApproved, PaymentReleased, etc.)
- Room helpers: `task_room()`, `user_room()`, `category_room()`, `GLOBAL_ROOM`
- `client.swarm`: 13 methods (status, health, agents, dashboard, metrics, events, tasks, poll, config, activate, suspend, budget)
- `client.relay`: 4 methods (create, get, assign_leg, handoff)
- `websockets` as optional dependency (`pip install em-plugin-sdk[realtime]`)
- 123 tests

### Phase 6 — Testing Helpers + Examples (commit `c9e2505`)
- `MockEMClient`: drop-in replacement for tests, configurable responses, call tracking via `resource._calls`
- 4 examples: quick_start, worker_agent, fee_calculator, webhook_server
- 142 tests

---

## API Coverage Matrix

### Covered (75 endpoints / ~82%)

| Resource | Methods | Endpoints |
|----------|---------|-----------|
| `client.tasks` | create, get, list, list_page, cancel, assign, batch_create, apply, list_applications, get_payment, get_transactions, available | 12 |
| `client.submissions` | list, submit, approve, reject, request_more_info | 5 |
| `client.workers` | get, register, balance, payment_events | 4 |
| `client.reputation` | get_agent, get_agent_identity, leaderboard, info, networks, em_reputation, em_identity, get_feedback, rate_worker, rate_agent, register, prepare_feedback, confirm_feedback | 13 |
| `client.evidence` | presign_upload, presign_download, upload, verify | 4 |
| `client.payments` | balance, events, task_payment, task_transactions | 4 |
| `client.webhooks` | create, list, get, update, delete, rotate_secret, test, verify_signature | 8 |
| `client.h2a` | publish, list, get, submissions, approve, reject, cancel | 7 |
| `client.agents` | directory, register_executor | 2 |
| `client.swarm` | status, health, agents, agent, dashboard, metrics, events, tasks, poll, update_config, activate_agent, suspend_agent, update_budget | 13 |
| `client.relay` | create, get, assign_leg, handoff | 4 |
| Top-level | health, config | 2 |
| **Total** | | **~75** |

### Not Covered (~17 endpoints / ~18%)

These are internal/admin endpoints that don't belong in a public SDK:

| Endpoint | Reason excluded |
|----------|----------------|
| `POST /identity/sync` | Internal: MRServ → EM identity push |
| `POST /identity/verify-challenge` | Internal: server-side EIP-191 verification |
| `GET /identity/lookup` | Internal: IRC identity lookup |
| `GET /auth/nonce` | Internal: nonce for ERC-8128 auth flow |
| `GET /auth/erc8128/nonce` | Alias of above |
| `GET /auth/erc8128/info` | Internal: ERC-8128 config |
| `GET /.well-known/x402` | Discovery: x402 payment descriptor |
| `GET /agent-info` | Redundant with `health()` |
| `GET /skills` | Discovery: machine-readable skill descriptors |
| `GET /public/metrics` | Could add — public platform metrics |
| `GET /ws/stats` | Internal: WebSocket connection stats |
| `GET /ws/rooms` | Internal: WebSocket room info |
| `POST /admin/fees/sweep` | Admin-only: fee distribution |
| Worker executor identity (3) | Niche: ERC-8004 identity for workers via executor ID |
| Chat history | Niche: IRC/chat log per task |

### Standalone Features (no server calls)

| Feature | Module | Description |
|---------|--------|-------------|
| Fee calculator | `fees.py` | `calculate_fee()`, `calculate_reverse_fee()`, `get_fee_rate()` — 21 category rates (11-13%) |
| Network registry | `networks.py` | 9 EVM chains + Solana, token addresses, escrow/operator flags, `is_valid_pair()`, `get_chain_id()` |
| Event types | `realtime/event_types.py` | 22 event constants + room helpers |
| Mock client | `testing/mock_client.py` | `MockEMClient` for consumer unit tests |

---

## What's Left (Nice-to-Have)

None of these block shipping. All are incremental improvements.

| Item | Effort | Impact | Priority |
|------|--------|--------|----------|
| **Sync client** (`EMClientSync`) | 1-2h | Devs not using async | P1 |
| **Fix broken integrations** (LangChain/CrewAI/OpenAI) | 2h | They use wrong field names, wrong endpoints — rebuild on this SDK | P1 |
| **Publish to PyPI** | 15min | `pip install em-plugin-sdk` | P1 |
| **Idempotency keys** (`Idempotency-Key` header) | 30min | Prevents duplicate task creation on retries | P2 |
| **Logging/debug mode** (`EM_LOG=debug`) | 30min | DX for troubleshooting | P2 |
| **Request ID tracking** (`X-Request-Id` on errors) | 30min | Support ticket debugging | P2 |
| **`client.realtime` shortcut** | 30min | `client.realtime.watch_task()` without separate import | P3 |
| **README badges + API reference** | 1h | Polish | P3 |
| **Add `public/metrics` endpoint** | 15min | Public platform stats | P3 |
| **ERC-8128 auth support** | 1h | Wallet-based auth as alternative to API key | P3 |

### Known Bugs in Other SDKs (Found During Analysis)

The 5-agent analysis discovered that **all 3 framework integrations are broken**:

| Integration | Bug | Severity |
|-------------|-----|----------|
| LangChain (`integrations/langchain/em_tools.py`) | Uses `description` instead of `instructions` for task creation | Critical — tasks would fail |
| CrewAI (`integrations/crewai/em_tools.py`) | Wrong field `evidence_schema` (should be `evidence_required`), wrong deadline conversion (`* 3600`), wrong approve endpoint (`/tasks/{id}/approve` instead of `/submissions/{id}/approve`) | Critical — multiple broken flows |
| OpenAI Agents (`integrations/openai-agents/em_tools.py`) | Uses `requests` (sync) with wrong `description` field, `X-API-Key` header inconsistency | Critical — tasks would fail |

**Recommendation**: Rebuild all three as thin wrappers over `em-plugin-sdk`, reducing each to ~50 lines.

---

## Dependencies

```toml
[project]
dependencies = [
    "httpx>=0.25.0",      # Async HTTP client
    "pydantic>=2.0",      # Model validation
]

[project.optional-dependencies]
realtime = ["websockets>=12.0"]  # For EMEventClient
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "respx>=0.21", "websockets>=12.0"]
```

---

## Usage Examples

### Agent publishes a task
```python
async with EMClient(api_key="em_...") as client:
    task = await client.tasks.create(CreateTaskParams(
        title="Verify store hours",
        instructions="Photo the posted hours at 123 Main St",
        category=TaskCategory.PHYSICAL_PRESENCE,
        bounty_usd=2.00,
        deadline_hours=4,
        evidence_required=[EvidenceType.PHOTO_GEO],
    ))
```

### Worker applies and submits
```python
async with EMClient(api_key="em_...") as client:
    await client.tasks.apply("task-uuid", "executor-uuid", message="On my way")
    await client.submissions.submit("task-uuid", SubmitEvidenceParams(
        executor_id="executor-uuid",
        evidence={"photo_geo": {"url": "https://...", "lat": 25.76, "lng": -80.19}},
    ))
```

### Offline fee calculation
```python
from em_plugin_sdk import calculate_fee, is_valid_pair

fee = calculate_fee(10.00, "physical_presence")
# fee.worker_amount = 8.70, fee.fee_amount = 1.30

assert is_valid_pair("base", "USDC")  # True
assert is_valid_pair("base", "PYUSD")  # False
```

### Real-time events
```python
from em_plugin_sdk.realtime import EMEventClient, EventType

async with EMEventClient(api_key="em_...") as ws:
    await ws.watch_task("task-uuid")
    ws.on(EventType.SUBMISSION_RECEIVED, lambda e: print("New submission!", e))
    async for event in ws.events():
        print(event["type"])
```

### Testing with MockEMClient
```python
from em_plugin_sdk.testing import MockEMClient

async def test_my_agent():
    client = MockEMClient()
    task = await client.tasks.create(params)
    assert task.id == "mock-task-001"
    assert client.tasks._calls[0] == ("create", params)
```
