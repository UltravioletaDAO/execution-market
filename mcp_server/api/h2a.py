"""
H2A (Human-to-Agent) API Routes

Endpoints for the H2A marketplace direction where humans publish tasks
for AI agents to execute. Uses JWT auth for humans and separate
/api/v1/h2a/* endpoints to avoid breaking existing A2H flows.

Endpoints:
  POST   /api/v1/h2a/tasks                    - Human publishes task
  GET    /api/v1/h2a/tasks                    - List human's published tasks
  GET    /api/v1/h2a/tasks/{task_id}          - View task details
  GET    /api/v1/h2a/tasks/{task_id}/submissions - View agent submissions
  POST   /api/v1/h2a/tasks/{task_id}/approve  - Approve + pay
  POST   /api/v1/h2a/tasks/{task_id}/reject   - Reject submission
  POST   /api/v1/h2a/tasks/{task_id}/cancel   - Cancel task
  GET    /api/v1/agents/directory              - Browse AI agents (public)
  POST   /api/v1/agents/register-executor      - Register agent executor
"""

import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    Path,
    Header,
    Request,
    Response,
)
from pydantic import BaseModel, Field

import supabase_client as db

from .routers._pagination import set_pagination_headers
from models import (
    PublishH2ATaskRequest,
    ApproveH2ASubmissionRequest,
    H2ATaskResponse,
    H2AApprovalResponse,
    AgentDirectoryEntry,
    AgentDirectoryResponse,
)

# Payment event audit trail
from integrations.x402.payment_events import log_payment_event

# Shared escrow chokepoint (sign-on-assignment) — see escrow_lock.py docstring
from integrations.x402.escrow_lock import (
    create_escrow_marker,
    get_escrow_marker,
    lock_with_fresh_auth,
)

# Re-use canonical helpers from routers (avoids duplication)
from .routers._helpers import get_platform_fee_percent, get_payment_dispatcher

logger = logging.getLogger(__name__)

TREASURY_ADDRESS = os.environ.get(
    "EM_TREASURY_ADDRESS", "0xae07B067934975cF3DA0aa1D09cF373b0FED3661"
)


def _h2a_is_owner(task: dict, auth: "JWTData") -> bool:
    """Publisher ownership: session match OR wallet match.

    Anonymous Supabase sessions rotate (Dynamic logout/login), orphaning
    tasks whose ``human_user_id`` points at a dead session — the publisher
    dashboard went empty and assign/approve 403'd on the publisher's own
    tasks. The durable identity is the WALLET: ``verify_jwt_auth`` resolves
    ``auth.wallet_address`` from the executor bound to the current session,
    and that binding was proven with a signed challenge
    (POST /account/link-wallet) — so a wallet match is an equally strong
    ownership proof.

    One session can own SEVERAL proven wallets (external + embedded executors
    bound to the same sub), so the match runs against ALL of them
    (``auth.wallet_addresses``), not just the limit-1 pick — otherwise the
    publisher's own task 403s whenever the lookup favors the other wallet.
    """
    if task.get("human_user_id") == auth.user_id:
        return True
    wallets = {w.lower() for w in (auth.wallet_addresses or []) if w}
    wallet = (auth.wallet_address or "").lower()
    if wallet:
        wallets.add(wallet)
    task_wallet = (task.get("human_wallet") or "").lower()
    return bool(task_wallet) and task_wallet in wallets


def _h2a_owner_filter(auth: "JWTData") -> Optional[str]:
    """PostgREST ``or_`` expression matching tasks owned by this session OR any
    of its proven wallets; None when the session has no wallets (caller falls
    back to the plain ``human_user_id`` filter). Mirrors ``_h2a_is_owner``."""
    wallets = [w.lower() for w in (auth.wallet_addresses or []) if w]
    primary = (auth.wallet_address or "").lower()
    if primary and primary not in wallets:
        wallets.append(primary)
    if not wallets:
        return None
    parts = [f"human_user_id.eq.{auth.user_id}"] + [
        f"human_wallet.eq.{w}" for w in wallets
    ]
    return ",".join(parts)


# Escrow statuses that allow a release/refund — mirror of the releasable set in
# api/routers/_helpers.py (ESCROW-004).
RELEASABLE_ESCROW_STATUSES = {"deposited", "funded", "locked", "active"}


# ---------------------------------------------------------------------------
# JWT Auth for Humans
# ---------------------------------------------------------------------------


class JWTData(BaseModel):
    """Validated JWT token data for human publishers."""

    user_id: str
    wallet_address: Optional[str] = None
    email: Optional[str] = None
    is_human: bool = True
    # ALL wallets proven for this session (one per linked executor profile,
    # most recently active first). wallet_address is always the first entry.
    wallet_addresses: list[str] = Field(default_factory=list)


async def verify_jwt_auth(
    authorization: Optional[str] = Header(None),
) -> JWTData:
    """
    Verify Supabase JWT for human publisher authentication.

    Supports both ES256 (JWKS, new Supabase default) and HS256 (legacy).
    Humans authenticate via their browser session (Dynamic.xyz / Supabase).
    The JWT contains user_id and wallet_address claims.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header required (Bearer <jwt_token>)",
        )

    token = authorization[7:].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    try:
        import jwt as pyjwt

        payload = _decode_supabase_jwt(token, pyjwt)

        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")

        wallet_address = payload.get("wallet_address")
        email = payload.get("email")
        wallet_addresses: list[str] = []

        if not wallet_address:
            try:
                client = db.get_client()
                # One session can have linked multiple wallets (external +
                # embedded executors both bound to the same sub) — fetch ALL
                # of them, ordered by last activity, so ownership checks
                # (_h2a_is_owner) can match any proven wallet. wallet_address
                # stays the most recently active one for callers that need a
                # single value. Endpoints where the exact wallet matters
                # (publish payer) must take it from the request instead of
                # relying on this lookup.
                result = (
                    client.table("executors")
                    .select("wallet_address")
                    .eq("user_id", user_id)
                    .order("updated_at", desc=True)
                    .execute()
                )
                rows = result.data if isinstance(result.data, list) else []
                wallet_addresses = [
                    r.get("wallet_address")
                    for r in rows
                    if isinstance(r, dict) and r.get("wallet_address")
                ]
                if wallet_addresses:
                    wallet_address = wallet_addresses[0]
            except Exception as e:
                logger.warning("Could not look up wallet for user %s: %s", user_id, e)

        if wallet_address and not wallet_addresses:
            wallet_addresses = [wallet_address]

        return JWTData(
            user_id=user_id,
            wallet_address=wallet_address,
            email=email,
            wallet_addresses=wallet_addresses,
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="JWT library not available")
    except HTTPException:
        raise
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError as e:
        logger.warning("H2A JWT validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")


# Cache the JWKS client to avoid fetching keys on every request
_jwks_client: object | None = None


def _get_jwks_client():
    """Lazy-init a PyJWKClient for the Supabase JWKS endpoint."""
    global _jwks_client
    if _jwks_client is None:
        from jwt import PyJWKClient

        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        if supabase_url:
            _jwks_client = PyJWKClient(
                f"{supabase_url}/auth/v1/.well-known/jwks.json",
                cache_keys=True,
                lifespan=3600,
            )
    return _jwks_client


def _decode_supabase_jwt(token: str, pyjwt) -> dict:
    """
    Decode a Supabase JWT, trying ES256 (JWKS) first, then HS256 fallback.
    """
    decode_opts = {"verify_exp": True, "verify_aud": False}

    # --- Attempt 1: ES256 via JWKS (new Supabase default) ---
    jwks = _get_jwks_client()
    if jwks is not None:
        try:
            signing_key = jwks.get_signing_key_from_jwt(token)
            return pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                options=decode_opts,
            )
        except (pyjwt.InvalidTokenError, Exception) as e:
            logger.debug("ES256/JWKS decode failed, trying HS256: %s", e)

    # --- Attempt 2: HS256 with shared secret (legacy) ---
    jwt_secret = os.environ.get(
        "SUPABASE_JWT_SECRET",
        os.environ.get("EM_JWT_SECRET", ""),
    )
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")

    return pyjwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"],
        options=decode_opts,
    )


async def verify_auth_method(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Accept either API key (agents) or Supabase JWT (humans).

    This dual-auth helper allows endpoints that both humans and agents
    can access (e.g., viewing task details).
    """
    from .auth import verify_api_key

    # Try API key first (agents)
    if x_api_key and x_api_key.startswith("em_"):
        return await verify_api_key(authorization=None, x_api_key=x_api_key)

    if authorization:
        bearer_token = (
            authorization[7:].strip() if authorization.startswith("Bearer ") else ""
        )

        # API key via Bearer
        if bearer_token.startswith("em_") or bearer_token.startswith("sk_em_"):
            return await verify_api_key(authorization=authorization, x_api_key=None)

        # JWT via Bearer
        if bearer_token.startswith("ey"):
            return await verify_jwt_auth(authorization)

    raise HTTPException(status_code=401, detail="API key or JWT token required")


# ---------------------------------------------------------------------------
# Feature flag helpers
# ---------------------------------------------------------------------------


async def _check_h2a_enabled():
    """Check if H2A feature is enabled."""
    try:
        client = db.get_client()
        result = (
            client.table("platform_config")
            .select("value")
            .eq("key", "feature.h2a_enabled")
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("value") == "false":
            raise HTTPException(
                status_code=403,
                detail="H2A marketplace is not currently enabled",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable — unable to verify feature status",
        )


def _h2a_escrow_enabled() -> bool:
    """True when human-published tasks use x402r escrow (sign-on-assignment).

    Gated by ``EM_H2A_ESCROW_ENABLED`` (default off). The flag only affects
    PUBLISH: tasks created without the escrow marker drain through the legacy
    sign-on-approval behavior regardless of the flag's current value.
    """
    return os.environ.get("EM_H2A_ESCROW_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )


async def _get_h2a_bounty_limits() -> tuple[Decimal, Decimal]:
    """Get H2A bounty limits from config."""
    min_bounty = Decimal("0.01")
    max_bounty = Decimal("500.00")
    try:
        client = db.get_client()
        result = (
            client.table("platform_config")
            .select("key, value")
            .in_("key", ["feature.h2a_min_bounty", "feature.h2a_max_bounty"])
            .execute()
        )
        if result.data:
            for row in result.data:
                if row["key"] == "feature.h2a_min_bounty":
                    min_bounty = Decimal(row["value"])
                elif row["key"] == "feature.h2a_max_bounty":
                    max_bounty = Decimal(row["value"])
    except Exception as e:
        logger.warning(
            "Failed to load H2A bounty limits from config, using defaults: %s", e
        )
    return min_bounty, max_bounty


async def _onramp_hold_active(human_wallet: str) -> tuple[bool, Optional[str]]:
    """Return (blocked, reason) if a recent card-funded onramp is still in hold.

    Chargeback / self-collusion mitigation (F-04): if the publisher funded their
    wallet via MoonPay card within the configured hold window, payout to the
    worker is blocked until the window elapses (card payments can be reversed
    after settlement). This is gated entirely behind ``EM_MOONPAY_ENABLED`` so
    the default crypto-native flow and the test suite are unaffected.

    The hold window is ``EM_ONRAMP_PAYOUT_HOLD_HOURS`` (default 0 = disabled).
    A value of 0 means no hold even when MoonPay is enabled, which keeps the
    bypass explicit and configurable for sandbox/demo.

    Source: ``moonpay_transactions`` mirror (migration 109), matched on the
    destination ``wallet_address``. The mirror is best-effort, so this fails
    OPEN — a query error never blocks a legitimate payout.
    """
    if os.environ.get("EM_MOONPAY_ENABLED", "false").lower() not in (
        "1",
        "true",
        "yes",
    ):
        return False, None

    try:
        hold_hours = float(os.environ.get("EM_ONRAMP_PAYOUT_HOLD_HOURS", "0"))
    except (TypeError, ValueError):
        hold_hours = 0.0
    if hold_hours <= 0 or not human_wallet:
        return False, None

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hold_hours)
        client = db.get_client()
        result = (
            client.table("moonpay_transactions")
            .select("created_at, status")
            .ilike("wallet_address", human_wallet)
            .eq("status", "completed")
            .gte("created_at", cutoff.isoformat())
            .limit(1)
            .execute()
        )
        if result.data:
            return True, (
                f"Payout held: a card-funded onramp completed within the last "
                f"{hold_hours:g}h. Funds are released after the hold window to "
                f"mitigate chargeback risk."
            )
    except Exception as e:
        # Fail open — the mirror is non-authoritative and must never wedge payouts.
        logger.warning("Onramp hold check failed (allowing payout): %s", e)
        return False, None

    return False, None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["H2A Marketplace"])


# ---------------------------------------------------------------------------
# H2A Task Endpoints
# ---------------------------------------------------------------------------


# Canonical neutral route — a human publishes for any party (human/agent/robot).
# The legacy "/api/v1/h2a/tasks" alias stays live (deprecated) so existing web,
# mobile and external integrations never break. Both map to the same handler.
# See MASTER_PLAN_UNIVERSAL_HIRING_MATRIX.md (Task 7.2).
@router.post(
    "/api/v1/publish",
    response_model=H2ATaskResponse,
    status_code=201,
    summary="Publish Task (universal)",
    description="A human publishes a task for any party (human/agent/robot) to execute.",
    tags=["Publish"],
)
@router.post(
    "/api/v1/h2a/tasks",
    response_model=H2ATaskResponse,
    status_code=201,
    summary="Publish H2A Task (deprecated alias of /api/v1/publish)",
    description="Deprecated alias. Use POST /api/v1/publish.",
    tags=["H2A Marketplace"],
    deprecated=True,
)
async def create_h2a_task(
    request: PublishH2ATaskRequest,
    auth: JWTData = Depends(verify_jwt_auth),
):
    """
    Human publishes a task for another party to execute.

    Creates a task with publisher_type='human' and the requested
    target_executor_type (any|human|agent|robot) — the human side of the
    universal hiring matrix. The task surfaces on the matching party's board.

    Payment depends on EM_H2A_ESCROW_ENABLED:
    - Flag ON (escrow-mode, sign-on-assignment): an ``escrows`` marker row is
      created at publish (NO signature — the EIP-3009 nonce commits to the
      receiver, so signing is only possible at assignment when the worker is
      known). Requires an escrow-capable network and bounty <= $100
      (DEPOSIT_LIMIT contract condition).
    - Flag OFF (legacy, sign-on-approval): unchanged — the human signs
      EIP-3009 authorizations only when approving the completed work.
    """
    await _check_h2a_enabled()

    # Resolve human's wallet. PREFER the wallet the client asserts in the
    # request body: it is the ACTIVE wallet in the user's widget — the one they
    # see, hold funds in, and will sign the escrow lock with at assignment.
    # auth.wallet_address comes from an executors.user_id lookup that is
    # AMBIGUOUS when one session has linked multiple wallets (external +
    # embedded): it silently registered the wrong payer and the assign-time
    # signature could never match. Trust model unchanged (self-DoS-only — a
    # wrong address only breaks the publisher's own escrow), and the signed
    # lock at assignment is the real ownership proof.
    wallet = request.publisher_wallet or auth.wallet_address
    if not wallet:
        raise HTTPException(
            status_code=400,
            detail="No wallet address linked to your account. Please connect a wallet first.",
        )
    wallet = wallet.lower()

    # Validate bounty against H2A limits
    bounty = Decimal(str(request.bounty_usd))
    min_bounty, max_bounty = await _get_h2a_bounty_limits()

    if bounty < min_bounty:
        raise HTTPException(
            status_code=400,
            detail=f"Bounty ${bounty} is below H2A minimum ${min_bounty}",
        )
    if bounty > max_bounty:
        raise HTTPException(
            status_code=400,
            detail=f"Bounty ${bounty} exceeds H2A maximum ${max_bounty}",
        )

    # Validate the stablecoin exists on the requested network. NETWORK_CONFIG is
    # the single source of truth; get_token_config raises ValueError on an
    # unsupported network or an unavailable token (e.g. PYUSD outside Ethereum).
    from integrations.x402.sdk_client import get_token_config, has_escrow_support

    try:
        get_token_config(request.payment_network, request.payment_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Escrow-mode validations (EM_H2A_ESCROW_ENABLED).
    escrow_mode = _h2a_escrow_enabled()
    if escrow_mode:
        if not has_escrow_support(request.payment_network):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Network '{request.payment_network}' does not support the "
                    "x402r escrow lifecycle required for escrow-mode tasks "
                    "(Solana is not supported yet). Choose an escrow-capable "
                    "EVM network."
                ),
            )
        if bounty > Decimal("100"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Bounty ${bounty} exceeds the $100 per-deposit limit "
                    "enforced by the escrow contract (DEPOSIT_LIMIT). "
                    "Escrow-mode tasks must have bounty <= $100."
                ),
            )

    # Calculate fees
    platform_fee_pct = await get_platform_fee_percent()
    fee_usd = float(bounty * platform_fee_pct)
    total_required = float(bounty) + fee_usd

    # Calculate deadline
    deadline = datetime.now(timezone.utc) + timedelta(hours=request.deadline_hours)

    # Build evidence schema
    evidence_schema = {
        "required": request.evidence_required,
        "optional": [],
    }

    # Create task in database
    try:
        client = db.get_client()
        task_data = {
            "agent_id": f"human:{auth.user_id}",  # Tag for H2A identification
            "title": request.title,
            "instructions": request.instructions,
            "category": request.category.value
            if hasattr(request.category, "value")
            else request.category,
            "bounty_usd": float(bounty),
            "deadline": deadline.isoformat(),
            "evidence_schema": evidence_schema,
            "payment_token": request.payment_token,
            "payment_network": request.payment_network,
            "status": "published",
            "min_reputation": 0,
            "publisher_type": "human",
            "human_wallet": wallet,
            "human_user_id": auth.user_id,
            # Store the real validated target party (any|human|agent|robot) so the
            # full hiring matrix is expressible. The model validator already
            # constrains the value; empty falls back to the historical 'agent'.
            # See MASTER_PLAN_UNIVERSAL_HIRING_MATRIX.md Task 0.4.
            "target_executor_type": request.target_executor_type or "agent",
            "required_capabilities": request.required_capabilities,
            "verification_mode": request.verification_mode or "manual",
        }

        result = client.table("tasks").insert(task_data).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to create task")

        task = result.data[0]

        if escrow_mode:
            # Marker row (NO signature): tags the task as escrow-mode so
            # assign/approve/cancel route through the escrow lifecycle. An
            # escrow-mode task must never exist without its marker — roll the
            # task back if the insert fails.
            try:
                await create_escrow_marker(
                    task["id"], float(bounty), request.payment_network, wallet
                )
            except Exception as marker_err:
                logger.error(
                    "H2A escrow marker creation failed for task %s: %s "
                    "-- rolling back task",
                    task["id"],
                    marker_err,
                )
                try:
                    client.table("tasks").delete().eq("id", task["id"]).execute()
                except Exception as del_err:
                    logger.error(
                        "H2A task rollback failed for task %s: %s",
                        task["id"],
                        del_err,
                    )
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Task creation failed: escrow marker could not be "
                        "created. No task was published."
                    ),
                )

            # Parity with the A2A publish flow: the expiry sweep
            # (jobs/task_expiration.py) keys its auto-refund on tasks.escrow_id,
            # which only the agent publish path used to set. Best-effort —
            # cancel/refund still work without it.
            try:
                client.table("tasks").update(
                    {"escrow_id": f"escrow_{task['id'][:8]}"}
                ).eq("id", task["id"]).execute()
            except Exception as eid_err:
                logger.warning(
                    "Could not set escrow_id on H2A task %s: %s",
                    task["id"],
                    eid_err,
                )

        logger.info(
            "H2A task created: task_id=%s, user=%s, bounty=$%s, escrow_mode=%s",
            task["id"],
            auth.user_id,
            bounty,
            escrow_mode,
        )

        return H2ATaskResponse(
            task_id=task["id"],
            status="published",
            bounty_usd=float(bounty),
            fee_usd=round(fee_usd, 2),
            total_required_usd=round(total_required, 2),
            deadline=deadline.isoformat(),
            publisher_type="human",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create H2A task: %s", str(e))
        raise HTTPException(status_code=500, detail="Task creation failed")


@router.get(
    "/api/v1/h2a/tasks",
    summary="List H2A Tasks",
    description="List tasks published by the authenticated human, or all published H2A tasks.",
    tags=["H2A Marketplace"],
)
async def list_h2a_tasks(
    request: Request,
    response: Response,
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    my_tasks: bool = Query(
        False, description="Only show my published tasks (requires auth)"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    """
    List H2A tasks. Can be filtered by status and category.

    If my_tasks=true, requires JWT auth and returns only the caller's tasks.
    Otherwise returns all published H2A tasks (public, for agents to browse).
    """
    try:
        client = db.get_client()
        query = (
            client.table("tasks")
            .select(
                "*, executor:executors(id, display_name, reputation_score, capabilities, executor_type)"
            )
            .eq("publisher_type", "human")
        )

        if my_tasks:
            auth = await verify_jwt_auth(authorization)
            # Ownership follows the WALLET(s), not just the rotating anonymous
            # session (see _h2a_is_owner): include tasks published under a
            # previous session of any of the same proven wallets.
            _owner_filter = _h2a_owner_filter(auth)
            if _owner_filter:
                query = query.or_(_owner_filter)
            else:
                query = query.eq("human_user_id", auth.user_id)

        if status:
            query = query.eq("status", status)
        else:
            if not my_tasks:
                # For public listing, show only published tasks
                query = query.eq("status", "published")

        if category:
            query = query.eq("category", category)

        # Count
        count_query = (
            client.table("tasks")
            .select("id", count="exact")
            .eq("publisher_type", "human")
        )
        if my_tasks and authorization:
            try:
                auth_data = await verify_jwt_auth(authorization)
                _count_filter = _h2a_owner_filter(auth_data)
                if _count_filter:
                    count_query = count_query.or_(_count_filter)
                else:
                    count_query = count_query.eq("human_user_id", auth_data.user_id)
            except Exception:
                pass
        if status:
            count_query = count_query.eq("status", status)
        elif not my_tasks:
            count_query = count_query.eq("status", "published")
        if category:
            count_query = count_query.eq("category", category)

        count_result = count_query.execute()
        total = count_result.count if count_result.count else 0

        # Paginated results
        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        tasks = result.data or []

        # Strip PII from public listings (non-owner views)
        if not my_tasks:
            for t in tasks:
                t.pop("human_wallet", None)
                t.pop("human_user_id", None)

        set_pagination_headers(
            response, request, total=total, offset=offset, limit=limit
        )
        return {
            "tasks": tasks,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": total > offset + len(tasks),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list H2A tasks: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/v1/h2a/tasks/{task_id}",
    summary="Get H2A Task Details",
    description="View details of an H2A task.",
    tags=["H2A Marketplace"],
)
async def get_h2a_task(
    task_id: str = Path(..., min_length=36, max_length=36),
    authorization: Optional[str] = Header(None),
):
    """Get details of an H2A task (public; owners see their payer wallet)."""
    try:
        client = db.get_client()
        result = (
            client.table("tasks")
            .select(
                "*, executor:executors(id, display_name, wallet_address, reputation_score, capabilities, executor_type)"
            )
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")

        # The OWNER keeps human_wallet: the escrow lock must be signed by the
        # exact wallet that published (the registered payer) — the dashboard
        # needs it to pick/verify the signing wallet at assignment. Best-effort
        # auth: anonymous viewers get the public (stripped) shape.
        is_owner = False
        if authorization:
            try:
                _viewer = await verify_jwt_auth(authorization)
                is_owner = _h2a_is_owner(task, _viewer)
            except Exception:
                is_owner = False

        # Strip PII from public view
        if not is_owner:
            task.pop("human_wallet", None)
        task.pop("human_user_id", None)

        # Expose escrow state so the frontend can detect escrow-mode /
        # escrow-locked tasks (sign-on-assignment). Best-effort.
        try:
            esc_res = (
                client.table("escrows")
                .select("status, funding_tx")
                .eq("task_id", task_id)
                .limit(1)
                .execute()
            )
            esc_rows = esc_res.data or []
            if esc_rows and isinstance(esc_rows[0], dict):
                task["escrow_status"] = esc_rows[0].get("status")
                task["escrow_tx"] = esc_rows[0].get("funding_tx") or task.get(
                    "escrow_tx"
                )
        except Exception as esc_err:
            logger.warning(
                "Could not load escrow state for H2A task %s: %s", task_id, esc_err
            )

        return task

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get H2A task %s: %s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/v1/h2a/tasks/{task_id}/submissions",
    summary="View Agent Submissions",
    description="View submissions from agents for an H2A task.",
    tags=["H2A Marketplace"],
)
async def get_h2a_submissions(
    task_id: str = Path(..., min_length=36, max_length=36),
    auth: JWTData = Depends(verify_jwt_auth),
):
    """View agent submissions for a task owned by the authenticated human."""
    try:
        # Verify task ownership
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select("id, human_user_id, human_wallet, publisher_type")
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if not _h2a_is_owner(task, auth):
            raise HTTPException(status_code=403, detail="Not your task")

        # Get submissions
        submissions_result = (
            client.table("submissions")
            .select(
                "*, executor:executors(id, display_name, wallet_address, reputation_score, capabilities, executor_type)"
            )
            .eq("task_id", task_id)
            .order("submitted_at", desc=True)
            .execute()
        )

        return {
            "task_id": task_id,
            "submissions": submissions_result.data or [],
            "count": len(submissions_result.data or []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get submissions for H2A task %s: %s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/v1/h2a/tasks/{task_id}/applications",
    summary="View Task Applications",
    description="View the workers who applied to an H2A task. Only the human publisher can view.",
    tags=["H2A Marketplace"],
)
async def get_h2a_applications(
    task_id: str = Path(..., min_length=36, max_length=36),
    auth: JWTData = Depends(verify_jwt_auth),
):
    """List applications for a task owned by the authenticated human publisher.

    The generic GET /tasks/{id}/applications gates ownership on agent_id, which a
    browser publisher (anonymous Supabase JWT) can never satisfy for an H2A task
    (agent_id is 'human:{user_id}'). This is the human-auth twin, mirroring
    get_h2a_submissions.
    """
    try:
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select("id, human_user_id, human_wallet, publisher_type")
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if not _h2a_is_owner(task, auth):
            raise HTTPException(status_code=403, detail="Not your task")

        apps_result = (
            client.table("task_applications")
            .select("id, task_id, executor_id, message, status, created_at")
            .eq("task_id", task_id)
            .order("created_at", desc=False)
            .execute()
        )
        applications = apps_result.data or []

        # Enrich with executor profile (separate lookup — no implicit FK join).
        executor_ids = [a["executor_id"] for a in applications]
        executor_map = {}
        if executor_ids:
            execs = (
                client.table("executors")
                .select(
                    "id, display_name, wallet_address, reputation_score, "
                    "tasks_completed, avg_rating"
                )
                .in_("id", executor_ids)
                .execute()
            )
            executor_map = {e["id"]: e for e in (execs.data or [])}

        for app in applications:
            app["executor"] = executor_map.get(app["executor_id"])

        return {
            "task_id": task_id,
            "applications": applications,
            "count": len(applications),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get applications for H2A task %s: %s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


class H2AAssignRequest(BaseModel):
    """Body for assigning an applied worker to an H2A task."""

    executor_id: str = Field(..., min_length=1, max_length=64)


@router.post(
    "/api/v1/h2a/tasks/{task_id}/assign",
    summary="Assign Worker to Task",
    description=(
        "Assign a worker who applied to an H2A task. Only the human publisher "
        "can assign. Escrow-mode tasks (published with EM_H2A_ESCROW_ENABLED) "
        "require an X-Payment-Auth header: the publisher signs the EIP-3009 "
        "escrow authorization for the chosen worker at assignment "
        "(sign-on-assignment) and funds are locked on-chain before the "
        "assignment is final. Legacy tasks (no escrow marker) keep the "
        "sign-on-approval behavior: status-only assign, funds move only when "
        "the publisher approves the completed work."
    ),
    tags=["H2A Marketplace"],
)
async def assign_h2a_worker(
    task_id: str = Path(..., min_length=36, max_length=36),
    request: H2AAssignRequest = ...,
    auth: JWTData = Depends(verify_jwt_auth),
    x_payment_auth: Optional[str] = Header(None, alias="X-Payment-Auth"),
):
    """Assign an applied worker.

    Escrow-mode (task has a pending_assignment escrow marker): requires
    X-Payment-Auth signed for the chosen worker (the EIP-3009 nonce =
    getHash(paymentInfo) commits to the receiver). The task is moved to
    accepted FIRST, then the escrow is locked via lock_with_fresh_auth();
    on any lock failure the assignment is rolled back to published.

    Legacy drain (no marker): status-only assign, exactly the historical
    sign-on-approval behavior — no escrow is touched.
    """
    try:
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select(
                "id, human_user_id, human_wallet, publisher_type, status, "
                "bounty_usd, payment_network, payment_token"
            )
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if not _h2a_is_owner(task, auth):
            raise HTTPException(status_code=403, detail="Not your task")
        if task.get("status") != "published":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot assign a task in status '{task.get('status')}'. "
                    "Only 'published' tasks can be assigned."
                ),
            )

        # The worker must have an application on file.
        app_result = (
            client.table("task_applications")
            .select("id")
            .eq("task_id", task_id)
            .eq("executor_id", request.executor_id)
            .limit(1)
            .execute()
        )
        if not app_result.data:
            raise HTTPException(
                status_code=404, detail="That worker has not applied to this task."
            )

        marker = await get_escrow_marker(task_id)

        if marker:
            # ── Escrow-mode: sign-on-assignment ──
            if not x_payment_auth:
                raise HTTPException(
                    status_code=402,
                    detail=(
                        "This task is escrow-mode: the publisher must sign the "
                        "EIP-3009 escrow authorization for the chosen worker "
                        "and send it in the X-Payment-Auth header. Use "
                        "GET /api/v1/h2a/payment-config to build the "
                        "paymentInfo for the task's network."
                    ),
                )

            # Resolve the worker wallet BEFORE any mutation.
            exec_result = (
                client.table("executors")
                .select("wallet_address")
                .eq("id", request.executor_id)
                .limit(1)
                .execute()
            )
            exec_rows = exec_result.data or []
            worker_wallet = (
                exec_rows[0].get("wallet_address")
                if exec_rows and isinstance(exec_rows[0], dict)
                else None
            )
            if not worker_wallet:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Worker has no wallet address linked — cannot lock "
                        "escrow for this assignment."
                    ),
                )

            dispatcher = get_payment_dispatcher()

            # Assignment first, lock second (mirrors the REST assign flow);
            # rolled back below if the lock does not land.
            client.table("tasks").update(
                {"executor_id": request.executor_id, "status": "accepted"}
            ).eq("id", task_id).execute()

            lock = await lock_with_fresh_auth(
                task_id,
                task,
                worker_wallet,
                x_payment_auth,
                dispatcher,
                expected_payer=task.get("human_wallet") or "",
            )

            if lock.get("status") == "locked":
                # Mark the chosen application accepted; the rest rejected.
                client.table("task_applications").update({"status": "accepted"}).eq(
                    "task_id", task_id
                ).eq("executor_id", request.executor_id).execute()
                client.table("task_applications").update({"status": "rejected"}).eq(
                    "task_id", task_id
                ).neq("executor_id", request.executor_id).execute()

                logger.info(
                    "H2A task assigned with escrow lock: task=%s, executor=%s, "
                    "user=%s, tx=%s",
                    task_id,
                    request.executor_id,
                    auth.user_id,
                    lock.get("escrow_tx"),
                )

                return {
                    "status": "accepted",
                    "task_id": task_id,
                    "executor_id": request.executor_id,
                    "escrow_tx": lock.get("escrow_tx"),
                }

            # Lock did not land — roll the assignment back to published.
            try:
                client.table("tasks").update(
                    {"status": "published", "executor_id": None}
                ).eq("id", task_id).execute()
            except Exception as revert_err:
                logger.error(
                    "H2A assign rollback failed: task=%s, error=%s",
                    task_id,
                    revert_err,
                )

            if lock.get("status") == "invalid_auth":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Invalid escrow authorization: "
                        f"{lock.get('error', 'validation failed')}"
                    ),
                )
            if lock.get("status") == "lock_failed":
                _ref = str(uuid.uuid4())[:8]
                logger.error(
                    "H2A escrow lock failed for task %s [ref=%s]: %s",
                    task_id,
                    _ref,
                    lock.get("error"),
                )
                raise HTTPException(
                    status_code=402,
                    detail=(
                        f"Escrow lock failed. Task remains published (ref: {_ref})."
                    ),
                )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Escrow lock error: "
                    f"{lock.get('error', 'unexpected failure')}. "
                    "Task remains published."
                ),
            )

        # ── Legacy drain (no escrow marker): sign-on-approval ──
        # Assign: set executor + move to accepted. No escrow is touched here;
        # funds move only when the publisher approves the completed work.
        client.table("tasks").update(
            {"executor_id": request.executor_id, "status": "accepted"}
        ).eq("id", task_id).execute()

        # Mark the chosen application accepted; the rest rejected.
        client.table("task_applications").update({"status": "accepted"}).eq(
            "task_id", task_id
        ).eq("executor_id", request.executor_id).execute()
        client.table("task_applications").update({"status": "rejected"}).eq(
            "task_id", task_id
        ).neq("executor_id", request.executor_id).execute()

        logger.info(
            "H2A task assigned: task=%s, executor=%s, user=%s",
            task_id,
            request.executor_id,
            auth.user_id,
        )

        return {
            "status": "accepted",
            "task_id": task_id,
            "executor_id": request.executor_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("H2A assign failed: task=%s, error=%s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _submit_h2a_publisher_reputation(
    task: dict,
    worker_tx: Optional[str],
    worker_score: Optional[int],
) -> None:
    """Publisher->worker ERC-8004 reputation after H2A approval (best-effort).

    The rater is the HUMAN publisher: their ERC-8004 identity is registered
    gaslessly (idempotent) and the on-chain feedback is attributed to THEM,
    bound to the release TX. This NEVER blocks the payout — every failure is
    logged and swallowed (the worker already has their funds).
    """
    try:
        publisher_wallet = task.get("human_wallet")
        executor_id = task.get("executor_id")
        if not (publisher_wallet and executor_id and worker_tx):
            return

        from integrations.erc8004.identity import ensure_publisher_identity
        from .routers._helpers import _send_reputation_feedback

        client = db.get_client()
        exec_row = (
            client.table("executors")
            .select("id, wallet_address")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        executor = exec_row.data[0] if exec_row.data else None
        worker_address = (executor or {}).get("wallet_address")
        if not worker_address:
            return

        network = task.get("payment_network") or "base"
        publisher_identity = await ensure_publisher_identity(
            publisher_wallet, network=network
        )
        rater_agent_id = (
            str(publisher_identity.agent_id)
            if publisher_identity.agent_id is not None
            else None
        )

        # Star rating (1-5) -> 0-100. None lets the grace-window default (Phase 5)
        # cover an approval that arrived without a score.
        score = worker_score * 20 if worker_score else None

        await _send_reputation_feedback(
            task=task,
            worker_address=worker_address,
            release_tx=worker_tx,
            executor=executor,
            override_score=score,
            rater_agent_id=rater_agent_id,
            rater_type="publisher",
        )
    except Exception as e:
        logger.error(
            "H2A publisher->worker reputation failed (non-blocking): task=%s, error=%s",
            task.get("id"),
            e,
        )


@router.post(
    "/api/v1/h2a/tasks/{task_id}/approve",
    response_model=H2AApprovalResponse,
    summary="Approve Agent Submission",
    description="Human approves agent's work and provides signed payment authorizations.",
    tags=["H2A Marketplace"],
)
async def approve_h2a_submission(
    task_id: str,
    request: ApproveH2ASubmissionRequest,
    auth: JWTData = Depends(verify_jwt_auth),
):
    """
    Human approves agent's work.

    For verdict='accepted', the payment path depends on the task's escrow:
    - Escrow-mode (releasable escrows row — sign-on-assignment tasks): the
      locked escrow is released to the worker via the Facilitator (1 TX,
      atomic 87/13 split on-chain). NO settlement signatures are needed;
      settlement_auth_* fields are ignored if sent.
    - Legacy (no escrow): sign-on-approval — requires both signatures:
      - settlement_auth_worker: EIP-3009 auth (human → agent, bounty amount)
      - settlement_auth_fee: EIP-3009 auth (human → treasury, 13% fee)
      Both are settled via the Facilitator for gasless on-chain transfer.

    For verdict='rejected' / 'needs_revision': NO escrow operation happens —
    a locked escrow stays locked. Refund only via cancel or deadline expiry
    (mirrors the A2A flow).
    """
    try:
        # Validate task ownership
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select(
                "id, human_user_id, human_wallet, publisher_type, bounty_usd, "
                "status, payment_network, payment_token"
            )
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if not _h2a_is_owner(task, auth):
            raise HTTPException(status_code=403, detail="Not your task")

        # Validate task is in an approvable status
        approvable_statuses = {"submitted", "in_progress"}
        current_status = task.get("status")
        if current_status not in approvable_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve task in status '{current_status}'. "
                f"Only tasks in {approvable_statuses} can be approved.",
            )

        # Get submission
        sub_result = (
            client.table("submissions")
            .select("*, executor:executors(id, wallet_address, display_name)")
            .eq("id", request.submission_id)
            .eq("task_id", task_id)
            .single()
            .execute()
        )

        if not sub_result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        submission = sub_result.data
        executor = submission.get("executor", {})
        agent_wallet = executor.get("wallet_address")

        # Idempotency: a submission already finalized (accepted/rejected) must
        # NOT be re-processed. Without this, a rejected submission could be
        # re-POSTed as 'accepted' and paid (the task may still be in a
        # processable status). Mirrors the A2A guard in routers/submissions.py.
        # 'more_info_requested' is intentionally NOT blocked — it's an
        # intermediate state; the worker resubmits by updating this same
        # submission (its verdict resets to 'pending') and the publisher
        # reviews the refreshed evidence.
        prior_verdict = submission.get("agent_verdict")
        if prior_verdict in ("accepted", "rejected"):
            raise HTTPException(
                status_code=409,
                detail=f"Submission already finalized with verdict "
                f"'{prior_verdict}'. It cannot be re-processed.",
            )

        if request.verdict == "accepted":
            # Reputation enforcement (Phase 5): the publisher MUST rate the
            # worker (1-5 stars) to approve+pay. On-chain bidirectional
            # reputation is what makes the market trustless — it is NOT
            # optional. Escape hatch for incident response only:
            # EM_H2A_REQUIRE_RATING=false.
            require_rating = os.environ.get(
                "EM_H2A_REQUIRE_RATING", "true"
            ).lower() not in ("false", "0", "no")
            if require_rating and request.worker_score is None:
                raise HTTPException(
                    status_code=422,
                    detail="A worker rating (worker_score, 1-5) is required "
                    "to approve and pay.",
                )

            # Anti-self-collusion (F-04): the worker being paid must not be the
            # publisher paying. Same guard style as SC-010 in payment_dispatcher
            # (worker != treasury/operator/payer). Blocks a publisher from
            # funding a task and approving their own wallet as the worker.
            # Applies to BOTH payment branches (escrow release and legacy).
            human_wallet = (task.get("human_wallet") or "").lower()
            worker_wallet = (agent_wallet or "").lower()
            if human_wallet and worker_wallet and human_wallet == worker_wallet:
                logger.error(
                    "H2A approval rejected: worker wallet == publisher wallet "
                    "(self-collusion) task=%s",
                    task_id,
                )
                raise HTTPException(
                    status_code=403,
                    detail="Worker wallet cannot equal the publisher wallet "
                    "(self-payment is not allowed).",
                )

            # Post-onramp hold period (F-04): block payout while a recent
            # card-funded onramp is still reversible. No-op unless MoonPay is
            # enabled AND EM_ONRAMP_PAYOUT_HOLD_HOURS > 0. Both branches.
            _hold_blocked, _hold_reason = await _onramp_hold_active(
                task.get("human_wallet") or ""
            )
            if _hold_blocked:
                raise HTTPException(status_code=403, detail=_hold_reason)

            # Detect a releasable escrow (sign-on-assignment tasks locked at
            # assignment). Best-effort lookup: on error fall through to legacy.
            esc_status = ""
            try:
                esc_res = (
                    client.table("escrows")
                    .select("id, status, funding_tx")
                    .eq("task_id", task_id)
                    .limit(1)
                    .execute()
                )
                esc_rows = esc_res.data or []
                if esc_rows and isinstance(esc_rows[0], dict):
                    esc_status = str(esc_rows[0].get("status") or "").lower()
            except Exception as esc_err:
                logger.warning(
                    "H2A approve: escrow lookup failed for task %s: %s",
                    task_id,
                    esc_err,
                )

            worker_tx = None
            fee_tx = None

            if esc_status in RELEASABLE_ESCROW_STATUSES:
                # ── Escrow-mode release: gasless 1-TX via Facilitator with
                # atomic on-chain fee split. settlement_auth_* are IGNORED —
                # the funds are already locked in escrow.
                dispatcher = get_payment_dispatcher()
                if not dispatcher:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Payment dispatcher unavailable — cannot release "
                            "escrow. Task status unchanged."
                        ),
                    )

                network = task.get("payment_network") or "base"
                token = task.get("payment_token") or "USDC"
                release = await dispatcher.release_direct_to_worker(
                    task_id=task_id,
                    network=network,
                    token=token,
                )
                if not release.get("success"):
                    err = release.get("error") or "release failed"
                    logger.error(
                        "H2A escrow release failed: task=%s, error=%s",
                        task_id,
                        err,
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            f"Escrow release failed: {err}. Task status unchanged."
                        ),
                    )
                worker_tx = release.get("tx_hash")
                fee_tx = release.get("fee_distribute_tx")

                # Finalize the escrows row (mirrors the A2A approve caller in
                # routers/_helpers.py:1546-1553): the dispatcher leaves the
                # claim-state 'releasing'; without this the row sticks there.
                if worker_tx:
                    try:
                        client.table("escrows").update(
                            {
                                "status": "released",
                                "release_tx": worker_tx,
                                "released_at": datetime.now(timezone.utc).isoformat(),
                            }
                        ).eq("task_id", task_id).execute()
                    except Exception as esc_fin_err:
                        logger.warning(
                            "H2A approve: escrow release finalization failed "
                            "for task %s (reconciler will sweep): %s",
                            task_id,
                            esc_fin_err,
                        )
            else:
                # ── Legacy sign-on-approval: requires both signatures.
                if (
                    not request.settlement_auth_worker
                    or not request.settlement_auth_fee
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Payment signatures required for approval "
                        "(settlement_auth_worker and settlement_auth_fee)",
                    )

                # Settlement via Facilitator — imitate the external-agent path
                # (_settle_external_auths): extract each base64 X-Payment header
                # that the web publisher signed and settle worker (bounty) + fee
                # (treasury) through the SDK client, gasless. This is the SAME
                # settlement the KK agents use; the only difference is the
                # signer (browser human vs programmatic agent).
                try:
                    from integrations.x402.sdk_client import get_sdk, SDK_AVAILABLE

                    if not SDK_AVAILABLE:
                        raise RuntimeError("x402 SDK unavailable")
                    sdk = get_sdk()
                    if not sdk:
                        raise RuntimeError("x402 SDK not initialised")

                    fee_pct = await get_platform_fee_percent()
                    bounty_amount = Decimal(str(task.get("bounty_usd", 0)))
                    platform_fee = (bounty_amount * fee_pct).quantize(
                        Decimal("0.000001")
                    )
                    network = task.get("payment_network") or "base"
                    token = task.get("payment_token") or "USDC"

                    settle_result = await sdk._settle_external_auths(
                        task_id=task_id,
                        worker_address=agent_wallet,
                        bounty_amount=bounty_amount,
                        platform_fee=platform_fee,
                        worker_auth_header=request.settlement_auth_worker,
                        fee_auth_header=request.settlement_auth_fee,
                        network=network,
                        token=token,
                    )

                    if not settle_result.get("success"):
                        raise RuntimeError(
                            settle_result.get("error") or "settlement failed"
                        )
                    worker_tx = settle_result.get("tx_hash")
                    fee_tx = settle_result.get("fee_tx_hash")
                except Exception as e:
                    logger.error("H2A payment settlement failed: %s", str(e))
                    # Log the failure as a payment event
                    try:
                        await log_payment_event(
                            event_type="h2a_settle_error",
                            task_id=task_id,
                            tx_hash=None,
                            amount_usdc=task.get("bounty_usd"),
                            from_address=task.get("human_wallet"),
                            to_address=agent_wallet,
                            metadata={
                                "submission_id": request.submission_id,
                                "error": str(e),
                            },
                        )
                    except Exception:
                        pass
                    # Settlement failed — do NOT update task/submission status
                    raise HTTPException(
                        status_code=502,
                        detail=f"Payment settlement failed: {str(e)}. Task status unchanged.",
                    )

                # Log payment events (legacy 2-transfer settlement only — the
                # escrow branch logs 'escrow_release' inside the dispatcher).
                try:
                    await log_payment_event(
                        event_type="h2a_settle_worker",
                        task_id=task_id,
                        tx_hash=worker_tx,
                        amount_usdc=task.get("bounty_usd"),
                        from_address=task.get("human_wallet"),
                        to_address=agent_wallet,
                        metadata={
                            "submission_id": request.submission_id,
                            "publisher_type": "human",
                        },
                    )
                    await log_payment_event(
                        event_type="h2a_settle_fee",
                        task_id=task_id,
                        tx_hash=fee_tx,
                        amount_usdc=float(
                            Decimal(str(task.get("bounty_usd", 0)))
                            * await get_platform_fee_percent()
                        ),
                        from_address=task.get("human_wallet"),
                        to_address=TREASURY_ADDRESS,
                        metadata={
                            "submission_id": request.submission_id,
                            "publisher_type": "human",
                        },
                    )
                except Exception as e:
                    logger.warning("Failed to log H2A payment events: %s", e)

            # Update task + submission status
            try:
                client.table("tasks").update(
                    {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", task_id).execute()

                client.table("submissions").update(
                    {
                        "agent_verdict": "accepted",
                        "agent_notes": request.notes,
                        "payment_tx": worker_tx,
                        "paid_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", request.submission_id).execute()
            except Exception as e:
                logger.error("Failed to update H2A task/submission status: %s", e)

            logger.info(
                "H2A submission approved: task=%s, submission=%s, worker_tx=%s",
                task_id,
                request.submission_id,
                worker_tx,
            )

            # Phase 2 — publisher->worker ERC-8004 reputation. Best-effort,
            # AFTER settle: the payout already landed; reputation never blocks it.
            await _submit_h2a_publisher_reputation(
                task=task,
                worker_tx=worker_tx,
                worker_score=request.worker_score,
            )

            return H2AApprovalResponse(
                status="accepted",
                worker_tx=worker_tx,
                fee_tx=fee_tx,
            )

        elif request.verdict == "rejected":
            # Mark the submission rejected first.
            client.table("submissions").update(
                {
                    "agent_verdict": "rejected",
                    "agent_notes": request.notes,
                }
            ).eq("id", request.submission_id).execute()

            # Refund the locked escrow to the publisher. The worker was
            # rejected, so the funds must NOT reach them. Leaving the task in
            # 'submitted' lets the expiration job auto-settle to the rejected
            # worker (P0 fund loss) — so we unwind the escrow here, mirroring
            # the cancel refund path. Refund uses refundExpiry (a long window),
            # so it works even after the authorization window expired.
            refund_tx = None
            esc_status = ""
            try:
                esc_res = (
                    client.table("escrows")
                    .select("id, status")
                    .eq("task_id", task_id)
                    .limit(1)
                    .execute()
                )
                esc_rows = esc_res.data or []
                if esc_rows and isinstance(esc_rows[0], dict):
                    esc_status = str(esc_rows[0].get("status") or "").lower()
            except Exception as esc_err:
                logger.warning(
                    "H2A reject: escrow lookup failed for task %s: %s",
                    task_id,
                    esc_err,
                )

            if esc_status in RELEASABLE_ESCROW_STATUSES:
                dispatcher = get_payment_dispatcher()
                if not dispatcher:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Payment dispatcher unavailable — submission marked "
                            "rejected but the escrow refund could not run. Cancel "
                            "the task to retry the refund."
                        ),
                    )
                refund = await dispatcher.refund_trustless_escrow(
                    task_id=task_id, reason="h2a_reject"
                )
                if not refund.get("success"):
                    err = refund.get("error") or "refund failed"
                    logger.error(
                        "H2A reject escrow refund failed: task=%s, error=%s",
                        task_id,
                        err,
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            f"Escrow refund failed: {err}. Submission marked "
                            "rejected; cancel the task to retry the refund."
                        ),
                    )
                refund_tx = refund.get("tx_hash")
                try:
                    client.table("escrows").update(
                        {
                            "status": "refunded",
                            "refund_tx": refund_tx,
                            "refunded_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("task_id", task_id).execute()
                    client.table("tasks").update({"refund_tx": refund_tx}).eq(
                        "id", task_id
                    ).execute()
                except Exception as esc_err:
                    logger.warning(
                        "H2A reject: escrow refund finalization failed for task "
                        "%s (reconciler will sweep): %s",
                        task_id,
                        esc_err,
                    )

            # Close the task so the expiration job never auto-pays the rejected
            # worker, and the publisher's dashboard stops showing it pending.
            client.table("tasks").update({"status": "cancelled"}).eq(
                "id", task_id
            ).execute()

            logger.info(
                "H2A submission rejected: task=%s, submission=%s, refund_tx=%s",
                task_id,
                request.submission_id,
                refund_tx,
            )

            return H2AApprovalResponse(
                status="rejected",
                refund_tx=refund_tx,
                notes=request.notes,
            )

        elif request.verdict == "needs_revision":
            # needs_revision does NOT touch the escrow either: funds stay
            # locked while the worker revises (refund only via cancel/expiry).
            client.table("submissions").update(
                {
                    "agent_verdict": "more_info_requested",
                    "agent_notes": request.notes,
                }
            ).eq("id", request.submission_id).execute()

            # Move task back to in_progress so agent can resubmit
            client.table("tasks").update({"status": "in_progress"}).eq(
                "id", task_id
            ).execute()

            logger.info(
                "H2A submission needs revision: task=%s, submission=%s",
                task_id,
                request.submission_id,
            )

            return H2AApprovalResponse(
                status="needs_revision",
                notes=request.notes,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("H2A approval failed: task=%s, error=%s", task_id, str(e))
        raise HTTPException(status_code=500, detail="Approval failed")


@router.post(
    "/api/v1/h2a/tasks/{task_id}/cancel",
    summary="Cancel H2A Task",
    description="Cancel a published H2A task.",
    tags=["H2A Marketplace"],
)
async def cancel_h2a_task(
    task_id: str = Path(..., min_length=36, max_length=36),
    auth: JWTData = Depends(verify_jwt_auth),
):
    """Cancel a published/accepted H2A task.

    Escrow-aware unwind:
    - pending_assignment marker (escrow never locked): free cancel — the task
      is cancelled and the marker row is set to 'cancelled'. No funds moved.
    - deposited escrow (locked at assignment): on-chain refund via
      refund_trustless_escrow(); on failure the task stays unchanged (502).
    - no escrow rows: legacy status-only cancel, exactly as before.
    """
    try:
        client = db.get_client()
        task_result = (
            client.table("tasks")
            .select("id, human_user_id, human_wallet, publisher_type, status")
            .eq("id", task_id)
            .single()
            .execute()
        )

        if not task_result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_result.data
        if task.get("publisher_type") != "human":
            raise HTTPException(status_code=404, detail="Not an H2A task")
        if not _h2a_is_owner(task, auth):
            raise HTTPException(status_code=403, detail="Not your task")

        # 'submitted'/'in_progress' are cancellable too: the publisher can pull
        # a pending delivery (refunding the locked escrow to themselves) instead
        # of being forced to wait for the deadline. This also lets them recover
        # funds if a reject's inline refund failed and left the task pending.
        cancellable = {"published", "accepted", "submitted", "in_progress"}
        if task.get("status") not in cancellable:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in status '{task.get('status')}'. "
                f"Only tasks in {cancellable} can be cancelled.",
            )

        # ── Escrow-mode marker, never locked → free cancel ──
        marker = await get_escrow_marker(task_id)
        if marker:
            client.table("tasks").update({"status": "cancelled"}).eq(
                "id", task_id
            ).execute()
            # Close the marker so the task can never lock later. Best-effort
            # CAS on pending_assignment (a cancelled task cannot be assigned,
            # so a stale marker is inert anyway).
            try:
                client.table("escrows").update({"status": "cancelled"}).eq(
                    "task_id", task_id
                ).eq("status", "pending_assignment").execute()
            except Exception as esc_err:
                logger.warning(
                    "Could not cancel escrow marker for task %s: %s",
                    task_id,
                    esc_err,
                )

            logger.info(
                "H2A escrow-mode task cancelled pre-lock (free): task=%s, user=%s",
                task_id,
                auth.user_id,
            )
            return {"status": "cancelled", "task_id": task_id}

        # ── Deposited escrow → on-chain refund, then cancel ──
        esc_status = ""
        try:
            esc_res = (
                client.table("escrows")
                .select("id, status")
                .eq("task_id", task_id)
                .limit(1)
                .execute()
            )
            esc_rows = esc_res.data or []
            if esc_rows and isinstance(esc_rows[0], dict):
                esc_status = str(esc_rows[0].get("status") or "").lower()
        except Exception as esc_err:
            logger.warning(
                "H2A cancel: escrow lookup failed for task %s: %s",
                task_id,
                esc_err,
            )

        if esc_status in RELEASABLE_ESCROW_STATUSES:
            dispatcher = get_payment_dispatcher()
            if not dispatcher:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Payment dispatcher unavailable — cannot refund "
                        "escrow. Task status unchanged."
                    ),
                )

            refund = await dispatcher.refund_trustless_escrow(
                task_id=task_id, reason="h2a_cancel"
            )
            if not refund.get("success"):
                err = refund.get("error") or "refund failed"
                logger.error(
                    "H2A escrow refund failed: task=%s, error=%s", task_id, err
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Escrow refund failed: {err}. Task status unchanged.",
                )

            refund_tx = refund.get("tx_hash")
            # The dispatcher leaves the row in the transitional 'refunding'
            # claim state — finalize it here (mirror of the REST cancel flow
            # in api/routers/tasks.py).
            try:
                client.table("escrows").update(
                    {
                        "status": "refunded",
                        "refund_tx": refund_tx,
                        "refunded_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("task_id", task_id).execute()
            except Exception as esc_err:
                logger.warning(
                    "Could not mark escrow refunded for task %s: %s",
                    task_id,
                    esc_err,
                )
            try:
                client.table("tasks").update({"refund_tx": refund_tx}).eq(
                    "id", task_id
                ).execute()
            except Exception as tx_err:
                logger.warning(
                    "Could not store refund_tx on task %s: %s", task_id, tx_err
                )

            client.table("tasks").update({"status": "cancelled"}).eq(
                "id", task_id
            ).execute()

            logger.info(
                "H2A task cancelled with escrow refund: task=%s, user=%s, tx=%s",
                task_id,
                auth.user_id,
                refund_tx,
            )
            return {
                "status": "cancelled",
                "task_id": task_id,
                "refund_tx": refund_tx,
            }

        # ── Legacy (no escrow rows): status-only cancel ──
        client.table("tasks").update({"status": "cancelled"}).eq(
            "id", task_id
        ).execute()

        logger.info("H2A task cancelled: task=%s, user=%s", task_id, auth.user_id)

        return {"status": "cancelled", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("H2A cancel failed: task=%s, error=%s", task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/v1/h2a/payment-config",
    summary="H2A Payment Config",
    description=(
        "Public fee/treasury config the web publisher needs to build the fee "
        "EIP-3009 authorization (treasury = payTo for the platform fee), plus "
        "the per-network escrow parameters needed to build the paymentInfo "
        "for sign-on-assignment escrow locks (all public on-chain constants)."
    ),
    tags=["H2A Marketplace"],
)
async def get_h2a_payment_config():
    """Treasury + fee percent + escrow signing parameters per network.

    The ``escrow`` block lets the browser build the EXACT paymentInfo the SDK
    builds (uvd_x402_sdk.advanced_escrow): the EIP-3009 nonce is
    keccak(chainId, escrow, keccak(PAYMENT_INFO_TYPEHASH, paymentInfo tuple
    with payer=0)) and the signed typed-data is ReceiveWithAuthorization over
    the network's USDC EIP-712 domain with to=token_collector.
    """
    fee_pct = await get_platform_fee_percent()

    from integrations.x402.sdk_client import NETWORK_CONFIG, has_escrow_support

    # PAYMENT_INFO_TYPEHASH + tier timings come from the SDK (single source of
    # truth); fall back to the documented protocol constants if unavailable.
    try:
        from uvd_x402_sdk.advanced_escrow import (
            PAYMENT_INFO_TYPEHASH,
            TIER_TIMINGS,
            TaskTier,
        )

        typehash = "0x" + PAYMENT_INFO_TYPEHASH.hex()
        micro = dict(TIER_TIMINGS[TaskTier.MICRO])
        standard = dict(TIER_TIMINGS[TaskTier.STANDARD])
    except Exception:
        typehash = "0xae68ac7ce30c86ece8196b61a7c486d8f0061f575037fbd34e7fe4e2820c6591"
        micro = {"pre": 3600, "auth": 7200, "refund": 86400}
        standard = {"pre": 7200, "auth": 86400, "refund": 604800}

    networks = {}
    for name, cfg in NETWORK_CONFIG.items():
        if not has_escrow_support(name):
            continue
        usdc = (cfg.get("tokens") or {}).get("USDC") or {}
        domain_name = usdc.get("name")
        domain_version = usdc.get("version")
        if not (domain_name and domain_version):
            # NETWORK_CONFIG is checked first; fall back to the SDK's network
            # registry, then to the canonical USDC domain.
            try:
                from uvd_x402_sdk.networks import get_network_by_chain_id

                sdk_net = get_network_by_chain_id(cfg.get("chain_id"))
                if sdk_net is not None:
                    domain_name = domain_name or sdk_net.usdc_domain_name
                    domain_version = domain_version or sdk_net.usdc_domain_version
            except Exception:
                pass
        networks[name] = {
            "chain_id": cfg.get("chain_id"),
            "operator": cfg.get("operator"),
            "escrow": cfg.get("escrow"),
            "token_collector": (cfg.get("x402r_infra") or {}).get("tokenCollector"),
            "usdc": usdc.get("address"),
            "usdc_domain_name": domain_name or "USD Coin",
            "usdc_domain_version": domain_version or "2",
        }

    return {
        "treasury": TREASURY_ADDRESS,
        "fee_pct": float(fee_pct),
        "escrow": {
            "payment_info_typehash": typehash,
            # Canonical fee bounds: max must cover the operator's 1300bps
            # static fee; fee_receiver is the network's operator address.
            "min_fee_bps": 0,
            "max_fee_bps": 1800,
            # Contract condition: $100 max per deposit.
            "deposit_limit_usd": 100,
            # Expiry windows (seconds, relative to now() at signing).
            "tier_timings": {"micro": micro, "standard": standard},
            "networks": networks,
        },
    }


# ---------------------------------------------------------------------------
# Agent Directory Endpoints
# ---------------------------------------------------------------------------


def _format_wallet_display(wallet: str) -> str:
    """Format wallet as 'Agent 0x857f...3a2B'."""
    if not wallet or len(wallet) < 10:
        return f"Agent {wallet}"
    return f"Agent {wallet[:6]}...{wallet[-4:]}"


def _parse_int_safe(val) -> int:
    """Parse value to int, returning 0 on failure."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


@router.get(
    "/api/v1/agents/directory",
    response_model=AgentDirectoryResponse,
    summary="Agent Directory",
    description="Browse AI agents: publishers and executors. Public endpoint.",
    tags=["Agent Directory"],
)
async def get_agent_directory(
    capability: Optional[str] = Query(
        None, description="Filter by capability (comma-separated)"
    ),
    min_rating: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query(
        "rating",
        description="Sort by: rating, tasks_completed, display_name, tasks_published, total_bounty",
    ),
    role: Optional[str] = Query(
        None, description="Filter by role: publisher, executor, both"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Browse the public AI agent directory.

    Returns agents that are registered executors AND/OR task publishers.
    Merges both datasets by wallet address. No authentication required.
    """
    try:
        client = db.get_client()

        # --- 1. Query executor agents ---
        executor_map: dict = {}  # wallet_lower -> entry_dict
        try:
            eq_query = (
                client.table("executors")
                .select("*")
                .eq("executor_type", "agent")
                .not_.is_("display_name", "null")
            )
            exec_result = eq_query.execute()
            for row in exec_result.data or []:
                wallet = (row.get("wallet_address") or "").lower()
                if not wallet:
                    wallet = row["id"].lower()
                executor_map[wallet] = {
                    "executor_id": row["id"],
                    "display_name": row.get("display_name", "Unknown Agent"),
                    "capabilities": row.get("capabilities"),
                    "rating": row.get("reputation_score", 0) or 0,
                    "tasks_completed": row.get("tasks_completed", 0) or 0,
                    "avg_rating": row.get("avg_rating", 0) or 0,
                    "agent_card_url": row.get("agent_card_url"),
                    "mcp_endpoint_url": row.get("mcp_endpoint_url"),
                    "erc8004_agent_id": row.get("erc8004_agent_id"),
                    "verified": row.get("is_verified", False) or False,
                    "bio": row.get("bio"),
                    "avatar_url": row.get("avatar_url"),
                    "pricing": row.get("pricing"),
                    "is_executor": True,
                    "is_publisher": False,
                    "tasks_published": 0,
                    "total_bounty_usd": 0.0,
                    "active_tasks": 0,
                }
        except Exception as e:
            logger.warning("Failed to query executor agents: %s", e)

        # --- 2. Query publisher agents from tasks ---
        # We query ALL tasks that have an agent_id, regardless of publisher_type.
        # This catches AI agents that published tasks but aren't registered as executors.
        # Deduplication is done by erc8004_agent_id when available, falling back to agent_id.
        publisher_map: dict = {}  # dedup_key -> stats
        _erc8004_to_key: dict = {}  # erc8004_agent_id -> dedup_key (for cross-source dedup)
        try:
            pub_query = client.table("tasks").select(
                "agent_id, bounty_usd, status, agent_name, erc8004_agent_id, publisher_type"
            )
            pub_result = pub_query.execute()
            for row in pub_result.data or []:
                agent_id = (row.get("agent_id") or "").lower()
                if not agent_id:
                    continue
                # Skip human-published tasks
                pub_type = row.get("publisher_type")
                if pub_type == "human":
                    continue

                erc_id = _parse_int_safe(row.get("erc8004_agent_id")) or None

                # Determine dedup key: prefer erc8004_agent_id to merge
                # tasks from the same on-chain agent across different wallets
                if erc_id and erc_id in _erc8004_to_key:
                    dedup_key = _erc8004_to_key[erc_id]
                elif erc_id:
                    dedup_key = agent_id
                    _erc8004_to_key[erc_id] = dedup_key
                else:
                    dedup_key = agent_id

                if dedup_key not in publisher_map:
                    publisher_map[dedup_key] = {
                        "tasks_published": 0,
                        "total_bounty_usd": 0.0,
                        "active_tasks": 0,
                        "agent_name": row.get("agent_name"),
                        "erc8004_agent_id": erc_id,
                    }
                publisher_map[dedup_key]["tasks_published"] += 1
                publisher_map[dedup_key]["total_bounty_usd"] += float(
                    row.get("bounty_usd", 0) or 0
                )
                # Prefer a non-None agent_name over existing
                if row.get("agent_name") and not publisher_map[dedup_key].get(
                    "agent_name"
                ):
                    publisher_map[dedup_key]["agent_name"] = row["agent_name"]
                # Backfill erc8004_agent_id if we didn't have it
                if erc_id and not publisher_map[dedup_key].get("erc8004_agent_id"):
                    publisher_map[dedup_key]["erc8004_agent_id"] = erc_id
                status = row.get("status", "")
                if status in ("published", "accepted", "in_progress"):
                    publisher_map[dedup_key]["active_tasks"] += 1
        except Exception as e:
            logger.warning("Failed to query publisher tasks: %s", e)

        # --- 3. Merge datasets ---
        # Dedup across both sources using erc8004_agent_id when available.
        merged: dict = {}
        _erc8004_to_merged_key: dict = {}  # erc8004_agent_id -> merged key

        # Add executors
        for wallet, data in executor_map.items():
            erc_id = _parse_int_safe(data.get("erc8004_agent_id")) or None
            merged[wallet] = data.copy()
            if erc_id:
                _erc8004_to_merged_key[erc_id] = wallet

        # Add/merge publishers — match by wallet key OR erc8004_agent_id
        for agent_id, stats in publisher_map.items():
            erc_id = stats.get("erc8004_agent_id")

            # Find existing merged entry: direct key match or erc8004 cross-match
            merge_target = None
            if agent_id in merged:
                merge_target = agent_id
            elif erc_id and erc_id in _erc8004_to_merged_key:
                merge_target = _erc8004_to_merged_key[erc_id]

            if merge_target is not None:
                # Agent exists as executor — merge publisher stats
                merged[merge_target]["is_publisher"] = True
                merged[merge_target]["tasks_published"] = stats["tasks_published"]
                merged[merge_target]["total_bounty_usd"] = stats["total_bounty_usd"]
                merged[merge_target]["active_tasks"] = stats["active_tasks"]
                if erc_id and not merged[merge_target].get("erc8004_agent_id"):
                    merged[merge_target]["erc8004_agent_id"] = erc_id
            else:
                # Publisher-only agent — create entry from task data
                display = stats.get("agent_name") or (
                    f"Agent #{erc_id}" if erc_id else _format_wallet_display(agent_id)
                )
                merged[agent_id] = {
                    "executor_id": agent_id,
                    "display_name": display,
                    "capabilities": None,
                    "rating": 0,
                    "tasks_completed": 0,
                    "avg_rating": 0,
                    "agent_card_url": None,
                    "mcp_endpoint_url": None,
                    "erc8004_agent_id": erc_id,
                    "verified": False,
                    "bio": None,
                    "avatar_url": None,
                    "pricing": None,
                    "is_executor": False,
                    "is_publisher": True,
                    "tasks_published": stats["tasks_published"],
                    "total_bounty_usd": stats["total_bounty_usd"],
                    "active_tasks": stats["active_tasks"],
                }
                if erc_id:
                    _erc8004_to_merged_key[erc_id] = agent_id

        # --- 4. Assign roles ---
        for wallet, data in merged.items():
            if data.get("is_executor") and data.get("is_publisher"):
                data["role"] = "both"
            elif data.get("is_publisher"):
                data["role"] = "publisher"
            else:
                data["role"] = "executor"

        # --- 5. Apply filters ---
        entries = list(merged.values())

        if role and isinstance(role, str) and role != "all":
            entries = [e for e in entries if e["role"] == role]

        if capability:
            caps = [c.strip() for c in capability.split(",")]
            entries = [
                e
                for e in entries
                if e.get("capabilities") and any(c in e["capabilities"] for c in caps)
            ]

        if min_rating is not None:
            entries = [e for e in entries if e.get("rating", 0) >= min_rating]

        # --- 6. Sort ---
        if sort == "tasks_completed":
            entries.sort(key=lambda e: e.get("tasks_completed", 0), reverse=True)
        elif sort == "display_name":
            entries.sort(key=lambda e: (e.get("display_name") or "").lower())
        elif sort == "tasks_published":
            entries.sort(key=lambda e: e.get("tasks_published", 0), reverse=True)
        elif sort == "total_bounty":
            entries.sort(key=lambda e: e.get("total_bounty_usd", 0), reverse=True)
        else:
            entries.sort(key=lambda e: e.get("rating", 0), reverse=True)

        # --- 7. Paginate ---
        total_count = len(entries)
        offset = (page - 1) * limit
        page_entries = entries[offset : offset + limit]

        agents = []
        for data in page_entries:
            agents.append(
                AgentDirectoryEntry(
                    executor_id=data["executor_id"],
                    display_name=data["display_name"],
                    capabilities=data.get("capabilities"),
                    rating=data.get("rating", 0),
                    tasks_completed=data.get("tasks_completed", 0),
                    avg_rating=data.get("avg_rating", 0) or 0,
                    agent_card_url=data.get("agent_card_url"),
                    mcp_endpoint_url=data.get("mcp_endpoint_url"),
                    erc8004_agent_id=data.get("erc8004_agent_id"),
                    verified=data.get("verified", False),
                    bio=data.get("bio"),
                    avatar_url=data.get("avatar_url"),
                    pricing=data.get("pricing"),
                    role=data.get("role", "executor"),
                    tasks_published=data.get("tasks_published", 0),
                    total_bounty_usd=data.get("total_bounty_usd", 0.0),
                    active_tasks=data.get("active_tasks", 0),
                )
            )

        return AgentDirectoryResponse(
            agents=agents,
            total=total_count,
            page=page,
            limit=limit,
        )

    except Exception as e:
        logger.error("Agent directory query failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/v1/agents/register-executor",
    summary="Register Agent Executor",
    description="Register an AI agent as an executor on the marketplace.",
    tags=["Agent Directory"],
    status_code=201,
)
async def register_agent_executor(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Register an AI agent as an executor on the marketplace.

    The agent must provide a wallet address and capabilities.
    Requires API key authentication.
    """
    from .auth import verify_api_key

    # Require API key for registration
    try:
        await verify_api_key(authorization, x_api_key)
    except HTTPException:
        raise HTTPException(
            status_code=401, detail="API key required for agent registration"
        )

    body = await request.json()

    wallet_address = body.get("wallet_address")
    display_name = body.get("display_name")
    capabilities = body.get("capabilities", [])

    if not wallet_address or not display_name or not capabilities:
        raise HTTPException(
            status_code=400,
            detail="wallet_address, display_name, and capabilities are required",
        )

    try:
        client = db.get_client()

        # Check if executor already exists with this wallet
        existing = (
            client.table("executors")
            .select("id")
            .eq("wallet_address", wallet_address)
            .execute()
        )

        if existing.data and len(existing.data) > 0:
            # Update existing
            executor_id = existing.data[0]["id"]
            client.table("executors").update(
                {
                    "display_name": display_name,
                    "capabilities": capabilities,
                    "executor_type": "agent",
                    "agent_card_url": body.get("agent_card_url"),
                    "mcp_endpoint_url": body.get("mcp_endpoint_url"),
                    "erc8004_agent_id": body.get("erc8004_agent_id"),
                    "pricing": body.get("pricing"),
                    "bio": body.get("bio"),
                    "is_verified": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", executor_id).execute()

            logger.info("Agent executor updated: %s (%s)", display_name, executor_id)

            return {
                "executor_id": executor_id,
                "display_name": display_name,
                "status": "updated",
            }
        else:
            # Create new executor
            executor_data = {
                "wallet_address": wallet_address,
                "display_name": display_name,
                "capabilities": capabilities,
                "executor_type": "agent",
                "agent_card_url": body.get("agent_card_url"),
                "mcp_endpoint_url": body.get("mcp_endpoint_url"),
                "erc8004_agent_id": body.get("erc8004_agent_id"),
                "pricing": body.get("pricing"),
                "bio": body.get("bio"),
                "is_verified": False,
                "reputation_score": 0,
                "tasks_completed": 0,
            }

            result = client.table("executors").insert(executor_data).execute()

            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=500, detail="Failed to register agent executor"
                )

            executor = result.data[0]
            logger.info(
                "Agent executor registered: %s (%s)",
                display_name,
                executor["id"],
            )

            return {
                "executor_id": executor["id"],
                "display_name": display_name,
                "status": "registered",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent registration failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
