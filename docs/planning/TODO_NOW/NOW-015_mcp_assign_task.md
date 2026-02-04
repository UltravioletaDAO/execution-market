# NOW-015: Implementar em_assign_task

## Metadata
- **Prioridad**: P0
- **Fase**: 1 - MCP Server
- **Dependencias**: NOW-011
- **Archivos a modificar**: `mcp_server/server.py`
- **Tiempo estimado**: 1-2 horas

## Descripción
Implementar el tool MCP que permite a un agent asignar una tarea a un worker específico.

## Contexto Técnico
- **Caller**: Agent (via MCP)
- **Validaciones**: Agent owns task, executor has applied, task is open
- **Side effects**: Notifica al worker, inicia timer

## Input Schema
```json
{
  "task_id": "uuid",
  "executor_id": "uuid",
  "agent_id": "string"
}
```

## Output Schema
```json
{
  "success": true,
  "task_id": "uuid",
  "executor_id": "uuid",
  "assigned_at": "2026-01-25T10:00:00Z",
  "deadline": "2026-01-25T14:00:00Z"
}
```

## Código de Referencia

```python
Tool(
    name="em_assign_task",
    description="Assign a task to a specific worker",
    inputSchema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "UUID of the task"
            },
            "executor_id": {
                "type": "string",
                "description": "UUID of the executor to assign"
            },
            "agent_id": {
                "type": "string",
                "description": "ID of the agent making the assignment"
            }
        },
        "required": ["task_id", "executor_id", "agent_id"]
    }
)

async def assign_task(args: dict) -> list[TextContent]:
    task_id = args["task_id"]
    executor_id = args["executor_id"]
    agent_id = args["agent_id"]

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

    # 1. Verify task exists and agent owns it
    task = supabase.table("tasks").select("*").eq("id", task_id).single().execute()
    if not task.data:
        return [TextContent(type="text", text='{"error": "Task not found"}')]

    if task.data["agent_id"] != agent_id:
        return [TextContent(type="text", text='{"error": "Not authorized to assign this task"}')]

    if task.data["status"] != "open":
        return [TextContent(type="text", text='{"error": "Task is not open for assignment"}')]

    # 2. Verify executor has applied
    application = supabase.table("applications").select("*").eq(
        "task_id", task_id
    ).eq(
        "executor_id", executor_id
    ).single().execute()

    if not application.data:
        return [TextContent(type="text", text='{"error": "Executor has not applied to this task"}')]

    # 3. Verify executor exists and is active
    executor = supabase.table("executors").select("*").eq("id", executor_id).single().execute()
    if not executor.data:
        return [TextContent(type="text", text='{"error": "Executor not found"}')]

    # 4. Calculate deadline
    from datetime import datetime, timedelta, UTC
    assigned_at = datetime.now(UTC)
    default_hours = task.data.get("time_limit_hours", 4)
    deadline = assigned_at + timedelta(hours=default_hours)

    # 5. Update task
    supabase.table("tasks").update({
        "status": "assigned",
        "assigned_executor_id": executor_id,
        "assigned_at": assigned_at.isoformat(),
        "deadline": deadline.isoformat()
    }).eq("id", task_id).execute()

    # 6. Update application status
    supabase.table("applications").update({
        "status": "accepted"
    }).eq("id", application.data["id"]).execute()

    # 7. Reject other applications
    supabase.table("applications").update({
        "status": "rejected"
    }).eq("task_id", task_id).neq("executor_id", executor_id).execute()

    # 8. TODO: Send notification to worker (Firebase/email)
    # await notify_worker(executor_id, "task_assigned", {...})

    result = {
        "success": True,
        "task_id": task_id,
        "executor_id": executor_id,
        "assigned_at": assigned_at.isoformat(),
        "deadline": deadline.isoformat()
    }

    return [TextContent(type="text", text=json.dumps(result))]
```

## Criterios de Éxito
- [ ] Tool registrado en MCP server
- [ ] Only task owner can assign
- [ ] Only applicants can be assigned
- [ ] Task status updated to "assigned"
- [ ] Deadline calculated correctly
- [ ] Other applications rejected
- [ ] Worker notified (TODO)

## Test Cases
```python
# Test 1: Successful assignment
result = await assign_task({
    "task_id": "open-task-uuid",
    "executor_id": "applicant-executor-uuid",
    "agent_id": "owner-agent-id"
})
assert result["success"] == True
assert result["deadline"] is not None

# Test 2: Not task owner
result = await assign_task({
    "task_id": "task-uuid",
    "executor_id": "executor-uuid",
    "agent_id": "wrong-agent-id"
})
assert "Not authorized" in result["error"]

# Test 3: Executor hasn't applied
result = await assign_task({
    "task_id": "task-uuid",
    "executor_id": "non-applicant-uuid",
    "agent_id": "owner-agent-id"
})
assert "not applied" in result["error"]

# Test 4: Task already assigned
result = await assign_task({
    "task_id": "already-assigned-task",
    "executor_id": "executor-uuid",
    "agent_id": "owner-agent-id"
})
assert "not open" in result["error"]
```

## Side Effects
1. Task status → "assigned"
2. Application status → "accepted"
3. Other applications → "rejected"
4. Worker notification sent (future)
5. Deadline timer started
