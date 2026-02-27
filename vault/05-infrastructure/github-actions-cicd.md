---
date: 2026-02-26
tags:
  - domain/infrastructure
  - cicd
  - github-actions
status: active
aliases:
  - CI/CD
  - GitHub Actions
  - deploy.yml
related-files:
  - .github/workflows/deploy.yml
---

# GitHub Actions CI/CD

Automated deployment pipeline triggered on push to `main`.

## Pipeline: `deploy.yml`

**Trigger**: Push to `main` branch
**Duration**: ~20 minutes end-to-end
**Reason user controls push**: Pushing triggers this pipeline, so only push when explicitly requested.

## Stages

| Stage | Tool | What it does |
|-------|------|--------------|
| Lint (Python) | ruff check | Static analysis on `mcp_server/` |
| Format (Python) | ruff format --check | Code style verification |
| Type check | mypy | Selected modules only |
| Test (Python) | pytest | All 1,027+ tests |
| Type check (TS) | tsc --noEmit | Dashboard TypeScript |
| Lint (TS) | ESLint | Dashboard code quality |
| Build Dashboard | docker build | `dashboard/Dockerfile` |
| Build MCP Server | docker build | `mcp_server/Dockerfile` |
| Push ECR | docker push | Both images to [[ecr-registry]] |
| Deploy ECS | aws ecs update-service | Force new deployment on [[ecs-fargate]] |

See [[ci-pipeline]] for the exact commands run in the lint/test stages.

## Key Constraints

- Images MUST use `:latest` tag per [[image-tagging-policy]]
- CI may create `ship-*` tags but task definitions reference `:latest`
- ruff version must match local (0.15.0+) to avoid format drift

## Git Workflow

```
Make changes -> commit locally -> user tests -> user says "push" -> git push -> pipeline runs
```

**NEVER auto-push.** Only push when the user explicitly requests it.

## Related

- [[ci-pipeline]] -- local CI commands reference
- [[ecr-registry]] -- image destination
- [[ecs-fargate]] -- deployment target
