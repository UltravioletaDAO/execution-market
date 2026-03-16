"""
ERC-8004 Reputation API Routes

Provides REST endpoints for on-chain reputation and identity via the Facilitator.
Bidirectional feedback: agents can rate workers, workers can rate agents.

Network: configurable via `ERC8004_NETWORK` (Base-first default).
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field

import supabase_client as db
from integrations.x402.payment_events import log_payment_event

# ERC-8004 Facilitator client
try:
    from integrations.erc8004 import (
        get_facilitator_client,
        get_em_reputation,
        get_em_identity,
        rate_worker,
        rate_agent,
        get_agent_info,
        get_agent_reputation,
        EM_AGENT_ID,
        ERC8004_CONTRACTS,
        ERC8004_NETWORK,
        ERC8004_SUPPORTED_NETWORKS,
        FACILITATOR_URL,
    )

    ERC8004_AVAILABLE = True
except ImportError:
    ERC8004_AVAILABLE = False
    ERC8004_SUPPORTED_NETWORKS = []
    EM_AGENT_ID = 0

from .auth import verify_agent_auth, AgentAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reputation", tags=["Reputation"])


def _normalize_address(value: Optional[str]) -> str:
    """Normalize wallet-like addresses for safe case-insensitive comparison."""
    return str(value or "").strip().lower()


async def _get_task_or_404(task_id: str) -> Dict[str, Any]:
    """Fetch task by id and raise 404 when not found."""
    try:
        task = await db.get_task(task_id)
    except Exception:
        task = None
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


# =============================================================================
# MODELS
# =============================================================================


class IdentityResponse(BaseModel):
    """Agent identity from ERC-8004 registry."""

    agent_id: int
    owner: str
    agent_uri: str
    agent_wallet: Optional[str] = None
    network: str
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    services: List[Dict[str, str]] = []


class ReputationResponse(BaseModel):
    """Reputation summary for an agent."""

    agent_id: int
    count: int
    score: float = Field(description="Reputation score (0-100)")
    network: str


class FeedbackRequest(BaseModel):
    """Request to submit feedback."""

    score: int = Field(
        ..., ge=0, le=100, description="Rating score from 0 (worst) to 100 (best)"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional comment about the interaction",
    )
    proof_tx: Optional[str] = Field(
        default=None, description="Transaction hash of payment (for verified feedback)"
    )


class WorkerFeedbackRequest(FeedbackRequest):
    """Request to rate a worker after task completion."""

    task_id: str = Field(
        ..., min_length=36, max_length=36, description="Task ID for context"
    )
    worker_address: Optional[str] = Field(
        default=None, description="Worker's wallet address"
    )


class AgentFeedbackRequest(FeedbackRequest):
    """Request for a worker to rate an agent."""

    agent_id: int = Field(..., ge=1, description="Agent's ERC-8004 token ID")
    task_id: str = Field(
        ..., min_length=36, max_length=36, description="Task ID for context"
    )


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    success: bool
    transaction_hash: Optional[str] = None
    feedback_index: Optional[int] = None
    network: str
    error: Optional[str] = None


class PrepareFeedbackRequest(BaseModel):
    """Request to prepare on-chain feedback parameters for worker signing."""

    agent_id: int = Field(..., ge=1, description="Target agent's ERC-8004 token ID")
    task_id: str = Field(
        ..., min_length=36, max_length=36, description="Task ID for context"
    )
    score: int = Field(
        ..., ge=0, le=100, description="Rating score from 0 (worst) to 100 (best)"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional comment about the interaction",
    )
    worker_address: str = Field(
        ..., min_length=42, max_length=42, description="Worker's wallet address"
    )


class PrepareFeedbackResponse(BaseModel):
    """Response with parameters for giveFeedback() on-chain call."""

    prepare_id: str = Field(description="Unique ID to confirm feedback later")
    contract_address: str
    chain_id: int
    agent_id: int
    value: int
    value_decimals: int = 0
    tag1: str
    tag2: str
    endpoint: str
    feedback_uri: str
    feedback_hash: str = Field(description="0x-prefixed keccak256 hex")
    estimated_gas: int = 200000


class ConfirmFeedbackRequest(BaseModel):
    """Request to confirm that the worker signed the feedback TX."""

    prepare_id: str = Field(..., description="prepare_id from prepare-feedback")
    tx_hash: str = Field(
        ..., min_length=66, max_length=66, description="0x-prefixed TX hash"
    )
    task_id: str = Field(
        ..., min_length=36, max_length=36, description="Task ID for context"
    )


class ConfirmFeedbackResponse(BaseModel):
    """Response after confirming feedback TX."""

    success: bool
    transaction_hash: Optional[str] = None
    network: str
    error: Optional[str] = None


class LeaderboardEntry(BaseModel):
    """A single entry in the reputation leaderboard."""

    id: str
    display_name: Optional[str] = None
    reputation_score: float
    tier: Optional[str] = None
    tasks_completed: int
    avg_rating: Optional[float] = None
    rank: int
    badges_count: int = 0


class ERC8004InfoResponse(BaseModel):
    """ERC-8004 integration status and info."""

    available: bool
    network: str
    facilitator_url: str
    em_agent_id: int
    contracts: Dict[str, str]


class MetadataEntry(BaseModel):
    """Key-value metadata for agent registration."""

    key: str = Field(..., min_length=1, max_length=64)
    value: str = Field(..., min_length=1, max_length=256)


class RegisterAgentRequest(BaseModel):
    """Request to register a new agent on ERC-8004 (gasless)."""

    network: str = Field(
        default="base", description="ERC-8004 network for registration"
    )
    agent_uri: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="URI to agent registration file (IPFS or HTTPS)",
    )
    metadata: Optional[List[MetadataEntry]] = Field(
        default=None, description="Optional key-value metadata pairs"
    )
    recipient: Optional[str] = Field(
        default=None, description="Optional address to receive the NFT after minting"
    )


class RegisterAgentResponse(BaseModel):
    """Response from agent registration."""

    success: bool
    agent_id: Optional[int] = Field(
        default=None, description="Newly assigned ERC-8004 agent ID"
    )
    transaction: Optional[str] = Field(default=None, description="Registration tx hash")
    transfer_transaction: Optional[str] = Field(
        default=None, description="NFT transfer tx hash (if recipient specified)"
    )
    owner: Optional[str] = None
    network: str
    error: Optional[str] = None


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """Top workers ranked by reputation score."""
    client = db.get_client()
    # Query executors table directly instead of reputation_leaderboard view
    # to avoid RLS/view permission issues that cause 500 errors.
    result = (
        client.table("executors")
        .select("id,display_name,reputation_score,tier,tasks_completed,avg_rating")
        .order("reputation_score", desc=True)
        .order("tasks_completed", desc=True)
        .limit(limit)
        .offset(offset)
        .execute()
    )
    entries = result.data or []
    # Add rank and badges_count (default 0) since we no longer use the view
    workers = []
    for i, r in enumerate(entries):
        r["rank"] = offset + i + 1
        r["badges_count"] = 0
        workers.append(LeaderboardEntry(**r).model_dump())
    return {
        "workers": workers,
        "count": len(workers),
    }


@router.get(
    "/info",
    response_model=ERC8004InfoResponse,
    responses={
        200: {"description": "ERC-8004 integration info"},
    },
)
async def get_erc8004_info() -> ERC8004InfoResponse:
    """
    Get ERC-8004 integration status and configuration.

    Returns contract addresses, network info, and Execution Market's agent ID.
    """
    if not ERC8004_AVAILABLE:
        return ERC8004InfoResponse(
            available=False,
            network="base",
            facilitator_url="https://facilitator.ultravioletadao.xyz",
            em_agent_id=469,
            contracts={},
        )

    contracts = ERC8004_CONTRACTS.get(ERC8004_NETWORK, {})

    return ERC8004InfoResponse(
        available=True,
        network=ERC8004_NETWORK,
        facilitator_url=FACILITATOR_URL,
        em_agent_id=EM_AGENT_ID,
        contracts={
            "identity_registry": contracts.get("identity_registry", ""),
            "reputation_registry": contracts.get("reputation_registry", ""),
        },
    )


@router.get(
    "/em",
    response_model=ReputationResponse,
    responses={
        200: {"description": "Execution Market's reputation"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def get_em_reputation_endpoint() -> ReputationResponse:
    """
    Get Execution Market's reputation as a platform/agent.

    Returns the aggregated reputation score from the ERC-8004 Reputation Registry
    on the configured facilitator network.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    reputation = await get_em_reputation()
    if not reputation:
        raise HTTPException(status_code=404, detail="EM reputation not found")

    return ReputationResponse(
        agent_id=reputation.agent_id,
        count=reputation.count,
        score=reputation.score,
        network=reputation.network,
    )


@router.get(
    "/em/identity",
    response_model=IdentityResponse,
    responses={
        200: {"description": "Execution Market's identity"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def get_em_identity_endpoint() -> IdentityResponse:
    """
    Get Execution Market's on-chain identity from ERC-8004 Identity Registry.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    identity = await get_em_identity()
    if not identity:
        raise HTTPException(status_code=404, detail="EM identity not found")

    return IdentityResponse(
        agent_id=identity.agent_id,
        owner=identity.owner,
        agent_uri=identity.agent_uri,
        agent_wallet=identity.agent_wallet,
        network=identity.network,
        name=identity.name,
        description=identity.description,
        image=identity.image,
        services=identity.services,
    )


@router.get(
    "/agents/{agent_id}",
    response_model=ReputationResponse,
    responses={
        200: {"description": "Agent reputation"},
        404: {"description": "Agent not found"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def get_agent_reputation_endpoint(
    agent_id: int = Path(..., ge=1, description="Agent's ERC-8004 token ID"),
) -> ReputationResponse:
    """
    Get reputation for any registered agent by their ERC-8004 token ID.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    reputation = await get_agent_reputation(agent_id)
    if not reputation:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return ReputationResponse(
        agent_id=reputation.agent_id,
        count=reputation.count,
        score=reputation.score,
        network=reputation.network,
    )


@router.get(
    "/agents/{agent_id}/identity",
    response_model=IdentityResponse,
    responses={
        200: {"description": "Agent identity"},
        404: {"description": "Agent not found"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def get_agent_identity_endpoint(
    agent_id: int = Path(..., ge=1, description="Agent's ERC-8004 token ID"),
) -> IdentityResponse:
    """
    Get identity for any registered agent by their ERC-8004 token ID.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    identity = await get_agent_info(agent_id)
    if not identity:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return IdentityResponse(
        agent_id=identity.agent_id,
        owner=identity.owner,
        agent_uri=identity.agent_uri,
        agent_wallet=identity.agent_wallet,
        network=identity.network,
        name=identity.name,
        description=identity.description,
        image=identity.image,
        services=identity.services,
    )


# =============================================================================
# IDENTITY REGISTRATION (Gasless — Facilitator pays gas)
# =============================================================================


@router.get(
    "/networks",
    responses={200: {"description": "List of supported ERC-8004 networks"}},
)
async def get_supported_networks() -> Dict[str, Any]:
    """
    Get all supported ERC-8004 networks for identity, reputation, and registration.

    Returns the 14 networks where agents can be registered and rated.
    """
    networks = []
    for name, contracts in ERC8004_CONTRACTS.items():
        if name == "base":  # skip legacy alias
            continue
        networks.append(
            {
                "network": name,
                "chain_id": contracts.get("chain_id"),
                "identity_registry": contracts.get("identity_registry"),
                "reputation_registry": contracts.get("reputation_registry"),
                "testnet": name.endswith(("-sepolia", "-amoy", "-fuji")),
            }
        )
    return {
        "count": len(networks),
        "networks": networks,
    }


@router.post(
    "/register",
    response_model=RegisterAgentResponse,
    responses={
        200: {"description": "Agent registered successfully"},
        400: {"description": "Invalid network or parameters"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def register_agent_endpoint(
    request: RegisterAgentRequest,
) -> RegisterAgentResponse:
    """
    Register a new agent on the ERC-8004 Identity Registry (gasless).

    The Ultravioleta Facilitator pays all gas fees. The caller does not
    need ETH or any native token on the target chain.

    Supported networks: ethereum, base, polygon, arbitrum, celo, bsc,
    monad, avalanche, and their testnets.

    If `recipient` is specified, the minted ERC-721 NFT is automatically
    transferred to that address after registration.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    if request.network not in ERC8004_CONTRACTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported network: {request.network}. Supported: {[n for n in ERC8004_SUPPORTED_NETWORKS if n != 'base']}",
        )

    client = get_facilitator_client()

    metadata_dicts = None
    if request.metadata:
        metadata_dicts = [{"key": m.key, "value": m.value} for m in request.metadata]

    result = await client.register_agent(
        network=request.network,
        agent_uri=request.agent_uri,
        metadata=metadata_dicts,
        recipient=request.recipient,
    )

    agent_id = result.get("agentId")
    success = result.get("success", False)

    logger.info(
        "SECURITY_AUDIT action=identity.register network=%s agent_id=%s success=%s",
        request.network,
        agent_id,
        success,
    )

    # Persist agent_id to executors table so downstream operations
    # (rate_worker, rate_agent) can find the worker's ERC-8004 identity.
    if success and agent_id and request.recipient:
        try:
            from integrations.erc8004.identity import update_executor_identity

            addr_lower = request.recipient.lower()
            executor_result = (
                db.get_client()
                .table("executors")
                .select("id")
                .ilike("wallet_address", addr_lower)
                .limit(1)
                .execute()
            )
            if executor_result.data:
                executor_id = executor_result.data[0]["id"]
                await update_executor_identity(executor_id, int(agent_id))
                logger.info(
                    "Persisted erc8004_agent_id=%s for executor %s (wallet %s)",
                    agent_id,
                    executor_id,
                    addr_lower[:10],
                )
        except Exception as exc:
            logger.warning(
                "Could not persist erc8004_agent_id after registration: %s", exc
            )

    return RegisterAgentResponse(
        success=success,
        agent_id=agent_id,
        transaction=result.get("transaction"),
        transfer_transaction=result.get("transferTransaction"),
        owner=result.get("owner"),
        network=result.get("network", request.network),
        error=result.get("error"),
    )


# =============================================================================
# AUTHENTICATED ENDPOINTS (Agents rate workers)
# =============================================================================


@router.post(
    "/workers/rate",
    response_model=FeedbackResponse,
    responses={
        200: {"description": "Feedback submitted"},
        401: {"description": "Unauthorized"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def rate_worker_endpoint(
    request: WorkerFeedbackRequest,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> FeedbackResponse:
    """
    Rate a worker after task completion (agent → worker).

    Agents use this endpoint to submit on-chain reputation feedback
    for workers who completed their tasks. The feedback is recorded
    via the configured facilitator network in the ERC-8004 Reputation Registry.

    **Requires authentication**: Agent must own the task.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    task = await _get_task_or_404(request.task_id)
    is_owner = task.get("agent_id") == auth.agent_id or (
        getattr(auth, "wallet_address", None)
        and task.get("agent_id") == auth.wallet_address
    )
    if not is_owner:
        raise HTTPException(
            status_code=403, detail="Not authorized to rate worker for this task"
        )

    task_status = str(task.get("status", "")).lower()
    if task_status in {"published", "cancelled", "expired"}:
        raise HTTPException(
            status_code=409, detail=f"Task status {task_status} cannot be rated yet"
        )

    task_executor_wallet = _normalize_address(
        (task.get("executor") or {}).get("wallet_address")
    )
    requested_worker_wallet = _normalize_address(request.worker_address)
    if (
        requested_worker_wallet
        and task_executor_wallet
        and requested_worker_wallet != task_executor_wallet
    ):
        raise HTTPException(
            status_code=403, detail="Worker address does not match assigned executor"
        )

    worker_address = requested_worker_wallet or task_executor_wallet
    if not worker_address:
        raise HTTPException(
            status_code=409, detail="Task has no assigned worker to rate"
        )

    # Resolve worker's ERC-8004 agent ID from executor record if available
    worker_agent_id = None
    executor = task.get("executor") or {}
    if executor.get("erc8004_agent_id"):
        worker_agent_id = int(executor["erc8004_agent_id"])

    result = await rate_worker(
        task_id=request.task_id,
        score=request.score,
        worker_address=worker_address,
        comment=request.comment or "",
        proof_tx=request.proof_tx,
        worker_agent_id=worker_agent_id,
    )

    logger.info(
        "Agent %s rated worker for task %s: score=%d, success=%s",
        auth.agent_id,
        request.task_id,
        request.score,
        result.success,
    )
    logger.info(
        "SECURITY_AUDIT action=reputation.rate_worker actor=%s task=%s worker=%s score=%d success=%s",
        auth.agent_id,
        request.task_id,
        worker_address,
        request.score,
        result.success,
    )

    # Persist reputation_tx in the approved submission for audit trail
    if result.success and result.transaction_hash:
        try:
            client = db.get_client()
            client.table("submissions").update(
                {"reputation_tx": result.transaction_hash}
            ).eq("task_id", request.task_id).eq("status", "approved").execute()
            logger.info(
                "Stored reputation_tx=%s for task %s",
                result.transaction_hash[:16],
                request.task_id,
            )
        except Exception as e:
            logger.warning(
                "Failed to store reputation_tx for task %s: %s", request.task_id, e
            )

        # Also update feedback_documents so mobile app can show the TX link
        try:
            client = db.get_client()
            client.table("feedback_documents").update(
                {"reputation_tx": result.transaction_hash}
            ).eq("task_id", request.task_id).eq(
                "feedback_type", "worker_rating"
            ).execute()
        except Exception as e:
            logger.debug("Could not update feedback_documents reputation_tx: %s", e)

        # Log to payment_events audit trail
        await log_payment_event(
            task_id=request.task_id,
            event_type="reputation_agent_rates_worker",
            status="success",
            tx_hash=result.transaction_hash,
            network=result.network
            or (ERC8004_NETWORK if ERC8004_AVAILABLE else "base"),
            metadata={
                "score": request.score,
                "worker_address": worker_address,
                "feedback_index": result.feedback_index,
            },
        )

    # Persist to ratings table so mobile/dashboard can display it
    if result.success:
        executor_id = (task.get("executor") or {}).get("id")
        if executor_id:
            try:
                stars = round(request.score / 20, 1)  # 0-100 → 0.0-5.0
                client = db.get_client()
                client.table("ratings").upsert(
                    {
                        "executor_id": executor_id,
                        "task_id": request.task_id,
                        "rater_id": str(auth.agent_id),
                        "rater_type": "agent",
                        "rating": request.score,
                        "stars": float(stars),
                        "comment": request.comment or None,
                        "task_value_usdc": float(task.get("bounty", 0)),
                        "is_public": True,
                    },
                    on_conflict="executor_id,task_id,rater_type",
                ).execute()
                logger.info(
                    "Stored rating in ratings table: executor=%s task=%s score=%d",
                    executor_id,
                    request.task_id,
                    request.score,
                )
            except Exception as e:
                logger.warning(
                    "Failed to store rating for task %s: %s", request.task_id, e
                )

    return FeedbackResponse(
        success=result.success,
        transaction_hash=result.transaction_hash,
        feedback_index=result.feedback_index,
        network=result.network,
        error=result.error,
    )


# =============================================================================
# WORKER ENDPOINTS (Workers rate agents)
# =============================================================================


@router.post(
    "/agents/rate",
    response_model=FeedbackResponse,
    responses={
        200: {"description": "Feedback prepared (pending worker signature)"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def rate_agent_endpoint(
    request: AgentFeedbackRequest,
) -> FeedbackResponse:
    """
    Rate an agent after task completion (worker → agent).

    **DEPRECATED**: Use prepare-feedback + confirm-feedback instead.
    This legacy endpoint persists S3 data but returns pending_worker_signature=True.
    The actual on-chain TX must be signed by the worker's wallet directly.

    **Public endpoint**: Any worker can rate agents they've worked with.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    task = await _get_task_or_404(request.task_id)
    task_status = str(task.get("status", "")).lower()
    if task_status in {"published", "cancelled", "expired"}:
        raise HTTPException(
            status_code=409, detail=f"Task status {task_status} cannot be rated yet"
        )

    task_executor_wallet = _normalize_address(
        (task.get("executor") or {}).get("wallet_address")
    )
    if not task.get("executor_id") and not task_executor_wallet:
        raise HTTPException(status_code=409, detail="Task has no assigned worker")

    # Verify the provided ERC-8004 agent identity exists on-chain.
    agent_identity = await get_agent_info(request.agent_id)
    if not agent_identity:
        raise HTTPException(
            status_code=404, detail=f"Agent {request.agent_id} not found"
        )

    # Verify the rated agent matches the task's agent.
    task_agent_raw = task.get("agent_id", "")
    identity_owner = _normalize_address(agent_identity.owner)

    if request.agent_id != EM_AGENT_ID:
        task_agent_addr = _normalize_address(task_agent_raw)
        if task_agent_addr and identity_owner and task_agent_addr != identity_owner:
            raise HTTPException(
                status_code=403,
                detail="Task agent does not match rated agent identity",
            )

    result = await rate_agent(
        agent_id=request.agent_id,
        task_id=request.task_id,
        score=request.score,
        comment=request.comment or "",
        proof_tx=request.proof_tx,
    )

    # Persist rating to DB so it shows in mobile app / dashboard
    # (rate_agent only does on-chain feedback + S3, not the ratings table)
    try:
        executor_id = task.get("executor_id")
        if executor_id:
            client = db.get_client()
            stars = round(request.score / 20, 1)
            client.table("ratings").upsert(
                {
                    "executor_id": executor_id,
                    "task_id": request.task_id,
                    "rater_id": executor_id,
                    "rater_type": "worker",
                    "rating": request.score,
                    "stars": float(stars),
                    "comment": request.comment or None,
                    "task_value_usdc": float(task.get("bounty_usd", 0)),
                    "is_public": True,
                },
                on_conflict="executor_id,task_id,rater_type",
            ).execute()
            logger.info(
                "Stored worker->agent rating in DB: executor=%s task=%s score=%d",
                executor_id,
                request.task_id,
                request.score,
            )
    except Exception as e:
        logger.warning("Failed to store worker->agent rating in DB (non-fatal): %s", e)

    # If relay path returned a TX hash, update feedback_documents so mobile shows the link
    if result.success and result.transaction_hash:
        try:
            client = db.get_client()
            client.table("feedback_documents").update(
                {"reputation_tx": result.transaction_hash}
            ).eq("task_id", request.task_id).eq(
                "feedback_type", "agent_rating"
            ).execute()
            logger.info(
                "Stored agent_rating reputation_tx=%s for task %s",
                result.transaction_hash[:16],
                request.task_id,
            )
        except Exception as e:
            logger.debug(
                "Could not update feedback_documents agent_rating reputation_tx: %s", e
            )

    logger.info(
        "Worker prepared agent rating %d for task %s: score=%d, pending_worker_signature=%s",
        request.agent_id,
        request.task_id,
        request.score,
        result.success,
    )
    logger.info(
        "SECURITY_AUDIT action=reputation.rate_agent task=%s agent_id=%d score=%d pending_worker_signature=%s",
        request.task_id,
        request.agent_id,
        request.score,
        result.success,
    )

    return FeedbackResponse(
        success=result.success,
        transaction_hash=result.transaction_hash,
        feedback_index=result.feedback_index,
        network=result.network,
        error=result.error,
    )


# =============================================================================
# WORKER DIRECT SIGNING (prepare → sign → confirm)
# =============================================================================


@router.post(
    "/prepare-feedback",
    response_model=PrepareFeedbackResponse,
    responses={
        200: {"description": "Feedback parameters prepared for worker signing"},
        404: {"description": "Task not found"},
        409: {"description": "Task status does not allow rating"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def prepare_feedback_endpoint(
    request: PrepareFeedbackRequest,
) -> PrepareFeedbackResponse:
    """
    Prepare on-chain feedback parameters for a worker to sign directly.

    The worker's wallet will call giveFeedback() on-chain, making
    msg.sender = worker address (trustless reputation).

    Flow: prepare-feedback → worker signs in wallet → confirm-feedback
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="ERC-8004 integration not available"
        )

    task = await _get_task_or_404(request.task_id)
    task_status = str(task.get("status", "")).lower()
    if task_status in {"published", "cancelled", "expired"}:
        raise HTTPException(
            status_code=409, detail=f"Task status {task_status} cannot be rated yet"
        )

    # Verify the worker is the assigned executor
    task_executor_wallet = _normalize_address(
        (task.get("executor") or {}).get("wallet_address")
    )
    worker_addr = _normalize_address(request.worker_address)
    if task_executor_wallet and worker_addr != task_executor_wallet:
        raise HTTPException(
            status_code=403,
            detail="Worker address does not match assigned executor",
        )

    # Verify the rated agent exists on-chain
    agent_identity = await get_agent_info(request.agent_id)
    if not agent_identity:
        raise HTTPException(
            status_code=404, detail=f"Agent {request.agent_id} not found on-chain"
        )

    # Persist feedback document to S3 + compute keccak256
    feedback_uri = ""
    feedback_hash = "0x" + "00" * 32
    try:
        from integrations.erc8004.feedback_store import persist_and_hash_feedback

        feedback_uri, feedback_hash = await persist_and_hash_feedback(
            task_id=request.task_id,
            feedback_type="agent_rating",
            score=request.score,
            rater_type="worker",
            target_type="agent",
            target_agent_id=request.agent_id,
            target_address=request.worker_address,
            comment=request.comment or "",
            network=ERC8004_NETWORK,
        )
    except Exception as exc:
        logger.warning("Feedback persistence failed (continuing): %s", exc)
        feedback_uri = (
            f"https://api.execution.market/api/v1/reputation/feedback/{request.task_id}"
        )

    # Store prepare_id for confirm step
    import uuid

    prepare_id = str(uuid.uuid4())
    try:
        client = db.get_client()
        client.table("feedback_documents").update({"prepare_id": prepare_id}).eq(
            "task_id", request.task_id
        ).eq("feedback_type", "agent_rating").execute()
    except Exception as exc:
        logger.debug("Could not store prepare_id in DB: %s", exc)

    contracts = ERC8004_CONTRACTS.get(ERC8004_NETWORK, {})

    logger.info(
        "Prepared feedback for worker signing: task=%s, agent=%d, prepare_id=%s",
        request.task_id,
        request.agent_id,
        prepare_id[:8],
    )

    return PrepareFeedbackResponse(
        prepare_id=prepare_id,
        contract_address=contracts.get(
            "reputation_registry", "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
        ),
        chain_id=contracts.get("chain_id", 8453),
        agent_id=request.agent_id,
        value=request.score,
        value_decimals=0,
        tag1="agent_rating",
        tag2="execution-market",
        endpoint=f"task:{request.task_id}",
        feedback_uri=feedback_uri,
        feedback_hash=feedback_hash,
        estimated_gas=200000,
    )


@router.post(
    "/confirm-feedback",
    response_model=ConfirmFeedbackResponse,
    responses={
        200: {"description": "Feedback TX confirmed"},
        400: {"description": "Invalid parameters"},
    },
)
async def confirm_feedback_endpoint(
    request: ConfirmFeedbackRequest,
) -> ConfirmFeedbackResponse:
    """
    Confirm that the worker signed and submitted the feedback TX.

    Stores the tx_hash in the database for audit trail.
    """
    # Store tx_hash in feedback_documents for the task
    try:
        client = db.get_client()
        client.table("feedback_documents").update(
            {"reputation_tx": request.tx_hash}
        ).eq("task_id", request.task_id).eq("feedback_type", "agent_rating").execute()
    except Exception as exc:
        logger.warning(
            "Could not store reputation_tx for task %s: %s", request.task_id, exc
        )

    # Also update the submission's reputation_tx field
    try:
        client = db.get_client()
        client.table("submissions").update(
            {"worker_reputation_tx": request.tx_hash}
        ).eq("task_id", request.task_id).eq("status", "approved").execute()
    except Exception as exc:
        logger.debug("Could not update submission worker_reputation_tx: %s", exc)

    logger.info(
        "Confirmed worker feedback TX: task=%s, tx=%s, prepare_id=%s",
        request.task_id,
        request.tx_hash[:16],
        request.prepare_id[:8],
    )

    # Log to payment_events audit trail
    await log_payment_event(
        task_id=request.task_id,
        event_type="reputation_worker_rates_agent",
        status="success",
        tx_hash=request.tx_hash,
        network=ERC8004_NETWORK if ERC8004_AVAILABLE else "base",
        metadata={
            "prepare_id": request.prepare_id,
            "worker_signed": True,
        },
    )

    # Persist worker→agent rating to ratings table for mobile/dashboard display
    try:
        task = await _get_task_or_404(request.task_id)
        executor_id = (task.get("executor") or {}).get("id")
        # Read score from feedback_documents
        client = db.get_client()
        fd_result = (
            client.table("feedback_documents")
            .select("score, comment")
            .eq("task_id", request.task_id)
            .eq("feedback_type", "agent_rating")
            .limit(1)
            .execute()
        )
        fd = fd_result.data[0] if fd_result.data else {}
        score = fd.get("score", 85)
        comment = fd.get("comment")

        if executor_id:
            stars = round(score / 20, 1)
            client.table("ratings").upsert(
                {
                    "executor_id": executor_id,
                    "task_id": request.task_id,
                    "rater_id": executor_id,
                    "rater_type": "worker",
                    "rating": score,
                    "stars": float(stars),
                    "comment": comment,
                    "task_value_usdc": float(task.get("bounty", 0)),
                    "is_public": True,
                },
                on_conflict="executor_id,task_id,rater_type",
            ).execute()
            logger.info(
                "Stored worker→agent rating: executor=%s task=%s score=%d",
                executor_id,
                request.task_id,
                score,
            )
    except Exception as e:
        logger.warning(
            "Failed to store worker→agent rating for task %s: %s",
            request.task_id,
            e,
        )

    return ConfirmFeedbackResponse(
        success=True,
        transaction_hash=request.tx_hash,
        network=ERC8004_NETWORK if ERC8004_AVAILABLE else "base",
    )


# =============================================================================
# FEEDBACK DOCUMENT RETRIEVAL
# =============================================================================


@router.get(
    "/feedback/{task_id}",
    summary="Get feedback document for a task",
    description="Retrieves the off-chain feedback document stored on S3. "
    "This is the data referenced by feedbackUri in ERC-8004 Reputation Registry.",
)
async def get_feedback_endpoint(
    task_id: str = Path(..., description="Task ID"),
    feedback_type: Optional[str] = None,
):
    """
    Retrieve feedback document for a task.

    The feedbackUri on-chain points here. Returns the full JSON document
    with score, comment, rejection reason, evidence, and transaction hashes.
    """
    try:
        from integrations.erc8004.feedback_store import get_feedback_document

        doc = await get_feedback_document(task_id, feedback_type)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No feedback document found for task {task_id}",
            )
        return doc
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Feedback store not available",
        )
    except Exception as exc:
        logger.error("Error fetching feedback for task %s: %s", task_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve feedback document",
        )
