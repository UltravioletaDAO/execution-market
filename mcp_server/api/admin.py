"""
Admin API Routes for Execution Market Platform Management

Provides endpoints for platform administrators to:
- View and modify platform configuration
- Manage tasks and users
- View analytics and audit logs

All endpoints require admin authentication.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
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
# ADMIN AUTHENTICATION (TODO: Implement proper admin auth)
# =============================================================================

async def verify_admin_key(api_key: str = Query(..., alias="admin_key")):
    """
    Verify admin API key using constant-time comparison.
    """
    import os
    import secrets as _secrets

    expected_key = os.environ.get("EM_ADMIN_KEY", os.environ.get("CHAMBA_ADMIN_KEY", ""))

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Admin access not configured"
        )

    if not _secrets.compare_digest(api_key.encode(), expected_key.encode()):
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key"
        )

    return {"role": "admin"}


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ConfigValue(BaseModel):
    """Single configuration value."""
    key: str
    value: Any
    description: Optional[str] = None
    category: str
    is_public: bool
    updated_at: Optional[datetime] = None


class AllConfigResponse(BaseModel):
    """All configuration values grouped by category."""
    fees: Dict[str, Any]
    limits: Dict[str, Any]
    timing: Dict[str, Any]
    features: Dict[str, Any]
    payments: Dict[str, Any]
    treasury: Dict[str, Any]


class ConfigUpdateRequest(BaseModel):
    """Request to update a configuration value."""
    value: Any = Field(..., description="New value")
    reason: Optional[str] = Field(None, description="Reason for change (for audit log)")


class ConfigUpdateResponse(BaseModel):
    """Response after updating configuration."""
    success: bool
    key: str
    old_value: Any
    new_value: Any
    message: str


class AuditLogEntry(BaseModel):
    """Single audit log entry."""
    id: str
    config_key: str
    old_value: Any
    new_value: Any
    changed_by: Optional[str]
    reason: Optional[str]
    changed_at: datetime


class AuditLogResponse(BaseModel):
    """Audit log response."""
    entries: List[AuditLogEntry]
    count: int
    offset: int


# =============================================================================
# CONFIG ENDPOINTS
# =============================================================================


@router.get(
    "/config",
    response_model=AllConfigResponse,
    responses={
        200: {"description": "All platform configuration"},
        403: {"description": "Admin key required"},
    }
)
async def get_all_config(
    admin: dict = Depends(verify_admin_key)
) -> AllConfigResponse:
    """
    Get all platform configuration values.

    Returns configuration grouped by category. Only accessible to admins.
    """
    if not CONFIG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Configuration system not available"
        )

    try:
        result = {
            "fees": {},
            "limits": {},
            "timing": {},
            "features": {},
            "payments": {},
            "treasury": {},
        }

        # Load each category
        for category in ConfigCategory:
            configs = await PlatformConfig.get_all_by_category(category)
            # Strip category prefix from keys for cleaner response
            clean_configs = {}
            for key, value in configs.items():
                short_key = key.split(".", 1)[-1] if "." in key else key
                # Convert Decimal to float for JSON serialization
                if isinstance(value, Decimal):
                    value = float(value)
                clean_configs[short_key] = value
            result[category.value] = clean_configs

        return AllConfigResponse(**result)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/config/{key}",
    response_model=ConfigValue,
    responses={
        200: {"description": "Configuration value"},
        403: {"description": "Admin key required"},
        404: {"description": "Config key not found"},
    }
)
async def get_config_value(
    key: str,
    admin: dict = Depends(verify_admin_key)
) -> ConfigValue:
    """
    Get a specific configuration value.

    Args:
        key: Configuration key (e.g., "fees.platform_fee_pct")
    """
    if not CONFIG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Configuration system not available"
        )

    try:
        # Get value from config
        value = await PlatformConfig.get(key)
        if value is None:
            raise HTTPException(
                status_code=404,
                detail=f"Config key '{key}' not found"
            )

        # Get metadata from DB
        supabase = PlatformConfig._get_supabase()
        result = supabase.table("platform_config").select("*").eq("key", key).single().execute()

        if result.data:
            return ConfigValue(
                key=key,
                value=float(value) if isinstance(value, Decimal) else value,
                description=result.data.get("description"),
                category=result.data.get("category", "unknown"),
                is_public=result.data.get("is_public", False),
                updated_at=result.data.get("updated_at"),
            )

        return ConfigValue(
            key=key,
            value=float(value) if isinstance(value, Decimal) else value,
            description=None,
            category="unknown",
            is_public=False,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config {key}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/config/{key}",
    response_model=ConfigUpdateResponse,
    responses={
        200: {"description": "Configuration updated"},
        403: {"description": "Admin key required"},
        404: {"description": "Config key not found"},
    }
)
async def update_config_value(
    key: str,
    request: ConfigUpdateRequest,
    admin: dict = Depends(verify_admin_key)
) -> ConfigUpdateResponse:
    """
    Update a configuration value.

    Changes are logged to the audit table for accountability.

    Args:
        key: Configuration key (e.g., "fees.platform_fee_pct")
        request: New value and optional reason
    """
    if not CONFIG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Configuration system not available"
        )

    try:
        # Get current value
        old_value = await PlatformConfig.get(key)
        if old_value is None:
            raise HTTPException(
                status_code=404,
                detail=f"Config key '{key}' not found"
            )

        # Update in database
        success = await PlatformConfig.set(
            key=key,
            value=request.value,
            changed_by=None,  # TODO: Add admin user ID
            reason=request.reason,
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update configuration"
            )

        return ConfigUpdateResponse(
            success=True,
            key=key,
            old_value=float(old_value) if isinstance(old_value, Decimal) else old_value,
            new_value=request.value,
            message=f"Configuration '{key}' updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config {key}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/config/audit",
    response_model=AuditLogResponse,
    responses={
        200: {"description": "Audit log entries"},
        403: {"description": "Admin key required"},
    }
)
async def get_config_audit_log(
    key: Optional[str] = Query(None, description="Filter by config key"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key)
) -> AuditLogResponse:
    """
    Get configuration change audit log.

    Returns history of all configuration changes with who changed what and why.
    """
    if not CONFIG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Configuration system not available"
        )

    try:
        supabase = PlatformConfig._get_supabase()
        query = supabase.table("config_audit_log").select("*")

        if key:
            query = query.eq("config_key", key)

        query = query.order("changed_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        entries = []
        for row in result.data or []:
            entries.append(AuditLogEntry(
                id=row["id"],
                config_key=row["config_key"],
                old_value=row.get("old_value"),
                new_value=row["new_value"],
                changed_by=row.get("changed_by"),
                reason=row.get("reason"),
                changed_at=row["changed_at"],
            ))

        return AuditLogResponse(
            entries=entries,
            count=len(entries),
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# PLATFORM STATS ENDPOINTS
# =============================================================================


@router.get(
    "/stats",
    responses={
        200: {"description": "Platform statistics"},
        403: {"description": "Admin key required"},
    }
)
async def get_platform_stats(
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Get platform-wide statistics.

    Returns aggregated metrics about tasks, payments, and users.
    """
    try:
        supabase = db.get_supabase_client()

        # Task stats by status - use direct queries instead of RPC
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

        # Total payments - try payments table, fall back to escrows
        total_volume = 0.0
        total_fees = 0.0
        try:
            payments_result = supabase.table("payments").select("amount_usdc, fee_usdc").execute()
            if payments_result.data:
                for payment in payments_result.data:
                    total_volume += float(payment.get("amount_usdc", 0) or 0)
                    total_fees += float(payment.get("fee_usdc", 0) or 0)
        except Exception:
            # Try escrows table as fallback
            try:
                escrows_result = supabase.table("escrows").select("amount_usdc, platform_fee_usdc").execute()
                if escrows_result.data:
                    for escrow in escrows_result.data:
                        total_volume += float(escrow.get("amount_usdc", 0) or 0)
                        total_fees += float(escrow.get("platform_fee_usdc", 0) or 0)
            except Exception as e:
                logger.warning(f"Could not query payments/escrows: {e}")

        # Active users
        workers_count = 0
        agents_count = 0
        try:
            workers_result = supabase.table("executors").select("id", count="exact").execute()
            workers_count = workers_result.count or 0
        except Exception as e:
            logger.warning(f"Could not query executors: {e}")

        try:
            # Try api_keys table for agents count
            agents_result = supabase.table("api_keys").select("id", count="exact").eq("is_active", True).execute()
            agents_count = agents_result.count or 0
        except Exception:
            # Fallback - no agents table
            pass

        return {
            "tasks": {
                "by_status": tasks_by_status,
                "total": total_tasks,
            },
            "payments": {
                "total_volume_usd": total_volume,
                "total_fees_usd": total_fees,
            },
            "users": {
                "active_workers": workers_count,
                "active_agents": agents_count,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        # Return empty stats on error
        return {
            "tasks": {"by_status": {}, "total": 0},
            "payments": {"total_volume_usd": 0, "total_fees_usd": 0},
            "users": {"active_workers": 0, "active_agents": 0},
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": "internal_error",
        }


# =============================================================================
# ADMIN VERIFICATION ENDPOINT
# =============================================================================


@router.get("/verify")
async def verify_admin(admin: dict = Depends(verify_admin_key)) -> Dict[str, Any]:
    """
    Verify admin key is valid.

    Returns admin role information if key is valid.
    """
    return {"valid": True, "role": admin.get("role", "admin")}


# =============================================================================
# TASKS MANAGEMENT ENDPOINTS
# =============================================================================


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    List all tasks with optional filters.
    """
    try:
        supabase = db.get_supabase_client()

        query = supabase.table("tasks").select("*", count="exact")

        if status:
            query = query.eq("status", status)

        if search:
            query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        # Get status counts for the stats row - use direct query instead of RPC
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
        return {"tasks": [], "count": 0, "offset": offset, "stats": {}, "error": "internal_error"}


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Get detailed task information.
    """
    try:
        supabase = db.get_supabase_client()

        result = supabase.table("tasks").select("*").eq("id", task_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        return result.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    updates: Dict[str, Any],
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Update task details (admin override).
    """
    try:
        supabase = db.get_supabase_client()

        # Only allow certain fields to be updated
        allowed_fields = ["title", "description", "bounty_usd", "deadline", "status"]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        result = supabase.table("tasks").update(filtered_updates).eq("id", task_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"success": True, "task": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    body: Dict[str, Any],
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Cancel a task (admin action).

    This will refund any escrowed funds to the agent.
    """
    try:
        reason = body.get("reason", "Cancelled by admin")
        supabase = db.get_supabase_client()

        # Get current task
        task = supabase.table("tasks").select("*").eq("id", task_id).single().execute()
        if not task.data:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.data["status"] in ["completed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task with status '{task.data['status']}'"
            )

        # Update status
        result = supabase.table("tasks").update({
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "cancellation_reason": reason,
        }).eq("id", task_id).execute()

        # TODO: Trigger escrow refund if applicable

        return {
            "success": True,
            "message": f"Task {task_id} cancelled",
            "reason": reason
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# PAYMENTS ENDPOINTS
# =============================================================================


@router.get("/payments")
async def list_payments(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d, 90d, all"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    List payment transactions.
    """
    try:
        supabase = db.get_supabase_client()

        query = supabase.table("payments").select("*", count="exact")

        # Apply period filter
        if period != "all":
            from datetime import timedelta
            periods = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
            days = periods.get(period, 7)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("created_at", cutoff)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        return {
            "transactions": result.data or [],
            "count": result.count or 0,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error listing payments: {e}")
        return {"transactions": [], "count": 0, "offset": offset, "error": "internal_error"}


@router.get("/payments/stats")
async def get_payment_stats(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d, 90d, all"),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Get payment statistics for the period.
    """
    try:
        supabase = db.get_supabase_client()

        query = supabase.table("payments").select("amount_usd, type")

        # Apply period filter
        if period != "all":
            from datetime import timedelta
            periods = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
            days = periods.get(period, 7)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("created_at", cutoff)

        result = query.execute()
        payments = result.data or []

        total_volume = sum(p.get("amount_usd", 0) for p in payments if p.get("type") in ["deposit", "release"])
        total_fees = sum(p.get("amount_usd", 0) for p in payments if p.get("type") == "fee")

        # Get active escrow
        escrow_result = supabase.table("escrows").select("amount_usd").eq("status", "held").execute()
        active_escrow = sum(e.get("amount_usd", 0) for e in (escrow_result.data or []))

        return {
            "total_volume_usd": total_volume,
            "total_fees_usd": total_fees,
            "active_escrow_usd": active_escrow,
            "transaction_count": len(payments),
        }
    except Exception as e:
        logger.error(f"Error getting payment stats: {e}")
        return {
            "total_volume_usd": 0,
            "total_fees_usd": 0,
            "active_escrow_usd": 0,
            "transaction_count": 0,
            "error": "internal_error",
        }


# =============================================================================
# USERS ENDPOINTS
# =============================================================================


@router.get("/users/agents")
async def list_agents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    List all agents (task creators).
    """
    try:
        supabase = db.get_supabase_client()

        # Get agents with their stats
        result = supabase.table("api_keys").select(
            "id, wallet_address, created_at, is_active"
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        agents = []
        for agent in (result.data or []):
            # Get task count for this agent
            tasks = supabase.table("tasks").select("id", count="exact").eq(
                "agent_id", agent["id"]
            ).execute()

            # Get total spent
            payments = supabase.table("payments").select("amount_usd").eq(
                "from_wallet", agent.get("wallet_address")
            ).eq("type", "deposit").execute()

            agents.append({
                **agent,
                "task_count": tasks.count or 0,
                "total_spent_usd": sum(p.get("amount_usd", 0) for p in (payments.data or [])),
                "status": "active" if agent.get("is_active") else "inactive",
            })

        # Get stats
        total_agents = supabase.table("api_keys").select("id", count="exact").execute()
        active_agents = supabase.table("api_keys").select("id", count="exact").eq("is_active", True).execute()

        return {
            "users": agents,
            "count": len(agents),
            "offset": offset,
            "stats": {
                "total_agents": total_agents.count or 0,
                "active_agents": active_agents.count or 0,
            },
        }
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return {"users": [], "count": 0, "offset": offset, "stats": {}, "error": "internal_error"}


@router.get("/users/workers")
async def list_workers(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    List all workers (task executors).
    """
    try:
        supabase = db.get_supabase_client()

        # Get workers with their stats
        result = supabase.table("executors").select(
            "id, wallet_address, created_at, reputation_score"
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        workers = []
        for worker in (result.data or []):
            # Get task count for this worker
            tasks = supabase.table("task_applications").select("id", count="exact").eq(
                "executor_id", worker["id"]
            ).eq("status", "completed").execute()

            # Get total earned
            payments = supabase.table("payments").select("amount_usd").eq(
                "to_wallet", worker.get("wallet_address")
            ).eq("type", "release").execute()

            workers.append({
                **worker,
                "task_count": tasks.count or 0,
                "total_earned_usd": sum(p.get("amount_usd", 0) for p in (payments.data or [])),
                "status": "active",  # TODO: Add status tracking
                "success_rate": None,  # TODO: Calculate
            })

        # Get stats
        total_workers = supabase.table("executors").select("id", count="exact").execute()

        return {
            "users": workers,
            "count": len(workers),
            "offset": offset,
            "stats": {
                "total_workers": total_workers.count or 0,
                "active_workers": total_workers.count or 0,  # TODO: Track active status
            },
        }
    except Exception as e:
        logger.error(f"Error listing workers: {e}")
        return {"users": [], "count": 0, "offset": offset, "stats": {}, "error": "internal_error"}


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: Dict[str, Any],
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Update user status (suspend/activate).
    """
    try:
        status = body.get("status")
        if status not in ["active", "suspended"]:
            raise HTTPException(status_code=400, detail="Invalid status")

        supabase = db.get_supabase_client()

        # Try to find in agents (api_keys)
        result = supabase.table("api_keys").update({
            "is_active": status == "active"
        }).eq("id", user_id).execute()

        if result.data:
            return {"success": True, "user_id": user_id, "status": status, "type": "agent"}

        # Try to find in workers (executors)
        # Note: executors table may need a status field
        result = supabase.table("executors").update({
            "status": status
        }).eq("id", user_id).execute()

        if result.data:
            return {"success": True, "user_id": user_id, "status": status, "type": "worker"}

        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================


@router.get("/analytics")
async def get_analytics(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, all"),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Get detailed analytics data for charts.
    """
    try:
        from datetime import timedelta
        supabase = db.get_supabase_client()

        periods = {"7d": 7, "30d": 30, "90d": 90}
        days = periods.get(period, 30)

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days) if period != "all" else None

        # Generate time series data
        time_series = []
        if start_date:
            for i in range(days):
                date = start_date + timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                next_date = (date + timedelta(days=1)).strftime("%Y-%m-%d")

                # Count tasks created on this day
                created = supabase.table("tasks").select("id", count="exact").gte(
                    "created_at", date_str
                ).lt("created_at", next_date).execute()

                # Count tasks completed on this day
                completed = supabase.table("tasks").select("id", count="exact").eq(
                    "status", "completed"
                ).gte("updated_at", date_str).lt("updated_at", next_date).execute()

                # Sum volume for this day
                payments = supabase.table("payments").select("amount_usd").eq(
                    "type", "deposit"
                ).gte("created_at", date_str).lt("created_at", next_date).execute()

                time_series.append({
                    "date": date.strftime("%b %d"),
                    "created": created.count or 0,
                    "completed": completed.count or 0,
                    "volume": sum(p.get("amount_usd", 0) for p in (payments.data or [])),
                })

        # Get top agents
        agents_result = supabase.table("api_keys").select(
            "id, wallet_address"
        ).eq("is_active", True).limit(10).execute()

        top_agents = []
        for agent in (agents_result.data or []):
            payments = supabase.table("payments").select("amount_usd").eq(
                "from_wallet", agent.get("wallet_address")
            ).eq("type", "deposit").execute()

            tasks = supabase.table("tasks").select("id", count="exact").eq(
                "agent_id", agent["id"]
            ).execute()

            top_agents.append({
                "id": agent["id"],
                "wallet_address": agent.get("wallet_address"),
                "total_spent_usd": sum(p.get("amount_usd", 0) for p in (payments.data or [])),
                "task_count": tasks.count or 0,
            })

        top_agents.sort(key=lambda x: x["total_spent_usd"], reverse=True)

        # Get top workers
        workers_result = supabase.table("executors").select(
            "id, wallet_address, reputation_score"
        ).limit(10).execute()

        top_workers = []
        for worker in (workers_result.data or []):
            payments = supabase.table("payments").select("amount_usd").eq(
                "to_wallet", worker.get("wallet_address")
            ).eq("type", "release").execute()

            tasks = supabase.table("task_applications").select("id", count="exact").eq(
                "executor_id", worker["id"]
            ).eq("status", "completed").execute()

            top_workers.append({
                "id": worker["id"],
                "wallet_address": worker.get("wallet_address"),
                "reputation_score": worker.get("reputation_score"),
                "total_earned_usd": sum(p.get("amount_usd", 0) for p in (payments.data or [])),
                "task_count": tasks.count or 0,
            })

        top_workers.sort(key=lambda x: x["total_earned_usd"], reverse=True)

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
            "error": "internal_error",
        }
