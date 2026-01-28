# NOW-013: Implementar chamba_get_my_tasks

## Metadata
- **Prioridad**: P0
- **Fase**: 1 - MCP Server
- **Dependencias**: NOW-008
- **Archivos a modificar**: `mcp_server/server.py`
- **Tiempo estimado**: 1 hora

## Descripción
Implementar el tool MCP que permite a un worker ver sus tareas (aplicadas, asignadas, completadas).

## Contexto Técnico
- **Filtros**: Por status, por fecha
- **Incluye**: Applications, submissions, earnings
- **Paginación**: Limit/offset

## Input Schema
```json
{
  "executor_id": "uuid",
  "status_filter": "all|applied|assigned|completed|rejected",
  "limit": 50,
  "offset": 0
}
```

## Output Schema
```json
{
  "tasks": [
    {
      "id": "uuid",
      "title": "Take photo of restaurant",
      "task_type": "verification",
      "bounty_usdc": 5.00,
      "status": "assigned",
      "my_status": "in_progress",
      "applied_at": "2026-01-25T09:00:00Z",
      "assigned_at": "2026-01-25T09:30:00Z",
      "submission": null,
      "earnings": null
    }
  ],
  "total_count": 25,
  "stats": {
    "total_completed": 15,
    "total_earned_usdc": 125.50,
    "average_rating": 4.7
  }
}
```

## Código de Referencia

```python
Tool(
    name="chamba_get_my_tasks",
    description="Get tasks for a worker (applied, assigned, completed)",
    inputSchema={
        "type": "object",
        "properties": {
            "executor_id": {
                "type": "string",
                "description": "UUID of the executor"
            },
            "status_filter": {
                "type": "string",
                "enum": ["all", "applied", "assigned", "completed", "rejected"],
                "default": "all"
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "maximum": 100
            },
            "offset": {
                "type": "integer",
                "default": 0
            }
        },
        "required": ["executor_id"]
    }
)

async def get_my_tasks(args: dict) -> list[TextContent]:
    executor_id = args["executor_id"]
    status_filter = args.get("status_filter", "all")
    limit = min(args.get("limit", 50), 100)
    offset = args.get("offset", 0)

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

    # Build query based on filter
    if status_filter == "applied":
        # Tasks I've applied to but not yet assigned
        query = supabase.rpc("get_worker_applications", {
            "p_executor_id": executor_id,
            "p_limit": limit,
            "p_offset": offset
        })
    elif status_filter == "assigned":
        # Tasks currently assigned to me
        query = supabase.table("tasks").select(
            "*, submissions(*)"
        ).eq("assigned_executor_id", executor_id).eq("status", "assigned")
    elif status_filter == "completed":
        # Tasks I've completed
        query = supabase.table("submissions").select(
            "*, tasks(*), payments(*)"
        ).eq("executor_id", executor_id).eq("status", "approved")
    elif status_filter == "rejected":
        # Tasks where my submission was rejected
        query = supabase.table("submissions").select(
            "*, tasks(*)"
        ).eq("executor_id", executor_id).eq("status", "rejected")
    else:
        # All my tasks
        query = supabase.rpc("get_all_worker_tasks", {
            "p_executor_id": executor_id,
            "p_limit": limit,
            "p_offset": offset
        })

    result = query.execute()

    # Get stats
    stats = await get_worker_stats(supabase, executor_id)

    # Format response
    tasks = format_tasks_response(result.data, status_filter)

    response = {
        "tasks": tasks,
        "total_count": len(tasks),
        "stats": stats
    }

    return [TextContent(type="text", text=json.dumps(response))]


async def get_worker_stats(supabase, executor_id: str) -> dict:
    """Get worker statistics"""
    # Completed tasks count
    completed = supabase.table("submissions").select(
        "id", count="exact"
    ).eq("executor_id", executor_id).eq("status", "approved").execute()

    # Total earnings
    earnings = supabase.table("payments").select(
        "amount_usdc"
    ).eq("executor_id", executor_id).eq("status", "completed").execute()

    total_earned = sum(float(p["amount_usdc"]) for p in earnings.data) if earnings.data else 0

    # Average rating
    rating_result = supabase.rpc("calculate_bayesian_score", {
        "p_executor_id": executor_id
    }).execute()

    return {
        "total_completed": completed.count or 0,
        "total_earned_usdc": round(total_earned, 2),
        "average_rating": round(rating_result.data or 50, 1)
    }


def format_tasks_response(data: list, status_filter: str) -> list:
    """Format tasks for response"""
    tasks = []
    for item in data:
        task = {
            "id": item.get("task_id") or item.get("id"),
            "title": item.get("title") or item.get("tasks", {}).get("title"),
            "task_type": item.get("task_type") or item.get("tasks", {}).get("task_type"),
            "bounty_usdc": float(item.get("bounty_usdc") or item.get("tasks", {}).get("bounty_usdc", 0)),
            "status": item.get("status"),
            "my_status": determine_my_status(item, status_filter),
            "applied_at": item.get("created_at"),
            "assigned_at": item.get("assigned_at"),
            "submission": item.get("submissions"),
            "earnings": item.get("payments")
        }
        tasks.append(task)
    return tasks
```

## RPC Function Requerida
```sql
CREATE OR REPLACE FUNCTION get_all_worker_tasks(
  p_executor_id UUID,
  p_limit INTEGER DEFAULT 50,
  p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
  task_id UUID,
  title TEXT,
  task_type TEXT,
  bounty_usdc DECIMAL,
  task_status TEXT,
  my_status TEXT,
  applied_at TIMESTAMPTZ,
  assigned_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.id AS task_id,
    t.title,
    t.task_type,
    t.bounty_usdc,
    t.status AS task_status,
    CASE
      WHEN s.status = 'approved' THEN 'completed'
      WHEN s.status = 'rejected' THEN 'rejected'
      WHEN s.status = 'pending_review' THEN 'submitted'
      WHEN t.assigned_executor_id = p_executor_id THEN 'assigned'
      WHEN a.id IS NOT NULL THEN 'applied'
      ELSE 'unknown'
    END AS my_status,
    a.created_at AS applied_at,
    t.assigned_at,
    s.reviewed_at AS completed_at
  FROM tasks t
  LEFT JOIN applications a ON a.task_id = t.id AND a.executor_id = p_executor_id
  LEFT JOIN submissions s ON s.task_id = t.id AND s.executor_id = p_executor_id
  WHERE a.executor_id = p_executor_id
     OR t.assigned_executor_id = p_executor_id
  ORDER BY COALESCE(a.created_at, t.assigned_at) DESC
  LIMIT p_limit
  OFFSET p_offset;
END;
$$;
```

## Criterios de Éxito
- [ ] Tool registrado en MCP server
- [ ] Filtro por status funciona
- [ ] Paginación funciona
- [ ] Stats calculados correctamente
- [ ] Incluye submissions y payments
- [ ] Performance < 200ms para 50 tasks

## Test Cases
```python
# Test 1: Get all tasks
result = await get_my_tasks({
    "executor_id": "executor-uuid"
})
assert "tasks" in result
assert "stats" in result

# Test 2: Filter by completed
result = await get_my_tasks({
    "executor_id": "executor-uuid",
    "status_filter": "completed"
})
assert all(t["my_status"] == "completed" for t in result["tasks"])

# Test 3: Pagination
result = await get_my_tasks({
    "executor_id": "executor-uuid",
    "limit": 10,
    "offset": 10
})
assert len(result["tasks"]) <= 10
```
