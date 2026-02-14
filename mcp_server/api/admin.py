"""
Admin API Routes for Execution Market Platform Management

Provides endpoints for platform administrators to:
- View and modify platform configuration
- Manage tasks and users
- View analytics and audit logs

All endpoints require admin authentication.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from pydantic import BaseModel, Field

import supabase_client as db

# Platform configuration
try:
    from config import PlatformConfig, ConfigCategory

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    PlatformConfig = None
    ConfigCategory = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# =============================================================================
# ADMIN AUTHENTICATION
# =============================================================================


async def verify_admin_key(
    authorization: Optional[str] = Header(None, description="Bearer admin key"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    x_admin_actor: Optional[str] = Header(None, alias="X-Admin-Actor"),
    admin_key: Optional[str] = Query(None, alias="admin_key"),
):
    """
    Verify admin key using constant-time comparison.

    Preferred auth order:
    1. Authorization: Bearer <admin_key>
    2. X-Admin-Key: <admin_key>
    3. admin_key query param (legacy fallback)
    """
    import os
    import secrets as _secrets

    expected_key = os.environ.get("EM_ADMIN_KEY", "").strip()

    if not expected_key:
        raise HTTPException(status_code=503, detail="Admin access not configured")

    provided_key = None
    source = None

    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Use: Bearer <admin_key>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        provided_key = authorization[7:].strip()
        source = "authorization"
    elif x_admin_key:
        provided_key = x_admin_key.strip()
        source = "x-admin-key"
    elif admin_key:
        provided_key = admin_key.strip()
        source = "query"
        logger.warning("Legacy admin auth via query param used")
    else:
        raise HTTPException(
            status_code=401,
            detail="Admin credentials required (Authorization Bearer or X-Admin-Key)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="Admin key is empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _secrets.compare_digest(provided_key.encode(), expected_key.encode()):
        raise HTTPException(status_code=403, detail="Invalid admin key")

    actor_id = ((x_admin_actor or "").strip()[:128]) or "system"

    return {
        "role": "admin",
        "auth_source": source,
        "actor_id": actor_id,
    }


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ConfigValue(BaseModel):
    """Single platform configuration key-value pair."""

    key: str = Field(
        ..., description="Configuration key (e.g. 'fees.platform_fee_pct')"
    )
    value: Any = Field(..., description="Current configuration value")
    description: Optional[str] = Field(
        None, description="Human-readable description of this setting"
    )
    category: str = Field(
        ...,
        description="Configuration category (fees, limits, timing, features, payments, treasury)",
    )
    is_public: bool = Field(..., description="Whether this setting is publicly visible")
    updated_at: Optional[datetime] = Field(
        None, description="Last update timestamp (ISO 8601)"
    )


class AllConfigResponse(BaseModel):
    """All platform configuration values grouped by category."""

    fees: Dict[str, Any] = Field(
        ..., description="Fee-related settings (platform fee pct, min fee, etc.)"
    )
    limits: Dict[str, Any] = Field(
        ..., description="Platform limits (min/max bounty, batch size, etc.)"
    )
    timing: Dict[str, Any] = Field(
        ..., description="Timing settings (task expiration, deadlines, etc.)"
    )
    features: Dict[str, Any] = Field(
        ..., description="Feature flags (escrow enabled, AI verification, etc.)"
    )
    payments: Dict[str, Any] = Field(
        ..., description="Payment settings (supported networks, tokens, etc.)"
    )
    treasury: Dict[str, Any] = Field(
        ..., description="Treasury settings (wallet address, fee distribution)"
    )


class ConfigUpdateRequest(BaseModel):
    """Request to update a platform configuration value."""

    value: Any = Field(..., description="New value for the configuration key")
    reason: Optional[str] = Field(
        None, description="Reason for change (recorded in audit log)"
    )


class ConfigUpdateResponse(BaseModel):
    """Response after updating a configuration value."""

    success: bool = Field(..., description="Whether the update was successful")
    key: str = Field(..., description="Configuration key that was updated")
    old_value: Any = Field(..., description="Previous value before the update")
    new_value: Any = Field(..., description="New value after the update")
    message: str = Field(..., description="Human-readable result message")


class AuditLogEntry(BaseModel):
    """Single entry in the configuration audit log."""

    id: str = Field(..., description="Unique audit entry ID")
    config_key: str = Field(..., description="Configuration key that was changed")
    old_value: Any = Field(..., description="Value before the change")
    new_value: Any = Field(..., description="Value after the change")
    changed_by: Optional[str] = Field(None, description="Actor who made the change")
    reason: Optional[str] = Field(None, description="Reason provided for the change")
    changed_at: datetime = Field(..., description="Timestamp of the change (ISO 8601)")


class AuditLogResponse(BaseModel):
    """Paginated list of configuration audit log entries."""

    entries: List[AuditLogEntry] = Field(..., description="List of audit log entries")
    count: int = Field(..., description="Total number of matching entries")
    offset: int = Field(..., description="Current pagination offset")


# =============================================================================
# ADMIN VERIFICATION ENDPOINT
# =============================================================================


@router.get(
    "/verify",
    summary="Verify Admin Credentials",
    description="Validate admin authentication credentials. Returns the admin role on success.",
    responses={
        200: {"description": "Admin credentials are valid"},
        401: {"description": "Missing or invalid admin credentials"},
        403: {"description": "Invalid admin key"},
        503: {"description": "Admin access not configured"},
    },
)
async def verify_admin(admin: dict = Depends(verify_admin_key)) -> Dict[str, Any]:
    return {"valid": True, "role": admin.get("role", "admin")}


# =============================================================================
# CONFIG ENDPOINTS
# IMPORTANT: /config/audit MUST be defined BEFORE /config/{key}
# to avoid FastAPI matching "audit" as a {key} parameter.
# =============================================================================


@router.get(
    "/config",
    response_model=AllConfigResponse,
    summary="Get All Configuration",
    description="Retrieve all platform configuration values grouped by category (fees, limits, timing, features, payments, treasury).",
    responses={
        200: {"description": "All configuration values by category"},
        401: {"description": "Unauthorized"},
        503: {"description": "Configuration system not available"},
    },
)
async def get_all_config(admin: dict = Depends(verify_admin_key)) -> AllConfigResponse:
    """Get all platform configuration values grouped by category."""
    if not CONFIG_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="Configuration system not available"
        )

    try:
        supabase = db.get_supabase_client()

        # Query all config rows directly from DB
        result = (
            supabase.table("platform_config").select("key, value, category").execute()
        )

        # Group by our response categories
        category_map = {
            "fees": "fees",
            "limits": "limits",
            "timing": "timing",
            "features": "features",
            "payments": "payments",
            "treasury": "treasury",
        }

        grouped: Dict[str, Dict[str, Any]] = {k: {} for k in category_map}

        for row in result.data or []:
            cat = row.get("category", "")
            if cat not in category_map:
                continue
            key = row["key"]
            short_key = key.split(".", 1)[-1] if "." in key else key
            value = row["value"]
            # JSONB values come as Python objects already
            if isinstance(value, Decimal):
                value = float(value)
            grouped[cat][short_key] = value

        # If DB returned nothing, fall back to PlatformConfig defaults
        if not result.data:
            for category in ConfigCategory:
                configs = await PlatformConfig.get_all_by_category(category)
                clean = {}
                for key, value in configs.items():
                    short_key = key.split(".", 1)[-1] if "." in key else key
                    if isinstance(value, Decimal):
                        value = float(value)
                    clean[short_key] = value
                grouped[category.value] = clean

        return AllConfigResponse(**grouped)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/config/audit",
    response_model=AuditLogResponse,
    summary="Get Configuration Audit Log",
    description="Retrieve the audit trail of all configuration changes. Supports filtering by key and category.",
    responses={
        200: {"description": "Paginated audit log entries"},
        401: {"description": "Unauthorized"},
    },
)
async def get_config_audit_log(
    key: Optional[str] = Query(None, description="Filter by config key"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None, description="Filter by category prefix"),
    admin: dict = Depends(verify_admin_key),
) -> AuditLogResponse:
    """Get configuration change audit log."""
    try:
        supabase = db.get_supabase_client()
        query = supabase.table("config_audit_log").select("*", count="exact")

        if key:
            query = query.eq("config_key", key)
        if category:
            query = query.like("config_key", f"{category}.%")

        query = query.order("changed_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        entries = []
        for row in result.data or []:
            entries.append(
                AuditLogEntry(
                    id=row["id"],
                    config_key=row["config_key"],
                    old_value=row.get("old_value"),
                    new_value=row["new_value"],
                    changed_by=row.get("changed_by"),
                    reason=row.get("reason"),
                    changed_at=row["changed_at"],
                )
            )

        return AuditLogResponse(
            entries=entries,
            count=result.count or len(entries),
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        return AuditLogResponse(entries=[], count=0, offset=offset)


@router.get(
    "/config/{key}",
    response_model=ConfigValue,
    summary="Get Configuration Value",
    description="Retrieve a specific configuration value by its key. Falls back to default values if not set in the database.",
    responses={
        200: {"description": "Configuration value found"},
        401: {"description": "Unauthorized"},
        404: {"description": "Configuration key not found"},
    },
)
async def get_config_value(
    key: str, admin: dict = Depends(verify_admin_key)
) -> ConfigValue:
    """Get a specific configuration value."""
    try:
        supabase = db.get_supabase_client()
        result = supabase.table("platform_config").select("*").eq("key", key).execute()

        if result.data:
            row = result.data[0]
            value = row["value"]
            if isinstance(value, Decimal):
                value = float(value)
            return ConfigValue(
                key=key,
                value=value,
                description=row.get("description"),
                category=row.get("category", "unknown"),
                is_public=row.get("is_public", False),
                updated_at=row.get("updated_at"),
            )

        # Fall back to PlatformConfig defaults
        if CONFIG_AVAILABLE:
            value = await PlatformConfig.get(key)
            if value is not None:
                return ConfigValue(
                    key=key,
                    value=float(value) if isinstance(value, Decimal) else value,
                    description=None,
                    category="unknown",
                    is_public=False,
                )

        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config {key}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/config/{key}",
    response_model=ConfigUpdateResponse,
    summary="Update Configuration Value",
    description="Update a platform configuration value. All changes are recorded in the audit log with the actor and optional reason.",
    responses={
        200: {"description": "Configuration updated successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Configuration key not found"},
        500: {"description": "Failed to update configuration"},
    },
)
async def update_config_value(
    key: str, request: ConfigUpdateRequest, admin: dict = Depends(verify_admin_key)
) -> ConfigUpdateResponse:
    """Update a configuration value. Changes are logged to the audit table."""
    try:
        supabase = db.get_supabase_client()

        # Get current value
        current = (
            supabase.table("platform_config").select("value").eq("key", key).execute()
        )
        if not current.data:
            raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

        old_value = current.data[0]["value"]

        # Pass raw value to Supabase — the client handles JSONB serialization.
        # Do NOT json.dumps() — that double-encodes (e.g. 100 → "100" string).
        new_value = request.value

        # Update directly in DB
        result = (
            supabase.table("platform_config")
            .update(
                {
                    "value": new_value,
                    "updated_by": admin.get("actor_id"),
                }
            )
            .eq("key", key)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=500, detail="Failed to update configuration"
            )

        # Update audit log reason directly (trigger can't capture session vars via REST)
        if request.reason:
            try:
                latest = (
                    supabase.table("config_audit_log")
                    .select("id")
                    .eq("config_key", key)
                    .order("changed_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if latest.data:
                    supabase.table("config_audit_log").update(
                        {
                            "reason": request.reason,
                        }
                    ).eq("id", latest.data[0]["id"]).execute()
            except Exception:
                pass  # Non-critical

        # Invalidate cache
        if CONFIG_AVAILABLE:
            PlatformConfig._cache.pop(key, None)

        logger.info(
            "SECURITY_AUDIT action=admin.config_update actor=%s source=%s key=%s reason_provided=%s",
            admin.get("actor_id"),
            admin.get("auth_source"),
            key,
            bool(request.reason),
        )

        return ConfigUpdateResponse(
            success=True,
            key=key,
            old_value=old_value,
            new_value=new_value,
            message=f"Configuration '{key}' updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config {key}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# PLATFORM STATS ENDPOINTS
# =============================================================================


@router.get(
    "/stats",
    summary="Get Platform Statistics",
    description="Get platform-wide statistics including task counts by status, financial metrics (volume, fees, active escrow), and user counts.",
    responses={
        200: {"description": "Platform statistics"},
        401: {"description": "Unauthorized"},
    },
)
async def get_platform_stats(admin: dict = Depends(verify_admin_key)) -> Dict[str, Any]:
    """Get platform-wide statistics."""
    try:
        supabase = db.get_supabase_client()

        # Task stats by status
        tasks_by_status: Dict[str, int] = {}
        total_tasks = 0
        try:
            tasks_result = supabase.table("tasks").select("status").execute()
            if tasks_result.data:
                for task in tasks_result.data:
                    status = task.get("status", "unknown")
                    tasks_by_status[status] = tasks_by_status.get(status, 0) + 1
                total_tasks = len(tasks_result.data)
        except Exception as e:
            logger.warning(f"Could not query tasks: {e}")

        # Financial stats derived from tasks (escrows table may not exist)
        total_volume = 0.0
        total_fees = 0.0
        active_escrow = 0.0
        try:
            fin_result = supabase.table("tasks").select("bounty_usd, status").execute()
            fee_pct = 0.13
            if fin_result.data:
                for task in fin_result.data:
                    amount = float(task.get("bounty_usd", 0) or 0)
                    total_volume += amount
                    if task.get("status") == "completed":
                        total_fees += amount * fee_pct
                    if task.get("status") in (
                        "published",
                        "accepted",
                        "in_progress",
                        "submitted",
                    ):
                        active_escrow += amount
        except Exception as e:
            logger.warning(f"Could not compute financial stats: {e}")

        # Active users — use count queries for efficiency
        workers_count = 0
        agents_count = 0
        try:
            workers_result = (
                supabase.table("executors").select("id", count="exact").execute()
            )
            workers_count = workers_result.count or 0
        except Exception as e:
            logger.warning(f"Could not count executors: {e}")

        try:
            agents_result = (
                supabase.table("api_keys")
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )
            agents_count = agents_result.count or 0
        except Exception as e:
            logger.warning(f"Could not count agents: {e}")

        # Orphaned payments alert: accepted submissions without payment_tx
        orphaned_count = 0
        try:
            orphaned_result = (
                supabase.table("submissions")
                .select("id", count="exact")
                .in_("agent_verdict", ["accepted", "approved"])
                .is_("payment_tx", "null")
                .execute()
            )
            orphaned_count = orphaned_result.count or 0
        except Exception as e:
            logger.warning(f"Could not count orphaned payments: {e}")

        return {
            "tasks": {
                "by_status": tasks_by_status,
                "total": total_tasks,
            },
            "payments": {
                "total_volume_usd": round(total_volume, 2),
                "total_fees_usd": round(total_fees, 2),
                "active_escrow_usd": round(active_escrow, 2),
                "orphaned_accepted_no_tx": orphaned_count,
            },
            "users": {
                "active_workers": workers_count,
                "active_agents": agents_count,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return {
            "tasks": {"by_status": {}, "total": 0},
            "payments": {
                "total_volume_usd": 0,
                "total_fees_usd": 0,
                "active_escrow_usd": 0,
            },
            "users": {"active_workers": 0, "active_agents": 0},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# TASKS MANAGEMENT ENDPOINTS
# =============================================================================


@router.get(
    "/tasks",
    summary="List All Tasks",
    description="List all tasks across the platform with optional status filtering and text search. Includes status distribution counts.",
    responses={
        200: {"description": "Paginated task list with status counts"},
        401: {"description": "Unauthorized"},
    },
)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """List all tasks across the platform with optional filters."""
    try:
        supabase = db.get_supabase_client()

        query = supabase.table("tasks").select("*", count="exact")

        if status:
            query = query.eq("status", status)

        if search:
            query = query.or_(f"title.ilike.%{search}%,instructions.ilike.%{search}%")

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        # Status counts
        all_tasks = supabase.table("tasks").select("status").execute()
        stats: Dict[str, int] = {}
        if all_tasks.data:
            for task in all_tasks.data:
                s = task.get("status", "unknown")
                stats[s] = stats.get(s, 0) + 1

        return {
            "tasks": result.data or [],
            "count": result.count or 0,
            "offset": offset,
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return {"tasks": [], "count": 0, "offset": offset, "stats": {}}


@router.get(
    "/tasks/{task_id}",
    summary="Get Task Detail",
    description="Get complete details for a specific task including all fields, evidence schema, and executor info.",
    responses={
        200: {"description": "Task details"},
        401: {"description": "Unauthorized"},
        404: {"description": "Task not found"},
    },
)
async def get_task_detail(
    task_id: str, admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """Get detailed task information."""
    try:
        supabase = db.get_supabase_client()
        result = (
            supabase.table("tasks").select("*").eq("id", task_id).single().execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/tasks/{task_id}",
    summary="Update Task (Admin Override)",
    description="Update task fields as an admin. Supports updating title, instructions, bounty, deadline, and status. Field names are mapped from frontend conventions to database columns.",
    responses={
        200: {"description": "Task updated successfully"},
        400: {"description": "No valid fields to update"},
        401: {"description": "Unauthorized"},
        404: {"description": "Task not found"},
    },
)
async def update_task(
    task_id: str, updates: Dict[str, Any], admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """Update task details (admin override)."""
    try:
        supabase = db.get_supabase_client()

        # Map frontend field names to actual DB columns
        field_map = {
            "title": "title",
            "description": "instructions",  # DB column is 'instructions'
            "instructions": "instructions",
            "bounty_usd": "bounty_usd",
            "deadline": "deadline",
            "status": "status",
        }

        filtered_updates = {}
        for k, v in updates.items():
            if k in field_map:
                filtered_updates[field_map[k]] = v

        if not filtered_updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        result = (
            supabase.table("tasks").update(filtered_updates).eq("id", task_id).execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"success": True, "task": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/tasks/{task_id}/cancel",
    summary="Cancel Task (Admin)",
    description="Force-cancel a task as an admin. Cannot cancel tasks already completed or cancelled.",
    responses={
        200: {"description": "Task cancelled successfully"},
        400: {"description": "Task cannot be cancelled in its current status"},
        401: {"description": "Unauthorized"},
        404: {"description": "Task not found"},
    },
)
async def cancel_task(
    task_id: str, body: Dict[str, Any], admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """Cancel a task (admin action)."""
    try:
        reason = body.get("reason", "Cancelled by admin")
        supabase = db.get_supabase_client()

        task = supabase.table("tasks").select("*").eq("id", task_id).single().execute()
        if not task.data:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.data["status"] in ["completed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task with status '{task.data['status']}'",
            )

        # Only update columns that exist on the tasks table
        supabase.table("tasks").update(
            {
                "status": "cancelled",
                "completion_notes": f"Admin cancel: {reason}",
            }
        ).eq("id", task_id).execute()

        return {
            "success": True,
            "message": f"Task {task_id} cancelled",
            "reason": reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# PAYMENTS ENDPOINTS (uses escrows table - payments table doesn't exist yet)
# =============================================================================


@router.get(
    "/payments",
    summary="List Payment Transactions",
    description="List payment transactions derived from task completions and cancellations. Supports time-period filtering.",
    responses={
        200: {"description": "Paginated payment transactions"},
        401: {"description": "Unauthorized"},
    },
)
async def list_payments(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d, 90d, all"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """List payment transactions derived from completed tasks."""
    try:
        supabase = db.get_supabase_client()

        # Use completed/submitted tasks as the source of truth for payments.
        # escrows table may not exist; tasks table always does.
        query = (
            supabase.table("tasks")
            .select("*", count="exact")
            .in_("status", ["completed", "submitted", "accepted", "cancelled"])
        )

        if period != "all":
            periods = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
            days = periods.get(period, 7)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("created_at", cutoff)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        transactions = []
        for row in result.data or []:
            status_map = {
                "completed": "confirmed",
                "submitted": "pending",
                "accepted": "pending",
                "cancelled": "refunded",
            }
            type_map = {
                "completed": "release",
                "submitted": "deposit",
                "accepted": "deposit",
                "cancelled": "refund",
            }
            transactions.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "type": type_map.get(row.get("status", ""), "unknown"),
                    "amount_usd": float(row.get("bounty_usd", 0) or 0),
                    "task_id": row["id"],
                    "wallet_address": row.get("agent_id", ""),
                    "status": status_map.get(row.get("status", ""), "pending"),
                    "tx_hash": row.get("escrow_tx"),
                    "payment_strategy": "x402_escrow",
                }
            )

        return {
            "transactions": transactions,
            "count": result.count or 0,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error listing payments: {e}", exc_info=True)
        return {"transactions": [], "count": 0, "offset": offset}


@router.get(
    "/payments/stats",
    summary="Get Payment Statistics",
    description="Get aggregated payment statistics including total volume, fees collected, and active escrow amounts. Supports time-period filtering.",
    responses={
        200: {"description": "Payment statistics"},
        401: {"description": "Unauthorized"},
    },
)
async def get_payment_stats(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d, 90d, all"),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """Get payment statistics derived from tasks."""
    try:
        supabase = db.get_supabase_client()

        # Derive payment stats from tasks table (escrows table may not exist)
        query = supabase.table("tasks").select("bounty_usd, status, created_at")

        if period != "all":
            periods = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
            days = periods.get(period, 7)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("created_at", cutoff)

        result = query.execute()
        tasks = result.data or []

        fee_pct = 0.13  # Default platform fee
        try:
            cfg = (
                supabase.table("platform_config")
                .select("value")
                .eq("key", "fees.platform_fee_pct")
                .execute()
            )
            if cfg.data:
                fee_pct = float(cfg.data[0]["value"])
        except Exception:
            pass

        total_volume = sum(float(t.get("bounty_usd", 0) or 0) for t in tasks)
        completed_volume = sum(
            float(t.get("bounty_usd", 0) or 0)
            for t in tasks
            if t.get("status") == "completed"
        )
        total_fees = round(completed_volume * fee_pct, 2)
        active_escrow = sum(
            float(t.get("bounty_usd", 0) or 0)
            for t in tasks
            if t.get("status") in ("published", "accepted", "in_progress", "submitted")
        )

        return {
            "total_volume_usd": round(total_volume, 2),
            "total_fees_usd": total_fees,
            "active_escrow_usd": round(active_escrow, 2),
            "transaction_count": len(tasks),
        }
    except Exception as e:
        logger.error(f"Error getting payment stats: {e}", exc_info=True)
        return {
            "total_volume_usd": 0,
            "total_fees_usd": 0,
            "active_escrow_usd": 0,
            "transaction_count": 0,
        }


# =============================================================================
# USERS ENDPOINTS
# =============================================================================


@router.get(
    "/users/agents",
    summary="List Agents",
    description="List all registered agents (task creators) with their task counts, spending totals, and status. Derived from API keys table.",
    responses={
        200: {"description": "Paginated list of agents with statistics"},
        401: {"description": "Unauthorized"},
    },
)
async def list_agents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """List all agents (task creators)."""
    try:
        supabase = db.get_supabase_client()

        # Use select("*") to avoid failing on missing columns
        result = (
            supabase.table("api_keys")
            .select("*", count="exact")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        agents = []
        for agent in result.data or []:
            agent_id = agent.get("agent_id") or agent["id"]

            # Count tasks — wrapped in try/except for resilience
            task_count = 0
            try:
                tasks = (
                    supabase.table("tasks")
                    .select("id", count="exact")
                    .eq("agent_id", agent_id)
                    .execute()
                )
                task_count = tasks.count or 0
            except Exception:
                pass

            # Sum total spent from tasks bounties (escrows table may not exist)
            total_spent = 0.0
            try:
                spent_tasks = (
                    supabase.table("tasks")
                    .select("bounty_usd")
                    .eq("agent_id", agent_id)
                    .in_(
                        "status", ["completed", "submitted", "accepted", "in_progress"]
                    )
                    .execute()
                )
                total_spent = sum(
                    float(t.get("bounty_usd", 0) or 0) for t in (spent_tasks.data or [])
                )
            except Exception:
                pass

            agents.append(
                {
                    "id": agent["id"],
                    "wallet_address": agent.get("agent_id", ""),
                    "name": agent.get("name", agent.get("key_prefix", "")),
                    "tier": agent.get("tier", "free"),
                    "created_at": agent.get("created_at"),
                    "task_count": task_count,
                    "total_spent_usd": round(total_spent, 2),
                    "status": "active" if agent.get("is_active") else "suspended",
                    "usage_count": agent.get("usage_count", 0),
                }
            )

        return {
            "users": agents,
            "count": result.count or len(agents),
            "offset": offset,
            "stats": {
                "total_agents": result.count or len(agents),
                "active_agents": sum(1 for a in agents if a["status"] == "active"),
            },
        }
    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        return {"users": [], "count": 0, "offset": offset, "stats": {}}


@router.get(
    "/users/workers",
    summary="List Workers",
    description="List all registered workers (task executors) with their completed task counts, earnings, and reputation scores.",
    responses={
        200: {"description": "Paginated list of workers with statistics"},
        401: {"description": "Unauthorized"},
    },
)
async def list_workers(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """List all workers (task executors)."""
    try:
        supabase = db.get_supabase_client()

        # Use select("*") to avoid failing on missing columns.
        # Different DB environments may have different column sets.
        result = (
            supabase.table("executors")
            .select("*", count="exact")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        workers = []
        for worker in result.data or []:
            # Count completed tasks
            task_count = 0
            try:
                tasks = (
                    supabase.table("tasks")
                    .select("id", count="exact")
                    .eq("executor_id", worker["id"])
                    .eq("status", "completed")
                    .execute()
                )
                task_count = tasks.count or 0
            except Exception:
                pass

            workers.append(
                {
                    "id": worker["id"],
                    "wallet_address": worker.get("wallet_address", ""),
                    "name": worker.get("display_name", ""),
                    "created_at": worker.get("created_at"),
                    "task_count": task_count,
                    "total_earned_usd": float(worker.get("total_earned_usdc", 0) or 0),
                    "reputation_score": worker.get("reputation_score", 0),
                    "status": worker.get("status", "active"),
                    "success_rate": None,
                }
            )

        return {
            "users": workers,
            "count": result.count or len(workers),
            "offset": offset,
            "stats": {
                "total_workers": result.count or len(workers),
                "active_workers": result.count or len(workers),
            },
        }
    except Exception as e:
        logger.error(f"Error listing workers: {e}", exc_info=True)
        return {"users": [], "count": 0, "offset": offset, "stats": {}}


@router.put(
    "/users/{user_id}/status",
    summary="Update User Status",
    description="Suspend or activate an agent or worker. Tries agent (api_keys) first, then worker (executors) table.",
    responses={
        200: {"description": "User status updated"},
        400: {"description": "Invalid status value"},
        401: {"description": "Unauthorized"},
        404: {"description": "User not found"},
    },
)
async def update_user_status(
    user_id: str, body: Dict[str, Any], admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """Update user status (suspend/activate)."""
    try:
        status = body.get("status")
        if status not in ["active", "suspended"]:
            raise HTTPException(status_code=400, detail="Invalid status")

        supabase = db.get_supabase_client()

        # Try agents first (api_keys)
        result = (
            supabase.table("api_keys")
            .update({"is_active": status == "active"})
            .eq("id", user_id)
            .execute()
        )

        if result.data:
            return {
                "success": True,
                "user_id": user_id,
                "status": status,
                "type": "agent",
            }

        # Try workers (executors)
        result = (
            supabase.table("executors")
            .update({"status": status})
            .eq("id", user_id)
            .execute()
        )

        if result.data:
            return {
                "success": True,
                "user_id": user_id,
                "status": status,
                "type": "worker",
            }

        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================


@router.get(
    "/analytics",
    summary="Get Platform Analytics",
    description="Get detailed analytics data for dashboard charts including daily time series (tasks created/completed, volume), top agents, and top workers.",
    responses={
        200: {"description": "Analytics data with time series and rankings"},
        401: {"description": "Unauthorized"},
    },
)
async def get_analytics(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, all"),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """Get detailed analytics data for charts."""
    try:
        supabase = db.get_supabase_client()

        periods_map = {"7d": 7, "30d": 30, "90d": 90}
        days = periods_map.get(period, 30)

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days) if period != "all" else None

        # Fetch all tasks and escrows in the period in ONE query each
        # then aggregate in Python (avoids N+1 per-day queries)
        time_series = []
        if start_date:
            start_str = start_date.strftime("%Y-%m-%d")

            all_tasks = (
                supabase.table("tasks")
                .select("created_at, status, updated_at, bounty_usd")
                .gte("created_at", start_str)
                .execute()
            )

            # Build daily maps from tasks data
            created_by_day: Dict[str, int] = {}
            completed_by_day: Dict[str, int] = {}
            volume_by_day: Dict[str, float] = {}

            for task in all_tasks.data or []:
                day = task["created_at"][:10]
                created_by_day[day] = created_by_day.get(day, 0) + 1
                # Track volume from task bounties
                amount = float(task.get("bounty_usd", 0) or 0)
                volume_by_day[day] = volume_by_day.get(day, 0) + amount
                if task.get("status") == "completed" and task.get("updated_at"):
                    cday = task["updated_at"][:10]
                    completed_by_day[cday] = completed_by_day.get(cday, 0) + 1

            for i in range(days):
                date = start_date + timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                time_series.append(
                    {
                        "date": date.strftime("%b %d"),
                        "created": created_by_day.get(date_str, 0),
                        "completed": completed_by_day.get(date_str, 0),
                        "volume": round(volume_by_day.get(date_str, 0), 2),
                    }
                )

        # Top agents (by task count)
        try:
            agents_result = (
                supabase.table("api_keys")
                .select("*")
                .eq("is_active", True)
                .limit(10)
                .execute()
            )
        except Exception:
            agents_result = type("R", (), {"data": []})()

        top_agents = []
        for agent in agents_result.data or []:
            agent_id = agent.get("agent_id") or agent["id"]

            task_count = 0
            total_spent = 0.0
            try:
                tasks = (
                    supabase.table("tasks")
                    .select("id, bounty_usd", count="exact")
                    .eq("agent_id", agent_id)
                    .execute()
                )
                task_count = tasks.count or 0
                total_spent = sum(
                    float(t.get("bounty_usd", 0) or 0) for t in (tasks.data or [])
                )
            except Exception:
                pass

            top_agents.append(
                {
                    "id": agent["id"],
                    "wallet_address": agent_id,
                    "name": agent.get("name", ""),
                    "total_spent_usd": round(total_spent, 2),
                    "task_count": task_count,
                }
            )

        top_agents.sort(key=lambda x: x["task_count"], reverse=True)

        # Top workers (by reputation)
        try:
            workers_result = (
                supabase.table("executors")
                .select("*")
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )
        except Exception:
            workers_result = type("R", (), {"data": []})()

        top_workers = []
        for worker in workers_result.data or []:
            task_count = 0
            try:
                tasks = (
                    supabase.table("tasks")
                    .select("id", count="exact")
                    .eq("executor_id", worker["id"])
                    .eq("status", "completed")
                    .execute()
                )
                task_count = tasks.count or 0
            except Exception:
                pass

            top_workers.append(
                {
                    "id": worker["id"],
                    "wallet_address": worker.get("wallet_address", ""),
                    "name": worker.get("display_name", ""),
                    "reputation_score": worker.get("reputation_score", 0),
                    "total_earned_usd": float(worker.get("total_earned_usdc", 0) or 0),
                    "task_count": task_count,
                }
            )

        return {
            "time_series": time_series,
            "top_agents": top_agents[:5],
            "top_workers": top_workers[:5],
            "trends": {
                "tasks": {"value": 0, "label": "vs last period"},
                "volume": {"value": 0, "label": "vs last period"},
                "fees": {"value": 0, "label": "vs last period"},
            },
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return {
            "time_series": [],
            "top_agents": [],
            "top_workers": [],
            "trends": {},
        }


# =============================================================================
# FEE MANAGEMENT ENDPOINTS (Batch Fee Collection)
# =============================================================================


@router.get(
    "/fees/accrued",
    summary="Get Accrued Fees",
    description=(
        "Show accumulated fees in the operator contract awaiting distribution to treasury. "
        "Fase 5 credit card model: fees are deducted on-chain at release (13% of bounty). "
        "Use POST /fees/sweep to call distributeFees() and flush to treasury."
    ),
    responses={
        200: {"description": "Accrued fee information"},
        401: {"description": "Unauthorized"},
        503: {"description": "Payment system not available"},
    },
)
async def get_accrued_fees(
    network: str = Query("base", description="Payment network"),
    token: str = Query("USDC", description="Token symbol"),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """Get accumulated fees available for sweep to treasury."""
    try:
        from integrations.x402.payment_dispatcher import get_dispatcher

        dispatcher = get_dispatcher()
        result = await dispatcher.get_accrued_fees(network=network, token=token)
        return result
    except ImportError:
        raise HTTPException(status_code=503, detail="Payment dispatcher not available")
    except Exception as e:
        logger.error(f"Error getting accrued fees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/fees/sweep",
    summary="Distribute Fees to Treasury",
    description=(
        "Call distributeFees() on the operator contract to flush accumulated fees to treasury. "
        "Fase 5 credit card model: fees accumulate in the operator contract on each release. "
        "Also sweeps any legacy platform wallet balance for backward compatibility."
    ),
    responses={
        200: {"description": "Sweep result with tx hash"},
        401: {"description": "Unauthorized"},
        503: {"description": "Payment system not available"},
    },
)
async def sweep_fees_to_treasury(
    network: str = Query("base", description="Payment network"),
    token: str = Query("USDC", description="Token symbol"),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """Sweep accumulated fees from platform wallet to treasury."""
    try:
        from integrations.x402.payment_dispatcher import get_dispatcher

        dispatcher = get_dispatcher()

        logger.info(
            "SECURITY_AUDIT action=admin.fee_sweep actor=%s source=%s network=%s",
            admin.get("actor_id"),
            admin.get("auth_source"),
            network,
        )

        result = await dispatcher.sweep_fees_to_treasury(network=network, token=token)
        return result
    except ImportError:
        raise HTTPException(status_code=503, detail="Payment dispatcher not available")
    except Exception as e:
        logger.error(f"Error sweeping fees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PAYMENT RETRY ENDPOINTS
# =============================================================================


@router.get(
    "/payments/orphaned",
    summary="Get Orphaned Payments",
    description="List submissions that were accepted/approved but are missing a payment transaction hash. These may need manual settlement retry.",
    responses={
        200: {"description": "List of orphaned submissions needing payment"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def get_orphaned_payments(
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """List submissions accepted/approved but missing payment_tx."""
    try:
        supabase = db.get_supabase_client()
        result = (
            supabase.table("submissions")
            .select(
                "id, task_id, executor_id, agent_verdict, payment_tx, updated_at, task:tasks(id, title, bounty_usd, escrow_tx, status), executor:executors(id, wallet_address, display_name)"
            )
            .in_("agent_verdict", ["accepted", "approved"])
            .is_("payment_tx", "null")
            .order("updated_at", desc=False)
            .limit(limit)
            .execute()
        )
        submissions = result.data or []
        return {
            "orphaned_submissions": submissions,
            "count": len(submissions),
        }
    except Exception as e:
        logger.error(f"Error fetching orphaned payments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/payments/retry/{submission_id}",
    summary="Retry Payment Settlement",
    description="Manually retry x402 payment settlement for an orphaned submission. Returns the payment transaction hash on success.",
    responses={
        200: {"description": "Settlement result (settled, already_paid, or failed)"},
        400: {"description": "Submission is not in accepted/approved state"},
        401: {"description": "Unauthorized"},
        404: {"description": "Submission not found"},
        500: {"description": "Internal server error"},
    },
)
async def retry_submission_payment(
    submission_id: str,
    admin: dict = Depends(verify_admin_key),
) -> Dict[str, Any]:
    """Manually retry settlement for a specific orphaned submission."""
    try:
        from jobs.auto_payment import _retry_settlement

        supabase = db.get_supabase_client()

        # Fetch the submission with task/executor joins
        result = (
            supabase.table("submissions")
            .select(
                "id, task_id, executor_id, agent_verdict, payment_tx, task:tasks(id, bounty_usd, escrow_tx, escrow_id, status), executor:executors(id, wallet_address)"
            )
            .eq("id", submission_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        submission = result.data[0]

        if submission.get("payment_tx"):
            return {
                "status": "already_paid",
                "payment_tx": submission["payment_tx"],
                "message": "Submission already has a payment_tx",
            }

        verdict = (submission.get("agent_verdict") or "").lower().strip()
        if verdict not in ("accepted", "approved"):
            raise HTTPException(
                status_code=400,
                detail=f"Submission verdict is '{verdict}', not accepted/approved",
            )

        success = await _retry_settlement(supabase, submission)

        if success:
            # Re-fetch to get the updated payment_tx
            updated = (
                supabase.table("submissions")
                .select("payment_tx, paid_at, payment_amount")
                .eq("id", submission_id)
                .limit(1)
                .execute()
            )
            updated_data = updated.data[0] if updated.data else {}
            return {
                "status": "settled",
                "payment_tx": updated_data.get("payment_tx"),
                "paid_at": updated_data.get("paid_at"),
                "payment_amount": updated_data.get("payment_amount"),
            }
        else:
            return {
                "status": "failed",
                "message": "Settlement attempt failed — check server logs for details",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying payment for submission {submission_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
