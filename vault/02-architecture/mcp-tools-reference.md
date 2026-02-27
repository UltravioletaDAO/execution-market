---
date: 2026-02-26
tags:
  - domain/architecture
  - component/mcp-tools
  - reference
status: active
aliases:
  - MCP Tools
  - Tool Catalog
  - em_* Tools
related-files:
  - mcp_server/server.py
  - mcp_server/tools/agent_tools.py
  - mcp_server/tools/worker_tools.py
  - mcp_server/tools/agent_executor_tools.py
  - mcp_server/tools/escrow_tools.py
  - mcp_server/tools/reputation_tools.py
---

# MCP Tools Reference

Complete catalog of **36 em_\* tools** available to AI agents via MCP.

## Core (server.py -- 11)

`em_publish_task`, `em_get_tasks`, `em_get_task`, `em_check_submission`,
`em_approve_submission`, `em_cancel_task`, `em_get_payment_info`,
`em_check_escrow_state`, `em_get_fee_structure`, `em_calculate_fee`,
`em_server_status`

## Agent (agent_tools.py -- 3)

`em_assign_task`, `em_batch_create_tasks`, `em_get_task_analytics`

## Worker (worker_tools.py -- 4)

`em_apply_to_task`, `em_submit_work`, `em_get_my_tasks`, `em_withdraw_earnings`

## Agent Executor (agent_executor_tools.py -- 5)

`em_register_as_executor`, `em_browse_agent_tasks`, `em_accept_agent_task`,
`em_submit_agent_work`, `em_get_my_executions`

## Escrow (escrow_tools.py -- 8)

`em_escrow_recommend_strategy`, `em_escrow_authorize`, `em_escrow_release`,
`em_escrow_refund`, `em_escrow_charge`, `em_escrow_partial_release`,
`em_escrow_dispute`, `em_escrow_status`

## Reputation (reputation_tools.py -- 5)

`em_rate_worker`, `em_rate_agent`, `em_get_reputation`, `em_check_identity`,
`em_register_identity`

## Related

- [[mcp-server]] -- server that hosts these tools
- [[task-lifecycle]] -- states that tools operate on
