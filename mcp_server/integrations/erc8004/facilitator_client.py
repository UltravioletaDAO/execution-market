"""
ERC-8004 Facilitator Client

Uses the Ultravioleta DAO Facilitator for ERC-8004 operations.
This is the production-ready approach - no direct on-chain calls needed.

Facilitator: https://facilitator.ultravioletadao.xyz

Endpoints:
- GET  /identity/{network}/{agentId}     - Get agent identity
- GET  /identity/{network}/{agentId}/metadata/{key} - Get agent metadata
- GET  /identity/{network}/total-supply  - Total registered agents
- POST /register                         - Gasless agent registration
- GET  /reputation/{network}/{agentId}   - Get reputation summary
- POST /feedback                         - Submit feedback
- POST /feedback/revoke                  - Revoke feedback
- POST /feedback/response                - Agent responds to feedback

ERC-8004 networks are auto-derived from sdk_client.py NETWORK_CONFIG (single source of truth).
All mainnets use the same CREATE2-deployed contracts at deterministic addresses.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field

import httpx

from integrations.erc8004.feedback_store import FEEDBACK_PUBLIC_URL
from integrations.x402.sdk_client import NETWORK_CONFIG as _PAYMENT_NETWORKS

logger = logging.getLogger(__name__)


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

# Contract addresses — CREATE2 deterministic deployment (same address on all mainnets/testnets)
_MAINNET_IDENTITY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
_MAINNET_REPUTATION = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
_TESTNET_IDENTITY = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
_TESTNET_REPUTATION = "0x8004B663056A597Dffe9eCcC1965A193B7388713"
_TESTNET_VALIDATION = "0x8004Cb1BF31DAf7788923b405b754f57acEB4272"

_TESTNET_SUFFIXES = ("-sepolia", "-amoy", "-fuji")

# --- Auto-derive ERC-8004 contracts from payment NETWORK_CONFIG ---
# All payment-network mainnets have ERC-8004 (CREATE2 same-address deployment).
# Testnets use different registry addresses and are listed explicitly below.
ERC8004_CONTRACTS: Dict[str, Dict[str, Any]] = {}

# Mainnets: auto-generated from sdk_client.py
for _net, _cfg in _PAYMENT_NETWORKS.items():
    if _net.endswith(_TESTNET_SUFFIXES):
        continue  # Testnets handled below
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

# Testnets: different CREATE2 registries, listed explicitly
for _testnet, _chain_id in [
    ("ethereum-sepolia", 11155111),
    ("base-sepolia", 84532),
    ("polygon-amoy", 80002),
    ("arbitrum-sepolia", 421614),
    ("celo-sepolia", 44787),
    ("avalanche-fuji", 43113),
]:
    ERC8004_CONTRACTS[_testnet] = {
        "identity_registry": _TESTNET_IDENTITY,
        "reputation_registry": _TESTNET_REPUTATION,
        "validation_registry": _TESTNET_VALIDATION,
        "chain_id": _chain_id,
    }

# Alias: "base-mainnet" → "base" (SDK uses "base-mainnet", facilitator uses "base")
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
# Facilitator Client
# =============================================================================


class ERC8004FacilitatorClient:
    """
    ERC-8004 client that uses the Facilitator for on-chain operations.

    This is the production approach - the Facilitator handles:
    - Gas fees
    - Transaction signing
    - Network management

    Usage:
        client = ERC8004FacilitatorClient()

        # Get agent identity
        identity = await client.get_identity(agent_id=469)

        # Submit feedback (agents/workers can rate each other)
        result = await client.submit_feedback(
            agent_id=469,
            value=85,
            tag1="quality",
        )

        # Get reputation
        reputation = await client.get_reputation(agent_id=469)
    """

    def __init__(
        self,
        facilitator_url: Optional[str] = None,
        network: str = ERC8004_NETWORK,
        timeout: float = 30.0,
    ):
        self.facilitator_url = facilitator_url or FACILITATOR_URL
        self.network = network
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            "ERC8004FacilitatorClient initialized: facilitator=%s, network=%s",
            self.facilitator_url,
            self.network,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ERC8004FacilitatorClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    # =========================================================================
    # Identity Operations
    # =========================================================================

    async def get_identity(self, agent_id: int) -> Optional[AgentIdentity]:
        """
        Get agent identity from ERC-8004 Identity Registry.

        Args:
            agent_id: The agent's token ID

        Returns:
            AgentIdentity or None if not found
        """
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.facilitator_url}/identity/{self.network}/{agent_id}"
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(
                    "Failed to get identity for agent %d: %s", agent_id, response.text
                )
                return None

            data = response.json()

            return AgentIdentity(
                agent_id=data.get("agentId", agent_id),
                owner=data.get("owner", ""),
                agent_uri=data.get("agentUri", ""),
                agent_wallet=data.get("agentWallet"),
                network=data.get("network", self.network),
                name=data.get("name"),
                description=data.get("description"),
                image=data.get("image"),
                services=data.get("services", []),
            )

        except Exception as e:
            logger.error("Failed to get identity for agent %d: %s", agent_id, e)
            return None

    # =========================================================================
    # Registration (Gasless — Facilitator pays gas)
    # =========================================================================

    async def register_agent(
        self,
        network: str,
        agent_uri: str,
        metadata: Optional[List[Dict[str, str]]] = None,
        recipient: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a new agent on the ERC-8004 Identity Registry (gasless).

        The facilitator pays all gas fees. If recipient is specified, the minted
        NFT is transferred to that address after registration.

        Args:
            network: ERC-8004 network (e.g. "base-mainnet", "ethereum", "polygon")
            agent_uri: URI to agent registration file (IPFS or HTTPS)
            metadata: Optional key-value pairs [{"key": "name", "value": "My Agent"}]
            recipient: Optional address to receive the NFT after minting

        Returns:
            dict with success, agentId, transaction, transferTransaction, owner, network
        """
        if network not in ERC8004_CONTRACTS:
            return {
                "success": False,
                "error": f"Unsupported network: {network}. Supported: {ERC8004_SUPPORTED_NETWORKS}",
            }

        client = await self._get_client()

        request_body: Dict[str, Any] = {
            "x402Version": 1,
            "network": network,
            "agentUri": agent_uri,
        }
        if metadata:
            request_body["metadata"] = metadata
        if recipient:
            request_body["recipient"] = recipient

        try:
            response = await client.post(
                f"{self.facilitator_url}/register",
                json=request_body,
            )

            data = response.json()

            if response.status_code != 200 or not data.get("success"):
                logger.error("Agent registration failed: %s", data)
                return {
                    "success": False,
                    "error": data.get("error", f"HTTP {response.status_code}"),
                    "network": network,
                }

            logger.info(
                "Agent registered: agentId=%s, network=%s, tx=%s",
                data.get("agentId"),
                data.get("network"),
                data.get("transaction"),
            )

            return {
                "success": True,
                "agentId": data.get("agentId"),
                "transaction": data.get("transaction"),
                "transferTransaction": data.get("transferTransaction"),
                "owner": data.get("owner"),
                "network": data.get("network", network),
            }

        except Exception as e:
            logger.error("Agent registration failed: %s", e)
            return {"success": False, "error": str(e), "network": network}

    async def get_identity_metadata(
        self,
        agent_id: int,
        key: str,
        network: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Read a metadata key from an agent's ERC-8004 identity.

        Args:
            agent_id: The agent's token ID
            key: Metadata key to read
            network: Network to query (defaults to self.network)

        Returns:
            dict with agentId, key, valueHex, valueUtf8, network — or None
        """
        net = network or self.network
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.facilitator_url}/identity/{net}/{agent_id}/metadata/{key}"
            )
            if response.status_code != 200:
                return None
            return response.json()
        except Exception as e:
            logger.error("Failed to get identity metadata: %s", e)
            return None

    async def get_total_supply(self, network: Optional[str] = None) -> Optional[int]:
        """Get total number of registered agents on a network."""
        net = network or self.network
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.facilitator_url}/identity/{net}/total-supply"
            )
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get("totalSupply")
        except Exception as e:
            logger.error("Failed to get total supply: %s", e)
            return None

    # =========================================================================
    # Reputation Operations
    # =========================================================================

    async def get_reputation(
        self,
        agent_id: int,
        tag1: str = "",
        tag2: str = "",
        include_feedback: bool = False,
    ) -> Optional[ReputationSummary]:
        """
        Get reputation summary for an agent.

        Args:
            agent_id: The agent's token ID
            tag1: Filter by primary tag
            tag2: Filter by secondary tag
            include_feedback: Include individual feedback entries

        Returns:
            ReputationSummary or None
        """
        client = await self._get_client()

        try:
            params = {}
            if tag1:
                params["tag1"] = tag1
            if tag2:
                params["tag2"] = tag2
            if include_feedback:
                params["includeFeedback"] = "true"

            response = await client.get(
                f"{self.facilitator_url}/reputation/{self.network}/{agent_id}",
                params=params,
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(
                    "Failed to get reputation for agent %d: %s", agent_id, response.text
                )
                return None

            data = response.json()
            summary = data.get("summary", data)

            return ReputationSummary(
                agent_id=data.get("agentId", agent_id),
                count=summary.get("count", 0),
                summary_value=summary.get("summaryValue", 0),
                summary_value_decimals=summary.get("summaryValueDecimals", 0),
                network=data.get("network", self.network),
            )

        except Exception as e:
            logger.error("Failed to get reputation for agent %d: %s", agent_id, e)
            return None

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
        """
        Submit reputation feedback for an agent.

        Args:
            agent_id: The agent's token ID
            value: Feedback value (0-100 for decimals=0)
            value_decimals: Decimal places for value
            tag1: Primary tag (e.g., "quality", "speed", "communication")
            tag2: Secondary tag
            endpoint: Service endpoint that was used
            feedback_uri: URI to off-chain feedback file (IPFS preferred)
            feedback_hash: Keccak256 hash of feedback content
            proof: Proof of payment (for verified feedback)

        Returns:
            FeedbackResult with transaction details
        """
        # Validate agent_id before making network call
        if not isinstance(agent_id, int) or agent_id <= 0:
            return FeedbackResult(
                success=False,
                error=f"agent_id must be a positive integer, got {agent_id}",
                network=self.network,
            )

        client = await self._get_client()

        try:
            request_body = {
                "x402Version": 1,
                "network": self.network,
                "feedback": {
                    "agentId": agent_id,
                    "value": value,
                    "valueDecimals": value_decimals,
                    "tag1": tag1,
                    "tag2": tag2,
                    "endpoint": endpoint,
                    "feedbackUri": feedback_uri,
                },
            }

            if feedback_hash:
                request_body["feedback"]["feedbackHash"] = feedback_hash

            if proof:
                request_body["feedback"]["proof"] = proof

            response = await client.post(
                f"{self.facilitator_url}/feedback",
                json=request_body,
            )

            data = response.json()

            if response.status_code != 200 or not data.get("success"):
                return FeedbackResult(
                    success=False,
                    error=data.get("error", f"HTTP {response.status_code}"),
                    network=self.network,
                )

            tx_hash = None
            if "transaction" in data:
                tx = data["transaction"]
                if isinstance(tx, dict) and "Evm" in tx:
                    tx_hash = (
                        "0x" + "".join(f"{b:02x}" for b in tx["Evm"])
                        if isinstance(tx["Evm"], list)
                        else tx["Evm"]
                    )
                elif isinstance(tx, str):
                    tx_hash = tx

            return FeedbackResult(
                success=True,
                transaction_hash=tx_hash,
                feedback_index=data.get("feedbackIndex"),
                network=data.get("network", self.network),
            )

        except Exception as e:
            logger.error("Failed to submit feedback: %s", e)
            return FeedbackResult(
                success=False,
                error=str(e),
                network=self.network,
            )

    async def revoke_feedback(
        self,
        agent_id: int,
        feedback_index: int,
    ) -> FeedbackResult:
        """
        Revoke previously submitted feedback.

        Args:
            agent_id: The agent's token ID
            feedback_index: Index of feedback to revoke

        Returns:
            FeedbackResult
        """
        client = await self._get_client()

        try:
            request_body = {
                "x402Version": 1,
                "network": self.network,
                "agentId": agent_id,
                "feedbackIndex": feedback_index,
            }

            response = await client.post(
                f"{self.facilitator_url}/feedback/revoke",
                json=request_body,
            )

            data = response.json()

            if response.status_code != 200 or not data.get("success"):
                return FeedbackResult(
                    success=False,
                    error=data.get("error", f"HTTP {response.status_code}"),
                    network=self.network,
                )

            tx_hash = None
            if "transaction" in data:
                tx = data["transaction"]
                if isinstance(tx, dict) and "Evm" in tx:
                    tx_hash = tx["Evm"]

            return FeedbackResult(
                success=True,
                transaction_hash=tx_hash,
                feedback_index=feedback_index,
                network=self.network,
            )

        except Exception as e:
            logger.error("Failed to revoke feedback: %s", e)
            return FeedbackResult(
                success=False,
                error=str(e),
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
        """
        Respond to feedback as the agent owner.

        Args:
            agent_id: The agent's token ID
            client_address: Address of client who left feedback
            feedback_index: Index of feedback to respond to
            response_uri: URI to response content (IPFS preferred)
            response_hash: Keccak256 hash of response content

        Returns:
            FeedbackResult
        """
        client = await self._get_client()

        try:
            request_body = {
                "x402Version": 1,
                "network": self.network,
                "agentId": agent_id,
                "clientAddress": {"Evm": client_address},
                "feedbackIndex": feedback_index,
                "responseUri": response_uri,
            }

            if response_hash:
                request_body["responseHash"] = response_hash

            response = await client.post(
                f"{self.facilitator_url}/feedback/response",
                json=request_body,
            )

            data = response.json()

            if response.status_code != 200 or not data.get("success"):
                return FeedbackResult(
                    success=False,
                    error=data.get("error", f"HTTP {response.status_code}"),
                    network=self.network,
                )

            return FeedbackResult(
                success=True,
                transaction_hash=data.get("transaction", {}).get("Evm"),
                feedback_index=feedback_index,
                network=self.network,
            )

        except Exception as e:
            logger.error("Failed to respond to feedback: %s", e)
            return FeedbackResult(
                success=False,
                error=str(e),
                network=self.network,
            )


# =============================================================================
# Execution Market-Specific Functions
# =============================================================================

_default_client: Optional[ERC8004FacilitatorClient] = None


def get_facilitator_client() -> ERC8004FacilitatorClient:
    """Get or create the default ERC8004FacilitatorClient instance."""
    global _default_client
    if _default_client is None:
        _default_client = ERC8004FacilitatorClient()
    return _default_client


async def get_em_reputation() -> Optional[ReputationSummary]:
    """Get Execution Market's reputation as an agent."""
    client = get_facilitator_client()
    return await client.get_reputation(EM_AGENT_ID)


async def get_em_identity() -> Optional[AgentIdentity]:
    """Get Execution Market's identity from the registry."""
    client = get_facilitator_client()
    return await client.get_identity(EM_AGENT_ID)


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

            onchain = await check_worker_identity(worker_address)
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
        return FeedbackResult(
            success=False,
            error=f"Worker {worker_address[:10]}... has no ERC-8004 identity. "
            "Register the worker first via POST /reputation/register.",
            network=ERC8004_NETWORK,
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
            network=ERC8004_NETWORK,
        )
    except Exception as exc:
        logger.warning("Feedback persistence failed (continuing): %s", exc)
        feedback_uri = f"{FEEDBACK_PUBLIC_URL}/feedback/{task_id}"

    # Direct on-chain call — platform wallet rates worker's identity.
    # Platform wallet doesn't own worker agents, so self-feedback check passes.
    # This bypasses the Facilitator, eliminating nonce races and ensuring
    # correct msg.sender attribution (our wallet = our agent).
    from integrations.erc8004.direct_reputation import give_feedback_direct

    return await give_feedback_direct(
        agent_id=target_agent_id,
        value=score,
        tag1="worker_rating",
        tag2=worker_address[:10] if worker_address else "",
        endpoint=f"task:{task_id}",
        feedback_uri=feedback_uri,
        feedback_hash=feedback_hash,
        # private_key=None → defaults to WALLET_PRIVATE_KEY (platform wallet)
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
) -> FeedbackResult:
    """
    Rate an agent (human/worker rates agent).

    Persists feedback document to S3 with keccak256 hash.

    If relay_private_key is provided, submits the on-chain giveFeedback() TX
    autonomously using the relay wallet (a secondary wallet at BIP-44 index+100
    that does NOT own any agent NFT, avoiding the self-feedback revert).
    This enables fully autonomous agent rating in the KK V2 swarm flow.

    If relay_private_key is NOT provided, returns pending_worker_signature=True
    — the actual on-chain TX must be signed by the worker's wallet directly
    via the dashboard (trustless, original behavior).

    Args:
        agent_id: Agent's ERC-8004 token ID
        task_id: Task identifier
        score: Rating 0-100
        comment: Optional comment
        proof_tx: Transaction hash of payment received
        task_title: Task title for context
        task_category: Task category
        bounty_usd: Task bounty amount
        relay_private_key: Optional relay wallet private key for autonomous
            on-chain signing. If provided, giveFeedback() is called directly.

    Returns:
        FeedbackResult with transaction_hash if relay key provided,
        or pending (transaction_hash=None) if not.
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
            network=ERC8004_NETWORK,
        )
    except Exception as exc:
        logger.warning("Feedback persistence failed (continuing): %s", exc)
        feedback_uri = f"{FEEDBACK_PUBLIC_URL}/feedback/{task_id}"

    # Autonomous path: relay wallet signs giveFeedback() directly on-chain
    if relay_private_key:
        logger.info(
            "Agent rating via relay wallet (autonomous): agent=%d, task=%s",
            agent_id,
            task_id,
        )
        from integrations.erc8004.direct_reputation import give_feedback_direct

        return await give_feedback_direct(
            agent_id=agent_id,
            value=score,
            tag1="agent_rating",
            tag2=f"task:{task_id[:8]}",
            endpoint=f"task:{task_id}",
            feedback_uri=feedback_uri,
            feedback_hash=feedback_hash,
            private_key=relay_private_key,
        )

    # No relay key available — return pending result.
    # The worker must sign the on-chain TX via their own wallet (dashboard flow)
    # or the relay key must be configured in ECS (EM_REPUTATION_RELAY_KEY).
    # We do NOT fall through to Facilitator because Facilitator becomes msg.sender
    # on-chain, which misrepresents who gave the feedback (trust violation).
    logger.warning(
        "Agent rating pending — no relay key available: agent=%d, task=%s",
        agent_id,
        task_id,
    )
    return FeedbackResult(
        success=True,
        transaction_hash=None,
    )


async def get_agent_info(agent_id: int) -> Optional[AgentIdentity]:
    """Get any agent's identity."""
    client = get_facilitator_client()
    return await client.get_identity(agent_id)


async def get_agent_reputation(agent_id: int) -> Optional[ReputationSummary]:
    """Get any agent's reputation."""
    client = get_facilitator_client()
    return await client.get_reputation(agent_id)
