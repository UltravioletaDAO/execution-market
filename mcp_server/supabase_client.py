"""
Execution Market MCP Server - Supabase Client

Database operations for the Execution Market MCP server.
"""

import os
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# Environment variables — resolved lazily in get_client() to avoid
# import-time failures when SUPABASE_URL is not set (e.g. in tests).


def _get_url() -> str:
    url = os.environ.get(
        "SUPABASE_URL",
        "https://test.supabase.co" if os.environ.get("TESTING") else "",
    )
    if not url:
        raise RuntimeError("SUPABASE_URL environment variable is required")
    return url


def _get_key() -> str:
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
        "SUPABASE_SERVICE_KEY"
    )

    if service_role_key:
        return service_role_key

    # No service role key found — check if we're in production
    environment = os.environ.get("EM_ENVIRONMENT", "").lower()
    is_production = environment in ("production", "prod")

    if is_production:
        raise ValueError(
            "CRITICAL: SUPABASE_SERVICE_ROLE_KEY is NOT set in production. "
            "The server MUST use a service role key (not anon key) to bypass RLS. "
            "Set SUPABASE_SERVICE_ROLE_KEY in your ECS task definition secrets."
        )

    # Non-production: fall back to anon key with a loud warning
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    if anon_key:
        logger.warning(
            "SECURITY_AUDIT action=supabase_key.anon_fallback "
            "SUPABASE_SERVICE_ROLE_KEY is not set — falling back to SUPABASE_ANON_KEY. "
            "This is INSECURE for production: RLS policies will block server operations. "
            "Set EM_ENVIRONMENT=production to make this a fatal error."
        )
        return anon_key

    raise ValueError(
        "SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY environment variable required"
    )


# Keep module-level references for backward compatibility but don't fail on import
SUPABASE_URL: str = ""  # populated lazily
SUPABASE_KEY: str = ""  # populated lazily

# Initialize Supabase client
_client: Optional[Client] = None
_applications_table_name: Optional[str] = None
logger = logging.getLogger(__name__)


def get_client() -> Client:
    """Get or create Supabase client (resolves env vars lazily)."""
    global _client, SUPABASE_URL, SUPABASE_KEY
    if _client is None:
        SUPABASE_URL = _get_url()
        SUPABASE_KEY = _get_key()
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def close_client() -> None:
    """Close the Supabase client and release resources."""
    global _client
    if _client is not None:
        try:
            # postgrest-py keeps an httpx client internally
            if hasattr(_client, "postgrest") and hasattr(_client.postgrest, "aclose"):
                import asyncio

                asyncio.get_event_loop().create_task(_client.postgrest.aclose())
        except Exception:
            pass
        _client = None
        logger.info("Supabase client closed")


# Alias for backwards compatibility
get_supabase_client = get_client


def _resolve_applications_table(client: Client) -> str:
    """
    Resolve canonical applications table name with backward compatibility.

    Prefer `task_applications` (schema canonical); fall back to legacy
    `applications` when running against older databases.
    """
    global _applications_table_name

    if _applications_table_name:
        return _applications_table_name

    for table_name in ("task_applications", "applications"):
        try:
            client.table(table_name).select("id").limit(1).execute()
            _applications_table_name = table_name
            if table_name != "task_applications":
                logger.warning(
                    "Using legacy applications table '%s'. Migrate to 'task_applications'.",
                    table_name,
                )
            return _applications_table_name
        except Exception:
            continue

    _applications_table_name = "task_applications"
    logger.warning(
        "Could not verify applications table existence. Defaulting to '%s'.",
        _applications_table_name,
    )
    return _applications_table_name


def get_applications_table_name() -> str:
    """Public helper for modules that need the resolved applications table."""
    return _resolve_applications_table(get_client())


def _extract_missing_column(error_msg: str) -> Optional[str]:
    """
    Extract missing column name from PostgREST schema errors.

    Example:
    "Could not find the 'assigned_at' column of 'tasks' in the schema cache"
    """
    match = re.search(r"Could not find the '([^']+)' column", error_msg)
    if match:
        return match.group(1)
    return None


# ============== TASK OPERATIONS ==============


async def create_task(
    agent_id: str,
    title: str,
    instructions: str,
    category: str,
    bounty_usd: float,
    deadline: datetime,
    evidence_required: List[str],
    evidence_optional: Optional[List[str]] = None,
    location_hint: Optional[str] = None,
    min_reputation: int = 0,
    payment_token: str = "USDC",
    payment_network: str = "base",
    target_executor_type: Optional[str] = None,
    skills_required: Optional[List[str]] = None,
    location_lat: Optional[float] = None,
    location_lng: Optional[float] = None,
    location_radius_km: Optional[float] = None,
    skill_version: Optional[str] = None,
    arbiter_mode: str = "manual",
    idempotency_key: Optional[str] = None,
    gps_required: Optional[bool] = None,
    geo_match_mode: Optional[str] = None,
    location_radius_m: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a new task in the database.

    arbiter_mode controls Ring 2 evidence verification:
        'manual' (default): agent reviews and approves submissions
        'auto':   ArbiterService releases/refunds without agent intervention
        'hybrid': arbiter recommends + agent confirms
    """
    client = get_client()

    evidence_schema: Dict[str, Any] = {
        "required": evidence_required,
        "optional": evidence_optional or [],
    }
    if gps_required is not None:
        evidence_schema["gps_required"] = gps_required

    task_data = {
        "agent_id": agent_id,
        "title": title,
        "instructions": instructions,
        "category": category,
        "bounty_usd": bounty_usd,
        "deadline": deadline.isoformat(),
        "evidence_schema": evidence_schema,
        "location_hint": location_hint,
        "min_reputation": min_reputation,
        "payment_token": payment_token,
        "payment_network": payment_network,
        "status": "published",
        "arbiter_mode": arbiter_mode,
        "arbiter_enabled": arbiter_mode != "manual",
    }

    if target_executor_type:
        task_data["target_executor_type"] = target_executor_type
    if skills_required:
        task_data["required_capabilities"] = skills_required
    if location_lat is not None and location_lng is not None:
        task_data["location_lat"] = location_lat
        task_data["location_lng"] = location_lng
    if location_radius_km is not None:
        task_data["location_radius_km"] = location_radius_km
    if skill_version:
        task_data["skill_version"] = skill_version
    if idempotency_key:
        task_data["idempotency_key"] = idempotency_key
    if geo_match_mode is not None:
        task_data["geo_match_mode"] = geo_match_mode
    if location_radius_m is not None:
        task_data["location_radius_m"] = location_radius_m

    result = client.table("tasks").insert(task_data).execute()

    if result.data and len(result.data) > 0:
        return result.data[0]
    raise Exception("Failed to create task")


async def get_task_by_idempotency_key(
    idempotency_key: str, agent_id: str
) -> Optional[Dict[str, Any]]:
    """Look up an existing task by idempotency key and agent.

    Returns the task dict if found, None otherwise.
    """
    client = get_client()
    result = (
        client.table("tasks")
        .select("*")
        .eq("idempotency_key", idempotency_key)
        .eq("agent_id", agent_id)
        .limit(1)
        .execute()
    )
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


async def get_tasks(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Get tasks with optional filters."""
    client = get_client()

    query = client.table("tasks").select(
        "*, executor:executors(id, display_name, reputation_score)"
    )

    if agent_id:
        query = query.eq("agent_id", agent_id)
    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)

    # Get total count first
    count_query = client.table("tasks").select("id", count="exact")
    if agent_id:
        count_query = count_query.eq("agent_id", agent_id)
    if status:
        count_query = count_query.eq("status", status)
    if category:
        count_query = count_query.eq("category", category)

    count_result = count_query.execute()
    total = count_result.count if count_result.count else 0

    # Get paginated results
    result = (
        query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    )

    return {
        "total": total,
        "count": len(result.data) if result.data else 0,
        "offset": offset,
        "tasks": result.data or [],
        "has_more": total > offset + (len(result.data) if result.data else 0),
    }


async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get a single task by ID."""
    client = get_client()

    try:
        result = (
            client.table("tasks")
            .select(
                "*, executor:executors(id, display_name, wallet_address, reputation_score, erc8004_agent_id)"
            )
            .eq("id", task_id)
            .single()
            .execute()
        )
        task_data = result.data
    except Exception:
        # .single() throws when 0 rows match
        return None

    if not task_data:
        return None

    # Enrich with escrow_status from the escrows table
    try:
        esc = (
            client.table("escrows")
            .select("status")
            .eq("task_id", task_id)
            .limit(1)
            .execute()
        )
        if esc.data:
            task_data["escrow_status"] = esc.data[0].get("status")
        else:
            task_data["escrow_status"] = None
    except Exception:
        task_data["escrow_status"] = None

    return task_data


async def update_task(task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update a task."""
    # Lifecycle state machine validation (log-only, non-blocking)
    if "status" in updates:
        try:
            from audit.lifecycle_validator import validate_transition

            current_task = await get_task(task_id)
            current_status = (current_task or {}).get("status", "")
            if current_status and not validate_transition(
                current_status, updates["status"], task_id
            ):
                logger.warning(
                    "Detected illegal transition for task %s: %s -> %s",
                    task_id,
                    current_status,
                    updates["status"],
                )
        except Exception as e:
            logger.debug("Lifecycle validation skipped: %s", e)

    client = get_client()
    pending_updates = dict(updates)

    # Handle schema drift by removing unknown columns and retrying.
    while pending_updates:
        try:
            result = (
                client.table("tasks")
                .update(pending_updates)
                .eq("id", task_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return result.data[0]
            raise Exception("Failed to update task")
        except Exception as e:
            missing_column = _extract_missing_column(str(e))
            if missing_column and missing_column in pending_updates:
                logger.warning(
                    "tasks.%s missing in current schema; retrying update for task %s without it",
                    missing_column,
                    task_id,
                )
                pending_updates.pop(missing_column, None)
                continue
            raise

    raise Exception(
        "Failed to update task: no compatible columns found in current schema"
    )


async def cancel_task(task_id: str, agent_id: str) -> Dict[str, Any]:
    """Cancel a task (published or accepted, owned by agent).

    The MCP tool and REST API perform their own status guards before calling
    this function, but we keep a basic safety check here as well.
    """
    get_client()

    # Verify ownership and status
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")
    if (task.get("agent_id") or "").lower() != (agent_id or "").lower():
        raise Exception("Not authorized to cancel this task")
    if task["status"] not in ("published", "accepted"):
        raise Exception(f"Cannot cancel task with status: {task['status']}")

    return await update_task(task_id, {"status": "cancelled"})


# ============== APPLICATION OPERATIONS ==============


async def get_applications_for_task(task_id: str) -> List[Dict[str, Any]]:
    """Get all applications for a task from the task_applications table."""
    client = get_client()
    table = _resolve_applications_table(client)

    result = (
        client.table(table)
        .select("id, task_id, executor_id, message, status, created_at")
        .eq("task_id", task_id)
        .order("created_at", desc=False)
        .execute()
    )

    apps = result.data or []

    # Enrich with executor wallet address (needed for agent-signed escrow)
    for app in apps:
        executor_id = app.get("executor_id")
        if executor_id:
            try:
                exec_result = (
                    client.table("executors")
                    .select("wallet_address, display_name")
                    .eq("id", executor_id)
                    .limit(1)
                    .execute()
                )
                if exec_result.data:
                    app["wallet_address"] = exec_result.data[0].get(
                        "wallet_address", ""
                    )
                    app["display_name"] = exec_result.data[0].get("display_name", "")
            except Exception:
                pass

    return apps


# ============== SUBMISSION OPERATIONS ==============


async def get_submissions_for_task(task_id: str) -> List[Dict[str, Any]]:
    """Get all submissions for a task."""
    client = get_client()

    result = (
        client.table("submissions")
        .select(
            "*, executor:executors(id, display_name, wallet_address, reputation_score, erc8004_agent_id)"
        )
        .eq("task_id", task_id)
        .order("submitted_at", desc=True)
        .execute()
    )

    return result.data or []


async def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    """Get a single submission by ID."""
    client = get_client()

    result = (
        client.table("submissions")
        .select(
            "*, task:tasks(*), executor:executors(id, display_name, wallet_address, reputation_score, erc8004_agent_id)"
        )
        .eq("id", submission_id)
        .single()
        .execute()
    )

    return result.data


async def update_submission_auto_check(
    submission_id: str,
    auto_check_passed: bool,
    auto_check_details: Dict[str, Any],
) -> None:
    """
    Update a submission with automated verification results.

    Populates the auto_check_passed and auto_check_details columns.
    Non-blocking: logs errors but never raises.
    """
    client = get_client()
    try:
        client.table("submissions").update(
            {
                "auto_check_passed": auto_check_passed,
                "auto_check_details": auto_check_details,
            }
        ).eq("id", submission_id).execute()
    except Exception as e:
        # Non-blocking — some schemas may not have these columns yet
        logger.warning(
            "Failed to update auto_check for submission %s: %s",
            submission_id,
            e,
        )


async def get_existing_perceptual_hashes(
    exclude_task_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Query recent submissions with perceptual hashes for duplicate detection.

    Returns list of dicts: [{"id": sub_id, "hashes": {...}, "task_id": ...}]
    """
    client = get_client()
    try:
        query = (
            client.table("submissions")
            .select("id, task_id, perceptual_hashes")
            .not_.is_("perceptual_hashes", "null")
            .order("submitted_at", desc=True)
            .limit(limit)
        )
        if exclude_task_id:
            query = query.neq("task_id", exclude_task_id)

        result = query.execute()
        return [
            {
                "id": row["id"],
                "task_id": row.get("task_id"),
                "hashes": row["perceptual_hashes"],
            }
            for row in (result.data or [])
            if row.get("perceptual_hashes")
        ]
    except Exception as e:
        logger.warning("Failed to query perceptual hashes: %s", e)
        return []


async def update_submission_perceptual_hashes(
    submission_id: str,
    hashes: Dict[str, Any],
) -> None:
    """Store perceptual hash data for a submission."""
    client = get_client()
    try:
        client.table("submissions").update({"perceptual_hashes": hashes}).eq(
            "id", submission_id
        ).execute()
    except Exception as e:
        logger.warning(
            "Failed to store perceptual hashes for submission %s: %s",
            submission_id,
            e,
        )


async def update_submission_ai_verification(
    submission_id: str,
    result: Dict[str, Any],
) -> None:
    """Store AI verification result for a submission."""
    client = get_client()
    try:
        client.table("submissions").update({"ai_verification_result": result}).eq(
            "id", submission_id
        ).execute()
    except Exception as e:
        logger.warning(
            "Failed to store AI verification result for submission %s: %s",
            submission_id,
            e,
        )


async def log_verification_inference(
    submission_id: str,
    task_id: str,
    check_name: str,
    tier: str,
    provider: str,
    model: str,
    prompt_version: str,
    prompt_hash: str,
    prompt_text: str,
    response_text: str,
    parsed_decision: Optional[str] = None,
    parsed_confidence: Optional[float] = None,
    parsed_issues: Optional[List] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None,
    estimated_cost_usd: Optional[float] = None,
    task_category: Optional[str] = None,
    evidence_types: Optional[List[str]] = None,
    photo_count: Optional[int] = None,
    commitment_hash: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Log a verification inference to the audit trail.

    Returns the inference ID if successful, None on failure.
    Non-blocking: logs errors but never raises.
    """
    client = get_client()
    try:
        row = {
            "submission_id": submission_id,
            "task_id": task_id,
            "check_name": check_name,
            "tier": tier,
            "provider": provider,
            "model": model,
            "prompt_version": prompt_version,
            "prompt_hash": prompt_hash,
            "prompt_text": prompt_text,
            "response_text": response_text,
            "parsed_decision": parsed_decision,
            "parsed_confidence": float(parsed_confidence)
            if parsed_confidence is not None
            else None,
            "parsed_issues": parsed_issues or [],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "estimated_cost_usd": float(estimated_cost_usd)
            if estimated_cost_usd is not None
            else None,
            "task_category": task_category,
            "evidence_types": evidence_types,
            "photo_count": photo_count,
            "commitment_hash": commitment_hash,
            "metadata": metadata or {},
        }
        # Remove None values to let DB defaults apply
        row = {k: v for k, v in row.items() if v is not None}

        result = client.table("verification_inferences").insert(row).execute()
        if result.data:
            return result.data[0].get("id")
        return None
    except Exception as e:
        logger.warning(
            "Failed to log verification inference for submission %s: %s",
            submission_id,
            e,
        )
        return None


async def get_inferences_for_submission(
    submission_id: str,
) -> List[Dict[str, Any]]:
    """
    Get all verification inferences for a submission.

    Returns list of inference records ordered by creation time.
    """
    client = get_client()
    try:
        result = (
            client.table("verification_inferences")
            .select("*")
            .eq("submission_id", submission_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(
            "Failed to get inferences for submission %s: %s",
            submission_id,
            e,
        )
        return []


async def update_inference_agent_feedback(
    submission_id: str,
    agent_decision: str,
    agent_notes: Optional[str] = None,
) -> int:
    """
    Update all inferences for a submission with agent's actual decision.

    Sets agent_agreed based on whether AI decision matches agent decision.
    Returns count of updated rows.
    """
    client = get_client()
    try:
        inferences = await get_inferences_for_submission(submission_id)
        updated = 0
        for inf in inferences:
            ai_decision = inf.get("parsed_decision")
            # Map agent verdict to comparable decision
            agent_comparable = (
                "approved" if agent_decision in ("accepted", "approved") else "rejected"
            )
            agreed = ai_decision == agent_comparable if ai_decision else None

            client.table("verification_inferences").update(
                {
                    "agent_agreed": agreed,
                    "agent_decision": agent_decision,
                    "agent_notes": agent_notes,
                }
            ).eq("id", inf["id"]).execute()
            updated += 1

        return updated
    except Exception as e:
        logger.warning(
            "Failed to update inference feedback for submission %s: %s",
            submission_id,
            e,
        )
        return 0


async def auto_approve_submission(
    submission_id: str,
    score: float,
    agent_notes: str,
) -> bool:
    """
    Auto-approve a submission if it hasn't been reviewed yet.

    Sets agent_verdict='accepted' only when current verdict is null or 'pending'.
    Returns True if the submission was auto-approved.
    """
    client = get_client()
    try:
        # Fetch current verdict
        current = (
            client.table("submissions")
            .select("agent_verdict, task_id")
            .eq("id", submission_id)
            .single()
            .execute()
        )
        if not current.data:
            return False

        verdict = current.data.get("agent_verdict")
        if verdict not in (None, "pending"):
            logger.info(
                "Skipping auto-approve for %s: already reviewed (verdict=%s)",
                submission_id,
                verdict,
            )
            return False

        # Guard: check the parent task is still in an approvable state
        task_id = current.data.get("task_id")
        if task_id:
            try:
                task_result = (
                    client.table("tasks")
                    .select("status")
                    .eq("id", task_id)
                    .limit(1)
                    .execute()
                )
                task_status = (
                    task_result.data[0].get("status", "") if task_result.data else ""
                )
                non_approvable = {"cancelled", "expired", "completed"}
                if task_status in non_approvable:
                    logger.info(
                        "Skipping auto-approve for %s: task %s is %s",
                        submission_id,
                        task_id,
                        task_status,
                    )
                    return False
            except Exception as e:
                logger.warning(
                    "Could not verify task status for auto-approve %s: %s",
                    submission_id,
                    e,
                )

        client.table("submissions").update(
            {
                "agent_verdict": "accepted",
                "agent_notes": agent_notes,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", submission_id).execute()

        logger.info(
            "Auto-approved submission %s with score %.3f",
            submission_id,
            score,
        )
        return True

    except Exception as e:
        logger.warning(
            "Failed to auto-approve submission %s: %s",
            submission_id,
            e,
        )
        return False


async def update_submission(
    submission_id: str,
    agent_id: str,
    verdict: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a submission with agent's verdict."""
    client = get_client()

    # Get submission and verify authorization
    submission = await get_submission(submission_id)
    if not submission:
        raise Exception(f"Submission {submission_id} not found")

    task = submission.get("task")
    if not task or (task.get("agent_id") or "").lower() != (agent_id or "").lower():
        raise Exception("Not authorized to update this submission")

    # Update submission
    updates = {
        "agent_verdict": verdict,
        "agent_notes": notes,
        "verified_at": datetime.now(timezone.utc).isoformat()
        if verdict == "accepted"
        else None,
    }

    result = (
        client.table("submissions").update(updates).eq("id", submission_id).execute()
    )

    if result.data and len(result.data) > 0:
        # If accepted, also update task status
        if verdict == "accepted":
            await update_task(
                task["id"],
                {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Update executor reputation
            await _update_executor_reputation(
                submission["executor_id"],
                task["id"],
                delta=10,  # +10 for completed task
                reason="Task completed successfully",
            )

        # If rejected, decide based on severity (passed via notes prefix or separate field):
        # - minor rejection: worker can resubmit → in_progress (same worker)
        # - major rejection: task returns to pool → published (clear executor)
        elif verdict == "rejected":
            current_status = task.get("status", "")
            rejection_notes = notes or ""
            is_major = rejection_notes.startswith("[MAJOR]")

            if current_status in ("submitted", "verifying", "in_progress"):
                if is_major:
                    # Major: return task to public pool for new workers
                    await update_task(
                        task["id"],
                        {
                            "status": "published",
                            "executor_id": None,
                            "assigned_at": None,
                        },
                    )
                else:
                    # Minor: same worker can resubmit
                    await update_task(task["id"], {"status": "in_progress"})

        return result.data[0]

    raise Exception("Failed to update submission")


async def _update_executor_reputation(
    executor_id: str,
    task_id: str,
    delta: int,
    reason: str,
) -> None:
    """Update executor's reputation score."""
    client = get_client()

    # Get current score
    executor = (
        client.table("executors")
        .select("reputation_score")
        .eq("id", executor_id)
        .single()
        .execute()
    )
    if not executor.data:
        return

    current_score = executor.data.get("reputation_score", 0)
    new_score = min(100, max(0, current_score + delta))

    client.table("executors").update({"reputation_score": new_score}).eq(
        "id", executor_id
    ).execute()
    client.table("reputation_log").insert(
        {
            "executor_id": executor_id,
            "task_id": task_id,
            "delta": delta,
            "new_score": new_score,
            "reason": reason,
        }
    ).execute()


# ============== EXECUTOR OPERATIONS ==============


async def get_executor_stats(executor_id: str) -> Optional[Dict[str, Any]]:
    """Get executor statistics."""
    client = get_client()

    result = (
        client.table("executors")
        .select(
            "id, display_name, wallet_address, reputation_score, tasks_completed, tasks_disputed"
        )
        .eq("id", executor_id)
        .single()
        .execute()
    )

    return result.data


# ============== WORKER OPERATIONS ==============


async def apply_to_task(
    task_id: str,
    executor_id: str,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Worker applies to a task."""
    client = get_client()
    applications_table = _resolve_applications_table(client)

    # Get task to verify it's available
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")
    if task["status"] != "published":
        raise Exception(f"Task is not available (status: {task['status']})")

    # Get executor to check reputation
    try:
        executor = (
            client.table("executors")
            .select("*")
            .eq("id", executor_id)
            .single()
            .execute()
        )
    except Exception:
        raise Exception(f"Executor {executor_id} not found")
    if not executor.data:
        raise Exception(f"Executor {executor_id} not found")

    # Self-application guard: agent cannot apply to its own task
    # Handles both wallet-address agent_ids and numeric ERC-8004 agent_ids
    executor_wallet = (executor.data.get("wallet_address") or "").lower()
    executor_agent_id = str(executor.data.get("erc8004_agent_id") or "")
    task_agent_id = str(task.get("agent_id") or "").lower()

    is_self = False
    # Case 1: wallet matches (case-insensitive)
    if executor_wallet and task_agent_id and executor_wallet == task_agent_id:
        is_self = True
    # Case 2: executor's ERC-8004 ID matches task's agent_id (numeric comparison)
    if executor_agent_id and task_agent_id and executor_agent_id == task_agent_id:
        is_self = True

    if is_self:
        raise Exception(
            "Cannot apply to your own task: executor wallet matches task agent"
        )

    # Check minimum reputation
    min_rep = task.get("min_reputation", 0)
    executor_rep = executor.data.get("reputation_score", 0)
    if executor_rep < min_rep:
        raise Exception(
            f"Insufficient reputation. Required: {min_rep}, yours: {executor_rep}"
        )

    # Check for existing application
    existing = (
        client.table(applications_table)
        .select("*")
        .eq("task_id", task_id)
        .eq("executor_id", executor_id)
        .execute()
    )

    if existing.data and len(existing.data) > 0:
        raise Exception("Already applied to this task")

    # Create application
    application_data = {
        "task_id": task_id,
        "executor_id": executor_id,
        "message": message,
        "status": "pending",
    }
    pending_application_data = dict(application_data)
    while pending_application_data:
        try:
            result = (
                client.table(applications_table)
                .insert(pending_application_data)
                .execute()
            )
            break
        except Exception as e:
            error_msg = str(e)
            # Catch unique constraint violation (PostgreSQL 23505) —
            # race condition where two agents insert between the read-check above.
            if "duplicate key" in error_msg or "23505" in error_msg:
                raise Exception("Already applied to this task") from e
            missing_column = _extract_missing_column(error_msg)
            if missing_column and missing_column in pending_application_data:
                logger.warning(
                    "%s.%s missing in current schema; retrying application insert without it",
                    applications_table,
                    missing_column,
                )
                pending_application_data.pop(missing_column, None)
                continue
            raise
    else:
        raise Exception("Failed to create application: no compatible columns found")

    if result.data and len(result.data) > 0:
        return {
            "application": result.data[0],
            "task": task,
            "executor": executor.data,
        }

    raise Exception("Failed to create application")


async def submit_work(
    task_id: str,
    executor_id: str,
    evidence: Dict[str, Any],
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Worker submits completed work."""
    client = get_client()

    # Get task
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")

    # Verify executor is assigned
    if task.get("executor_id") != executor_id:
        raise Exception("You are not assigned to this task")

    # Reject submissions past the task deadline
    task_deadline = task.get("deadline")
    if task_deadline:
        try:
            if isinstance(task_deadline, str):
                deadline_dt = datetime.fromisoformat(
                    task_deadline.replace("Z", "+00:00")
                )
            else:
                deadline_dt = task_deadline
            if datetime.now(timezone.utc) > deadline_dt:
                raise Exception(
                    "Task deadline has passed. Cannot submit or resubmit evidence."
                )
        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse deadline '%s': %s — allowing submission",
                task_deadline,
                e,
            )

    if task["status"] not in ["accepted", "in_progress"]:
        raise Exception(
            f"Task is not in a submittable state (status: {task['status']})"
        )

    # Validate required evidence
    required = task.get("evidence_schema", {}).get("required", [])
    missing = [r for r in required if r not in evidence]
    if missing:
        raise Exception(f"Missing required evidence: {', '.join(missing)}")

    # --- Escrow validation: reject submission if escrow not funded on-chain ---
    payment_mode = os.environ.get("EM_PAYMENT_MODE", "fase1")
    if payment_mode != "fase1":
        _FUNDED_ESCROW_STATUSES = {
            "deposited",
            "funded",
            "locked",
            "active",
            "partial_released",
        }
        try:
            esc_result = (
                client.table("escrows")
                .select("status,expires_at")
                .eq("task_id", task_id)
                .limit(1)
                .execute()
            )
            esc = esc_result.data[0] if esc_result.data else None
        except Exception as e:
            logger.warning("Escrow lookup failed for task %s: %s", task_id, e)
            esc = None

        if not esc:
            try:
                from integrations.x402.payment_events import log_payment_event

                await log_payment_event(
                    task_id=task_id,
                    event_type="escrow_validation_failed",
                    status="blocked",
                    metadata={
                        "action": "submit_work",
                        "escrow_status": "none",
                        "executor_id": executor_id,
                        "reason": "No escrow record found",
                    },
                )
            except Exception:
                pass  # Don't let logging failure block the validation
            raise Exception(
                "Cannot submit evidence: no escrow record found. "
                "The agent must fund this task before you can submit."
            )
        esc_status = (esc.get("status") or "").lower().strip()
        if esc_status not in _FUNDED_ESCROW_STATUSES:
            try:
                from integrations.x402.payment_events import log_payment_event

                await log_payment_event(
                    task_id=task_id,
                    event_type="escrow_validation_failed",
                    status="blocked",
                    metadata={
                        "action": "submit_work",
                        "escrow_status": esc_status,
                        "executor_id": executor_id,
                        "reason": f"Escrow status '{esc_status}' not in funded statuses",
                    },
                )
            except Exception:
                pass  # Don't let logging failure block the validation
            raise Exception(
                f"Cannot submit evidence: escrow not confirmed on-chain "
                f"(status: {esc_status}). Wait for the agent to fund this task."
            )

    # Create submission
    # Bug fix: removed 'notes' field — it doesn't exist in the submissions table schema.
    # Also removed the retry-with-column-removal workaround that was masking the issue.
    submission_data = {
        "task_id": task_id,
        "executor_id": executor_id,
        "evidence": evidence,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "agent_verdict": "pending",
    }
    result = client.table("submissions").insert(submission_data).execute()

    if result.data and len(result.data) > 0:
        # Update task status
        await update_task(task_id, {"status": "submitted"})

        return {
            "submission": result.data[0],
            "task": task,
        }

    raise Exception("Failed to create submission")


async def get_executor_tasks(
    executor_id: str,
    status: Optional[str] = None,
    include_applications: bool = True,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get all tasks for an executor (assigned + applications)."""
    client = get_client()
    applications_table = _resolve_applications_table(client)

    # Get assigned tasks
    tasks_query = (
        client.table("tasks")
        .select("*, agent:agents(id, display_name)")
        .eq("executor_id", executor_id)
    )

    if status:
        tasks_query = tasks_query.eq("status", status)

    tasks_result = tasks_query.order("created_at", desc=True).limit(limit).execute()
    assigned_tasks = tasks_result.data or []

    # Get applications
    applications = []
    if include_applications:
        app_result = (
            client.table(applications_table)
            .select("*, task:tasks(*)")
            .eq("executor_id", executor_id)
            .eq("status", "pending")
            .execute()
        )
        applications = app_result.data or []

    # Get submissions
    sub_result = (
        client.table("submissions")
        .select("*, task:tasks(*)")
        .eq("executor_id", executor_id)
        .order("submitted_at", desc=True)
        .limit(10)
        .execute()
    )
    submissions = sub_result.data or []

    return {
        "assigned_tasks": assigned_tasks,
        "applications": applications,
        "recent_submissions": submissions,
        "totals": {
            "assigned": len(assigned_tasks),
            "pending_applications": len(applications),
            "submissions": len(submissions),
        },
    }


async def get_executor_earnings(executor_id: str) -> Dict[str, Any]:
    """Get earnings summary for an executor."""
    client = get_client()

    payments_result = (
        client.table("payments").select("*").eq("executor_id", executor_id).execute()
    )
    payments = payments_result.data or []

    completed = [p for p in payments if p.get("status") == "completed"]
    pending = [p for p in payments if p.get("status") == "pending"]
    available = [p for p in payments if p.get("status") == "available"]

    total_earned = sum(float(p.get("amount_usdc", 0)) for p in completed)
    total_pending = sum(float(p.get("amount_usdc", 0)) for p in pending)
    total_available = sum(float(p.get("amount_usdc", 0)) for p in available)

    return {
        "total_earned": total_earned,
        "pending": total_pending,
        "available": total_available,
        "payments": payments[-10:],
    }


async def assign_task(
    task_id: str,
    agent_id: str,
    executor_id: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Agent assigns a task to a specific executor."""
    client = get_client()
    applications_table = _resolve_applications_table(client)

    # Get task
    task = await get_task(task_id)
    if not task:
        raise Exception(f"Task {task_id} not found")

    # Verify agent owns the task
    if task["agent_id"] != agent_id:
        raise Exception("Not authorized to assign this task")

    if task["status"] != "published":
        raise Exception(f"Task cannot be assigned (status: {task['status']})")

    # Verify executor exists
    executor = (
        client.table("executors").select("*").eq("id", executor_id).single().execute()
    )
    if not executor.data:
        raise Exception(f"Executor {executor_id} not found")

    # Self-assignment guard: agent cannot assign task to itself
    executor_wallet = (executor.data.get("wallet_address") or "").lower()
    executor_agent_id = str(executor.data.get("erc8004_agent_id") or "")
    task_agent_id = str(task.get("agent_id") or "").lower()

    is_self = False
    if executor_wallet and task_agent_id and executor_wallet == task_agent_id:
        is_self = True
    if executor_agent_id and task_agent_id and executor_agent_id == task_agent_id:
        is_self = True

    if is_self:
        raise Exception("Cannot assign task to yourself: executor matches task agent")

    # Check minimum reputation
    min_rep = task.get("min_reputation", 0)
    if executor.data.get("reputation_score", 0) < min_rep:
        raise Exception(f"Executor has insufficient reputation. Required: {min_rep}")

    # --- Best-effort balance check at assignment time (Fase 1) ---
    payment_mode = os.environ.get("EM_PAYMENT_MODE", "fase1")
    if payment_mode == "fase1":
        try:
            from integrations.x402.sdk_client import EMX402SDK
            from decimal import Decimal

            bounty = Decimal(
                str(task.get("bounty_amount") or task.get("lock_amount") or "0")
            )
            if bounty > 0:
                sdk = EMX402SDK()
                agent_address = task.get("agent_id", "")
                if agent_address.startswith("0x"):
                    balance_result = await sdk.check_agent_balance(
                        agent_address=agent_address,
                        required_amount=bounty,
                    )
                    logger.info(
                        "Balance check at assignment: task=%s agent=%s sufficient=%s balance=%s required=%s",
                        task_id,
                        agent_address[:10],
                        balance_result.get("sufficient"),
                        balance_result.get("balance"),
                        bounty,
                    )
                    if not balance_result.get("sufficient", True):
                        raise Exception(
                            f"Insufficient agent balance for bounty. "
                            f"Balance: {balance_result.get('balance', '?')} USDC, "
                            f"Required: {bounty} USDC"
                        )
        except ImportError:
            logger.debug("x402 SDK not available for balance check at assignment")
        except Exception as e:
            if "Insufficient agent balance" in str(e):
                raise
            logger.warning("Best-effort balance check failed (non-blocking): %s", e)

    # --- Escrow validation: reject assignment if escrow not ready ---
    if payment_mode != "fase1":
        _VALID_ASSIGN_STATUSES = {
            "pending_assignment",
            "deposited",
            "funded",
            "authorized",
            "active",
            "locked",
        }
        try:
            esc_result = (
                client.table("escrows")
                .select("status")
                .eq("task_id", task_id)
                .limit(1)
                .execute()
            )
            esc = esc_result.data[0] if esc_result.data else None
        except Exception as e:
            logger.warning("Escrow lookup failed for task %s: %s", task_id, e)
            esc = None

        if not esc:
            # No escrow record — allow assignment but warn.
            # The caller (REST endpoint or MCP tool) handles escrow lock
            # after assignment. Tasks created before ADR-001 or without
            # X-Payment-Auth won't have escrow records at this point.
            logger.warning(
                "No escrow record for task %s at assignment. "
                "Caller must handle escrow lock post-assignment.",
                task_id,
            )
        else:
            esc_status = (esc.get("status") or "").lower().strip()
            if esc_status not in _VALID_ASSIGN_STATUSES:
                try:
                    from integrations.x402.payment_events import log_payment_event

                    await log_payment_event(
                        task_id=task_id,
                        event_type="escrow_validation_failed",
                        status="blocked",
                        metadata={
                            "action": "assign_task",
                            "escrow_status": esc_status,
                            "executor_id": executor_id,
                            "reason": f"Escrow status '{esc_status}' not valid for assignment",
                        },
                    )
                except Exception:
                    pass  # Don't let logging failure block the validation
                raise Exception(
                    f"Cannot assign: escrow status is '{esc_status}'. "
                    f"Expected one of: {', '.join(sorted(_VALID_ASSIGN_STATUSES))}"
                )

    # Update task
    updates = {
        "executor_id": executor_id,
        "status": "accepted",
        "assignment_notes": notes,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
    }

    updated_task = await update_task(task_id, updates)

    # Update any pending application to accepted
    try:
        client.table(applications_table).update({"status": "accepted"}).eq(
            "task_id", task_id
        ).eq("executor_id", executor_id).execute()
    except Exception as e:
        logger.warning(
            "Could not mark selected application as accepted (table=%s, task=%s, executor=%s): %s",
            applications_table,
            task_id,
            executor_id,
            e,
        )

    # Reject other applications
    rejection_updates = {
        "status": "rejected",
        "rejection_reason": "Task assigned to another executor",
    }
    while rejection_updates:
        try:
            client.table(applications_table).update(rejection_updates).eq(
                "task_id", task_id
            ).neq("executor_id", executor_id).execute()
            break
        except Exception as e:
            missing_column = _extract_missing_column(str(e))
            if missing_column and missing_column in rejection_updates:
                logger.warning(
                    "%s.%s missing in current schema; retrying reject-applications update without it",
                    applications_table,
                    missing_column,
                )
                rejection_updates.pop(missing_column, None)
                continue
            logger.warning(
                "Could not reject non-selected applications (table=%s, task=%s): %s",
                applications_table,
                task_id,
                e,
            )
            break

    return {
        "task": updated_task,
        "executor": executor.data,
    }


# ============== ANALYTICS OPERATIONS ==============


async def get_agent_analytics(
    agent_id: str,
    days: int = 30,
) -> Dict[str, Any]:
    """Get analytics for an agent's tasks."""
    client = get_client()

    # Calculate date range
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    tasks_result = (
        client.table("tasks")
        .select("*")
        .eq("agent_id", agent_id)
        .gte("created_at", start_date.isoformat())
        .execute()
    )

    tasks = tasks_result.data or []

    total = len(tasks)
    by_status: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    total_paid = 0.0

    for task in tasks:
        status = task.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

        # Count by category
        category = task.get("category", "unknown")
        by_category[category] = by_category.get(category, 0) + 1

        # Sum bounties for completed tasks
        if status == "completed":
            total_paid += float(task.get("bounty_usd", 0))

    completed = by_status.get("completed", 0)
    completion_rate = (completed / total * 100) if total > 0 else 0
    avg_bounty = (total_paid / completed) if completed > 0 else 0

    # Get top workers
    top_workers = []
    if completed > 0:
        # Get completed task executor IDs
        completed_tasks = [t for t in tasks if t.get("status") == "completed"]
        executor_ids = list(
            set(t.get("executor_id") for t in completed_tasks if t.get("executor_id"))
        )

        if executor_ids:
            workers_result = (
                client.table("executors")
                .select("id, display_name, reputation_score")
                .in_("id", executor_ids[:10])
                .execute()
            )

            if workers_result.data:
                # Count tasks per worker
                worker_counts = {}
                for t in completed_tasks:
                    eid = t.get("executor_id")
                    if eid:
                        worker_counts[eid] = worker_counts.get(eid, 0) + 1

                for worker in workers_result.data:
                    worker["tasks_completed"] = worker_counts.get(worker["id"], 0)
                    worker["reputation"] = worker.get("reputation_score", 0)
                    top_workers.append(worker)

                top_workers.sort(key=lambda w: w["tasks_completed"], reverse=True)

    # Calculate average times (simplified)
    avg_times = {
        "to_accept": "~2 hours",
        "to_complete": "~6 hours",
        "to_approve": "~30 minutes",
    }

    return {
        "totals": {
            "total": total,
            "completed": completed,
            "completion_rate": completion_rate,
            "total_paid": total_paid,
            "avg_bounty": avg_bounty,
        },
        "by_status": by_status,
        "by_category": by_category,
        "average_times": avg_times,
        "top_workers": top_workers[:5],
        "period_days": days,
    }
