# Testing

Execution Market has a comprehensive test suite with **1,950+ tests** across backend (Python), frontend (Vitest), and end-to-end (Playwright).

## Backend Tests (1,944 Python)

Located in `mcp_server/tests/`. Run with pytest.

```bash
cd mcp_server

# All tests
pytest

# Specific markers
pytest -m core              # 276 tests — routes, auth, reputation, workers
pytest -m payments          # 251 tests — escrow, fees, multichain, protocol fee
pytest -m erc8004           # 177 tests — identity, scoring, registration
pytest -m security          # 61 tests  — fraud detection, GPS anti-spoofing
pytest -m infrastructure    # 77 tests  — webhooks, WebSocket, A2A

# Combine
pytest -m "core or erc8004"
pytest -m "payments or erc8004"

# Verbose
pytest -v -m payments

# Coverage
pytest --cov=. --cov-report=html
```

### Test Markers Reference

| Marker | Count | Coverage |
|--------|-------|---------|
| `core` | 276 | REST routes, MCP tools, auth, reputation, workers, platform config |
| `payments` | 251 | PaymentDispatcher, escrow, fees, multichain, EIP-3009 |
| `erc8004` | 177 | Scoring algorithm, side effects, auto-registration, reputation tools |
| `security` | 61 | Fraud detection, GPS anti-spoofing, rate limiting |
| `infrastructure` | 77 | Webhooks, WebSocket, A2A protocol, timestamps |
| *(unmarked)* | ~153 | A2A, gas dust, feedback, task transactions |

### Test Configuration

`mcp_server/pytest.ini` defines all markers and settings. Tests use mocked Supabase/blockchain calls (no live network required for unit tests).

## Dashboard Tests (8 Vitest)

```bash
cd dashboard
npm run test          # Vitest unit tests
npm run test:coverage # With coverage report
```

## E2E Tests (Playwright)

```bash
cd e2e
npm install
npx playwright install
npx playwright test

# Specific tests
npx playwright test task-lifecycle.spec.ts
npx playwright test --headed    # Visual mode
npx playwright test --ui        # Playwright UI mode
```

## Golden Flow (Full Lifecycle E2E)

The **Golden Flow** is the definitive acceptance test. If it passes, the platform is healthy. It tests the complete production lifecycle:

1. Health check
2. Task creation (escrow lock)
3. Worker registration
4. ERC-8004 identity check
5. Task application
6. Worker assignment
7. Evidence submission
8. AI verification
9. Approval + payment release
10. Bidirectional reputation update
11. On-chain verification

```bash
# Requires production API access and funded wallets
python scripts/e2e_golden_flow.py
```

Golden Flow results are published in `docs/reports/GOLDEN_FLOW_REPORT.md`.

**Last known result**: 7/8 chains PASS (Solana Fase 1 confirmed ✓)

## CI Pipeline

Tests run automatically on every push via GitHub Actions:

```yaml
# .github/workflows/ci.yml
- Lint: ruff (Python), ESLint (TypeScript), mypy (type check)
- Test: pytest (backend) + vitest (dashboard)
- Security: CodeQL + Semgrep + Trivy + Gitleaks + Bandit
- Build: Docker images (on test pass)
```

## Writing Tests

### Backend Test Pattern

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.core
def test_create_task(client: TestClient, mock_db):
    """Test task creation returns correct structure."""
    response = client.post("/api/v1/tasks", json={
        "title": "Test task",
        "category": "physical_presence",
        "bounty_usd": 0.10,
        "deadline_hours": 1,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "published"
    assert data["bounty_usd"] == 0.10

@pytest.mark.payments
def test_fee_calculation():
    """Test 13% fee calculation with minimum."""
    from mcp_server.payments import calculate_fee
    worker, fee = calculate_fee(1.00)
    assert worker == 0.87
    assert fee == 0.13

    # Test minimum fee
    worker_small, fee_small = calculate_fee(0.05)
    assert fee_small == 0.01  # Minimum fee applied
```

### Dashboard Test Pattern

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TaskCard } from '../components/TaskCard'

describe('TaskCard', () => {
  it('displays task details correctly', () => {
    render(<TaskCard task={{ title: 'Test', bounty_usd: 1.50, status: 'published' }} />)
    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('$1.50')).toBeInTheDocument()
  })
})
```

## Security Scanning

The CI pipeline runs:

| Tool | What it scans |
|------|--------------|
| **CodeQL** | Code vulnerabilities (Python + TypeScript) |
| **Semgrep** | Security anti-patterns |
| **Trivy** | Container image vulnerabilities |
| **Gitleaks** | Secrets in code |
| **Bandit** | Python security issues |
| **Safety** | Python dependency vulnerabilities |
