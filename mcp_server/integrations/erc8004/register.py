"""
ERC-8004 Worker Registration

Handles on-chain identity registration for Chamba workers.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


class RegistrationStatus(str, Enum):
    """Worker registration status."""
    NOT_REGISTERED = "not_registered"
    PENDING = "pending"
    REGISTERED = "registered"
    SUSPENDED = "suspended"


@dataclass
class WorkerIdentity:
    """Worker identity from ERC-8004."""
    token_id: int
    wallet_address: str
    registration_timestamp: int
    is_active: bool
    metadata_uri: Optional[str] = None


# ERC-8004 Agent Registry ABI (minimal)
ERC8004_ABI = [
    {
        "inputs": [{"name": "wallet", "type": "address"}],
        "name": "getAgentByOwner",
        "outputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "owner", "type": "address"},
            {"name": "registrationTime", "type": "uint256"},
            {"name": "isActive", "type": "bool"},
            {"name": "metadataURI", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "metadataURI", "type": "string"}
        ],
        "name": "registerAgent",
        "outputs": [{"name": "tokenId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "isAgentActive",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "wallet", "type": "address"}],
        "name": "hasAgent",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "key", "type": "string"},
            {"name": "value", "type": "bytes"}
        ],
        "name": "setMetadata",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "key", "type": "string"}
        ],
        "name": "getMetadata",
        "outputs": [{"name": "", "type": "bytes"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class ERC8004Registry:
    """
    ERC-8004 Registry client for worker identity management.

    Handles registration, lookup, and metadata management for
    Chamba workers using the ERC-8004 Agent Registry standard.
    """

    # Contract addresses by network
    CONTRACTS = {
        "sepolia": "0x1234567890123456789012345678901234567890",  # Testnet
        "base": "0x0987654321098765432109876543210987654321",      # Production
        "base-sepolia": "0xabcdef0123456789abcdef0123456789abcdef01"
    }

    # RPC endpoints
    RPC_URLS = {
        "sepolia": "https://rpc.sepolia.org",
        "base": "https://mainnet.base.org",
        "base-sepolia": "https://sepolia.base.org"
    }

    def __init__(
        self,
        network: str = "sepolia",
        private_key: Optional[str] = None,
        rpc_url: Optional[str] = None
    ):
        """
        Initialize ERC-8004 Registry client.

        Args:
            network: Network name (sepolia, base, base-sepolia)
            private_key: Private key for write operations (optional)
            rpc_url: Custom RPC URL (optional)
        """
        self.network = network
        self.private_key = private_key or os.getenv("ERC8004_PRIVATE_KEY")

        # Setup Web3
        rpc = rpc_url or os.getenv("ERC8004_RPC_URL") or self.RPC_URLS.get(network)
        if not rpc:
            raise ValueError(f"No RPC URL for network: {network}")

        self.w3 = Web3(Web3.HTTPProvider(rpc))

        # Add POA middleware for Base
        if "base" in network.lower():
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Setup contract
        contract_address = os.getenv("ERC8004_CONTRACT") or self.CONTRACTS.get(network)
        if not contract_address:
            raise ValueError(f"No contract address for network: {network}")

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=ERC8004_ABI
        )

        # Setup account if private key provided
        self.account = None
        if self.private_key:
            self.account = self.w3.eth.account.from_key(self.private_key)

        logger.info(f"ERC8004Registry initialized on {network}")

    async def is_registered(self, wallet_address: str) -> bool:
        """
        Check if a wallet has a registered ERC-8004 identity.

        Args:
            wallet_address: Wallet address to check

        Returns:
            True if registered
        """
        try:
            checksum_addr = Web3.to_checksum_address(wallet_address)
            return self.contract.functions.hasAgent(checksum_addr).call()
        except Exception as e:
            logger.error(f"Error checking registration: {e}")
            return False

    async def get_identity(self, wallet_address: str) -> Optional[WorkerIdentity]:
        """
        Get worker identity from ERC-8004.

        Args:
            wallet_address: Wallet address

        Returns:
            WorkerIdentity or None if not registered
        """
        try:
            checksum_addr = Web3.to_checksum_address(wallet_address)

            # Check if registered
            if not await self.is_registered(wallet_address):
                return None

            # Get agent data
            result = self.contract.functions.getAgentByOwner(checksum_addr).call()
            token_id, owner, reg_time, is_active, metadata_uri = result

            return WorkerIdentity(
                token_id=token_id,
                wallet_address=owner,
                registration_timestamp=reg_time,
                is_active=is_active,
                metadata_uri=metadata_uri if metadata_uri else None
            )

        except Exception as e:
            logger.error(f"Error getting identity: {e}")
            return None

    async def register_worker(
        self,
        metadata_uri: str = "",
        gas_limit: int = 200000
    ) -> Optional[int]:
        """
        Register a new worker identity.

        Args:
            metadata_uri: IPFS URI with worker metadata
            gas_limit: Gas limit for transaction

        Returns:
            Token ID or None on failure
        """
        if not self.account:
            raise ValueError("Private key required for registration")

        try:
            # Build transaction
            tx = self.contract.functions.registerAgent(metadata_uri).build_transaction({
                'from': self.account.address,
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address)
            })

            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt['status'] == 1:
                # Get token ID from logs (simplified)
                logger.info(f"Worker registered, tx: {tx_hash.hex()}")

                # Query the new identity
                identity = await self.get_identity(self.account.address)
                return identity.token_id if identity else None
            else:
                logger.error("Registration transaction failed")
                return None

        except Exception as e:
            logger.error(f"Error registering worker: {e}")
            return None

    async def set_metadata(
        self,
        token_id: int,
        key: str,
        value: bytes,
        gas_limit: int = 100000
    ) -> bool:
        """
        Set metadata on worker identity.

        Args:
            token_id: Worker's token ID
            key: Metadata key (e.g., "chamba_reputation")
            value: Metadata value as bytes
            gas_limit: Gas limit

        Returns:
            True on success
        """
        if not self.account:
            raise ValueError("Private key required")

        try:
            tx = self.contract.functions.setMetadata(
                token_id, key, value
            ).build_transaction({
                'from': self.account.address,
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address)
            })

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            return receipt['status'] == 1

        except Exception as e:
            logger.error(f"Error setting metadata: {e}")
            return False

    async def get_metadata(self, token_id: int, key: str) -> Optional[bytes]:
        """
        Get metadata from worker identity.

        Args:
            token_id: Worker's token ID
            key: Metadata key

        Returns:
            Metadata value or None
        """
        try:
            return self.contract.functions.getMetadata(token_id, key).call()
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return None

    async def check_active(self, wallet_address: str) -> bool:
        """
        Check if worker identity is active.

        Args:
            wallet_address: Worker's wallet

        Returns:
            True if active
        """
        identity = await self.get_identity(wallet_address)
        return identity.is_active if identity else False

    def get_registration_status(self, wallet_address: str) -> RegistrationStatus:
        """
        Get worker's registration status synchronously.

        Args:
            wallet_address: Wallet address

        Returns:
            RegistrationStatus
        """
        try:
            checksum_addr = Web3.to_checksum_address(wallet_address)

            if not self.contract.functions.hasAgent(checksum_addr).call():
                return RegistrationStatus.NOT_REGISTERED

            result = self.contract.functions.getAgentByOwner(checksum_addr).call()
            _, _, _, is_active, _ = result

            if is_active:
                return RegistrationStatus.REGISTERED
            else:
                return RegistrationStatus.SUSPENDED

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return RegistrationStatus.NOT_REGISTERED


# Utility functions

def create_worker_metadata(
    name: str,
    skills: list[str],
    location_hint: Optional[str] = None,
    bio: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create metadata JSON for worker registration.

    Args:
        name: Display name
        skills: List of skills
        location_hint: General location
        bio: Short bio

    Returns:
        Metadata dict for IPFS upload
    """
    return {
        "name": name,
        "description": bio or f"Chamba worker: {name}",
        "image": "",  # Profile image IPFS URI
        "attributes": [
            {"trait_type": "skills", "value": ",".join(skills)},
            {"trait_type": "location", "value": location_hint or "Global"},
            {"trait_type": "platform", "value": "Chamba"}
        ],
        "external_url": f"https://chamba.ultravioletadao.xyz/worker/{name}"
    }
