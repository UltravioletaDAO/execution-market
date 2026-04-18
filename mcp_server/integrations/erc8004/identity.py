"""
ERC-8004 Identity Verification & Worker Registration

Two responsibilities:

1. **Agent identity verification** (existing) -- fresh lookup by numeric agent ID
   via the Ultravioleta Facilitator for task-creation validation.

2. **Worker identity check & registration** (new) -- on-chain ``balanceOf`` via
   Base RPC to determine whether a worker wallet holds an ERC-8004 identity
   token, plus unsigned-tx preparation so the frontend wallet can sign and
   submit ``register(string agentURI)``.

Usage::

    # Agent verification (existing)
    result = await verify_agent_identity("469", network="base")

    # Worker identity check (new)
    result = await check_worker_identity("0xABC...")

    # Build registration tx for worker to sign (new)
    tx = await build_worker_registration_tx("0xABC...")
"""

import os
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional

import httpx

from utils.pii import truncate_wallet

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent identity verification (existing functionality)
# ---------------------------------------------------------------------------

_NOT_REGISTERED: Dict[str, Any] = {
    "registered": False,
    "agent_id": None,
    "metadata_uri": None,
    "owner": None,
    "name": None,
    "network": None,
}


async def verify_agent_identity(
    agent_id_or_wallet: str,
    network: str = "base",
) -> Dict[str, Any]:
    """
    Verify an agent's ERC-8004 on-chain identity via the Facilitator.

    Resolution strategy:
      1. If *agent_id_or_wallet* is purely numeric, treat it as an ERC-8004
         agent token ID and look it up directly through the Facilitator.
      2. Otherwise (e.g. a wallet address or arbitrary string), the identity
         cannot currently be resolved via the Facilitator, so we return
         ``registered=False``.

    Always performs a fresh lookup -- no caching.

    Parameters
    ----------
    agent_id_or_wallet:
        Either a numeric ERC-8004 agent ID (e.g. ``"469"``) or a wallet
        address / opaque agent identifier.
    network:
        ERC-8004 network to query (default ``"base"``).

    Returns
    -------
    dict with keys:
        - ``registered`` (bool)
        - ``agent_id`` (int | None)
        - ``metadata_uri`` (str | None)
        - ``owner`` (str | None) -- on-chain owner address
        - ``name`` (str | None)
        - ``network`` (str | None)
    """
    # ---- Try numeric agent ID path ------------------------------------------
    try:
        numeric_id = int(agent_id_or_wallet)
    except (ValueError, TypeError):
        numeric_id = None

    if numeric_id is not None:
        return await _lookup_by_agent_id(numeric_id, network)

    # ---- Non-numeric identifier -- cannot resolve via facilitator -----------
    logger.info(
        "ERC-8004 identity check: agent_id=%s is not numeric, "
        "cannot resolve via facilitator (network=%s)",
        agent_id_or_wallet,
        network,
    )
    return dict(_NOT_REGISTERED, network=network)


# ---------------------------------------------------------------------------
# Internal helpers for agent verification
# ---------------------------------------------------------------------------


async def _lookup_by_agent_id(agent_id: int, network: str) -> Dict[str, Any]:
    """
    Look up an agent by its numeric ERC-8004 token ID using the Facilitator.
    """
    try:
        from .facilitator_client import get_facilitator_client

        client = get_facilitator_client()
        # Override the client's default network for this specific call
        original_network = client.network
        client.network = network
        try:
            identity = await client.get_identity(agent_id)
        finally:
            client.network = original_network

        if identity is None:
            logger.info(
                "ERC-8004 identity NOT found: agent_id=%d, network=%s",
                agent_id,
                network,
            )
            return dict(_NOT_REGISTERED, network=network)

        logger.info(
            "ERC-8004 identity VERIFIED: agent_id=%d, owner=%s, name=%s, network=%s",
            identity.agent_id,
            truncate_wallet(identity.owner),
            identity.name,
            identity.network,
        )
        return {
            "registered": True,
            "agent_id": identity.agent_id,
            "metadata_uri": identity.agent_uri,
            "owner": identity.owner,
            "name": identity.name,
            "network": identity.network,
        }

    except Exception as exc:
        logger.error(
            "ERC-8004 identity lookup failed (non-blocking): agent_id=%d, "
            "network=%s, error=%s",
            agent_id,
            network,
            exc,
        )
        # Return not-registered on error so that task creation is not blocked.
        return dict(_NOT_REGISTERED, network=network)


# =============================================================================
# Worker Identity -- On-Chain Check & Registration
# =============================================================================

# Contract addresses (CREATE2-deployed -- same address on every mainnet)
IDENTITY_REGISTRY_MAINNET = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
IDENTITY_REGISTRY_TESTNET = "0x8004A818BFB912233c491871b3d84c89A494BD9e"

# Network configuration
BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")

# Default worker metadata URI template
DEFAULT_WORKER_URI_TEMPLATE = "https://execution.market/workers/{wallet}"

_USE_TESTNET = os.environ.get("ERC8004_USE_TESTNET", "").lower() in (
    "1",
    "true",
    "yes",
)


def _get_registry_address() -> str:
    """Get the correct identity registry address for the current environment."""
    env_override = os.environ.get("ERC8004_IDENTITY_REGISTRY")
    if env_override:
        return env_override
    return IDENTITY_REGISTRY_TESTNET if _USE_TESTNET else IDENTITY_REGISTRY_MAINNET


def _get_chain_id() -> int:
    if _USE_TESTNET:
        return 11155111  # Sepolia
    return BASE_CHAIN_ID


def _get_rpc_url() -> str:
    if _USE_TESTNET:
        return os.environ.get("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
    return BASE_RPC_URL


# ---------------------------------------------------------------------------
# ABI encoding helpers (zero extra dependencies)
# ---------------------------------------------------------------------------


def _encode_address(addr: str) -> str:
    """ABI-encode an address as a left-padded 32-byte hex word (no 0x prefix)."""
    return addr.lower().replace("0x", "").zfill(64)


def _encode_string(s: str) -> str:
    """ABI-encode a dynamic string: length word + data padded to 32-byte boundary."""
    encoded_bytes = s.encode("utf-8")
    length = len(encoded_bytes)
    padded_len = ((length + 31) // 32) * 32
    padded = encoded_bytes.ljust(padded_len, b"\x00")
    return hex(length)[2:].zfill(64) + padded.hex()


# Pre-computed 4-byte selectors (keccak256 of the canonical signature)
SELECTOR_BALANCE_OF = "0x70a08231"  # balanceOf(address)
SELECTOR_REGISTER = "0xf2c298be"  # register(string)
SELECTOR_TOKEN_OF_OWNER = "0x2f745c59"  # tokenOfOwnerByIndex(address,uint256)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class WorkerIdentityStatus(str, Enum):
    """Worker on-chain identity status."""

    REGISTERED = "registered"
    NOT_REGISTERED = "not_registered"
    ERROR = "error"


@dataclass
class WorkerIdentityResult:
    """Result of checking a worker's on-chain identity."""

    status: WorkerIdentityStatus
    agent_id: Optional[int] = None
    wallet_address: Optional[str] = None
    network: str = "base"
    chain_id: int = BASE_CHAIN_ID
    registry_address: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for k, v in asdict(self).items():
            d[k] = v.value if isinstance(v, Enum) else v
        return d


@dataclass
class RegistrationTxData:
    """Unsigned transaction data for ERC-8004 registration."""

    to: str
    data: str
    chain_id: int
    value: str  # "0x0"
    agent_uri: str
    estimated_gas: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Lightweight JSON-RPC helpers (no web3 needed)
# ---------------------------------------------------------------------------


async def _eth_call(to: str, data: str, rpc_url: Optional[str] = None) -> str:
    """Execute an ``eth_call`` and return the hex-encoded result."""
    url = rpc_url or _get_rpc_url()
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
        body = resp.json()
    if "error" in body:
        raise RuntimeError(f"RPC error: {body['error']}")
    return body.get("result", "0x")


async def _eth_estimate_gas(
    from_addr: str,
    to: str,
    data: str,
    rpc_url: Optional[str] = None,
) -> int:
    """Estimate gas for a transaction via JSON-RPC."""
    url = rpc_url or _get_rpc_url()
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_estimateGas",
        "params": [{"from": from_addr, "to": to, "data": data}],
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
        body = resp.json()
    if "error" in body:
        raise RuntimeError(
            f"Gas estimation failed: {body['error'].get('message', body['error'])}"
        )
    return int(body["result"], 16)


# ---------------------------------------------------------------------------
# Worker Identity Check
# ---------------------------------------------------------------------------


async def check_worker_identity(
    wallet_address: str,
    network: str = "base",
) -> WorkerIdentityResult:
    """
    Check whether a wallet holds an ERC-8004 identity token on-chain.

    Uses ``balanceOf(address)`` via direct JSON-RPC to the specified network.
    If balance > 0, attempts ``tokenOfOwnerByIndex(address, 0)`` to retrieve
    the token ID.

    Parameters
    ----------
    wallet_address:
        Worker's Ethereum address (``0x``-prefixed).
    network:
        EVM network name (e.g. ``"base"``, ``"polygon"``, ``"skale"``).
        Defaults to ``"base"``.

    Returns
    -------
    WorkerIdentityResult
    """
    from .facilitator_client import ERC8004_CONTRACTS
    from ..x402.sdk_client import get_rpc_url

    # Resolve per-chain config from ERC8004_CONTRACTS (auto-derived from NETWORK_CONFIG)
    net_cfg = ERC8004_CONTRACTS.get(network, {})
    registry = net_cfg.get("identity_registry", _get_registry_address())
    chain_id = net_cfg.get("chain_id", _get_chain_id())
    rpc_url = get_rpc_url(network)

    try:
        # 1. balanceOf(wallet)
        calldata = SELECTOR_BALANCE_OF + _encode_address(wallet_address)
        raw = await _eth_call(registry, calldata, rpc_url=rpc_url)
        balance = int(raw, 16) if raw and raw != "0x" else 0

        if balance == 0:
            return WorkerIdentityResult(
                status=WorkerIdentityStatus.NOT_REGISTERED,
                wallet_address=wallet_address.lower(),
                network=network,
                chain_id=chain_id,
                registry_address=registry,
            )

        # 2. Retrieve token ID via tokenOfOwnerByIndex(address, 0)
        #    NOTE: The ERC-8004 contract may NOT implement ERC-721 Enumerable,
        #    so this call can revert.  Fall back to DB lookup if it fails.
        agent_id: Optional[int] = None
        try:
            tok_data = (
                SELECTOR_TOKEN_OF_OWNER + _encode_address(wallet_address) + "0" * 64
            )
            tok_raw = await _eth_call(registry, tok_data, rpc_url=rpc_url)
            if tok_raw and tok_raw != "0x":
                agent_id = int(tok_raw, 16)
        except Exception as e:
            logger.debug("tokenOfOwnerByIndex unavailable (non-enumerable): %s", e)

        # 2b. Fallback: SDK get_identity_by_owner (facilitator v1.41.1+).
        #     Works on all chains including SKALE (no Enumerable needed).
        if agent_id is None:
            try:
                from .facilitator_client import _sdk_client, _to_facilitator_network

                fac_net = _to_facilitator_network(network)
                owner_result = await _sdk_client.get_identity_by_owner(
                    fac_net, wallet_address
                )
                if owner_result and owner_result.agent_id is not None:
                    agent_id = int(owner_result.agent_id)
                    logger.info(
                        "Resolved agent_id=%d via SDK owner lookup for %s on %s",
                        agent_id,
                        truncate_wallet(wallet_address),
                        network,
                    )
            except Exception as fac_err:
                logger.debug("SDK owner lookup failed: %s", fac_err)

        return WorkerIdentityResult(
            status=WorkerIdentityStatus.REGISTERED,
            agent_id=agent_id,
            wallet_address=wallet_address.lower(),
            network=network,
            chain_id=chain_id,
            registry_address=registry,
        )

    except Exception as e:
        logger.error(
            "Worker identity check failed for %s: %s",
            truncate_wallet(wallet_address),
            e,
        )
        return WorkerIdentityResult(
            status=WorkerIdentityStatus.ERROR,
            wallet_address=wallet_address.lower(),
            network=network,
            chain_id=chain_id,
            registry_address=registry,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Gasless Worker Registration (via Facilitator — all 14 networks)
# ---------------------------------------------------------------------------


async def register_worker_gasless(
    wallet_address: str,
    agent_uri: Optional[str] = None,
    network: str = "base",
    metadata: Optional[list] = None,
) -> WorkerIdentityResult:
    """
    Register a worker on ERC-8004 via the Facilitator (gasless).

    The facilitator pays gas on any of 14 supported networks. The minted
    NFT is transferred to the worker's wallet address.

    Parameters
    ----------
    wallet_address:
        Worker's Ethereum address — receives the ERC-8004 NFT.
    agent_uri:
        Metadata URI. Defaults to ``https://execution.market/workers/{wallet}``.
    network:
        ERC-8004 network (default ``"base"``). Any of 14 supported.
    metadata:
        Optional key-value pairs [{"key": "name", "value": "Worker Name"}].

    Returns
    -------
    WorkerIdentityResult with agent_id if successful.
    """
    if not agent_uri:
        agent_uri = DEFAULT_WORKER_URI_TEMPLATE.format(
            wallet=wallet_address.lower(),
        )

    try:
        from .facilitator_client import get_facilitator_client

        client = get_facilitator_client()
        result = await client.register_agent(
            network=network,
            agent_uri=agent_uri,
            metadata=metadata,
            recipient=wallet_address,  # transfer NFT to worker
        )

        if not result.get("success"):
            return WorkerIdentityResult(
                status=WorkerIdentityStatus.ERROR,
                wallet_address=wallet_address.lower(),
                network=network,
                error=result.get("error", "Registration failed"),
            )

        agent_id = result.get("agentId")
        logger.info(
            "Worker registered gaslessly: wallet=%s, agent_id=%s, network=%s, tx=%s",
            truncate_wallet(wallet_address),
            agent_id,
            network,
            result.get("transaction"),
        )

        from .facilitator_client import ERC8004_CONTRACTS

        chain_id = ERC8004_CONTRACTS.get(network, {}).get("chain_id", 0)

        return WorkerIdentityResult(
            status=WorkerIdentityStatus.REGISTERED,
            agent_id=agent_id,
            wallet_address=wallet_address.lower(),
            network=network,
            chain_id=chain_id,
        )

    except Exception as e:
        logger.error("Gasless worker registration failed: %s", e)
        return WorkerIdentityResult(
            status=WorkerIdentityStatus.ERROR,
            wallet_address=wallet_address.lower(),
            network=network,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Registration Transaction Builder (Legacy — worker pays gas)
# ---------------------------------------------------------------------------


def _build_register_calldata(agent_uri: str) -> str:
    """
    Build ABI-encoded calldata for ``register(string agentURI)``.

    Encoding layout::

        0x3ffbd47f                         # 4-byte selector
        0000...0020                        # offset to string data (32)
        0000...00XX                        # string length
        <utf-8 bytes padded to 32>         # string data
    """
    offset = "0" * 62 + "20"  # 0x20 = 32
    string_data = _encode_string(agent_uri)
    return SELECTOR_REGISTER + offset + string_data


async def build_worker_registration_tx(
    wallet_address: str,
    agent_uri: Optional[str] = None,
) -> RegistrationTxData:
    """
    Build an unsigned transaction for ERC-8004 identity registration.

    The worker signs and submits this via their own wallet (Dynamic.xyz
    frontend).  Gas cost is approximately $0.01 on Base Mainnet.

    Parameters
    ----------
    wallet_address:
        Worker's wallet address -- will be ``msg.sender`` for the registration.
    agent_uri:
        Metadata URI.  Defaults to ``https://execution.market/workers/{wallet}``.

    Returns
    -------
    RegistrationTxData with fields ``to``, ``data``, ``chain_id``, ``value``,
    ``agent_uri``, and ``estimated_gas``.
    """
    registry = _get_registry_address()
    chain_id = _get_chain_id()

    if not agent_uri:
        agent_uri = DEFAULT_WORKER_URI_TEMPLATE.format(
            wallet=wallet_address.lower(),
        )

    calldata = _build_register_calldata(agent_uri)

    # Gas estimation (the wallet will re-estimate, this is informational)
    estimated_gas: Optional[int] = None
    try:
        estimated_gas = await _eth_estimate_gas(
            from_addr=wallet_address,
            to=registry,
            data=calldata,
        )
        estimated_gas = int(estimated_gas * 1.2)  # +20 % buffer
    except Exception as e:
        logger.warning("Gas estimation failed for registration: %s", e)

    return RegistrationTxData(
        to=registry,
        data=calldata,
        chain_id=chain_id,
        value="0x0",
        agent_uri=agent_uri,
        estimated_gas=estimated_gas,
    )


# ---------------------------------------------------------------------------
# Registration Confirmation
# ---------------------------------------------------------------------------


async def confirm_worker_registration(
    wallet_address: str,
    tx_hash: Optional[str] = None,
    network: str = "base",
) -> WorkerIdentityResult:
    """
    Re-check on-chain state after a registration tx to confirm success.

    Always performs a fresh on-chain lookup on the specified network.
    """
    if tx_hash:
        logger.info(
            "Confirming worker registration: wallet=%s tx=%s network=%s",
            truncate_wallet(wallet_address),
            tx_hash,
            network,
        )

    return await check_worker_identity(wallet_address, network=network)


# ---------------------------------------------------------------------------
# Supabase helper -- persist on-chain identity in executor row
# ---------------------------------------------------------------------------


async def update_executor_identity(
    executor_id: str,
    agent_id: Optional[int],
) -> bool:
    """
    Store the worker's on-chain ERC-8004 agent ID in Supabase.

    Updates ``executors.erc8004_agent_id`` and (if columns exist)
    ``reputation_contract`` / ``reputation_token_id``.
    """
    try:
        import supabase_client as db

        client = db.get_client()
        update_data: Dict[str, Any] = {"erc8004_agent_id": agent_id}

        # Best-effort: also set legacy columns
        try:
            update_data["reputation_contract"] = _get_registry_address()
            update_data["reputation_token_id"] = agent_id
        except Exception:
            pass

        client.table("executors").update(update_data).eq(
            "id",
            executor_id,
        ).execute()

        logger.info(
            "Updated executor %s with erc8004_agent_id=%s",
            executor_id,
            agent_id,
        )
        return True

    except Exception as e:
        logger.error("Failed to update executor %s identity: %s", executor_id, e)
        return False
