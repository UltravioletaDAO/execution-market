---
date: 2026-02-26
tags:
  - domain/testing
  - tools
  - task-creation
status: active
aliases:
  - Task Factory
  - task-factory.ts
related-files:
  - scripts/task-factory.ts
  - scripts/e2e_mcp_api.py
---

# Task Factory

CLI tool for creating test tasks on the Execution Market platform.

## Script

```bash
cd scripts
npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--preset` | (required) | Task template: `screenshot`, `photo`, etc. |
| `--bounty` | 0.10 | USDC bounty amount |
| `--deadline` | 10 | Minutes until task expires |
| `--network` | base | Payment network |

## Budget Rules

Per [[test-budget]]:
- Bounties **ALWAYS < $0.20**
- ~$5 USDC per chain must last through all testing cycles
- E2E standard: `TEST_BOUNTY = 0.10`
- Deadlines: 5-15 minutes for test tasks

## Alternative: E2E Script

For full lifecycle testing (not just task creation):

```bash
python scripts/e2e_mcp_api.py
```

This runs the complete task lifecycle through the REST API: create -> accept -> submit -> approve.

## Production Wallet

`0xD3868E1eD738CED6945A574a7c769433BeD5d474` -- funded on all 8 chains.

## Related

- [[test-budget]] -- budget constraints
- [[golden-flow]] -- full E2E acceptance test
