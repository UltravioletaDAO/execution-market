"""
Shared utilities for E2E tests.

Provides:
- Two-wallet configuration (Agent=0x3403, Worker=0x857f)
- USDC balance checker via RPC
- API helper for common operations
- Masking helpers for secure logging
"""

import json
import logging
import os
from decimal import Decimal
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# ============== CONFIGURATION ==============

API_BASE = os.environ.get("EM_API_URL", "https://mcp.execution.market")
FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")
PLATFORM_FEE_PCT = Decimal("0.08")

# Wallet addresses (known, not secret)
WALLET_A_ADDRESS = "0x34033041a5944B8F10f8E4D8496Bfb84f1A293A8"  # Production/Agent
WALLET_B_ADDRESS = "0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd"  # Dev/Worker
TREASURY_ADDRESS = "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"

# Network configuration
NETWORKS = {
    "base": {
        "rpc": "https://mainnet.base.org",
        "chain_id": 8453,
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    },
    "ethereum": {
        "rpc": "https://eth.llamarpc.com",
        "chain_id": 1,
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    },
    "polygon": {
        "rpc": "https://polygon-rpc.com",
        "chain_id": 137,
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    },
    "arbitrum": {
        "rpc": "https://arb1.arbitrum.io/rpc",
        "chain_id": 42161,
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    },
    "celo": {
        "rpc": "https://forno.celo.org",
        "chain_id": 42220,
        "usdc": "0xcebA9300f2b948710d2653dD7B07f33A8B32118C",
    },
    "monad": {
        "rpc": "https://rpc.monad.xyz",
        "chain_id": 143,
        "usdc": "0x754704Bc059F8C67012fEd69BC8A327a5aafb603",
    },
    "avalanche": {
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
        "chain_id": 43114,
        "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
    },
}

ENABLED_NETWORKS = ["base", "ethereum", "polygon", "arbitrum", "celo", "monad", "avalanche"]


# ============== SECURITY HELPERS ==============


def mask_key(key: str) -> str:
    if not key or len(key) < 12:
        return "***MASKED***"
    return f"{key[:6]}...{key[-4:]}"


def mask_address(addr: str) -> str:
    if not addr:
        return "***EMPTY***"
    return f"{addr[:10]}...{addr[-4:]}"


# ============== USDC BALANCE CHECKER ==============


async def get_usdc_balance(
    http_client, network: str, wallet_address: str
) -> Optional[Decimal]:
    """Query USDC balance via eth_call to public RPC.

    Returns balance in USDC (6 decimals) or None on failure.
    """
    net_config = NETWORKS.get(network)
    if not net_config:
        return None

    # balanceOf(address) selector = 0x70a08231
    # Pad address to 32 bytes
    addr_clean = wallet_address.lower().replace("0x", "")
    call_data = f"0x70a08231000000000000000000000000{addr_clean}"

    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {"to": net_config["usdc"], "data": call_data},
            "latest",
        ],
        "id": 1,
    }

    try:
        resp = await http_client.post(
            net_config["rpc"],
            json=payload,
            timeout=15.0,
        )
        result = resp.json().get("result", "0x0")
        balance_raw = int(result, 16)
        return Decimal(balance_raw) / Decimal(10**6)
    except Exception as e:
        logger.warning(f"Failed to get USDC balance on {network}: {e}")
        return None


# ============== API HELPERS ==============


class EMApiClient:
    """Helper for Execution Market API calls."""

    def __init__(self, http_client, api_key: str):
        self.client = http_client
        self.api_key = api_key
        self.base = API_BASE

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    async def create_task(
        self,
        bounty_usd: float,
        payment_header: Optional[str] = None,
        network: str = "base",
        title: Optional[str] = None,
        deadline_hours: int = 1,
    ) -> Dict[str, Any]:
        """Create a task. Returns response dict (not just task)."""
        import uuid

        headers = self._headers()
        if payment_header:
            headers["X-Payment"] = payment_header

        body = {
            "title": title or f"[E2E] Test task {uuid.uuid4().hex[:8]}",
            "instructions": "Automated E2E test. Respond with: test_complete. " * 2,
            "category": "simple_action",
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "evidence_required": ["text_response"],
            "payment_network": network,
        }

        resp = await self.client.post(
            f"{self.base}/api/v1/tasks",
            headers=headers,
            json=body,
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        resp = await self.client.get(
            f"{self.base}/api/v1/tasks/{task_id}",
            headers=self._headers(),
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def cancel_task(self, task_id: str, reason: str = "E2E test cleanup") -> Dict[str, Any]:
        resp = await self.client.post(
            f"{self.base}/api/v1/tasks/{task_id}/cancel",
            headers=self._headers(),
            json={"reason": reason},
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def register_worker(
        self, wallet_address: str, display_name: str = "E2E Test Worker"
    ) -> Dict[str, Any]:
        resp = await self.client.post(
            f"{self.base}/api/v1/executors/register",
            json={
                "wallet_address": wallet_address,
                "display_name": display_name,
            },
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def apply_to_task(
        self, task_id: str, executor_id: str, message: str = "E2E test application"
    ) -> Dict[str, Any]:
        resp = await self.client.post(
            f"{self.base}/api/v1/tasks/{task_id}/apply",
            json={
                "executor_id": executor_id,
                "message": message,
            },
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def submit_work(
        self,
        task_id: str,
        executor_id: str,
        evidence: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        body = {
            "executor_id": executor_id,
            "evidence": evidence or [
                {"type": "text_response", "content": "test_complete"}
            ],
            "notes": "E2E automated submission",
        }
        resp = await self.client.post(
            f"{self.base}/api/v1/tasks/{task_id}/submit",
            json=body,
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def approve_submission(
        self, submission_id: str, verdict: str = "accepted", notes: str = "E2E auto-approve"
    ) -> Dict[str, Any]:
        resp = await self.client.post(
            f"{self.base}/api/v1/submissions/{submission_id}/approve",
            headers=self._headers(),
            json={"verdict": verdict, "notes": notes},
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def rate_worker(
        self, task_id: str, worker_wallet: str, score: int = 85
    ) -> Dict[str, Any]:
        resp = await self.client.post(
            f"{self.base}/api/v1/reputation/workers/rate",
            headers=self._headers(),
            json={
                "task_id": task_id,
                "worker_wallet": worker_wallet,
                "score": score,
                "comment": "E2E test rating",
            },
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def rate_agent(
        self, agent_id: int, task_id: str, score: int = 90
    ) -> Dict[str, Any]:
        resp = await self.client.post(
            f"{self.base}/api/v1/reputation/agents/rate",
            json={
                "agent_id": agent_id,
                "task_id": task_id,
                "score": score,
                "comment": "E2E test rating",
            },
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def health(self) -> Dict[str, Any]:
        resp = await self.client.get(f"{self.base}/health")
        return {"status_code": resp.status_code, "data": resp.json()}

    async def config(self) -> Dict[str, Any]:
        resp = await self.client.get(f"{self.base}/api/v1/config")
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_available_tasks(self) -> Dict[str, Any]:
        resp = await self.client.get(
            f"{self.base}/api/v1/tasks/available",
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_reputation_info(self) -> Dict[str, Any]:
        resp = await self.client.get(f"{self.base}/api/v1/reputation/info")
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_reputation_networks(self) -> Dict[str, Any]:
        resp = await self.client.get(f"{self.base}/api/v1/reputation/networks")
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_em_reputation(self) -> Dict[str, Any]:
        resp = await self.client.get(f"{self.base}/api/v1/reputation/em")
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_em_identity(self) -> Dict[str, Any]:
        resp = await self.client.get(f"{self.base}/api/v1/reputation/em/identity")
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_agent_reputation(self, agent_id: int) -> Dict[str, Any]:
        resp = await self.client.get(
            f"{self.base}/api/v1/reputation/agents/{agent_id}"
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_agent_identity(self, agent_id: int) -> Dict[str, Any]:
        resp = await self.client.get(
            f"{self.base}/api/v1/reputation/agents/{agent_id}/identity"
        )
        return {"status_code": resp.status_code, "data": resp.json()}

    async def get_escrow_config(self) -> Dict[str, Any]:
        resp = await self.client.get(f"{self.base}/api/v1/escrow/config")
        return {"status_code": resp.status_code, "data": resp.json()}

    async def reject_submission(
        self, submission_id: str, notes: str = "E2E auto-reject"
    ) -> Dict[str, Any]:
        resp = await self.client.post(
            f"{self.base}/api/v1/submissions/{submission_id}/reject",
            headers=self._headers(),
            json={"notes": notes},
        )
        return {"status_code": resp.status_code, "data": resp.json()}


# ============== FACILITATOR HELPERS ==============


async def check_facilitator_health(http_client) -> Optional[Dict]:
    """Check facilitator reachability."""
    try:
        resp = await http_client.get(
            f"{FACILITATOR_URL}/health",
            timeout=10.0,
        )
        return {"status_code": resp.status_code, "data": resp.json()}
    except Exception as e:
        logger.warning(f"Facilitator health check failed: {e}")
        return None


async def check_contract_code(
    http_client, network: str, contract_address: str
) -> bool:
    """Check if a contract address has code deployed (not an EOA)."""
    net_config = NETWORKS.get(network)
    if not net_config:
        return False

    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [contract_address, "latest"],
        "id": 1,
    }

    try:
        resp = await http_client.post(
            net_config["rpc"],
            json=payload,
            timeout=15.0,
        )
        result = resp.json().get("result", "0x")
        # "0x" or "0x0" means no code = EOA
        return len(result) > 4
    except Exception as e:
        logger.warning(f"Contract code check failed on {network}: {e}")
        return False
