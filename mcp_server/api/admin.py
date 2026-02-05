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
        raise HTTPException(
            status_code=503,
            detail="Admin access not configured"
        )

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
        raise HTTPException(
            status_code=403,
            detail="Invalid admin key"
        )

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
    key: str
    value: Any
    description: Optional[str] = None
    category: str
    is_public: bool
    updated_at: Optional[datetime] = None


class AllConfigResponse(BaseModel):
    fees: Dict[str, Any]
    limits: Dict[str, Any]
    timing: Dict[str, Any]
    features: Dict[str, Any]
    payments: Dict[str, Any]
    treasury: Dict[str, Any]


class ConfigUpdateRequest(BaseModel):
    value: Any = Field(..., description="New value")
    reason: Optional[str] = Field(None, description="Reason for change (for audit log)")


class ConfigUpdateResponse(BaseModel):
    success: bool
    key: str
    old_value: Any
    new_value: Any
    message: str


class AuditLogEntry(BaseModel):
    id: str
    config_key: str
    old_value: Any
    new_value: Any
    changed_by: Optional[str]
    reason: Optional[str]
    changed_at: datetime


class AuditLogResponse(BaseModel):
    entries: List[AuditLogEntry]
    count: int
    offset: int


# =============================================================================
# ADMIN VERIFICATION ENDPOINT
# =============================================================================


@router.get("/verify")
async def verify_admin(admin: dict = Depends(verify_admin_key)) -> Dict[str, Any]:
    return {"valid": True, "role": admin.get("role", "admin")}


# =============================================================================
# CONFIG ENDPOINTS
# IMPORTANT: /config/audit MUST be defined BEFORE /config/{key}
# to avoid FastAPI matching "audit" as a {key} parameter.
# =============================================================================


@router.get("/config", response_model=AllConfigResponse)
async def get_all_config(
    admin: dict = Depends(verify_admin_key)
) -> AllConfigResponse:
    """Get all platform configuration values grouped by category."""
    if not CONFIG_AVAILABLE:
        raise HTTPException(status_code=503, detail="Configuration system not available")

    try:
        supabase = db.get_supabase_client()

        # Query all config rows directly from DB
        result = supabase.table("platform_config").select(
            "key, value, category"
        ).execute()

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

        for row in (result.data or []):
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


@router.get("/config/audit", response_model=AuditLogResponse)
async def get_config_audit_log(
    key: Optional[str] = Query(None, description="Filter by config key"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None, description="Filter by category prefix"),
    admin: dict = Depends(verify_admin_key)
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
            count=result.count or len(entries),
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        return AuditLogResponse(entries=[], count=0, offset=offset)


@router.get("/config/{key}", response_model=ConfigValue)
async def get_config_value(
    key: str,
    admin: dict = Depends(verify_admin_key)
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


@router.put("/config/{key}", response_model=ConfigUpdateResponse)
async def update_config_value(
    key: str,
    request: ConfigUpdateRequest,
    admin: dict = Depends(verify_admin_key)
) -> ConfigUpdateResponse:
    """Update a configuration value. Changes are logged to the audit table."""
    try:
        supabase = db.get_supabase_client()

        # Get current value
        current = supabase.table("platform_config").select("value").eq("key", key).execute()
        if not current.data:
            raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

        old_value = current.data[0]["value"]

        # Pass raw value to Supabase — the client handles JSONB serialization.
        # Do NOT json.dumps() — that double-encodes (e.g. 100 → "100" string).
        new_value = request.value

        # Update directly in DB
        result = supabase.table("platform_config").update({
            "value": new_value,
            "updated_by": admin.get("actor_id"),
        }).eq("key", key).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update configuration")

        # Update audit log reason directly (trigger can't capture session vars via REST)
        if request.reason:
            try:
                latest = supabase.table("config_audit_log").select("id").eq(
                    "config_key", key
                ).order("changed_at", desc=True).limit(1).execute()
                if latest.data:
                    supabase.table("config_audit_log").update({
                        "reason": request.reason,
                    }).eq("id", latest.data[0]["id"]).execute()
            except Exception:
                pass  # Non-critical

        # Invalidate cache
        if CONFIG_AVAILABLE:
            PlatformConfig._cache.pop(key, None)

        logger.info(
            "SECURITY_AUDIT action=admin.config_update actor=%s source=%s key=%s reason_provided=%s",
            admin.get("actor_id"), admin.get("auth_source"), key, bool(request.reason),
        )

        return ConfigUpdateResponse(
            success=True,
            key=key,
            old_value=old_value,
            new_value=new_value,
            message=f"Configuration '{key}' updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config {key}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# PLATFORM STATS ENDPOINTS
# =============================================================================


@router.get("/stats")
async def get_platform_stats(
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
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

        # Financial stats from escrows table (correct columns)
        total_volume = 0.0
        total_fees = 0.0
        active_escrow = 0.0
        try:
            escrows_result = supabase.table("escrows").select(
                "total_amount_usdc, platform_fee_usdc, status"
            ).execute()
            if escrows_result.data:
                for escrow in escrows_result.data:
                    amount = float(escrow.get("total_amount_usdc", 0) or 0)
                    fee = float(escrow.get("platform_fee_usdc", 0) or 0)
                    total_volume += amount
                    total_fees += fee
                    if escrow.get("status") in ("pending", "funded"):
                        active_escrow += amount
        except Exception as e:
            logger.warning(f"Could not query escrows: {e}")

        # Active users
        workers_count = 0
        agents_count = 0
        try:
            workers_result = supabase.table("executors").select("id", count="exact").execute()
            workers_count = workers_result.count or 0
        except Exception as e:
            logger.warning(f"Could not query executors: {e}")

        try:
            agents_result = supabase.table("api_keys").select("id", count="exact").eq("is_active", True).execute()
            agents_count = agents_result.count or 0
        except Exception:
            pass

        return {
            "tasks": {
                "by_status": tasks_by_status,
                "total": total_tasks,
            },
            "payments": {
                "total_volume_usd": round(total_volume, 2),
                "total_fees_usd": round(total_fees, 2),
                "active_escrow_usd": round(active_escrow, 2),
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
            "payments": {"total_volume_usd": 0, "total_fees_usd": 0, "active_escrow_usd": 0},
            "users": {"active_workers": 0, "active_agents": 0},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


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
    """List all tasks with optional filters."""
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


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """Get detailed task information."""
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
                detail=f"Cannot cancel task with status '{task.data['status']}'"
            )

        # Only update columns that exist on the tasks table
        result = supabase.table("tasks").update({
            "status": "cancelled",
            "completion_notes": f"Admin cancel: {reason}",
        }).eq("id", task_id).execute()

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
# PAYMENTS ENDPOINTS (uses escrows table - payments table doesn't exist yet)
# =============================================================================


@router.get("/payments")
async def list_payments(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d, 90d, all"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """List escrow transactions (proxy for payments until payments table exists)."""
    try:
        supabase = db.get_supabase_client()

        query = supabase.table("escrows").select("*", count="exact")

        if period != "all":
            periods = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
            days = periods.get(period, 7)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("created_at", cutoff)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        # Map escrow rows to transaction-like format for the frontend
        transactions = []
        for row in (result.data or []):
            transactions.append({
                "id": row["id"],
                "created_at": row["created_at"],
                "type": _escrow_status_to_type(row.get("status")),
                "amount_usd": float(row.get("total_amount_usdc", 0) or 0),
                "task_id": row.get("task_id"),
                "wallet_address": row.get("agent_id", ""),
                "status": "confirmed" if row.get("status") in ("funded", "released", "refunded") else "pending",
                "tx_hash": row.get("funding_tx"),
                "payment_strategy": "escrow_capture",
            })

        return {
            "transactions": transactions,
            "count": result.count or 0,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error listing payments: {e}")
        return {"transactions": [], "count": 0, "offset": offset}


def _escrow_status_to_type(status: Optional[str]) -> str:
    """Map escrow status to a payment type label."""
    mapping = {
        "pending": "deposit",
        "funded": "deposit",
        "released": "release",
        "partial_released": "partial_release",
        "refunded": "refund",
        "disputed": "dispute",
        "expired": "expired",
    }
    return mapping.get(status or "", "unknown")


@router.get("/payments/stats")
async def get_payment_stats(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d, 90d, all"),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """Get payment statistics for the period."""
    try:
        supabase = db.get_supabase_client()

        query = supabase.table("escrows").select(
            "total_amount_usdc, platform_fee_usdc, status, created_at"
        )

        if period != "all":
            periods = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
            days = periods.get(period, 7)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            query = query.gte("created_at", cutoff)

        result = query.execute()
        escrows = result.data or []

        total_volume = sum(float(e.get("total_amount_usdc", 0) or 0) for e in escrows)
        total_fees = sum(float(e.get("platform_fee_usdc", 0) or 0) for e in escrows)
        active_escrow = sum(
            float(e.get("total_amount_usdc", 0) or 0)
            for e in escrows
            if e.get("status") in ("pending", "funded")
        )

        return {
            "total_volume_usd": round(total_volume, 2),
            "total_fees_usd": round(total_fees, 2),
            "active_escrow_usd": round(active_escrow, 2),
            "transaction_count": len(escrows),
        }
    except Exception as e:
        logger.error(f"Error getting payment stats: {e}")
        return {
            "total_volume_usd": 0,
            "total_fees_usd": 0,
            "active_escrow_usd": 0,
            "transaction_count": 0,
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
    """List all agents (task creators)."""
    try:
        supabase = db.get_supabase_client()

        # api_keys columns: id, key_prefix, agent_id, name, tier, is_active, usage_count, created_at
        result = supabase.table("api_keys").select(
            "id, key_prefix, agent_id, name, tier, is_active, usage_count, created_at"
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        agents = []
        for agent in (result.data or []):
            # Count tasks by agent_id (the ERC-8004 identifier)
            agent_id = agent.get("agent_id") or agent["id"]
            tasks = supabase.table("tasks").select("id", count="exact").eq(
                "agent_id", agent_id
            ).execute()

            # Sum total spent from escrows
            total_spent = 0.0
            try:
                escrows = supabase.table("escrows").select("total_amount_usdc").eq(
                    "agent_id", agent_id
                ).execute()
                total_spent = sum(float(e.get("total_amount_usdc", 0) or 0) for e in (escrows.data or []))
            except Exception:
                pass

            agents.append({
                "id": agent["id"],
                "wallet_address": agent.get("agent_id", ""),  # Frontend expects wallet_address
                "name": agent.get("name", agent.get("key_prefix", "")),
                "tier": agent.get("tier", "free"),
                "created_at": agent["created_at"],
                "task_count": tasks.count or 0,
                "total_spent_usd": round(total_spent, 2),
                "status": "active" if agent.get("is_active") else "suspended",
                "usage_count": agent.get("usage_count", 0),
            })

        # Stats
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
        return {"users": [], "count": 0, "offset": offset, "stats": {}}


@router.get("/users/workers")
async def list_workers(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """List all workers (task executors)."""
    try:
        supabase = db.get_supabase_client()

        # executors columns: id, wallet_address, display_name, reputation_score,
        #   status, total_earned_usdc, created_at
        result = supabase.table("executors").select(
            "id, wallet_address, display_name, reputation_score, status, total_earned_usdc, created_at"
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        workers = []
        for worker in (result.data or []):
            # Count completed tasks from tasks table (not task_applications)
            tasks = supabase.table("tasks").select("id", count="exact").eq(
                "executor_id", worker["id"]
            ).eq("status", "completed").execute()

            workers.append({
                "id": worker["id"],
                "wallet_address": worker.get("wallet_address", ""),
                "name": worker.get("display_name", ""),
                "created_at": worker["created_at"],
                "task_count": tasks.count or 0,
                "total_earned_usd": float(worker.get("total_earned_usdc", 0) or 0),
                "reputation_score": worker.get("reputation_score", 0),
                "status": worker.get("status", "active"),
                "success_rate": None,
            })

        # Stats
        total_workers = supabase.table("executors").select("id", count="exact").execute()

        return {
            "users": workers,
            "count": len(workers),
            "offset": offset,
            "stats": {
                "total_workers": total_workers.count or 0,
                "active_workers": total_workers.count or 0,
            },
        }
    except Exception as e:
        logger.error(f"Error listing workers: {e}")
        return {"users": [], "count": 0, "offset": offset, "stats": {}}


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: Dict[str, Any],
    admin: dict = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """Update user status (suspend/activate)."""
    try:
        status = body.get("status")
        if status not in ["active", "suspended"]:
            raise HTTPException(status_code=400, detail="Invalid status")

        supabase = db.get_supabase_client()

        # Try agents first (api_keys)
        result = supabase.table("api_keys").update({
            "is_active": status == "active"
        }).eq("id", user_id).execute()

        if result.data:
            return {"success": True, "user_id": user_id, "status": status, "type": "agent"}

        # Try workers (executors)
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

            all_tasks = supabase.table("tasks").select(
                "created_at, status, updated_at"
            ).gte("created_at", start_str).execute()

            try:
                all_escrows = supabase.table("escrows").select(
                    "total_amount_usdc, created_at"
                ).gte("created_at", start_str).execute()
            except Exception:
                all_escrows = type("R", (), {"data": []})()

            # Build daily maps
            created_by_day: Dict[str, int] = {}
            completed_by_day: Dict[str, int] = {}
            volume_by_day: Dict[str, float] = {}

            for task in (all_tasks.data or []):
                day = task["created_at"][:10]
                created_by_day[day] = created_by_day.get(day, 0) + 1
                if task.get("status") == "completed" and task.get("updated_at"):
                    cday = task["updated_at"][:10]
                    completed_by_day[cday] = completed_by_day.get(cday, 0) + 1

            for escrow in (all_escrows.data or []):
                day = escrow["created_at"][:10]
                amount = float(escrow.get("total_amount_usdc", 0) or 0)
                volume_by_day[day] = volume_by_day.get(day, 0) + amount

            for i in range(days):
                date = start_date + timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                time_series.append({
                    "date": date.strftime("%b %d"),
                    "created": created_by_day.get(date_str, 0),
                    "completed": completed_by_day.get(date_str, 0),
                    "volume": round(volume_by_day.get(date_str, 0), 2),
                })

        # Top agents (by task count)
        agents_result = supabase.table("api_keys").select(
            "id, agent_id, name"
        ).eq("is_active", True).limit(10).execute()

        top_agents = []
        for agent in (agents_result.data or []):
            agent_id = agent.get("agent_id") or agent["id"]
            tasks = supabase.table("tasks").select("id", count="exact").eq(
                "agent_id", agent_id
            ).execute()

            total_spent = 0.0
            try:
                escrows = supabase.table("escrows").select("total_amount_usdc").eq(
                    "agent_id", agent_id
                ).execute()
                total_spent = sum(float(e.get("total_amount_usdc", 0) or 0) for e in (escrows.data or []))
            except Exception:
                pass

            top_agents.append({
                "id": agent["id"],
                "wallet_address": agent_id,
                "name": agent.get("name", ""),
                "total_spent_usd": round(total_spent, 2),
                "task_count": tasks.count or 0,
            })

        top_agents.sort(key=lambda x: x["task_count"], reverse=True)

        # Top workers (by reputation)
        workers_result = supabase.table("executors").select(
            "id, wallet_address, display_name, reputation_score, total_earned_usdc"
        ).order("reputation_score", desc=True).limit(10).execute()

        top_workers = []
        for worker in (workers_result.data or []):
            tasks = supabase.table("tasks").select("id", count="exact").eq(
                "executor_id", worker["id"]
            ).eq("status", "completed").execute()

            top_workers.append({
                "id": worker["id"],
                "wallet_address": worker.get("wallet_address", ""),
                "name": worker.get("display_name", ""),
                "reputation_score": worker.get("reputation_score", 0),
                "total_earned_usd": float(worker.get("total_earned_usdc", 0) or 0),
                "task_count": tasks.count or 0,
            })

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
