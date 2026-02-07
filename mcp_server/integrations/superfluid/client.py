"""
Superfluid Client for Streaming Payments

Enables real-time payment streams for long-running tasks.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for a payment stream."""

    sender: str
    receiver: str
    token: str
    flow_rate: int  # Tokens per second (in wei)
    task_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class StreamInfo:
    """Information about an active stream."""

    stream_id: str
    sender: str
    receiver: str
    token: str
    flow_rate: int
    started_at: datetime
    total_streamed: int
    is_active: bool


# Superfluid Host ABI (minimal)
SUPERFLUID_HOST_ABI = [
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "ctx", "type": "bytes"},
        ],
        "name": "callAgreement",
        "outputs": [{"name": "newCtx", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# CFA (Constant Flow Agreement) ABI (minimal)
CFA_ABI = [
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "sender", "type": "address"},
            {"name": "receiver", "type": "address"},
            {"name": "flowRate", "type": "int96"},
            {"name": "ctx", "type": "bytes"},
        ],
        "name": "createFlow",
        "outputs": [{"name": "newCtx", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "sender", "type": "address"},
            {"name": "receiver", "type": "address"},
            {"name": "flowRate", "type": "int96"},
            {"name": "ctx", "type": "bytes"},
        ],
        "name": "updateFlow",
        "outputs": [{"name": "newCtx", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "sender", "type": "address"},
            {"name": "receiver", "type": "address"},
            {"name": "ctx", "type": "bytes"},
        ],
        "name": "deleteFlow",
        "outputs": [{"name": "newCtx", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "sender", "type": "address"},
            {"name": "receiver", "type": "address"},
        ],
        "name": "getFlow",
        "outputs": [
            {"name": "timestamp", "type": "uint256"},
            {"name": "flowRate", "type": "int96"},
            {"name": "deposit", "type": "uint256"},
            {"name": "owedDeposit", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


class SuperfluidClient:
    """
    Client for Superfluid streaming payments.

    Supports:
    - Creating payment streams
    - Updating flow rates
    - Pausing/resuming streams
    - Querying stream status
    """

    # Contract addresses by network
    CONTRACTS = {
        "base": {
            "host": "0x4C073B3baB6d8826b8C5b229f3cfdC1eC6E47E74",
            "cfa": "0x19ba78B9cDB05A877718841c574325fdB53601bb",
            "usdcx": "0xD04383398dD2426297da660F9CCA3d439AF9ce1b",  # Super USDC
        },
        "base-sepolia": {
            "host": "0x109412E3C84f0539b43d39dB691B08c90f58dC7c",
            "cfa": "0x8a3170AdbC67233196371226141736E4151e7C26",
            "usdcx": "0x9CE2062b085A2268E8d769fFC040f6692315fd2c",
        },
    }

    # Flow rate for $18/hr = $0.005/second
    HOURLY_RATE_18 = int(18 * 1e18 / 3600)  # In wei per second

    def __init__(
        self,
        network: str = "base",
        private_key: Optional[str] = None,
        rpc_url: Optional[str] = None,
    ):
        """
        Initialize Superfluid client.

        Args:
            network: Network name (base, base-sepolia)
            private_key: Private key for transactions
            rpc_url: Custom RPC URL
        """
        self.network = network
        self.private_key = private_key or os.getenv("SUPERFLUID_PRIVATE_KEY")

        # RPC URLs
        rpc_urls = {
            "base": "https://mainnet.base.org",
            "base-sepolia": "https://sepolia.base.org",
        }

        rpc = rpc_url or os.getenv("SUPERFLUID_RPC_URL") or rpc_urls.get(network)
        if not rpc:
            raise ValueError(f"No RPC URL for network: {network}")

        self.w3 = Web3(Web3.HTTPProvider(rpc))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Setup contracts
        contracts = self.CONTRACTS.get(network)
        if not contracts:
            raise ValueError(f"No contract addresses for network: {network}")

        self.host = self.w3.eth.contract(
            address=Web3.to_checksum_address(contracts["host"]), abi=SUPERFLUID_HOST_ABI
        )
        self.cfa = self.w3.eth.contract(
            address=Web3.to_checksum_address(contracts["cfa"]), abi=CFA_ABI
        )
        self.usdcx_address = Web3.to_checksum_address(contracts["usdcx"])

        # Setup account
        self.account = None
        if self.private_key:
            self.account = self.w3.eth.account.from_key(self.private_key)

        logger.info(f"SuperfluidClient initialized on {network}")

    def calculate_flow_rate(
        self, hourly_rate_usd: float, token_decimals: int = 18
    ) -> int:
        """
        Calculate flow rate in wei per second.

        Args:
            hourly_rate_usd: Hourly rate in USD
            token_decimals: Token decimals

        Returns:
            Flow rate in wei per second
        """
        per_second = Decimal(hourly_rate_usd) / Decimal(3600)
        return int(per_second * Decimal(10**token_decimals))

    async def create_stream(
        self, receiver: str, flow_rate: int, task_id: str
    ) -> Optional[str]:
        """
        Create a new payment stream.

        Args:
            receiver: Receiver address
            flow_rate: Tokens per second (in wei)
            task_id: Associated task ID

        Returns:
            Transaction hash or None
        """
        if not self.account:
            raise ValueError("Private key required to create stream")

        try:
            receiver = Web3.to_checksum_address(receiver)

            # Build createFlow transaction
            tx_data = self.cfa.encodeABI(
                fn_name="createFlow",
                args=[
                    self.usdcx_address,
                    self.account.address,
                    receiver,
                    flow_rate,
                    b"",  # Empty context
                ],
            )

            # Send via host.callAgreement
            tx = self.host.functions.callAgreement(
                self.cfa.address, tx_data
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": 500000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                logger.info(
                    f"Stream created: {receiver}, rate: {flow_rate}, task: {task_id}"
                )
                return tx_hash.hex()
            else:
                logger.error("Create stream transaction failed")
                return None

        except Exception as e:
            logger.error(f"Error creating stream: {e}")
            return None

    async def update_stream(self, receiver: str, new_flow_rate: int) -> Optional[str]:
        """
        Update an existing stream's flow rate.

        Args:
            receiver: Receiver address
            new_flow_rate: New flow rate

        Returns:
            Transaction hash or None
        """
        if not self.account:
            raise ValueError("Private key required")

        try:
            receiver = Web3.to_checksum_address(receiver)

            tx_data = self.cfa.encodeABI(
                fn_name="updateFlow",
                args=[
                    self.usdcx_address,
                    self.account.address,
                    receiver,
                    new_flow_rate,
                    b"",
                ],
            )

            tx = self.host.functions.callAgreement(
                self.cfa.address, tx_data
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": 300000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                logger.info(f"Stream updated: {receiver}, new rate: {new_flow_rate}")
                return tx_hash.hex()
            return None

        except Exception as e:
            logger.error(f"Error updating stream: {e}")
            return None

    async def delete_stream(self, receiver: str) -> Optional[str]:
        """
        Delete (stop) a stream.

        Args:
            receiver: Receiver address

        Returns:
            Transaction hash or None
        """
        if not self.account:
            raise ValueError("Private key required")

        try:
            receiver = Web3.to_checksum_address(receiver)

            tx_data = self.cfa.encodeABI(
                fn_name="deleteFlow",
                args=[self.usdcx_address, self.account.address, receiver, b""],
            )

            tx = self.host.functions.callAgreement(
                self.cfa.address, tx_data
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": 300000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                logger.info(f"Stream deleted: {receiver}")
                return tx_hash.hex()
            return None

        except Exception as e:
            logger.error(f"Error deleting stream: {e}")
            return None

    async def get_stream_info(self, sender: str, receiver: str) -> Optional[StreamInfo]:
        """
        Get information about a stream.

        Args:
            sender: Sender address
            receiver: Receiver address

        Returns:
            StreamInfo or None
        """
        try:
            sender = Web3.to_checksum_address(sender)
            receiver = Web3.to_checksum_address(receiver)

            result = self.cfa.functions.getFlow(
                self.usdcx_address, sender, receiver
            ).call()

            timestamp, flow_rate, deposit, owed_deposit = result

            if flow_rate == 0:
                return None

            return StreamInfo(
                stream_id=f"{sender}_{receiver}",
                sender=sender,
                receiver=receiver,
                token=self.usdcx_address,
                flow_rate=flow_rate,
                started_at=datetime.fromtimestamp(timestamp),
                total_streamed=0,  # Would calculate from timestamp
                is_active=flow_rate > 0,
            )

        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return None

    async def pause_stream(self, receiver: str) -> Optional[str]:
        """Pause stream by setting flow rate to 0."""
        return await self.update_stream(receiver, 0)

    async def resume_stream(self, receiver: str, flow_rate: int) -> Optional[str]:
        """Resume stream with specified flow rate."""
        return await self.update_stream(receiver, flow_rate)
