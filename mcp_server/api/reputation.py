"""
ERC-8004 Reputation API Routes

Provides REST endpoints for on-chain reputation and identity via the Facilitator.
Bidirectional feedback: agents can rate workers, workers can rate agents.

Network: Ethereum Mainnet
Contracts:
- Identity Registry: 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
- Reputation Registry: 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

# ERC-8004 Facilitator client
try:
    from integrations.erc8004 import (
        get_facilitator_client,
        get_chamba_reputation,
        get_chamba_identity,
        rate_worker,
        rate_agent,
        get_agent_info,
        get_agent_reputation,
        CHAMBA_AGENT_ID,
        ERC8004_CONTRACTS,
        ERC8004_NETWORK,
        FACILITATOR_URL,
    )
    ERC8004_AVAILABLE = True
except ImportError:
    ERC8004_AVAILABLE = False

from .auth import verify_api_key, APIKeyData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reputation", tags=["Reputation"])


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
        ...,
        ge=0,
        le=100,
        description="Rating score from 0 (worst) to 100 (best)"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional comment about the interaction"
    )
    proof_tx: Optional[str] = Field(
        default=None,
        description="Transaction hash of payment (for verified feedback)"
    )


class WorkerFeedbackRequest(FeedbackRequest):
    """Request to rate a worker after task completion."""
    task_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Task ID for context"
    )
    worker_address: Optional[str] = Field(
        default=None,
        description="Worker's wallet address"
    )


class AgentFeedbackRequest(FeedbackRequest):
    """Request for a worker to rate an agent."""
    agent_id: int = Field(
        ...,
        ge=1,
        description="Agent's ERC-8004 token ID"
    )
    task_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Task ID for context"
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
    chamba_agent_id: int
    contracts: Dict[str, str]


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================


@router.get(
    "/info",
    response_model=ERC8004InfoResponse,
    responses={
        200: {"description": "ERC-8004 integration info"},
    }
)
async def get_erc8004_info() -> ERC8004InfoResponse:
    """
    Get ERC-8004 integration status and configuration.

    Returns contract addresses, network info, and Chamba's agent ID.
    """
    if not ERC8004_AVAILABLE:
        return ERC8004InfoResponse(
            available=False,
            network="ethereum",
            facilitator_url="https://facilitator.ultravioletadao.xyz",
            chamba_agent_id=469,
            contracts={},
        )

    contracts = ERC8004_CONTRACTS.get(ERC8004_NETWORK, {})

    return ERC8004InfoResponse(
        available=True,
        network=ERC8004_NETWORK,
        facilitator_url=FACILITATOR_URL,
        chamba_agent_id=CHAMBA_AGENT_ID,
        contracts={
            "identity_registry": contracts.get("identity_registry", ""),
            "reputation_registry": contracts.get("reputation_registry", ""),
        },
    )


@router.get(
    "/chamba",
    response_model=ReputationResponse,
    responses={
        200: {"description": "Chamba's reputation"},
        503: {"description": "ERC-8004 integration unavailable"},
    }
)
async def get_chamba_reputation_endpoint() -> ReputationResponse:
    """
    Get Chamba's reputation as a platform/agent.

    Returns the aggregated reputation score from the ERC-8004 Reputation Registry.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(status_code=503, detail="ERC-8004 integration not available")

    reputation = await get_chamba_reputation()
    if not reputation:
        raise HTTPException(status_code=404, detail="Chamba reputation not found")

    return ReputationResponse(
        agent_id=reputation.agent_id,
        count=reputation.count,
        score=reputation.score,
        network=reputation.network,
    )


@router.get(
    "/chamba/identity",
    response_model=IdentityResponse,
    responses={
        200: {"description": "Chamba's identity"},
        503: {"description": "ERC-8004 integration unavailable"},
    }
)
async def get_chamba_identity_endpoint() -> IdentityResponse:
    """
    Get Chamba's on-chain identity from ERC-8004 Identity Registry.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(status_code=503, detail="ERC-8004 integration not available")

    identity = await get_chamba_identity()
    if not identity:
        raise HTTPException(status_code=404, detail="Chamba identity not found")

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
    }
)
async def get_agent_reputation_endpoint(
    agent_id: int = Path(..., ge=1, description="Agent's ERC-8004 token ID")
) -> ReputationResponse:
    """
    Get reputation for any registered agent by their ERC-8004 token ID.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(status_code=503, detail="ERC-8004 integration not available")

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
    }
)
async def get_agent_identity_endpoint(
    agent_id: int = Path(..., ge=1, description="Agent's ERC-8004 token ID")
) -> IdentityResponse:
    """
    Get identity for any registered agent by their ERC-8004 token ID.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(status_code=503, detail="ERC-8004 integration not available")

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
# AUTHENTICATED ENDPOINTS (Agents rate workers)
# =============================================================================


@router.post(
    "/workers/rate",
    response_model=FeedbackResponse,
    responses={
        200: {"description": "Feedback submitted"},
        401: {"description": "Unauthorized"},
        503: {"description": "ERC-8004 integration unavailable"},
    }
)
async def rate_worker_endpoint(
    request: WorkerFeedbackRequest,
    api_key: APIKeyData = Depends(verify_api_key)
) -> FeedbackResponse:
    """
    Rate a worker after task completion (agent → worker).

    Agents use this endpoint to submit on-chain reputation feedback
    for workers who completed their tasks. The feedback is recorded
    on Ethereum mainnet via the ERC-8004 Reputation Registry.

    **Requires authentication**: Agent must own the task.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(status_code=503, detail="ERC-8004 integration not available")

    # TODO: Verify agent owns the task (api_key.agent_id matches task.agent_id)

    result = await rate_worker(
        task_id=request.task_id,
        score=request.score,
        worker_address=request.worker_address or "",
        comment=request.comment or "",
        proof_tx=request.proof_tx,
    )

    logger.info(
        "Agent %s rated worker for task %s: score=%d, success=%s",
        api_key.agent_id, request.task_id, request.score, result.success
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
    }
)
async def rate_agent_endpoint(
    request: AgentFeedbackRequest,
) -> FeedbackResponse:
    """
    Rate an agent after task completion (worker → agent).

    Workers use this endpoint to submit on-chain reputation feedback
    for agents who published tasks. This creates bidirectional
    accountability in the Chamba ecosystem.

    **Public endpoint**: Any worker can rate agents they've worked with.
    """
    if not ERC8004_AVAILABLE:
        raise HTTPException(status_code=503, detail="ERC-8004 integration not available")

    # TODO: Verify worker was assigned to the task

    result = await rate_agent(
        agent_id=request.agent_id,
        task_id=request.task_id,
        score=request.score,
        comment=request.comment or "",
        proof_tx=request.proof_tx,
    )

    logger.info(
        "Worker rated agent %d for task %s: score=%d, success=%s",
        request.agent_id, request.task_id, request.score, result.success
    )

    return FeedbackResponse(
        success=result.success,
        transaction_hash=result.transaction_hash,
        feedback_index=result.feedback_index,
        network=result.network,
        error=result.error,
    )
