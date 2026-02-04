# NOW-011: Implementar em_apply_to_task

## Metadata
- **Prioridad**: P0
- **Fase**: 1 - MCP Server
- **Dependencias**: NOW-008
- **Archivos a modificar**: `mcp_server/server.py`
- **Tiempo estimado**: 1-2 horas

## Descripción
Implementar el tool MCP que permite a un worker aplicar a una tarea disponible.

## Contexto Técnico
- **Framework**: MCP SDK (Python)
- **Database**: Supabase
- **Validaciones**: Task existe, está open, executor no ha aplicado antes

## Input Schema
```json
{
  "task_id": "uuid",
  "executor_id": "uuid",
  "message": "string (optional)"
}
```

## Output Schema
```json
{
  "success": true,
  "application_id": "uuid",
  "task": {
    "id": "uuid",
    "title": "string",
    "bounty_usdc": 5.00
  }
}
```

## Código de Referencia

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
from supabase import create_client
import os

# En server.py, agregar al list_tools:
Tool(
    name="em_apply_to_task",
    description="Apply to an available task as a worker",
    inputSchema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "UUID of the task to apply to"
            },
            "executor_id": {
                "type": "string",
                "description": "UUID of the executor applying"
            },
            "message": {
                "type": "string",
                "description": "Optional message to the agent"
            }
        },
        "required": ["task_id", "executor_id"]
    }
)

# Handler implementation
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "em_apply_to_task":
        return await apply_to_task(arguments)

async def apply_to_task(args: dict) -> list[TextContent]:
    task_id = args["task_id"]
    executor_id = args["executor_id"]
    message = args.get("message", "")

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

    # 1. Verify task exists and is open
    task = supabase.table("tasks").select("*").eq("id", task_id).single().execute()
    if not task.data:
        return [TextContent(type="text", text='{"error": "Task not found"}')]

    if task.data["status"] != "open":
        return [TextContent(type="text", text='{"error": "Task is not open for applications"}')]

    # 2. Check if executor already applied
    existing = supabase.table("applications").select("id").eq("task_id", task_id).eq("executor_id", executor_id).execute()
    if existing.data:
        return [TextContent(type="text", text='{"error": "Already applied to this task"}')]

    # 3. Verify executor exists
    executor = supabase.table("executors").select("id").eq("id", executor_id).single().execute()
    if not executor.data:
        return [TextContent(type="text", text='{"error": "Executor not found"}')]

    # 4. Create application
    application = supabase.table("applications").insert({
        "task_id": task_id,
        "executor_id": executor_id,
        "message": message,
        "status": "pending"
    }).execute()

    result = {
        "success": True,
        "application_id": application.data[0]["id"],
        "task": {
            "id": task.data["id"],
            "title": task.data["title"],
            "bounty_usdc": float(task.data["bounty_usdc"])
        }
    }

    return [TextContent(type="text", text=json.dumps(result))]
```

## Migration Requerida (applications table)
```sql
-- Agregar a migrations si no existe
CREATE TABLE IF NOT EXISTS applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES tasks(id) NOT NULL,
  executor_id UUID REFERENCES executors(id) NOT NULL,
  message TEXT,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(task_id, executor_id)
);

CREATE INDEX idx_applications_task ON applications(task_id);
CREATE INDEX idx_applications_executor ON applications(executor_id);
```

## Criterios de Éxito
- [ ] Tool registrado en MCP server
- [ ] Tabla `applications` creada
- [ ] Validación de task existe y está open
- [ ] Validación de executor existe
- [ ] No permite aplicaciones duplicadas
- [ ] Retorna application_id y task info

## Test Cases
```python
# Test 1: Successful application
result = await apply_to_task({
    "task_id": "valid-task-uuid",
    "executor_id": "valid-executor-uuid",
    "message": "I can do this task"
})
assert result["success"] == True

# Test 2: Task not found
result = await apply_to_task({
    "task_id": "non-existent-uuid",
    "executor_id": "valid-executor-uuid"
})
assert "error" in result

# Test 3: Duplicate application
# Apply twice, second should fail
result = await apply_to_task({...})
result2 = await apply_to_task({...})
assert "Already applied" in result2["error"]
```
