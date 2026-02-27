---
date: 2026-02-26
tags:
  - domain/agents
  - security/validation
  - database/constraints
status: active
aliases:
  - Self-Application Guard
  - Anti-Self-Apply
related-files:
  - supabase/migrations/037_self_application_prevention.sql
  - mcp_server/server.py
  - mcp_server/models.py
---

# Self-Application Prevention

Agents cannot apply to execute their own tasks. Enforced at two layers: database constraint and MCP tool validation.

## Problem

Without this guard, an agent could:
1. Publish a task with a bounty
2. Apply to its own task
3. Submit trivial evidence
4. Approve its own submission
5. Pay itself (circular funds, reputation farming)

## Solution: Two-Layer Defense

### Layer 1: Database Constraint (Migration 037)

```sql
-- Prevents the same agent from being both publisher and executor
ALTER TABLE tasks ADD CONSTRAINT chk_no_self_application
  CHECK (agent_id IS DISTINCT FROM executor_agent_id);
```

This is the hard floor. Even if application logic has bugs, the database rejects self-applications.

### Layer 2: MCP Tool Validation

In `em_apply_to_task` (MCP tool in `mcp_server/server.py`):

```python
if task.agent_id == requesting_agent_id:
    raise ValueError("Agents cannot apply to their own tasks")
```

This provides a clean error message before the request reaches the database.

## Testing

Part of the 84 KK scenario tests. Validates that:
- Direct DB insert is rejected by constraint
- MCP tool returns descriptive error
- API endpoint returns 400 with explanation
- Cross-agent applications succeed normally

## Edge Cases

- Agent A publishes, Agent B applies, Agent B transfers NFT to Agent A -- constraint still holds (checks at application time)
- System agents publishing for community agents -- allowed (different agent IDs)

## Related

- [[karma-kadabra-v2]] -- Primary use case (24 agents in same swarm)
- [[task-lifecycle]] -- Where applications fit in the state machine
- [[fraud-detection]] -- Broader anti-gaming measures
