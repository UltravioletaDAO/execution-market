# CI/CD Pipeline Documentation

> Last updated: 2026-02-07

## Overview

Execution Market uses three GitHub Actions workflows that run on every push to `main`:

| Workflow | File | Triggers | Purpose |
|----------|------|----------|---------|
| CI | `.github/workflows/ci.yml` | push to main/develop, PRs | Lint, test, build Docker |
| Execution Market CI/CD | `.github/workflows/deploy.yml` | push to main/production, PRs | Full deploy pipeline |
| Security | `.github/workflows/security.yml` | push to main/develop, PRs, weekly | Security scanning |

There is also a **Release** workflow (`.github/workflows/release.yml`) triggered manually via `workflow_dispatch`.

---

## CI Workflow (`ci.yml`)

```
Lint Backend ────> Test Backend ──┐
                                   ├──> Build Docker Images
Lint Frontend ──> Test Frontend ──┘
```

### Jobs

#### Lint Backend
- **ruff check**: Python linter (rules configured in `mcp_server/pyproject.toml`)
- **ruff format --check**: Code formatting verification
- **mypy**: Type checking (`continue-on-error: true` — 1300+ pre-existing errors)

#### Lint Frontend
- **ESLint**: JS/TS linting (config: `dashboard/.eslintrc.cjs`, max 200 warnings)
- **tsc --noEmit**: TypeScript type checking

#### Test Backend
- **pytest**: Python tests with coverage (`continue-on-error: true` — 39 pre-existing failures)
- Coverage uploaded to Codecov

#### Test Frontend
- **vitest**: React component tests with coverage via `@vitest/coverage-v8`
- Coverage uploaded to Codecov

#### Build Docker Images
- Only runs on `push` events (not PRs)
- Builds both `mcp_server/Dockerfile` and `dashboard/Dockerfile`
- Uses GitHub Actions cache (`type=gha`)
- Does NOT push to registry (that's the deploy workflow's job)

### E2E Tests
**Disabled as of 2026-02-07.** Tests reference `[data-testid="login-form"]` which doesn't exist (app uses Dynamic.xyz). Run locally instead:
```bash
cd e2e && npm install && npx playwright test
```

---

## Deploy Workflow (`deploy.yml`)

```
Test MCP Server ──┐
                   ├──> Build & Push to ECR ──> Deploy to ECS ──> Health Check
Test Dashboard ───┘
```

### Environment Variables

| Variable | Value |
|----------|-------|
| `AWS_REGION` | `us-east-2` |
| `ECR_REGISTRY` | `{AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com` |
| `MCP_SERVER_ECR_REPO` | `em-production-mcp-server` |
| `DASHBOARD_ECR_REPO` | `em-production-dashboard` |
| `ECS_CLUSTER` | `em-production-cluster` |
| `MCP_SERVER_SERVICE` | `em-production-mcp-server` |
| `MCP_SERVER_CONTAINER` | `mcp-server` |
| `DASHBOARD_SERVICE` | `em-production-dashboard` |
| `DASHBOARD_CONTAINER` | `dashboard` |
| `BASE_URL` | `https://execution.market` |
| `API_URL` | `https://api.execution.market` |

> **Important**: Container names (`mcp-server`, `dashboard`) differ from service names. The ECS task definitions use the short names.

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key |
| `AWS_ACCOUNT_ID` | AWS account ID (for ECR registry URL) |

### Jobs

#### Build and Push Docker Images
- Only runs on push to `main` or `production`
- Builds with `docker/build-push-action@v5`
- Pushes to ECR with tags: `{sha}` and `latest`
- Dashboard build uses `NODE_OPTIONS=--max_old_space_size=4096` to prevent OOM

#### Deploy to ECS
- Downloads current task definitions from ECS
- Updates container image in task definitions
- Deploys via `aws-actions/amazon-ecs-deploy-task-definition@v1`
- Waits for service stability
- Health check: `curl https://api.execution.market/health` must return 200

#### Notify on Failure
- Runs if any job fails
- Currently just logs to GitHub Step Summary (add Slack/Discord webhook as needed)

---

## Security Workflow (`security.yml`)

All security scan jobs use `continue-on-error: true` — they are **informational only** and never block deployments.

| Job | Tool | What it scans |
|-----|------|--------------|
| CodeQL Analysis | github/codeql-action | Python + JS/TS code for vulnerabilities |
| Python Security Scan | Bandit + Safety | Python code + dependency CVEs |
| NPM Security Audit | npm audit | Node.js dependency CVEs |
| Container Security Scan | Trivy | Docker images for known vulns |
| Secret Scanning | Gitleaks + TruffleHog | Git history for leaked secrets |
| License Compliance | pip-licenses + license-checker | GPL/AGPL license violations |
| Semgrep SAST | Semgrep | Multi-language security patterns |
| Dependency Review | actions/dependency-review | PR-only: new dependency risks |

### Prerequisites

- **CodeQL**: Requires "Code scanning" enabled in repo Settings > Security > Code security and analysis
- **SARIF uploads** (Trivy, Semgrep): Also require Code scanning enabled

### Reports

All scan reports are uploaded as GitHub Actions artifacts (30-day retention):
- `bandit-report` — Python security issues
- `safety-report` — Python dependency vulnerabilities
- `npm-audit-report` — Node.js dependency vulnerabilities
- `license-reports` — License compliance for Python + Node.js

---

## Release Workflow (`release.yml`)

Triggered manually via `workflow_dispatch` with a version bump type (`patch`, `minor`, `major`).

Steps:
1. Calculate new version from latest git tag
2. Run all tests
3. Build and push Docker images
4. Create git tag and GitHub release
5. Update CHANGELOG.md

---

## Known Issues & Non-Blocking Steps

These steps have `continue-on-error: true` to prevent blocking CI while pre-existing issues are addressed:

| Step | Workflow | Reason |
|------|----------|--------|
| mypy | ci.yml, deploy.yml | 1300+ pre-existing type errors |
| pytest | ci.yml | 39 pre-existing test failures |
| All security scans | security.yml | Informational, not blockers |
| E2E tests | — | Removed from CI (run locally) |

### To Fix

1. **mypy errors**: Gradually add type annotations, remove `continue-on-error` when clean
2. **pytest failures**: Fix broken tests, remove `continue-on-error` when green
3. **E2E tests**: Update `e2e/fixtures/auth.ts` for Dynamic.xyz, re-add to CI
4. **CodeQL**: Enable "Code scanning" in GitHub repo settings

---

## Local Development vs CI

| Task | Local Command | CI Equivalent |
|------|--------------|--------------|
| Lint Python | `cd mcp_server && ruff check .` | Lint Backend job |
| Format Python | `cd mcp_server && ruff format .` | `ruff format --check .` |
| Type check Python | `cd mcp_server && mypy . --ignore-missing-imports` | mypy step (non-blocking) |
| Test Python | `cd mcp_server && pytest -v` | Test Backend job |
| Lint Frontend | `cd dashboard && npm run lint` | Lint Frontend job |
| Type check TS | `cd dashboard && npm run typecheck` | `tsc --noEmit` step |
| Test Frontend | `cd dashboard && npm run test:run` | Test Frontend job |
| E2E tests | `cd e2e && npx playwright test` | **Not in CI** |
| Docker build | `docker build -f dashboard/Dockerfile ./dashboard` | Build Docker Images job |

---

## Manual Deploy

If GitHub Actions deploy fails or you need to deploy manually:

```bash
# 1. Login to ECR
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  518898403364.dkr.ecr.us-east-2.amazonaws.com

# 2. Build + push dashboard
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard
docker tag em-dashboard:latest \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
docker push \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest

# 3. Build + push MCP server
docker build --no-cache -f mcp_server/Dockerfile -t em-mcp ./mcp_server
docker tag em-mcp:latest \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
docker push \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest

# 4. Force new deployment
aws ecs update-service --cluster em-production-cluster \
  --service em-production-dashboard --force-new-deployment --region us-east-2
aws ecs update-service --cluster em-production-cluster \
  --service em-production-mcp-server --force-new-deployment --region us-east-2

# 5. Verify
sleep 90
curl https://api.execution.market/health
curl https://execution.market
```
