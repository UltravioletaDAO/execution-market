"""
Reputation & Identity MCP Tools for Execution Market (WS-4)

Exposes ERC-8004 reputation and identity operations to AI agents via MCP tools:
- em_rate_worker: Agent rates a worker after task completion
- em_rate_agent: Worker rates an agent after task completion
- em_get_reputation: Get on-chain reputation for any agent
- em_check_identity: Check if a wallet has an ERC-8004 identity
- em_register_identity: Register a new identity (gasless)

All tools are gated behind the `erc8004_mcp_tools_enabled` feature flag.
"""

import json
import logging
import os
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Feature flag: env var or future feature_flags module
_ERC8004_MCP_TOOLS_ENABLED: Optional[bool] = None


def _is_feature_enabled() -> bool:
    """Check if erc8004_mcp_tools are enabled.

    Resolution order:
    1. feature_flags module (if available — created by Task #1)
    2. EM_ERC8004_MCP_TOOLS_ENABLED env var (default: true)
    """
    global _ERC8004_MCP_TOOLS_ENABLED
    if _ERC8004_MCP_TOOLS_ENABLED is not None:
        return _ERC8004_MCP_TOOLS_ENABLED

    # Try the feature_flags module first
    try:
        from feature_flags import is_enabled  # type: ignore[import-not-found]

        _ERC8004_MCP_TOOLS_ENABLED = is_enabled("erc8004_mcp_tools_enabled")
        return _ERC8004_MCP_TOOLS_ENABLED
    except (ImportError, Exception):
        pass

    # Fallback: env var (defaults to enabled)
    val = os.environ.get("EM_ERC8004_MCP_TOOLS_ENABLED", "true").lower()
    _ERC8004_MCP_TOOLS_ENABLED = val in ("1", "true", "yes")
    return _ERC8004_MCP_TOOLS_ENABLED


# Availability flags
ERC8004_AVAILABLE = False
try:
    from integrations.erc8004.facilitator_client import (
        get_facilitator_client,
        rate_worker as _rate_worker,
        rate_agent as _rate_agent,
    )
    from integrations.erc8004.identity import (
        check_worker_identity as _check_worker_identity,
        register_worker_gasless as _register_worker_gasless,
    )

    ERC8004_AVAILABLE = True
except ImportError:
    logger.warning("ERC-8004 integration not available for MCP reputation tools")


FEATURE_DISABLED_MSG = (
    "Error: ERC-8004 MCP reputation tools are not enabled. "
    "Set EM_ERC8004_MCP_TOOLS_ENABLED=true to activate."
)

ERC8004_UNAVAILABLE_MSG = (
    "Error: ERC-8004 integration is not available. Install the required dependencies."
)


def register_reputation_tools(
    mcp: FastMCP,
    db_module: Any = None,
) -> None:
    """Register reputation and identity tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        db_module: Database module (defaults to supabase_client)
    """
    if db_module is None:
        import supabase_client as db_module  # noqa: F811

    # ------------------------------------------------------------------
    # 1. em_rate_worker
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_rate_worker",
        annotations={
            "title": "Rate a Worker",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_rate_worker(
        submission_id: str,
        score: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> str:
        """
        Rate a worker after reviewing their submission.

        Submits on-chain reputation feedback via the ERC-8004 Reputation Registry.
        If no score is provided, a dynamic score is computed from the submission.

        Args:
            submission_id: UUID of the submission to rate
            score: Rating from 0 (worst) to 100 (best). Optional — auto-scored if omitted.
            comment: Optional comment about the worker's performance

        Returns:
            Rating result with transaction hash, or error message.
        """
        if not _is_feature_enabled():
            return FEATURE_DISABLED_MSG
        if not ERC8004_AVAILABLE:
            return ERC8004_UNAVAILABLE_MSG

        try:
            # Look up submission
            client = db_module.get_client()
            result = (
                client.table("submissions")
                .select("*, tasks(*)")
                .eq("id", submission_id)
                .limit(1)
                .execute()
            )
            if not result.data:
                return f"Error: Submission {submission_id} not found"

            submission = result.data[0]
            task = submission.get("tasks") or {}
            task_id = task.get("id") or submission.get("task_id")

            if not task_id:
                return "Error: Could not resolve task for this submission"

            # Dynamic scoring if no explicit score
            actual_score = score
            score_source = "explicit"
            if actual_score is None:
                try:
                    from mcp_server.reputation.scoring import calculate_dynamic_score

                    result = calculate_dynamic_score(task, submission, {})
                    actual_score = result["score"]
                    score_source = "dynamic"
                except (ImportError, Exception) as e:
                    logger.warning("Dynamic scoring unavailable: %s", e)
                    actual_score = 75  # Reasonable default
                    score_source = "default"

            # Clamp score
            actual_score = max(0, min(100, actual_score))

            # Get worker wallet from submission executor
            executor = submission.get("executor") or {}
            worker_address = executor.get("wallet_address", "")

            # Get payment tx for proof
            proof_tx = submission.get("payment_tx") or submission.get("reputation_tx")

            feedback = await _rate_worker(
                task_id=str(task_id),
                score=actual_score,
                worker_address=worker_address,
                comment=comment or "",
                proof_tx=proof_tx,
            )

            if not feedback.success:
                return f"Error: Rating failed - {feedback.error}"

            # Store reputation_tx in submission for audit
            if feedback.transaction_hash:
                try:
                    client.table("submissions").update(
                        {"reputation_tx": feedback.transaction_hash}
                    ).eq("id", submission_id).execute()
                except Exception as db_err:
                    logger.warning("Failed to store reputation_tx: %s", db_err)
                # Also update feedback_documents for mobile/dashboard display
                try:
                    client.table("feedback_documents").update(
                        {"reputation_tx": feedback.transaction_hash}
                    ).eq("task_id", str(task_id)).eq(
                        "feedback_type", "worker_rating"
                    ).execute()
                except Exception:
                    pass  # Best-effort

            return f"""# Worker Rated Successfully

**Submission ID**: `{submission_id}`
**Score**: {actual_score}/100 ({score_source})
**Transaction**: `{feedback.transaction_hash or "N/A"}`
**Network**: {feedback.network}

{f"**Comment**: {comment}" if comment else ""}

On-chain reputation feedback recorded in the ERC-8004 Reputation Registry."""

        except Exception as e:
            logger.error("em_rate_worker failed: %s", e)
            return f"Error: Failed to rate worker - {str(e)}"

    # ------------------------------------------------------------------
    # 2. em_rate_agent
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_rate_agent",
        annotations={
            "title": "Rate an Agent",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_rate_agent(
        task_id: str,
        score: int,
        comment: Optional[str] = None,
    ) -> str:
        """
        Rate an AI agent after completing a task (worker -> agent feedback).

        Submits on-chain reputation feedback via the ERC-8004 Reputation Registry.

        Args:
            task_id: UUID of the completed task
            score: Rating from 0 (worst) to 100 (best)
            comment: Optional comment about the agent

        Returns:
            Rating result with transaction hash, or error message.
        """
        if not _is_feature_enabled():
            return FEATURE_DISABLED_MSG
        if not ERC8004_AVAILABLE:
            return ERC8004_UNAVAILABLE_MSG

        try:
            # Validate score range
            if not (0 <= score <= 100):
                return "Error: Score must be between 0 and 100"

            # Fetch task to get agent_id
            task = await db_module.get_task(task_id)
            if not task:
                return f"Error: Task {task_id} not found"

            # Verify task is in a rateable state
            task_status = str(task.get("status", "")).lower()
            if task_status in ("published", "cancelled", "expired"):
                return f"Error: Task in status '{task_status}' cannot be rated"

            # Resolve agent's ERC-8004 ID — prefer per-chain erc8004_agent_id
            # (task.agent_id is now a wallet address, not a numeric ID)
            agent_id_int = task.get("erc8004_agent_id")
            if agent_id_int is not None:
                try:
                    agent_id_int = int(agent_id_int)
                except (ValueError, TypeError):
                    agent_id_int = None
            if agent_id_int is None:
                # Fallback: try agent_id field (legacy tasks may have numeric ID)
                try:
                    agent_id_int = int(task.get("agent_id", ""))
                except (ValueError, TypeError):
                    return (
                        "Error: Task has no numeric ERC-8004 agent ID. "
                        "Cannot submit on-chain feedback."
                    )

            # Get payment tx for proof
            proof_tx = None
            try:
                client = db_module.get_client()
                sub_result = (
                    client.table("submissions")
                    .select("payment_tx")
                    .eq("task_id", task_id)
                    .eq("status", "approved")
                    .limit(1)
                    .execute()
                )
                if sub_result.data:
                    proof_tx = sub_result.data[0].get("payment_tx")
            except Exception:
                pass

            # Check for relay wallet key — enables autonomous on-chain signing
            # (KK V2 swarm flow: each agent has a relay wallet at BIP-44 index+100)
            relay_key = os.environ.get("EM_RELAY_PRIVATE_KEY") or None

            feedback = await _rate_agent(
                agent_id=agent_id_int,
                task_id=task_id,
                score=score,
                comment=comment or "",
                proof_tx=proof_tx,
                relay_private_key=relay_key,
            )

            if not feedback.success:
                return f"Error: Rating failed - {feedback.error}"

            # Determine signing mode for the response
            if relay_key and feedback.transaction_hash:
                signing_mode = "autonomous (relay wallet)"
            else:
                signing_mode = "pending worker signature"

            return f"""# Agent Rated Successfully

**Task ID**: `{task_id}`
**Agent ID**: {agent_id_int}
**Score**: {score}/100
**Transaction**: `{feedback.transaction_hash or "N/A"}`
**Network**: {feedback.network}
**Signing Mode**: {signing_mode}

{f"**Comment**: {comment}" if comment else ""}

On-chain reputation feedback recorded in the ERC-8004 Reputation Registry."""

        except Exception as e:
            logger.error("em_rate_agent failed: %s", e)
            return f"Error: Failed to rate agent - {str(e)}"

    # ------------------------------------------------------------------
    # 3. em_get_reputation
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_get_reputation",
        annotations={
            "title": "Get Agent Reputation",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def em_get_reputation(
        agent_id: Optional[int] = None,
        wallet_address: Optional[str] = None,
        network: str = "base",
    ) -> str:
        """
        Get on-chain reputation for an agent from the ERC-8004 Reputation Registry.

        Provide either agent_id (numeric ERC-8004 token ID) or wallet_address.

        Args:
            agent_id: ERC-8004 agent token ID (e.g. 2106)
            wallet_address: Agent's wallet address (resolved to agent_id)
            network: ERC-8004 network (default: "base")

        Returns:
            Reputation score, rating count, and network info.
        """
        if not _is_feature_enabled():
            return FEATURE_DISABLED_MSG
        if not ERC8004_AVAILABLE:
            return ERC8004_UNAVAILABLE_MSG

        try:
            if agent_id is None and wallet_address is None:
                return "Error: Provide either agent_id or wallet_address"

            resolved_id = agent_id

            # If wallet_address given, try to resolve to agent_id
            if resolved_id is None and wallet_address:
                identity_result = await _check_worker_identity(wallet_address)
                if (
                    identity_result.status.value == "registered"
                    and identity_result.agent_id is not None
                ):
                    resolved_id = identity_result.agent_id
                else:
                    return f"""# Identity Not Found

**Wallet**: `{wallet_address}`
**Status**: Not registered on ERC-8004

This wallet does not have an ERC-8004 identity on {network}.
Use `em_register_identity` to register."""

            client = get_facilitator_client()
            original_network = client.network
            client.network = network
            try:
                reputation = await client.get_reputation(resolved_id)
            finally:
                client.network = original_network

            if not reputation:
                return f"""# No Reputation Found

**Agent ID**: {resolved_id}
**Network**: {network}

No reputation data found. The agent may be newly registered
or has not received any feedback yet."""

            return json.dumps(
                {
                    "agent_id": reputation.agent_id,
                    "score": reputation.score,
                    "rating_count": reputation.count,
                    "network": reputation.network,
                    "summary_value": reputation.summary_value,
                    "summary_value_decimals": reputation.summary_value_decimals,
                },
                indent=2,
            )

        except Exception as e:
            logger.error("em_get_reputation failed: %s", e)
            return f"Error: Failed to get reputation - {str(e)}"

    # ------------------------------------------------------------------
    # 4. em_check_identity
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_check_identity",
        annotations={
            "title": "Check ERC-8004 Identity",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def em_check_identity(
        wallet_address: str,
        network: str = "base",
    ) -> str:
        """
        Check if a wallet address has an ERC-8004 identity on-chain.

        Args:
            wallet_address: Ethereum wallet address (0x-prefixed)
            network: Network to check (default: "base")

        Returns:
            Identity status: registered/not_registered, agent_id if found.
        """
        if not _is_feature_enabled():
            return FEATURE_DISABLED_MSG
        if not ERC8004_AVAILABLE:
            return ERC8004_UNAVAILABLE_MSG

        try:
            result = await _check_worker_identity(wallet_address)

            return json.dumps(
                {
                    "is_registered": result.status.value == "registered",
                    "agent_id": result.agent_id,
                    "wallet_address": result.wallet_address,
                    "network": result.network,
                    "chain_id": result.chain_id,
                    "registry_address": result.registry_address,
                },
                indent=2,
            )

        except Exception as e:
            logger.error("em_check_identity failed: %s", e)
            return f"Error: Failed to check identity - {str(e)}"

    # ------------------------------------------------------------------
    # 5. em_register_identity
    # ------------------------------------------------------------------

    @mcp.tool(
        name="em_register_identity",
        annotations={
            "title": "Register ERC-8004 Identity (Gasless)",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_register_identity(
        wallet_address: str,
        mode: str = "gasless",
        network: str = "base",
    ) -> str:
        """
        Register a new ERC-8004 identity on-chain (gasless via Facilitator).

        The Facilitator pays all gas fees. The minted ERC-721 NFT is
        transferred to the specified wallet address.

        Args:
            wallet_address: Wallet address to register and receive the NFT
            mode: Must be "gasless" (only supported mode)
            network: ERC-8004 network (default: "base")

        Returns:
            Registration result with agent_id and transaction hash.
        """
        if not _is_feature_enabled():
            return FEATURE_DISABLED_MSG
        if not ERC8004_AVAILABLE:
            return ERC8004_UNAVAILABLE_MSG

        try:
            if mode != "gasless":
                return "Error: Only 'gasless' mode is supported"

            # Validate wallet address format
            if not wallet_address or not wallet_address.startswith("0x"):
                return (
                    "Error: wallet_address must be a valid 0x-prefixed Ethereum address"
                )
            if len(wallet_address) != 42:
                return "Error: wallet_address must be 42 characters (0x + 40 hex)"

            result = await _register_worker_gasless(
                wallet_address=wallet_address,
                network=network,
            )

            if result.status.value == "error":
                return f"Error: Registration failed - {result.error}"

            return json.dumps(
                {
                    "success": result.status.value == "registered",
                    "agent_id": result.agent_id,
                    "wallet_address": result.wallet_address,
                    "network": result.network,
                    "chain_id": result.chain_id,
                },
                indent=2,
            )

        except Exception as e:
            logger.error("em_register_identity failed: %s", e)
            return f"Error: Failed to register identity - {str(e)}"

    logger.info(
        "Reputation tools registered (feature_enabled=%s, erc8004_available=%s)",
        _is_feature_enabled(),
        ERC8004_AVAILABLE,
    )
