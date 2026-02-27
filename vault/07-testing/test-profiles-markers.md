---
date: 2026-02-26
tags:
  - domain/testing
  - pytest
  - unit-tests
status: active
aliases:
  - Test Profiles
  - pytest markers
  - Test Markers
related-files:
  - mcp_server/pytest.ini
  - mcp_server/tests/
---

# Test Profiles & Markers

The backend test suite (1,027+ tests) is organized with **pytest markers** for selective execution.

## Configuration

File: `mcp_server/pytest.ini`

## Marker Reference

| Marker | Tests | Coverage |
|--------|-------|----------|
| `core` | 276 | Routes, MCP tools, auth, reputation, workers, platform config, architecture |
| `payments` | 251 | PaymentDispatcher, escrow, fees, multichain, protocol fee |
| `erc8004` | 177 | Scoring, side effects, auto-registration, rejection, reputation tools, ERC-8128 |
| `security` | 61 | Fraud detection, GPS antispoofing |
| `infrastructure` | 77 | Webhooks, WebSocket, A2A, timestamps |
| *(unmarked)* | 153 | A2A protocol, gas dust, prepare feedback, task transactions |
| `h2a` | 31 | Human-to-Agent publisher flows |
| `agent_executor` | 46 | Agent-as-executor scenarios |

## Usage

```bash
cd mcp_server

# All tests
pytest

# Single profile
pytest -m core
pytest -m payments

# Combined profiles
pytest -m "core or erc8004"
pytest -m "core or payments"

# Exclude a profile
pytest -m "not security"
```

## Environment

Tests require `TESTING=true` environment variable:

```bash
TESTING=true pytest
```

## Gaps Identified (2026-02-18 audit)

95 test gaps found across H2A, Agent Executor, A2A bridge, and DB migrations. Design document: `docs/reports/TEST_SUITE_DESIGN_2026-02-18.md`.

## Related

- [[ci-pipeline]] -- runs all tests in CI
- [[golden-flow]] -- E2E acceptance (separate from unit tests)
