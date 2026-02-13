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

from .auth import verify_api_key_if_required, APIKeyData

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
    api_key: APIKeyData = Depends(verify_api_key_if_required),
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
    if task.get("agent_id") != api_key.agent_id:
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
        api_key.agent_id,
        request.task_id,
        request.score,
        result.success,
    )
    logger.info(
        "SECURITY_AUDIT action=reputation.rate_worker actor=%s task=%s worker=%s score=%d success=%s",
        api_key.agent_id,
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
        200: {"description": "Feedback submitted"},
        503: {"description": "ERC-8004 integration unavailable"},
    },
)
async def rate_agent_endpoint(
    request: AgentFeedbackRequest,
) -> FeedbackResponse:
    """
    Rate an agent after task completion (worker → agent).

    Workers use this endpoint to submit on-chain reputation feedback
    for agents who published tasks. This creates bidirectional
    accountability in the Execution Market ecosystem.

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
    # task.agent_id is an internal ID (API key or wallet), while
    # agent_identity.owner is the on-chain owner (may be the Facilitator
    # for gasless registrations). Compare against known EM agent ID
    # or against the task's agent wallet/ID with normalization.
    task_agent_raw = task.get("agent_id", "")
    identity_owner = _normalize_address(agent_identity.owner)

    # Strategy: if the rated agent is our EM agent, accept as valid
    # (the task was created by our platform). Otherwise check wallet match.
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

    logger.info(
        "Worker rated agent %d for task %s: score=%d, success=%s",
        request.agent_id,
        request.task_id,
        request.score,
        result.success,
    )
    logger.info(
        "SECURITY_AUDIT action=reputation.rate_agent task=%s agent_id=%d score=%d success=%s",
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
