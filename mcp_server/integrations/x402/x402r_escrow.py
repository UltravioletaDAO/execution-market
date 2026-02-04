"""
x402r Escrow Integration for Execution Market

Direct integration with x402r escrow contracts for payment management.
No unnecessary wrappers - uses contracts directly via web3.

Contracts (Base Mainnet):
- Factory: 0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814
- Escrow: 0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC

Flow:
1. Agent pays to Execution Market's proxy address (via x402 with refund extension)
2. Facilitator calls executeDeposit → funds in Escrow
3. Execution Market releases to worker OR refunds to agent

For future: Keep EMEscrow.sol implementation ready for when we want
full control over the escrow logic.
"""

import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)


# =============================================================================
# Contract Addresses
# =============================================================================

CONTRACTS = {
    "base": {
        "factory": "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814",
        "escrow": "0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "chain_id": 8453,
        "rpc": "https://mainnet.base.org",
    },
    "base-sepolia": {
        "factory": "0xf981D813842eE78d18ef8ac825eef8e2C8A8BaC2",
        "escrow": "0xF7F2Bc463d79Bd3E5Cb693944B422c39114De058",
        "usdc": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # USDC on Base Sepolia
        "chain_id": 84532,
        "rpc": "https://sepolia.base.org",
    },
}


# =============================================================================
# Configuration from Environment
# =============================================================================

def get_network() -> str:
    return os.environ.get("X402R_NETWORK", "base-sepolia")


def get_merchant_address() -> str:
    return os.environ.get("X402R_MERCHANT_ADDRESS", "")


def get_proxy_address() -> str:
    return os.environ.get("X402R_PROXY_ADDRESS", "")


def get_private_key() -> Optional[str]:
    return os.environ.get("WALLET_PRIVATE_KEY") or os.environ.get("X402R_PRIVATE_KEY")


# =============================================================================
# Escrow Contract ABI (key functions only)
# =============================================================================

# Based on x402r-contracts AuthCaptureEscrow
ESCROW_ABI = [
    # View deposit info
    {
        "name": "deposits",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "depositId", "type": "bytes32"}],
        "outputs": [
            {"name": "payer", "type": "address"},
            {"name": "merchant", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "token", "type": "address"},
            {"name": "state", "type": "uint8"},
            {"name": "createdAt", "type": "uint256"},
        ],
    },
    # Release funds to a recipient
    {
        "name": "release",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "depositId", "type": "bytes32"},
            {"name": "recipient", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [],
    },
    # Refund to original payer
    {
        "name": "refundInEscrow",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "depositId", "type": "bytes32"}],
        "outputs": [],
    },
    # Check merchant balance
    {
        "name": "merchantBalance",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "merchant", "type": "address"},
            {"name": "token", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]

FACTORY_ABI = [
    {
        "name": "getRelayAddress",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "merchantPayout", "type": "address"}],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "name": "getMerchantFromRelay",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "relayAddress", "type": "address"}],
        "outputs": [{"name": "", "type": "address"}],
    },
]

ERC20_ABI = [
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]


# =============================================================================
# Types
# =============================================================================

class DepositState(Enum):
    """State of a deposit in the escrow."""
    NON_EXISTENT = 0
    IN_ESCROW = 1
    RELEASED = 2
    REFUNDED = 3


@dataclass
class DepositInfo:
    """Information about a deposit in escrow."""
    deposit_id: str
    payer: str
    merchant: str
    amount: Decimal
    token: str
    state: DepositState
    created_at: datetime


@dataclass
class ReleaseResult:
    """Result of a release operation."""
    success: bool
    tx_hash: Optional[str]
    deposit_id: str
    recipient: str
    amount: Decimal
    error: Optional[str] = None


@dataclass
class RefundResult:
    """Result of a refund operation."""
    success: bool
    tx_hash: Optional[str]
    deposit_id: str
    payer: str
    amount: Decimal
    error: Optional[str] = None


# =============================================================================
# X402r Escrow Client
# =============================================================================

class X402rEscrow:
    """
    Client for interacting with x402r escrow contracts.

    Usage:
        escrow = X402rEscrow()

        # Release payment to worker
        result = await escrow.release_to_worker(
            deposit_id="0x...",
            worker_address="0x...",
            amount=Decimal("10.00")
        )

        # Refund to agent
        result = await escrow.refund_to_agent(deposit_id="0x...")
    """

    def __init__(
        self,
        network: Optional[str] = None,
        private_key: Optional[str] = None,
    ):
        self.network = network or get_network()
        self._private_key = private_key or get_private_key()

        if self.network not in CONTRACTS:
            raise ValueError(f"Unknown network: {self.network}. Use: base or base-sepolia")

        self.config = CONTRACTS[self.network]
        self.w3 = Web3(Web3.HTTPProvider(self.config["rpc"]))

        # Initialize account if private key provided
        self.account = None
        if self._private_key:
            self.account = Account.from_key(self._private_key)
            logger.info("X402rEscrow initialized with account: %s...", self.account.address[:10])
        else:
            logger.info("X402rEscrow initialized in read-only mode (no private key)")

        # Contract instances
        self.escrow = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.config["escrow"]),
            abi=ESCROW_ABI,
        )
        self.factory = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.config["factory"]),
            abi=FACTORY_ABI,
        )

        logger.info("X402rEscrow connected to %s", self.network)

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get_deposit(self, deposit_id: str) -> Optional[DepositInfo]:
        """
        Get information about a deposit.

        Args:
            deposit_id: The deposit identifier (bytes32 hex)

        Returns:
            DepositInfo or None if not found
        """
        try:
            deposit_id_bytes = bytes.fromhex(deposit_id.replace("0x", ""))
            if len(deposit_id_bytes) != 32:
                deposit_id_bytes = deposit_id_bytes.ljust(32, b'\x00')

            result = self.escrow.functions.deposits(deposit_id_bytes).call()
            payer, merchant, amount, token, state, created_at = result

            if payer == "0x0000000000000000000000000000000000000000":
                return None

            return DepositInfo(
                deposit_id=deposit_id,
                payer=payer,
                merchant=merchant,
                amount=Decimal(amount) / Decimal(10**6),  # USDC has 6 decimals
                token=token,
                state=DepositState(state),
                created_at=datetime.fromtimestamp(created_at, tz=timezone.utc),
            )
        except Exception as e:
            logger.error("Failed to get deposit %s: %s", deposit_id, e)
            return None

    def get_proxy_address(self, merchant: Optional[str] = None) -> Optional[str]:
        """Get the proxy address for a merchant."""
        merchant = merchant or get_merchant_address()
        if not merchant:
            return None

        try:
            proxy = self.factory.functions.getRelayAddress(
                Web3.to_checksum_address(merchant)
            ).call()

            if proxy == "0x0000000000000000000000000000000000000000":
                return None

            return proxy
        except Exception as e:
            logger.error("Failed to get proxy for %s: %s", merchant, e)
            return None

    def get_merchant_balance(self, merchant: Optional[str] = None) -> Decimal:
        """Get the USDC balance held in escrow for a merchant."""
        merchant = merchant or get_merchant_address()
        if not merchant:
            return Decimal("0")

        try:
            balance = self.escrow.functions.merchantBalance(
                Web3.to_checksum_address(merchant),
                Web3.to_checksum_address(self.config["usdc"]),
            ).call()

            return Decimal(balance) / Decimal(10**6)
        except Exception as e:
            logger.error("Failed to get balance for %s: %s", merchant, e)
            return Decimal("0")

    # =========================================================================
    # Transaction Parsing
    # =========================================================================

    def get_deposit_id_from_tx(self, tx_hash: str) -> Optional[str]:
        """
        Extract deposit_id from a transaction receipt.

        Scans logs emitted by the escrow contract for the first indexed
        bytes32 parameter (the depositId in the Deposited event).

        Args:
            tx_hash: Transaction hash of the escrow deposit.

        Returns:
            The deposit_id as a hex string, or None if not found.
        """
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            escrow_addr = self.config["escrow"].lower()

            for log in receipt.get("logs", []):
                if log["address"].lower() == escrow_addr and len(log["topics"]) >= 2:
                    # First indexed parameter after event signature is the depositId
                    deposit_id = log["topics"][1]
                    if isinstance(deposit_id, bytes):
                        return "0x" + deposit_id.hex()
                    return str(deposit_id)

            logger.warning("No escrow event found in tx %s", tx_hash)
            return None
        except Exception as e:
            logger.error("Failed to extract deposit_id from tx %s: %s", tx_hash, e)
            return None

    # =========================================================================
    # Write Operations
    # =========================================================================

    async def release_to_worker(
        self,
        deposit_id: str,
        worker_address: str,
        amount: Decimal,
    ) -> ReleaseResult:
        """
        Release escrowed funds to a worker.

        Args:
            deposit_id: The deposit identifier
            worker_address: Worker's wallet address
            amount: Amount to release (in USDC)

        Returns:
            ReleaseResult with transaction details
        """
        if not self.account:
            return ReleaseResult(
                success=False,
                tx_hash=None,
                deposit_id=deposit_id,
                recipient=worker_address,
                amount=amount,
                error="No private key configured",
            )

        try:
            deposit_id_bytes = bytes.fromhex(deposit_id.replace("0x", ""))
            if len(deposit_id_bytes) != 32:
                deposit_id_bytes = deposit_id_bytes.ljust(32, b'\x00')

            amount_wei = int(amount * Decimal(10**6))

            # Build transaction
            func = self.escrow.functions.release(
                deposit_id_bytes,
                Web3.to_checksum_address(worker_address),
                amount_wei,
            )

            tx = func.build_transaction({
                "from": self.account.address,
                "gas": 150000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "chainId": self.config["chain_id"],
            })

            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt["status"] != 1:
                return ReleaseResult(
                    success=False,
                    tx_hash=tx_hash.hex(),
                    deposit_id=deposit_id,
                    recipient=worker_address,
                    amount=amount,
                    error="Transaction reverted",
                )

            logger.info(
                "Released %s USDC to %s: tx=%s",
                amount, worker_address[:10], tx_hash.hex()
            )

            return ReleaseResult(
                success=True,
                tx_hash=tx_hash.hex(),
                deposit_id=deposit_id,
                recipient=worker_address,
                amount=amount,
            )

        except Exception as e:
            logger.error("Release failed: %s", e)
            return ReleaseResult(
                success=False,
                tx_hash=None,
                deposit_id=deposit_id,
                recipient=worker_address,
                amount=amount,
                error=str(e),
            )

    async def refund_to_agent(self, deposit_id: str) -> RefundResult:
        """
        Refund escrowed funds to the original payer (agent).

        Args:
            deposit_id: The deposit identifier

        Returns:
            RefundResult with transaction details
        """
        if not self.account:
            return RefundResult(
                success=False,
                tx_hash=None,
                deposit_id=deposit_id,
                payer="",
                amount=Decimal("0"),
                error="No private key configured",
            )

        try:
            # Get deposit info first
            deposit = self.get_deposit(deposit_id)
            if not deposit:
                return RefundResult(
                    success=False,
                    tx_hash=None,
                    deposit_id=deposit_id,
                    payer="",
                    amount=Decimal("0"),
                    error="Deposit not found",
                )

            if deposit.state != DepositState.IN_ESCROW:
                return RefundResult(
                    success=False,
                    tx_hash=None,
                    deposit_id=deposit_id,
                    payer=deposit.payer,
                    amount=deposit.amount,
                    error=f"Cannot refund: deposit state is {deposit.state.name}",
                )

            deposit_id_bytes = bytes.fromhex(deposit_id.replace("0x", ""))
            if len(deposit_id_bytes) != 32:
                deposit_id_bytes = deposit_id_bytes.ljust(32, b'\x00')

            # Build transaction
            func = self.escrow.functions.refundInEscrow(deposit_id_bytes)

            tx = func.build_transaction({
                "from": self.account.address,
                "gas": 100000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "chainId": self.config["chain_id"],
            })

            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt["status"] != 1:
                return RefundResult(
                    success=False,
                    tx_hash=tx_hash.hex(),
                    deposit_id=deposit_id,
                    payer=deposit.payer,
                    amount=deposit.amount,
                    error="Transaction reverted",
                )

            logger.info(
                "Refunded %s USDC to %s: tx=%s",
                deposit.amount, deposit.payer[:10], tx_hash.hex()
            )

            return RefundResult(
                success=True,
                tx_hash=tx_hash.hex(),
                deposit_id=deposit_id,
                payer=deposit.payer,
                amount=deposit.amount,
            )

        except Exception as e:
            logger.error("Refund failed: %s", e)
            return RefundResult(
                success=False,
                tx_hash=None,
                deposit_id=deposit_id,
                payer="",
                amount=Decimal("0"),
                error=str(e),
            )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_payment_extension(self) -> Dict[str, Any]:
        """
        Get the x402r refund extension for payment payloads.

        Returns the extension that agents should include when paying Execution Market.
        """
        merchant = get_merchant_address()
        proxy = get_proxy_address() or self.get_proxy_address(merchant)

        if not proxy or not merchant:
            raise ValueError("X402R_PROXY_ADDRESS and X402R_MERCHANT_ADDRESS must be set")

        return {
            "refund": {
                "info": {
                    "factoryAddress": self.config["factory"],
                    "merchantPayouts": {
                        proxy: merchant
                    }
                }
            }
        }

    def get_config(self) -> Dict[str, Any]:
        """Get current x402r configuration."""
        merchant = get_merchant_address()
        proxy = get_proxy_address()

        return {
            "network": self.network,
            "chain_id": self.config["chain_id"],
            "factory": self.config["factory"],
            "escrow": self.config["escrow"],
            "usdc": self.config["usdc"],
            "merchant": merchant,
            "proxy": proxy or self.get_proxy_address(merchant),
            "account": self.account.address if self.account else None,
        }


# =============================================================================
# Module-Level Instance
# =============================================================================

_default_escrow: Optional[X402rEscrow] = None


def get_x402r_escrow() -> X402rEscrow:
    """Get or create the default X402rEscrow instance."""
    global _default_escrow
    if _default_escrow is None:
        _default_escrow = X402rEscrow()
    return _default_escrow


# =============================================================================
# Convenience Functions
# =============================================================================

async def release_payment(
    deposit_id: str,
    worker_address: str,
    amount: Decimal,
) -> ReleaseResult:
    """Release payment to worker (convenience function)."""
    escrow = get_x402r_escrow()
    return await escrow.release_to_worker(deposit_id, worker_address, amount)


async def refund_payment(deposit_id: str) -> RefundResult:
    """Refund payment to agent (convenience function)."""
    escrow = get_x402r_escrow()
    return await escrow.refund_to_agent(deposit_id)


def get_deposit_info(deposit_id: str) -> Optional[DepositInfo]:
    """Get deposit information (convenience function)."""
    escrow = get_x402r_escrow()
    return escrow.get_deposit(deposit_id)


def get_deposit_id(tx_hash: str) -> Optional[str]:
    """Extract deposit_id from transaction hash (convenience function)."""
    escrow = get_x402r_escrow()
    return escrow.get_deposit_id_from_tx(tx_hash)
