"""
x402 Protocol Client for Chamba (NOW-024)

Handles escrow deposits, releases, and refunds via x402-rs facilitator.
Supports both direct contract calls and facilitator-mediated operations.

Contracts (Base Mainnet):
- MerchantRouter: 0xa48E8AdcA504D2f48e5AF6be49039354e922913F
- DepositRelayFactory: 0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814
- USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
"""

import os
import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum
import json
import uuid

import httpx
from web3 import Web3
from eth_account import Account

# POA middleware for chains like Base, Polygon, etc.
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware
    except ImportError:
        geth_poa_middleware = None  # Not needed in newer web3 versions

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Contract addresses (Base Mainnet)
MERCHANT_ROUTER = "0xa48E8AdcA504D2f48e5AF6be49039354e922913F"
DEPOSIT_RELAY_FACTORY = "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814"

# Token addresses by network
TOKEN_ADDRESSES = {
    "base": {
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "eurc": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
        "dai": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        "usdt": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    },
    "polygon": {
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "eurc": "0x18ec0A6E18E5bc3784fDd3a3634b31245ab704F6",
        "dai": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
        "usdt": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    },
    "optimism": {
        "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "dai": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "usdt": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
    },
    "arbitrum": {
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "dai": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "usdt": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    },
}

# Token decimals
TOKEN_DECIMALS = {
    "usdc": 6,
    "eurc": 6,
    "dai": 18,
    "usdt": 6,
}

# Chain IDs
CHAIN_IDS = {
    "base": 8453,
    "polygon": 137,
    "optimism": 10,
    "arbitrum": 42161,
    "ethereum": 1,
}

# Default facilitator URL
DEFAULT_FACILITATOR_URL = "https://x402.ultravioleta.xyz"


# =============================================================================
# Enums and Data Classes
# =============================================================================

class PaymentToken(str, Enum):
    """Supported payment tokens."""
    USDC = "usdc"
    EURC = "eurc"
    DAI = "dai"
    USDT = "usdt"


class EscrowStatus(str, Enum):
    """Escrow lifecycle states."""
    PENDING = "pending"
    ACTIVE = "active"
    RELEASED = "released"
    PARTIAL = "partial"
    REFUNDED = "refunded"
    EXPIRED = "expired"
    DISPUTED = "disputed"


class X402Error(Exception):
    """Base exception for x402 operations."""

    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code or "X402_ERROR"
        self.details = details or {}


class EscrowCreationError(X402Error):
    """Failed to create escrow."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "ESCROW_CREATION_FAILED", details)


class EscrowReleaseError(X402Error):
    """Failed to release escrow."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "ESCROW_RELEASE_FAILED", details)


class EscrowRefundError(X402Error):
    """Failed to refund escrow."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "ESCROW_REFUND_FAILED", details)


class FacilitatorError(X402Error):
    """Facilitator returned an error."""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[str] = None):
        super().__init__(message, "FACILITATOR_ERROR", {
            "status_code": status_code,
            "response": response,
        })
        self.status_code = status_code
        self.response = response


class InsufficientFundsError(X402Error):
    """Insufficient funds for operation."""
    def __init__(self, required: Decimal, available: Decimal, token: PaymentToken):
        super().__init__(
            f"Insufficient {token.value.upper()}: need {required}, have {available}",
            "INSUFFICIENT_FUNDS",
            {"required": str(required), "available": str(available), "token": token.value},
        )


@dataclass
class PaymentResult:
    """Result of a payment operation."""
    success: bool
    tx_hash: Optional[str]
    amount: Decimal
    token: PaymentToken
    recipient: str
    timestamp: datetime
    network: str = "base"
    error: Optional[str] = None
    gas_used: Optional[int] = None


@dataclass
class EscrowDeposit:
    """Represents an escrow deposit."""
    escrow_id: str
    task_id: str
    amount: Decimal
    token: PaymentToken
    depositor: str
    beneficiary: str
    tx_hash: str
    created_at: datetime
    timeout_at: datetime
    status: EscrowStatus = EscrowStatus.ACTIVE
    network: str = "base"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EscrowInfo:
    """Current state of an escrow."""
    escrow_id: str
    depositor: str
    beneficiary: str
    amount: Decimal
    token: PaymentToken
    timeout_timestamp: int
    status: EscrowStatus
    released_amount: Decimal = Decimal("0")
    release_history: List[Dict] = field(default_factory=list)


# =============================================================================
# Contract ABIs
# =============================================================================

MERCHANT_ROUTER_ABI = [
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "recipient", "type": "address"},
            {"name": "memo", "type": "string"}
        ],
        "name": "pay",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "merchant", "type": "address"}],
        "name": "getMerchantInfo",
        "outputs": [
            {"name": "registered", "type": "bool"},
            {"name": "name", "type": "string"},
            {"name": "webhookUrl", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "webhookUrl", "type": "string"}
        ],
        "name": "registerMerchant",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

DEPOSIT_RELAY_ABI = [
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "beneficiary", "type": "address"},
            {"name": "timeout", "type": "uint256"},
            {"name": "taskId", "type": "bytes32"}
        ],
        "name": "createEscrow",
        "outputs": [{"name": "escrowId", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "escrowId", "type": "bytes32"},
            {"name": "recipient", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "releaseEscrow",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "escrowId", "type": "bytes32"}],
        "name": "refundEscrow",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "escrowId", "type": "bytes32"}],
        "name": "getEscrow",
        "outputs": [
            {"name": "depositor", "type": "address"},
            {"name": "beneficiary", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "timeout", "type": "uint256"},
            {"name": "released", "type": "bool"},
            {"name": "refunded", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]


# =============================================================================
# X402 Client
# =============================================================================

class X402Client:
    """
    Client for x402 protocol operations.

    Supports two modes:
    1. Direct on-chain operations via Web3
    2. Facilitator-mediated operations via HTTP

    Features:
    - Multi-token support (USDC, EURC, DAI, USDT)
    - Escrow creation, release, and refund
    - Direct payments
    - Balance checking
    """

    def __init__(
        self,
        facilitator_url: Optional[str] = None,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        network: str = "base",
        default_token: PaymentToken = PaymentToken.USDC,
        timeout: float = 30.0,
    ):
        """
        Initialize x402 client.

        Args:
            facilitator_url: x402-rs facilitator URL (default: env X402_FACILITATOR_URL)
            rpc_url: RPC URL for direct operations (default: env X402_RPC_URL)
            private_key: Private key for signing (default: env X402_PRIVATE_KEY)
            network: Default network (base, polygon, etc.)
            default_token: Default payment token
            timeout: HTTP timeout in seconds
        """
        self.facilitator_url = facilitator_url or os.environ.get(
            "X402_FACILITATOR_URL", DEFAULT_FACILITATOR_URL
        )
        self.rpc_url = rpc_url or os.environ.get("X402_RPC_URL", self._get_default_rpc(network))
        self._private_key = private_key or os.environ.get("X402_PRIVATE_KEY")
        self.network = network
        self.default_token = default_token
        self.timeout = timeout

        # Initialize Web3 for direct operations
        self.w3: Optional[Web3] = None
        self.account: Optional[Any] = None
        self._init_web3()

        # HTTP client for facilitator
        self._http_client: Optional[httpx.AsyncClient] = None

        # Contract instances (lazy loaded)
        self._contracts: Dict[str, Any] = {}

        logger.info(f"X402Client initialized: network={network}, facilitator={self.facilitator_url}")

    def _get_default_rpc(self, network: str) -> str:
        """Get default RPC URL for network."""
        defaults = {
            "base": "https://mainnet.base.org",
            "polygon": "https://polygon-rpc.com",
            "optimism": "https://mainnet.optimism.io",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
        }
        return defaults.get(network, "https://mainnet.base.org")

    def _init_web3(self) -> None:
        """Initialize Web3 connection."""
        if not self.rpc_url:
            return

        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if geth_poa_middleware:
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

            if self._private_key:
                self.account = Account.from_key(self._private_key)
                logger.info(f"Web3 initialized with account: {self.account.address[:10]}...")
            else:
                logger.info("Web3 initialized in read-only mode (no private key)")
        except Exception as e:
            logger.warning(f"Failed to initialize Web3: {e}")
            self.w3 = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> "X402Client":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # =========================================================================
    # Token Utilities
    # =========================================================================

    def get_token_address(self, token: PaymentToken, network: Optional[str] = None) -> str:
        """Get token contract address for network."""
        net = network or self.network
        tokens = TOKEN_ADDRESSES.get(net, TOKEN_ADDRESSES["base"])
        address = tokens.get(token.value)
        if not address:
            raise X402Error(f"Token {token.value} not supported on {net}")
        return address

    def get_token_decimals(self, token: PaymentToken) -> int:
        """Get decimals for token."""
        return TOKEN_DECIMALS.get(token.value, 6)

    def to_token_amount(self, amount: Decimal, token: PaymentToken) -> int:
        """Convert decimal amount to token wei."""
        decimals = self.get_token_decimals(token)
        return int(amount * Decimal(10 ** decimals))

    def from_token_amount(self, amount: int, token: PaymentToken) -> Decimal:
        """Convert token wei to decimal amount."""
        decimals = self.get_token_decimals(token)
        return Decimal(amount) / Decimal(10 ** decimals)

    def _get_token_contract(self, token: PaymentToken) -> Any:
        """Get or create token contract instance."""
        if not self.w3:
            raise X402Error("Web3 not initialized")

        key = f"token_{token.value}"
        if key not in self._contracts:
            address = self.get_token_address(token)
            self._contracts[key] = self.w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=ERC20_ABI,
            )
        return self._contracts[key]

    # =========================================================================
    # Balance and Allowance
    # =========================================================================

    async def check_balance(
        self,
        address: Optional[str] = None,
        tokens: Optional[List[PaymentToken]] = None,
    ) -> Dict[str, Any]:
        """
        Check balances for an address.

        Args:
            address: Address to check (default: configured account)
            tokens: Tokens to check (default: all supported)

        Returns:
            Dict with balances for each token plus native currency
        """
        if not self.w3:
            raise X402Error("Web3 not initialized")

        addr = address or (self.account.address if self.account else None)
        if not addr:
            raise X402Error("No address provided and no account configured")

        addr = Web3.to_checksum_address(addr)
        tokens = tokens or list(PaymentToken)

        result = {
            "address": addr,
            "network": self.network,
            "native": float(self.w3.from_wei(self.w3.eth.get_balance(addr), "ether")),
        }

        for token in tokens:
            try:
                contract = self._get_token_contract(token)
                balance_wei = contract.functions.balanceOf(addr).call()
                result[token.value] = float(self.from_token_amount(balance_wei, token))
            except Exception as e:
                logger.warning(f"Failed to get {token.value} balance: {e}")
                result[token.value] = 0.0

        return result

    async def ensure_approval(
        self,
        spender: str,
        amount: Decimal,
        token: PaymentToken = PaymentToken.USDC,
    ) -> Optional[str]:
        """
        Ensure token is approved for spending.

        Args:
            spender: Contract address to approve
            amount: Amount to approve
            token: Token to approve

        Returns:
            Transaction hash if approval was needed, None if already approved
        """
        if not self.w3 or not self.account:
            raise X402Error("Web3 with private key required for approvals")

        spender = Web3.to_checksum_address(spender)
        amount_wei = self.to_token_amount(amount, token)
        contract = self._get_token_contract(token)

        # Check current allowance
        current = contract.functions.allowance(
            self.account.address, spender
        ).call()

        if current >= amount_wei:
            logger.debug(f"Already approved {amount} {token.value} for {spender}")
            return None

        # Approve max for convenience
        max_uint = 2**256 - 1
        func = contract.functions.approve(spender, max_uint)
        tx_hash = self._build_and_send_tx(func)

        # Wait for confirmation
        self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        logger.info(f"Approved {token.value} for {spender}: {tx_hash}")

        return tx_hash

    def _build_and_send_tx(self, func: Any, value: int = 0) -> str:
        """Build, sign, and send a transaction."""
        if not self.w3 or not self.account:
            raise X402Error("Web3 with private key required for transactions")

        chain_id = CHAIN_IDS.get(self.network, 8453)

        tx = func.build_transaction({
            "from": self.account.address,
            "value": value,
            "gas": 200000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "chainId": chain_id,
        })

        # Estimate gas
        tx["gas"] = self.w3.eth.estimate_gas(tx)

        # Sign and send
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

        return tx_hash.hex()

    # =========================================================================
    # Facilitator Health Check
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """Check facilitator health and supported features."""
        client = await self._get_http_client()

        try:
            # Check health endpoint
            health_resp = await client.get(f"{self.facilitator_url}/health")
            health = health_resp.json() if health_resp.status_code == 200 else {"status": "unhealthy"}

            # Check supported networks
            supported_resp = await client.get(f"{self.facilitator_url}/supported")
            supported = supported_resp.json() if supported_resp.status_code == 200 else {}

            # Check version
            version_resp = await client.get(f"{self.facilitator_url}/version")
            version = version_resp.json() if version_resp.status_code == 200 else {}

            return {
                "healthy": health.get("status") == "healthy",
                "version": version.get("version"),
                "supported": supported,
                "facilitator_url": self.facilitator_url,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "facilitator_url": self.facilitator_url,
            }

    # =========================================================================
    # Escrow Operations (via Facilitator)
    # =========================================================================

    async def create_escrow(
        self,
        task_id: str,
        amount: Decimal,
        token: Optional[PaymentToken] = None,
        beneficiary: Optional[str] = None,
        timeout_hours: int = 48,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EscrowDeposit:
        """
        Create an escrow deposit for a task.

        This uses the x402r extension for refundable payments.

        Args:
            task_id: Unique task identifier
            amount: Amount to escrow
            token: Token to use (default: client default)
            beneficiary: Initial beneficiary address
            timeout_hours: Hours until escrow can be refunded
            metadata: Additional metadata to store

        Returns:
            EscrowDeposit with escrow details

        Raises:
            EscrowCreationError: If creation fails
        """
        token = token or self.default_token

        if not self.account:
            raise EscrowCreationError("Private key required to create escrow")

        # Generate escrow ID
        escrow_id = f"escrow_{task_id}_{uuid.uuid4().hex[:8]}"
        timeout_timestamp = int(datetime.now(timezone.utc).timestamp()) + (timeout_hours * 3600)

        # Check balance first
        balance = await self.check_balance(tokens=[token])
        if Decimal(str(balance[token.value])) < amount:
            raise InsufficientFundsError(
                required=amount,
                available=Decimal(str(balance[token.value])),
                token=token,
            )

        logger.info(f"Creating escrow: task={task_id}, amount={amount} {token.value}")

        # For direct on-chain escrow
        if self.w3 and self.account:
            try:
                result = await self._create_escrow_onchain(
                    task_id=task_id,
                    amount=amount,
                    token=token,
                    beneficiary=beneficiary or self.account.address,
                    timeout_timestamp=timeout_timestamp,
                )

                return EscrowDeposit(
                    escrow_id=result["escrow_id"],
                    task_id=task_id,
                    amount=amount,
                    token=token,
                    depositor=self.account.address,
                    beneficiary=beneficiary or self.account.address,
                    tx_hash=result["tx_hash"],
                    created_at=datetime.now(timezone.utc),
                    timeout_at=datetime.fromtimestamp(timeout_timestamp, tz=timezone.utc),
                    status=EscrowStatus.ACTIVE,
                    network=self.network,
                    metadata=metadata or {},
                )
            except Exception as e:
                raise EscrowCreationError(f"On-chain escrow creation failed: {e}")

        raise EscrowCreationError("No valid method to create escrow (need Web3 or facilitator)")

    async def _create_escrow_onchain(
        self,
        task_id: str,
        amount: Decimal,
        token: PaymentToken,
        beneficiary: str,
        timeout_timestamp: int,
    ) -> Dict[str, Any]:
        """Create escrow via direct on-chain call."""
        if not self.w3 or not self.account:
            raise X402Error("Web3 with private key required")

        # Get contracts
        token_address = self.get_token_address(token)
        amount_wei = self.to_token_amount(amount, token)

        # Ensure approval
        await self.ensure_approval(DEPOSIT_RELAY_FACTORY, amount, token)

        # Get deposit relay contract
        deposit_relay = self.w3.eth.contract(
            address=Web3.to_checksum_address(DEPOSIT_RELAY_FACTORY),
            abi=DEPOSIT_RELAY_ABI,
        )

        # Convert task_id to bytes32
        task_id_bytes = Web3.keccak(text=task_id)

        # Create escrow
        func = deposit_relay.functions.createEscrow(
            Web3.to_checksum_address(token_address),
            amount_wei,
            Web3.to_checksum_address(beneficiary),
            timeout_timestamp,
            task_id_bytes,
        )
        tx_hash = self._build_and_send_tx(func)

        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] != 1:
            raise EscrowCreationError("Transaction reverted", {"tx_hash": tx_hash})

        return {
            "escrow_id": task_id_bytes.hex(),
            "tx_hash": tx_hash,
            "gas_used": receipt["gasUsed"],
        }

    async def release_escrow(
        self,
        escrow_id: str,
        recipient: str,
        amount: Optional[Decimal] = None,
        token: Optional[PaymentToken] = None,
    ) -> PaymentResult:
        """
        Release escrow funds to a recipient.

        Args:
            escrow_id: Escrow identifier
            recipient: Address to receive funds
            amount: Amount to release (None = full amount)
            token: Token type (for amount conversion)

        Returns:
            PaymentResult with transaction details

        Raises:
            EscrowReleaseError: If release fails
        """
        token = token or self.default_token

        logger.info(f"Releasing escrow: id={escrow_id[:16]}..., recipient={recipient[:10]}...")

        if self.w3 and self.account:
            try:
                # Get escrow info first
                info = await self.get_escrow_info(escrow_id)

                if info.status in (EscrowStatus.RELEASED, EscrowStatus.REFUNDED):
                    raise EscrowReleaseError(f"Escrow already {info.status.value}")

                release_amount = amount or info.amount

                # Get deposit relay contract
                deposit_relay = self.w3.eth.contract(
                    address=Web3.to_checksum_address(DEPOSIT_RELAY_FACTORY),
                    abi=DEPOSIT_RELAY_ABI,
                )

                escrow_id_bytes = bytes.fromhex(escrow_id.replace("0x", ""))
                amount_wei = self.to_token_amount(release_amount, token)

                func = deposit_relay.functions.releaseEscrow(
                    escrow_id_bytes,
                    Web3.to_checksum_address(recipient),
                    amount_wei,
                )
                tx_hash = self._build_and_send_tx(func)

                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

                return PaymentResult(
                    success=receipt["status"] == 1,
                    tx_hash=tx_hash,
                    amount=release_amount,
                    token=token,
                    recipient=recipient,
                    timestamp=datetime.now(timezone.utc),
                    network=self.network,
                    gas_used=receipt["gasUsed"],
                )
            except EscrowReleaseError:
                raise
            except Exception as e:
                raise EscrowReleaseError(f"Release failed: {e}")

        raise EscrowReleaseError("No valid method to release escrow")

    async def refund_escrow(
        self,
        escrow_id: str,
        reason: str = "cancelled",
    ) -> PaymentResult:
        """
        Refund escrow to the original depositor.

        Args:
            escrow_id: Escrow identifier
            reason: Reason for refund

        Returns:
            PaymentResult with transaction details

        Raises:
            EscrowRefundError: If refund fails
        """
        logger.info(f"Refunding escrow: id={escrow_id[:16]}..., reason={reason}")

        if self.w3 and self.account:
            try:
                # Get escrow info first
                info = await self.get_escrow_info(escrow_id)

                if info.status == EscrowStatus.RELEASED:
                    raise EscrowRefundError("Escrow already released")
                if info.status == EscrowStatus.REFUNDED:
                    raise EscrowRefundError("Escrow already refunded")

                # Get deposit relay contract
                deposit_relay = self.w3.eth.contract(
                    address=Web3.to_checksum_address(DEPOSIT_RELAY_FACTORY),
                    abi=DEPOSIT_RELAY_ABI,
                )

                escrow_id_bytes = bytes.fromhex(escrow_id.replace("0x", ""))

                func = deposit_relay.functions.refundEscrow(escrow_id_bytes)
                tx_hash = self._build_and_send_tx(func)

                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

                return PaymentResult(
                    success=receipt["status"] == 1,
                    tx_hash=tx_hash,
                    amount=info.amount,
                    token=info.token,
                    recipient=info.depositor,
                    timestamp=datetime.now(timezone.utc),
                    network=self.network,
                    gas_used=receipt["gasUsed"],
                )
            except EscrowRefundError:
                raise
            except Exception as e:
                raise EscrowRefundError(f"Refund failed: {e}")

        raise EscrowRefundError("No valid method to refund escrow")

    async def get_escrow_info(self, escrow_id: str) -> EscrowInfo:
        """
        Get current state of an escrow.

        Args:
            escrow_id: Escrow identifier

        Returns:
            EscrowInfo with current state
        """
        if not self.w3:
            raise X402Error("Web3 required to get escrow info")

        deposit_relay = self.w3.eth.contract(
            address=Web3.to_checksum_address(DEPOSIT_RELAY_FACTORY),
            abi=DEPOSIT_RELAY_ABI,
        )

        escrow_id_bytes = bytes.fromhex(escrow_id.replace("0x", ""))
        escrow = deposit_relay.functions.getEscrow(escrow_id_bytes).call()
        depositor, beneficiary, amount, timeout, released, refunded = escrow

        # Determine status
        if released:
            status = EscrowStatus.RELEASED
        elif refunded:
            status = EscrowStatus.REFUNDED
        elif timeout < int(datetime.now(timezone.utc).timestamp()):
            status = EscrowStatus.EXPIRED
        else:
            status = EscrowStatus.ACTIVE

        return EscrowInfo(
            escrow_id=escrow_id,
            depositor=depositor,
            beneficiary=beneficiary,
            amount=self.from_token_amount(amount, self.default_token),
            token=self.default_token,
            timeout_timestamp=timeout,
            status=status,
        )

    # =========================================================================
    # Direct Payments
    # =========================================================================

    async def send_payment(
        self,
        to_address: str,
        amount: Decimal,
        token: Optional[PaymentToken] = None,
        memo: Optional[str] = None,
    ) -> PaymentResult:
        """
        Send a direct payment via MerchantRouter.

        Args:
            to_address: Recipient address
            amount: Amount to send
            token: Token to use
            memo: Optional payment memo

        Returns:
            PaymentResult with transaction details
        """
        token = token or self.default_token

        if not self.w3 or not self.account:
            raise X402Error("Web3 with private key required for payments")

        try:
            to_address = Web3.to_checksum_address(to_address)
            token_address = self.get_token_address(token)
            amount_wei = self.to_token_amount(amount, token)

            # Ensure approval
            await self.ensure_approval(MERCHANT_ROUTER, amount, token)

            # Get merchant router
            merchant_router = self.w3.eth.contract(
                address=Web3.to_checksum_address(MERCHANT_ROUTER),
                abi=MERCHANT_ROUTER_ABI,
            )

            # Send payment
            func = merchant_router.functions.pay(
                Web3.to_checksum_address(token_address),
                amount_wei,
                to_address,
                memo or "",
            )
            tx_hash = self._build_and_send_tx(func)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            return PaymentResult(
                success=receipt["status"] == 1,
                tx_hash=tx_hash,
                amount=amount,
                token=token,
                recipient=to_address,
                timestamp=datetime.now(timezone.utc),
                network=self.network,
                gas_used=receipt["gasUsed"],
            )
        except Exception as e:
            return PaymentResult(
                success=False,
                tx_hash=None,
                amount=amount,
                token=token,
                recipient=to_address,
                timestamp=datetime.now(timezone.utc),
                network=self.network,
                error=str(e),
            )

    # =========================================================================
    # Facilitator Payment Processing
    # =========================================================================

    async def verify_payment(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Verify a payment with the facilitator.

        Args:
            payment_payload: x402 payment payload
            requirements: Payment requirements

        Returns:
            Verification response from facilitator
        """
        client = await self._get_http_client()

        verify_request = {
            "x402Version": 1,
            "paymentPayload": payment_payload,
            "paymentRequirements": requirements,
        }

        try:
            response = await client.post(
                f"{self.facilitator_url}/verify",
                json=verify_request,
            )

            if response.status_code != 200:
                raise FacilitatorError(
                    f"Verify failed with status {response.status_code}",
                    response.status_code,
                    response.text,
                )

            return response.json()
        except httpx.RequestError as e:
            raise FacilitatorError(f"Request failed: {e}")

    async def settle_payment(
        self,
        payment_payload: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Settle a payment via the facilitator.

        Args:
            payment_payload: x402 payment payload
            requirements: Payment requirements

        Returns:
            Settlement response from facilitator
        """
        client = await self._get_http_client()

        settle_request = {
            "x402Version": 1,
            "paymentPayload": payment_payload,
            "paymentRequirements": requirements,
        }

        try:
            response = await client.post(
                f"{self.facilitator_url}/settle",
                json=settle_request,
            )

            if response.status_code != 200:
                raise FacilitatorError(
                    f"Settle failed with status {response.status_code}",
                    response.status_code,
                    response.text,
                )

            return response.json()
        except httpx.RequestError as e:
            raise FacilitatorError(f"Request failed: {e}")


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_chamba_escrow(
    task_id: str,
    bounty_amount: Decimal,
    token: PaymentToken = PaymentToken.USDC,
    timeout_hours: int = 48,
) -> EscrowDeposit:
    """
    Convenience function to create an escrow for a Chamba task.

    Uses environment variables for configuration:
    - X402_PRIVATE_KEY: Signing key
    - X402_RPC_URL: RPC endpoint
    - X402_FACILITATOR_URL: Facilitator URL
    """
    async with X402Client(default_token=token) as client:
        return await client.create_escrow(
            task_id=task_id,
            amount=bounty_amount,
            token=token,
            timeout_hours=timeout_hours,
        )


async def release_task_payment(
    escrow_id: str,
    worker_address: str,
    amount: Optional[Decimal] = None,
    token: PaymentToken = PaymentToken.USDC,
) -> PaymentResult:
    """
    Convenience function to release payment to a worker.
    """
    async with X402Client(default_token=token) as client:
        return await client.release_escrow(
            escrow_id=escrow_id,
            recipient=worker_address,
            amount=amount,
            token=token,
        )


async def refund_task_escrow(
    escrow_id: str,
    reason: str = "task_cancelled",
) -> PaymentResult:
    """
    Convenience function to refund an escrow.
    """
    async with X402Client() as client:
        return await client.refund_escrow(
            escrow_id=escrow_id,
            reason=reason,
        )
