# NOW-012: Implementar chamba_submit_work

## Metadata
- **Prioridad**: P0
- **Fase**: 1 - MCP Server
- **Dependencias**: NOW-011
- **Archivos a modificar**: `mcp_server/server.py`
- **Tiempo estimado**: 2-3 horas

## Descripción
Implementar el tool MCP que permite a un worker enviar evidencia de trabajo completado.

## Contexto Técnico
- **Evidence**: JSON con URLs de fotos/videos en Supabase Storage
- **Validation**: Schema de evidence debe coincidir con task.evidence_required
- **Triggers**: Puede triggerear partial payout y verificación automática

## Input Schema
```json
{
  "task_id": "uuid",
  "executor_id": "uuid",
  "evidence": {
    "photos": ["https://...signed-url-1", "https://...signed-url-2"],
    "gps": {
      "lat": 25.7617,
      "lng": -80.1918,
      "accuracy": 10
    },
    "timestamp": "2026-01-25T10:30:00Z",
    "notes": "Completed as requested"
  }
}
```

## Output Schema
```json
{
  "success": true,
  "submission_id": "uuid",
  "status": "pending_review",
  "verification_tier": "auto|ai|agent|human",
  "partial_payout": {
    "released": true,
    "amount_usdc": 1.50
  }
}
```

## Código de Referencia

```python
Tool(
    name="chamba_submit_work",
    description="Submit completed work with evidence for a task",
    inputSchema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "UUID of the task"
            },
            "executor_id": {
                "type": "string",
                "description": "UUID of the executor submitting"
            },
            "evidence": {
                "type": "object",
                "description": "Evidence JSON matching task requirements",
                "properties": {
                    "photos": {"type": "array", "items": {"type": "string"}},
                    "gps": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "lng": {"type": "number"},
                            "accuracy": {"type": "number"}
                        }
                    },
                    "timestamp": {"type": "string"},
                    "notes": {"type": "string"}
                }
            }
        },
        "required": ["task_id", "executor_id", "evidence"]
    }
)

async def submit_work(args: dict) -> list[TextContent]:
    task_id = args["task_id"]
    executor_id = args["executor_id"]
    evidence = args["evidence"]

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

    # 1. Verify task exists and is assigned to this executor
    task = supabase.table("tasks").select("*").eq("id", task_id).single().execute()
    if not task.data:
        return [TextContent(type="text", text='{"error": "Task not found"}')]

    if task.data["status"] != "assigned":
        return [TextContent(type="text", text='{"error": "Task is not in assigned status"}')]

    if task.data.get("assigned_executor_id") != executor_id:
        return [TextContent(type="text", text='{"error": "Task not assigned to this executor"}')]

    # 2. Validate evidence schema
    evidence_required = task.data.get("evidence_required", {})
    validation_result = validate_evidence_schema(evidence, evidence_required)
    if not validation_result["valid"]:
        return [TextContent(type="text", text=json.dumps({"error": validation_result["reason"]}))]

    # 3. Run auto-verification checks
    auto_checks = await run_auto_verification(evidence, task.data)

    # 4. Determine verification tier
    verification_tier = determine_verification_tier(auto_checks)

    # 5. Create submission
    submission = supabase.table("submissions").insert({
        "task_id": task_id,
        "executor_id": executor_id,
        "evidence": evidence,
        "status": "pending_review",
        "verification_tier": verification_tier,
        "auto_check_results": auto_checks
    }).execute()

    # 6. Release partial payout if configured
    partial_payout = None
    if task.data.get("partial_payout_percent", 0) > 0:
        partial_amount = float(task.data["bounty_usdc"]) * task.data["partial_payout_percent"] / 100
        partial_payout = await release_partial_payout(task_id, submission.data[0]["id"], partial_amount)

    # 7. Update task status
    supabase.table("tasks").update({"status": "pending_review"}).eq("id", task_id).execute()

    result = {
        "success": True,
        "submission_id": submission.data[0]["id"],
        "status": "pending_review",
        "verification_tier": verification_tier,
        "partial_payout": partial_payout
    }

    return [TextContent(type="text", text=json.dumps(result))]


def validate_evidence_schema(evidence: dict, required: dict) -> dict:
    """Validate that evidence matches required schema"""
    # Check required photos
    if required.get("photos_min", 0) > 0:
        photos = evidence.get("photos", [])
        if len(photos) < required["photos_min"]:
            return {"valid": False, "reason": f"Minimum {required['photos_min']} photos required"}

    # Check GPS if required
    if required.get("gps_required", False):
        if "gps" not in evidence or not evidence["gps"].get("lat"):
            return {"valid": False, "reason": "GPS location required"}

    return {"valid": True}


async def run_auto_verification(evidence: dict, task: dict) -> dict:
    """Run automated verification checks"""
    checks = {}

    # GPS check
    if evidence.get("gps") and task.get("location"):
        distance = calculate_distance(
            evidence["gps"]["lat"], evidence["gps"]["lng"],
            task["location"]["lat"], task["location"]["lng"]
        )
        checks["gps_valid"] = distance <= task.get("radius_meters", 500)
        checks["gps_distance"] = distance

    # Timestamp check
    if evidence.get("timestamp"):
        photo_time = parse_datetime(evidence["timestamp"])
        checks["timestamp_valid"] = (datetime.now(UTC) - photo_time).total_seconds() < 300  # 5 min

    # Duplicate check (hash-based)
    if evidence.get("photos"):
        checks["duplicate_check"] = await check_photo_duplicates(evidence["photos"])

    return checks


def determine_verification_tier(checks: dict) -> str:
    """Determine which verification tier based on auto checks"""
    score = sum([
        checks.get("gps_valid", False) * 0.3,
        checks.get("timestamp_valid", False) * 0.3,
        checks.get("duplicate_check", {}).get("is_unique", False) * 0.4
    ])

    if score >= 0.95:
        return "auto"
    elif score >= 0.70:
        return "ai"
    elif score >= 0.50:
        return "agent"
    else:
        return "human"
```

## Criterios de Éxito
- [ ] Tool registrado en MCP server
- [ ] Evidence schema validation funciona
- [ ] Auto-verification checks ejecutan
- [ ] Verification tier se determina correctamente
- [ ] Submission se crea en DB
- [ ] Partial payout se libera si configurado
- [ ] Task status se actualiza

## Test Cases
```python
# Test 1: Successful submission
result = await submit_work({
    "task_id": "assigned-task-uuid",
    "executor_id": "correct-executor-uuid",
    "evidence": {
        "photos": ["url1", "url2"],
        "gps": {"lat": 25.76, "lng": -80.19},
        "timestamp": "2026-01-25T10:30:00Z"
    }
})
assert result["success"] == True

# Test 2: Missing required evidence
result = await submit_work({
    "task_id": "task-requiring-3-photos",
    "executor_id": "executor-uuid",
    "evidence": {"photos": ["url1"]}
})
assert "error" in result

# Test 3: Wrong executor
result = await submit_work({
    "task_id": "task-assigned-to-other",
    "executor_id": "wrong-executor-uuid",
    "evidence": {...}
})
assert "not assigned" in result["error"]
```
