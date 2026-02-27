---
date: 2026-02-26
tags:
  - domain/testing
  - ci
  - linting
  - type-checking
status: active
aliases:
  - CI Pipeline
  - Continuous Integration
related-files:
  - .github/workflows/deploy.yml
  - mcp_server/pytest.ini
  - dashboard/tsconfig.json
---

# CI Pipeline

Six-stage quality gate that runs on every push. All stages must pass before deployment.

## Stages

### 1. Python Lint

```bash
cd mcp_server && ruff check .
```

Static analysis for bugs, unused imports, style violations.

### 2. Python Format Check

```bash
cd mcp_server && ruff format --check .
```

**CRITICAL**: ruff version must be 0.15.0+ locally. Different versions format differently, causing CI failures.

### 3. Type Check

```bash
cd mcp_server && mypy models.py api/admin.py api/reputation.py websocket/server.py \
  --ignore-missing-imports --follow-imports=skip
```

Selected modules only (not full codebase).

### 4. Python Tests

```bash
cd mcp_server && TESTING=true pytest
```

All 1,027+ tests. See [[test-profiles-markers]] for selective runs.

### 5. TypeScript Type Check

```bash
cd dashboard && npx tsc --noEmit
```

### 6. TypeScript Lint

```bash
cd dashboard && npm run lint
```

## Local Pre-commit

```bash
cd mcp_server && ruff format . && ruff check . && TESTING=true pytest
cd dashboard && npx tsc --noEmit && npm run lint
```

**CRITICAL**: ruff format failures usually mean version mismatch. Fix with `pip install --user --force-reinstall ruff` (must be 0.15.0+).

## Related

- [[github-actions-cicd]] -- full deployment pipeline
- [[test-profiles-markers]] -- pytest marker system
