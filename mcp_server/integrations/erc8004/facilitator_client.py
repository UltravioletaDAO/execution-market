"""
ERC-8004 Facilitator Client

Thin wrapper around the SDK's ``Erc8004Client`` for ERC-8004 operations.
The SDK handles HTTP transport, serialisation, and model validation;
this module adds EM-specific helpers (rate_worker, rate_agent, cross-chain
reputation, network translation).

Facilitator: https://facilitator.ultravioletadao.xyz

ERC-8004 networks are auto-derived from sdk_client.py NETWORK_CONFIG (single source of truth).
All mainnets use the same CREATE2-deployed contracts at deterministic addresses.
"""

import asyncio
import os
import logging
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field

from uvd_x402_sdk.erc8004 import Erc8004Client as _SdkErc8004Client
from uvd_x402_sdk.networks import normalize_network as _normalize_network

from integrations.erc8004.feedback_store import FEEDBACK_PUBLIC_URL
from integrations.x402.sdk_client import NETWORK_CONFIG as _PAYMENT_NETWORKS

logger = logging.getLogger(__name__)


# =============================================================================
# Network name normalization (SDK v0.19.3+)
# =============================================================================
# The SDK's normalize_network() handles aliases:
#   "skale" -> "skale-base", "skale-testnet" -> "skale-base-sepolia", etc.
# This replaces the old manual _FACILITATOR_NETWORK_MAP.


def _to_facilitator_network(network: str) -> str:
    """Normalize EM internal network name to facilitator-compatible name."""
    return _normalize_network(network)


# =============================================================================
# Configuration
# =============================================================================

FACILITATOR_URL = os.environ.get(
    "X402_FACILITATOR_URL", "https://facilitator.ultravioletadao.xyz"
)

# Base-first default for Execution Market runtime
ERC8004_NETWORK = os.environ.get("ERC8004_NETWORK", "base")

# Execution Market Agent ID
EM_AGENT_ID = int(os.environ.get("EM_AGENT_ID", "469"))

# Contract addresses — CREATE2 deterministic deployment (same address on all mainnets)
_MAINNET_IDENTITY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
_MAINNET_REPUTATION = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

# --- Auto-derive ERC-8004 contracts from payment NETWORK_CONFIG ---
# All payment-network mainnets have ERC-8004 (CREATE2 same-address deployment).
ERC8004_CONTRACTS: Dict[str, Dict[str, Any]] = {}

_TESTNET_SUFFIXES = ("-sepolia", "-amoy", "-fuji")

# Mainnets: auto-generated from sdk_client.py
for _net, _cfg in _PAYMENT_NETWORKS.items():
    if _net.endswith(_TESTNET_SUFFIXES):
        continue  # Skip testnets
    # Solana (SVM) uses different on-chain programs, not EVM registries
    if _net == "solana":
        ERC8004_CONTRACTS["solana"] = {
            "agent_registry_program": "8oo4dC4JvBLwy5tGgiH3WwK4B9PWxL9Z4XjA2jzkQMbQ",
            "atom_engine_program": "AToMw53aiPQ8j7iHVb4fGt6nzUNxUhcPc3tbPBZuzVVb",
            "chain_id": None,
            "network_type": "svm",
        }
        continue
    ERC8004_CONTRACTS[_net] = {
        "identity_registry": _MAINNET_IDENTITY,
        "reputation_registry": _MAINNET_REPUTATION,
        "chain_id": _cfg["chain_id"],
    }

# BSC: ERC-8004 identity/reputation only (no x402 payment support)
ERC8004_CONTRACTS["bsc"] = {
    "identity_registry": _MAINNET_IDENTITY,
    "reputation_registry": _MAINNET_REPUTATION,
    "chain_id": 56,
}

# Alias: "base-mainnet" -> "base" (SDK uses "base-mainnet", facilitator uses "base")
ERC8004_CONTRACTS["base-mainnet"] = ERC8004_CONTRACTS["base"]

# All supported network names
ERC8004_SUPPORTED_NETWORKS = list(ERC8004_CONTRACTS.keys())


# =============================================================================
# Types
# =============================================================================


@dataclass
class AgentIdentity:
    """Agent identity from ERC-8004 Identity Registry."""

    agent_id: Union[int, str]  # int for EVM token IDs, str for Solana Base58 pubkeys
    owner: str
    agent_uri: str
    agent_wallet: Optional[str] = None
    network: str = ERC8004_NETWORK
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    services: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class FeedbackResult:
    """Result of submitting feedback."""

    success: bool
    transaction_hash: Optional[str] = None
    feedback_index: Optional[int] = None
    error: Optional[str] = None
    network: str = ERC8004_NETWORK


@dataclass
class ReputationSummary:
    """Aggregated reputation for an agent."""

    agent_id: int
    count: int
    summary_value: int
    summary_value_decimals: int = 0
    network: str = ERC8004_NETWORK

    @property
    def score(self) -> float:
        """Get score as percentage (0-100)."""
        if self.summary_value_decimals == 0:
            return float(self.summary_value)
        return float(self.summary_value) / (10**self.summary_value_decimals)


# =============================================================================
# SDK singleton — replaces the old ERC8004FacilitatorClient class
# =============================================================================

_sdk_client = _SdkErc8004Client(base_url=FACILITATOR_URL)


def _fac_net(network: str) -> str:
    """Shorthand: translate EM network name to facilitator name."""
    return _to_facilitator_network(network)


# =============================================================================
# Module-level async functions (thin SDK wrappers)
# =============================================================================


async def get_identity(
    agent_id: int, network: str = ERC8004_NETWORK
) -> Optional[AgentIdentity]:
    """Get agent identity from ERC-8004 Identity Registry via SDK."""
    try:
        result = await _sdk_client.get_identity(_fac_net(network), agent_id)
        if not result or not result.agent_id:
            return None
        return AgentIdentity(
            agent_id=result.agent_id,
            owner=result.owner or "",
            agent_uri=result.agent_uri or "",
            agent_wallet=getattr(result, "agent_wallet", None),
            network=getattr(result, "network", network),
            name=getattr(result, "name", None),
            description=getattr(result, "description", None),
            image=getattr(result, "image", None),
            services=getattr(result, "services", []),
        )
    except Exception as e:
        logger.error(
            "Failed to get identity for agent %d on %s: %s", agent_id, network, e
        )
        return None


async def register_agent(
    network: str,
    agent_uri: str,
    metadata: Optional[List[Dict[str, str]]] = None,
    recipient: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a new agent on the ERC-8004 Identity Registry (gasless) via SDK."""
    if network not in ERC8004_CONTRACTS:
        return {
            "success": False,
            "error": f"Unsupported network: {network}. Supported: {ERC8004_SUPPORTED_NETWORKS}",
        }
    try:
        result = await _sdk_client.register_agent(
            network=_fac_net(network),
            agent_uri=agent_uri,
            metadata=metadata,
            recipient=recipient,
        )
        agent_id = getattr(result, "agent_id", None)
        tx = getattr(result, "transaction", None)
        transfer_tx = getattr(result, "transfer_transaction", None)
        owner = getattr(result, "owner", None)

        logger.info(
            "Agent registered: agentId=%s, network=%s, tx=%s",
            agent_id,
            network,
            tx,
        )

        return {
            "success": True,
            "agentId": agent_id,
            "transaction": tx,
            "transferTransaction": transfer_tx,
            "owner": owner,
            "network": network,
        }
    except Exception as e:
        error_msg = str(e)
        # Treat "already registered" as idempotent success
        if any(s in error_msg.lower() for s in ("already", "duplicate", "exists")):
            logger.info(
                "Registration idempotent for %s on %s: %s",
                agent_uri[:30] if agent_uri else "unknown",
                network,
                error_msg,
            )
            return {
                "success": True,
                "idempotent": True,
                "network": network,
                "error": None,
            }
        logger.error("Agent registration failed on %s: %s", network, e)
        return {"success": False, "error": error_msg, "network": network}


async def get_reputation(
    agent_id: int,
    network: str = ERC8004_NETWORK,
    tag1: str = "",
    tag2: str = "",
    include_feedback: bool = False,
) -> Optional[ReputationSummary]:
    """Get reputation summary for an agent via SDK."""
    try:
        result = await _sdk_client.get_reputation(
            _fac_net(network),
            agent_id,
            tag1=tag1 or None,
            tag2=tag2 or None,
            include_feedback=include_feedback,
        )
        if not result:
            return None
        summary = getattr(result, "summary", result)
        return ReputationSummary(
            agent_id=getattr(summary, "agent_id", agent_id),
            count=getattr(summary, "count", 0),
            summary_value=getattr(summary, "summary_value", 0),
            summary_value_decimals=getattr(summary, "summary_value_decimals", 0),
            network=getattr(result, "network", network),
        )
    except Exception as e:
        logger.error(
            "Failed to get reputation for agent %d on %s: %s", agent_id, network, e
        )
        return None


async def submit_feedback(
    agent_id: int,
    value: int,
    network: str = ERC8004_NETWORK,
    value_decimals: int = 0,
    tag1: str = "",
    tag2: str = "",
    endpoint: str = "",
    feedback_uri: str = "",
    feedback_hash: Optional[str] = None,
    proof: Optional[Dict[str, Any]] = None,
) -> FeedbackResult:
    """Submit reputation feedback via SDK."""
    if not isinstance(agent_id, int) or agent_id <= 0:
        return FeedbackResult(
            success=False,
            error=f"agent_id must be a positive integer, got {agent_id}",
            network=network,
        )
    try:
        result = await _sdk_client.submit_feedback(
            network=_fac_net(network),
            agent_id=agent_id,
            value=value,
            value_decimals=value_decimals,
            tag1=tag1,
            tag2=tag2,
            endpoint=endpoint,
            feedback_uri=feedback_uri,
            feedback_hash=feedback_hash,
            proof=proof,
        )
        tx_hash = getattr(result, "transaction", None)
        return FeedbackResult(
            success=getattr(result, "success", True),
            transaction_hash=tx_hash,
            feedback_index=getattr(result, "feedback_index", None),
            network=getattr(result, "network", network),
        )
    except Exception as e:
        logger.error("Failed to submit feedback: %s", e)
        return FeedbackResult(success=False, error=str(e), network=network)


async def revoke_feedback(
    agent_id: int,
    feedback_index: int,
    network: str = ERC8004_NETWORK,
) -> FeedbackResult:
    """Revoke previously submitted feedback via SDK."""
    try:
        result = await _sdk_client.revoke_feedback(
            network=_fac_net(network),
            agent_id=agent_id,
            feedback_index=feedback_index,
        )
        tx_hash = getattr(result, "transaction", None)
        return FeedbackResult(
            success=getattr(result, "success", True),
            transaction_hash=tx_hash,
            feedback_index=feedback_index,
            network=getattr(result, "network", network),
        )
    except Exception as e:
        logger.error("Failed to revoke feedback: %s", e)
        return FeedbackResult(success=False, error=str(e), network=network)


async def respond_to_feedback(
    agent_id: int,
    feedback_index: int,
    response_text: str,
    network: str = ERC8004_NETWORK,
    response_uri: Optional[str] = None,
) -> FeedbackResult:
    """Respond to feedback as the agent owner via SDK."""
    try:
        result = await _sdk_client.append_response(
            network=_fac_net(network),
            agent_id=agent_id,
            feedback_index=feedback_index,
            response_text=response_text,
            response_uri=response_uri,
        )
        tx_hash = getattr(result, "transaction", None)
        return FeedbackResult(
            success=getattr(result, "success", True),
            transaction_hash=tx_hash,
            feedback_index=feedback_index,
            network=getattr(result, "network", network),
        )
    except Exception as e:
        logger.error("Failed to respond to feedback: %s", e)
        return FeedbackResult(success=False, error=str(e), network=network)


async def get_identity_metadata(
    agent_id: int,
    key: str,
    network: str = ERC8004_NETWORK,
) -> Optional[Dict[str, Any]]:
    """Read a metadata key from an agent's ERC-8004 identity via SDK."""
    try:
        result = await _sdk_client.get_identity_metadata(
            _fac_net(network), agent_id, key
        )
        if not result:
            return None
        return {
            "agentId": getattr(result, "agent_id", agent_id),
            "key": getattr(result, "key", key),
            "valueHex": getattr(result, "value_hex", None),
            "valueUtf8": getattr(result, "value_utf8", None),
            "network": getattr(result, "network", network),
        }
    except Exception as e:
        logger.error("Failed to get identity metadata: %s", e)
        return None


async def get_total_supply(network: str = ERC8004_NETWORK) -> Optional[int]:
    """Get total number of registered agents on a network via SDK."""
    try:
        result = await _sdk_client.get_identity_total_supply(_fac_net(network))
        if not result:
            return None
        return getattr(result, "total_supply", None)
    except Exception as e:
        logger.error("Failed to get total supply: %s", e)
        return None


# =============================================================================
# Backward-compatible shim — callers that instantiate ERC8004FacilitatorClient
# or call get_facilitator_client() keep working without changes.
# =============================================================================


class ERC8004FacilitatorClient:
    """Thin compatibility wrapper.  Delegates to module-level SDK functions."""

    def __init__(
        self,
        facilitator_url: Optional[str] = None,
        network: str = ERC8004_NETWORK,
        timeout: float = 30.0,
    ):
        self.facilitator_url = facilitator_url or FACILITATOR_URL
        self.network = network
        self.timeout = timeout

    async def close(self) -> None:  # noqa: D401
        """No-op — the SDK manages its own transport."""

    async def __aenter__(self) -> "ERC8004FacilitatorClient":
        return self

    async def __aexit__(self, *args) -> None:
        pass

    # -- Identity --
    async def get_identity(self, agent_id: int) -> Optional[AgentIdentity]:
        return await get_identity(agent_id, network=self.network)

    # -- Registration --
    async def register_agent(
        self,
        network: str,
        agent_uri: str,
        metadata: Optional[List[Dict[str, str]]] = None,
        recipient: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await register_agent(
            network=network,
            agent_uri=agent_uri,
            metadata=metadata,
            recipient=recipient,
        )

    # -- Reputation --
    async def get_reputation(
        self,
        agent_id: int,
        tag1: str = "",
        tag2: str = "",
        include_feedback: bool = False,
    ) -> Optional[ReputationSummary]:
        return await get_reputation(
            agent_id,
            network=self.network,
            tag1=tag1,
            tag2=tag2,
            include_feedback=include_feedback,
        )

    # -- Feedback --
    async def submit_feedback(
        self,
        agent_id: int,
        value: int,
        value_decimals: int = 0,
        tag1: str = "",
        tag2: str = "",
        endpoint: str = "",
        feedback_uri: str = "",
        feedback_hash: Optional[str] = None,
        proof: Optional[Dict[str, Any]] = None,
    ) -> FeedbackResult:
        return await submit_feedback(
            agent_id=agent_id,
            value=value,
            network=self.network,
            value_decimals=value_decimals,
            tag1=tag1,
            tag2=tag2,
            endpoint=endpoint,
            feedback_uri=feedback_uri,
            feedback_hash=feedback_hash,
            proof=proof,
        )

    async def revoke_feedback(
        self, agent_id: int, feedback_index: int
    ) -> FeedbackResult:
        return await revoke_feedback(
            agent_id=agent_id,
            feedback_index=feedback_index,
            network=self.network,
        )

    async def respond_to_feedback(
        self,
        agent_id: int,
        client_address: str,
        feedback_index: int,
        response_uri: str,
        response_hash: Optional[str] = None,
    ) -> FeedbackResult:
        return await respond_to_feedback(
            agent_id=agent_id,
            feedback_index=feedback_index,
            response_text=response_uri,
            network=self.network,
            response_uri=response_uri,
        )

    async def get_identity_metadata(
        self, agent_id: int, key: str, network: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        return await get_identity_metadata(
            agent_id, key, network=network or self.network
        )

    async def get_total_supply(self, network: Optional[str] = None) -> Optional[int]:
        return await get_total_supply(network=network or self.network)


_default_client: Optional[ERC8004FacilitatorClient] = None


def get_facilitator_client() -> ERC8004FacilitatorClient:
    """Get or create the default ERC8004FacilitatorClient shim."""
    global _default_client
    if _default_client is None:
        _default_client = ERC8004FacilitatorClient()
    return _default_client


# =============================================================================
# Execution Market-Specific Functions
# =============================================================================


async def get_em_reputation() -> Optional[ReputationSummary]:
    """Get Execution Market's reputation as an agent."""
    return await get_reputation(EM_AGENT_ID)


async def get_em_identity() -> Optional[AgentIdentity]:
    """Get Execution Market's identity from the registry."""
    return await get_identity(EM_AGENT_ID)


async def rate_worker(
    task_id: str,
    score: int,
    worker_address: str = "",
    comment: str = "",
    proof_tx: Optional[str] = None,
    rejection_reason: str = "",
    evidence_urls: Optional[list] = None,
    submission_id: str = "",
    task_title: str = "",
    task_category: str = "",
    bounty_usd: float = 0.0,
    worker_agent_id: Optional[int] = None,
    network: str = ERC8004_NETWORK,
) -> FeedbackResult:
    """
    Rate a worker after task completion (agent rates human).

    Submits on-chain feedback to the WORKER's ERC-8004 agent identity.
    Persists feedback document to S3 with keccak256 hash on-chain.

    Args:
        task_id: Task identifier
        score: Rating 0-100
        worker_address: Worker's wallet address (for tag and DB lookup)
        comment: Optional comment
        proof_tx: Transaction hash of payment (for verified feedback)
        rejection_reason: Reason for rejection (if applicable)
        evidence_urls: URLs of evidence files
        submission_id: Submission identifier
        task_title: Task title for context
        task_category: Task category
        bounty_usd: Task bounty amount
        worker_agent_id: Worker's ERC-8004 agent ID (looked up from DB if not provided)

    Returns:
        FeedbackResult
    """
    # Invalidate cross-chain cache for this worker (reputation is about to change)
    if worker_address:
        invalidate_cross_chain_cache(worker_address)

    # Resolve worker's ERC-8004 agent ID — feedback goes to THEIR identity
    target_agent_id = worker_agent_id
    if not target_agent_id and worker_address:
        try:
            import supabase_client as db

            addr_lower = worker_address.lower()
            result = (
                db.get_client()
                .table("executors")
                .select("erc8004_agent_id")
                .ilike("wallet_address", addr_lower)
                .limit(1)
                .execute()
            )
            if result.data and result.data[0].get("erc8004_agent_id"):
                target_agent_id = int(result.data[0]["erc8004_agent_id"])
                logger.info(
                    "Resolved worker %s -> ERC-8004 agent %d",
                    worker_address[:10],
                    target_agent_id,
                )
        except Exception as exc:
            logger.warning("Could not resolve worker ERC-8004 agent ID: %s", exc)

    # Fallback: check on-chain identity if DB lookup failed
    if not target_agent_id and worker_address:
        try:
            from integrations.erc8004.identity import check_worker_identity

            onchain = await check_worker_identity(worker_address, network=network)
            if onchain.agent_id:
                target_agent_id = onchain.agent_id
                logger.info(
                    "Resolved worker %s on-chain -> agent %d (DB was empty)",
                    worker_address[:10],
                    target_agent_id,
                )
                # Best-effort: persist to DB for future lookups
                try:
                    from integrations.erc8004.identity import update_executor_identity

                    exec_result = (
                        db.get_client()
                        .table("executors")
                        .select("id")
                        .ilike("wallet_address", worker_address.lower())
                        .limit(1)
                        .execute()
                    )
                    if exec_result.data:
                        await update_executor_identity(
                            exec_result.data[0]["id"], target_agent_id
                        )
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("On-chain identity check failed: %s", exc)

    if not target_agent_id:
        logger.warning(
            "Cannot rate worker %s for task %s on %s: no ERC-8004 identity found "
            "(checked DB + on-chain). Worker must register first via "
            "POST /reputation/register or enable erc8004_auto_register_worker.",
            worker_address[:10] if worker_address else "unknown",
            task_id,
            network,
        )
        return FeedbackResult(
            success=False,
            error=f"Worker {worker_address[:10]}... has no ERC-8004 identity. "
            "Register the worker first via POST /reputation/register.",
            network=network,
        )

    # Persist feedback document to S3 and compute hash
    feedback_uri = ""
    feedback_hash = None
    try:
        from integrations.erc8004.feedback_store import persist_and_hash_feedback

        feedback_type = "rejection" if rejection_reason else "worker_rating"
        feedback_uri, feedback_hash = await persist_and_hash_feedback(
            task_id=task_id,
            feedback_type=feedback_type,
            score=score,
            rater_type="agent",
            rater_id=str(EM_AGENT_ID),
            target_type="worker",
            target_address=worker_address,
            target_agent_id=target_agent_id,
            comment=comment,
            rejection_reason=rejection_reason,
            evidence_urls=evidence_urls,
            submission_id=submission_id,
            payment_tx=proof_tx or "",
            task_title=task_title,
            task_category=task_category,
            bounty_usd=bounty_usd,
            network=network,
        )
    except Exception as exc:
        logger.warning("Feedback persistence failed (continuing): %s", exc)
        feedback_uri = f"{FEEDBACK_PUBLIC_URL}/feedback/{task_id}"

    # Submit via Facilitator (gasless). Same pattern as rate_agent().
    # Facilitator pays gas; no relay wallet or private key in ECS needed.
    return await submit_feedback(
        agent_id=target_agent_id,
        value=score,
        tag1="worker_rating",
        tag2=worker_address[:10] if worker_address else "",
        endpoint=f"task:{task_id}",
        feedback_uri=feedback_uri,
        feedback_hash=feedback_hash,
        network=network,
    )


async def rate_agent(
    agent_id: int,
    task_id: str,
    score: int,
    comment: str = "",
    proof_tx: Optional[str] = None,
    task_title: str = "",
    task_category: str = "",
    bounty_usd: float = 0.0,
    relay_private_key: Optional[str] = None,
    network: str = ERC8004_NETWORK,
) -> FeedbackResult:
    """
    Rate an agent (human/worker rates agent).

    Persists feedback document to S3 with keccak256 hash.

    Submits feedback via Facilitator (gasless). No relay wallet needed.
    Facilitator pays gas; rater identity is recorded in feedbackURI + tags.

    Args:
        agent_id: Agent's ERC-8004 token ID
        task_id: Task identifier
        score: Rating 0-100
        comment: Optional comment
        proof_tx: Transaction hash of payment received
        task_title: Task title for context
        task_category: Task category
        bounty_usd: Task bounty amount
        relay_private_key: Ignored (kept for API compatibility).

    Returns:
        FeedbackResult with transaction_hash on success.
    """
    # Persist feedback document to S3 and compute hash
    feedback_uri = ""
    feedback_hash = None
    try:
        from integrations.erc8004.feedback_store import persist_and_hash_feedback

        feedback_uri, feedback_hash = await persist_and_hash_feedback(
            task_id=task_id,
            feedback_type="agent_rating",
            score=score,
            rater_type="worker",
            target_type="agent",
            target_agent_id=agent_id,
            comment=comment,
            payment_tx=proof_tx or "",
            task_title=task_title,
            task_category=task_category,
            bounty_usd=bounty_usd,
            network=network,
        )
    except Exception as exc:
        logger.warning("Feedback persistence failed (continuing): %s", exc)
        feedback_uri = f"{FEEDBACK_PUBLIC_URL}/feedback/{task_id}"

    # Correct architecture: use Facilitator via SDK (gasless).
    # Facilitator pays gas; no relay wallet or private key in ECS needed.
    # The actual rater identity is recorded in feedbackURI content + tags.
    # (relay_private_key param kept for API compatibility but is intentionally unused)
    logger.info(
        "Agent rating via Facilitator (SDK, gasless): agent=%d, task=%s",
        agent_id,
        task_id,
    )
    return await submit_feedback(
        agent_id=agent_id,
        value=score,
        tag1="agent_rating",
        tag2=f"task:{task_id[:8]}",
        endpoint=f"task:{task_id}",
        feedback_uri=feedback_uri,
        feedback_hash=feedback_hash,
        network=network,
    )


async def get_agent_info(agent_id: int) -> Optional[AgentIdentity]:
    """Get any agent's identity."""
    return await get_identity(agent_id)


async def get_agent_reputation(agent_id: int) -> Optional[ReputationSummary]:
    """Get any agent's reputation."""
    return await get_reputation(agent_id)


# =============================================================================
# Cross-Chain Reputation Aggregation
# =============================================================================

# The 9 EVM chains where ERC-8004 identity and reputation are active.
# Excludes Solana (SVM, no ERC-721) and BSC (no x402 payments/escrow).
_CROSS_CHAIN_EVM_NETWORKS = [
    "base",
    "ethereum",
    "polygon",
    "arbitrum",
    "celo",
    "monad",
    "avalanche",
    "optimism",
    "skale",
]

# Cache: wallet_address.lower() -> (timestamp, result_dict)
_cross_chain_cache: Dict[str, tuple] = {}
_CROSS_CHAIN_CACHE_TTL = 600  # 10 minutes


@dataclass
class ChainReputationDetail:
    """Per-chain reputation detail for cross-chain aggregation."""

    network: str
    agent_ids: List[int]
    scores: List[float]
    average: float
    review_count: int


@dataclass
class CrossChainReputationResult:
    """Aggregated reputation across multiple chains."""

    wallet_address: str
    final_score: float
    chain_count: int
    total_reviews: int
    per_chain: Dict[str, ChainReputationDetail]
    chains_with_identity: int
    chains_skipped: int  # identity but 0 reviews
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wallet_address": self.wallet_address,
            "final_score": round(self.final_score, 2),
            "chain_count": self.chain_count,
            "total_reviews": self.total_reviews,
            "chains_with_identity": self.chains_with_identity,
            "chains_skipped": self.chains_skipped,
            "per_chain": {
                net: {
                    "agent_ids": detail.agent_ids,
                    "scores": detail.scores,
                    "average": round(detail.average, 2),
                    "review_count": detail.review_count,
                }
                for net, detail in self.per_chain.items()
            },
            "cached": self.cached,
        }


def invalidate_cross_chain_cache(wallet_address: str) -> None:
    """Invalidate cross-chain reputation cache for a wallet."""
    key = wallet_address.lower()
    _cross_chain_cache.pop(key, None)


async def get_cross_chain_reputation(
    wallet_address: str,
    networks: Optional[List[str]] = None,
) -> CrossChainReputationResult:
    """
    Aggregate reputation across all EVM chains where a wallet has identity.

    Algorithm:
    1. For each enabled EVM chain (parallel, 5s timeout per chain):
       - check_worker_identity(wallet, network=net) -> balance + agent_id(s)
    2. For chains where balance > 0:
       - Get all agent_ids via tokenOfOwnerByIndex
       - SDK GET /reputation/{network}/{agent_id} -> scores
    3. Per-chain average = mean of all scores on that chain
    4. Skip chains with 0 reviews (identity but no feedback)
    5. Final score = mean of per-chain averages (equal weight per chain)

    Args:
        wallet_address: Ethereum wallet (0x-prefixed)
        networks: Optional list of chains to query (defaults to all 9 EVM)

    Returns:
        CrossChainReputationResult with per-chain breakdown
    """
    import time

    wallet_lower = wallet_address.lower()

    # Check cache
    cached = _cross_chain_cache.get(wallet_lower)
    if cached:
        ts, result = cached
        if time.time() - ts < _CROSS_CHAIN_CACHE_TTL:
            from copy import copy

            cached_copy = copy(result)
            cached_copy.cached = True
            return cached_copy

    target_networks = networks or _CROSS_CHAIN_EVM_NETWORKS

    # Step 1: Check identity on all chains in parallel
    from integrations.erc8004.identity import check_worker_identity

    async def _check_identity_safe(net: str):
        try:
            return net, await asyncio.wait_for(
                check_worker_identity(wallet_lower, network=net),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Cross-chain identity check timeout: %s (5s)", net)
            return net, None
        except Exception as exc:
            logger.warning("Cross-chain identity check error on %s: %s", net, exc)
            return net, None

    identity_results = await asyncio.gather(
        *[_check_identity_safe(net) for net in target_networks]
    )

    # Step 2: For chains with identity, get reputation for each agent_id
    chains_with_identity = 0
    per_chain: Dict[str, ChainReputationDetail] = {}

    async def _get_chain_reputation(net: str, agent_ids: List[int]):
        """Get all reputation scores for a list of agent_ids on one chain."""
        scores: List[float] = []
        for aid in agent_ids:
            try:
                rep = await asyncio.wait_for(
                    get_reputation(aid, network=net),
                    timeout=5.0,
                )
                if rep and rep.count > 0:
                    scores.append(rep.score)
            except asyncio.TimeoutError:
                logger.warning("Reputation timeout: agent %d on %s", aid, net)
            except Exception as exc:
                logger.warning("Reputation error: agent %d on %s: %s", aid, net, exc)
        return net, agent_ids, scores

    rep_tasks = []
    for net, identity_result in identity_results:
        if identity_result is None:
            continue
        if identity_result.status.value != "registered":
            continue
        chains_with_identity += 1

        # Collect agent_ids — may have multiple NFTs
        agent_ids = []
        if identity_result.agent_id is not None:
            agent_ids.append(identity_result.agent_id)
        # TODO: if balance > 1, enumerate additional tokens via tokenOfOwnerByIndex
        # For now, we get the first one (most common case)

        if agent_ids:
            rep_tasks.append(_get_chain_reputation(net, agent_ids))

    # Run all reputation queries in parallel
    if rep_tasks:
        rep_results = await asyncio.gather(*rep_tasks, return_exceptions=True)
    else:
        rep_results = []

    chains_skipped = 0
    for result in rep_results:
        if isinstance(result, Exception):
            logger.warning("Cross-chain reputation gather error: %s", result)
            continue
        net, agent_ids, scores = result
        if not scores:
            chains_skipped += 1
            continue
        avg = sum(scores) / len(scores)
        per_chain[net] = ChainReputationDetail(
            network=net,
            agent_ids=agent_ids,
            scores=scores,
            average=avg,
            review_count=len(scores),
        )

    # Step 3: Compute final score (average of per-chain averages)
    if per_chain:
        final_score = sum(d.average for d in per_chain.values()) / len(per_chain)
        total_reviews = sum(d.review_count for d in per_chain.values())
    else:
        final_score = 0.0
        total_reviews = 0

    result = CrossChainReputationResult(
        wallet_address=wallet_lower,
        final_score=final_score,
        chain_count=len(per_chain),
        total_reviews=total_reviews,
        per_chain=per_chain,
        chains_with_identity=chains_with_identity,
        chains_skipped=chains_skipped,
        cached=False,
    )

    # Cache the result
    _cross_chain_cache[wallet_lower] = (time.time(), result)

    return result
