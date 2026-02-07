"""
SealRegistry - On-chain Seal Registry Interface (NOW-183)

Manages seal storage and retrieval on the blockchain.
Uses the SealRegistry smart contract to:
- Issue new seals
- Revoke seals
- Query seal ownership
- Verify seal validity

Contract Architecture:
    SealRegistry (ERC-1155 Multi-Token)
    - Each seal TYPE is a token ID
    - Workers can hold multiple seals (different types)
    - Seals are non-transferable (soulbound)
    - Includes metadata URI for each seal type
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC

from web3 import Web3

# Handle different web3 versions for POA middleware
try:
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware as ExtraDataToPOAMiddleware
    except ImportError:
        ExtraDataToPOAMiddleware = None

from .types import (
    Seal,
    SealBundle,
    SealCategory,
    SkillSealType,
    WorkSealType,
    BehaviorSealType,
    get_requirement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONTRACT ABI
# =============================================================================

SEAL_REGISTRY_ABI = [
    # View functions
    {
        "inputs": [
            {"name": "holder", "type": "address"},
            {"name": "sealTypeId", "type": "uint256"},
        ],
        "name": "hasSeal",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "holder", "type": "address"}],
        "name": "getSeals",
        "outputs": [
            {"name": "sealTypeIds", "type": "uint256[]"},
            {"name": "issuedAts", "type": "uint256[]"},
            {"name": "expiresAts", "type": "uint256[]"},
            {"name": "isActives", "type": "bool[]"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "holder", "type": "address"},
            {"name": "sealTypeId", "type": "uint256"},
        ],
        "name": "getSealDetails",
        "outputs": [
            {"name": "issuedAt", "type": "uint256"},
            {"name": "expiresAt", "type": "uint256"},
            {"name": "isActive", "type": "bool"},
            {"name": "issuer", "type": "address"},
            {"name": "metadataHash", "type": "bytes32"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "sealTypeId", "type": "uint256"}],
        "name": "getSealTypeInfo",
        "outputs": [
            {"name": "name", "type": "string"},
            {"name": "category", "type": "uint8"},
            {"name": "totalIssued", "type": "uint256"},
            {"name": "metadataURI", "type": "string"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "holder", "type": "address"}],
        "name": "getSealCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    # Write functions
    {
        "inputs": [
            {"name": "holder", "type": "address"},
            {"name": "sealTypeId", "type": "uint256"},
            {"name": "expiresAt", "type": "uint256"},
            {"name": "metadataHash", "type": "bytes32"},
        ],
        "name": "issueSeal",
        "outputs": [{"name": "success", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "holders", "type": "address[]"},
            {"name": "sealTypeIds", "type": "uint256[]"},
            {"name": "expiresAts", "type": "uint256[]"},
            {"name": "metadataHashes", "type": "bytes32[]"},
        ],
        "name": "batchIssueSeal",
        "outputs": [{"name": "successCount", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "holder", "type": "address"},
            {"name": "sealTypeId", "type": "uint256"},
            {"name": "reason", "type": "string"},
        ],
        "name": "revokeSeal",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "holder", "type": "address"},
            {"name": "sealTypeId", "type": "uint256"},
            {"name": "newExpiresAt", "type": "uint256"},
        ],
        "name": "renewSeal",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # Events
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "holder", "type": "address"},
            {"indexed": True, "name": "sealTypeId", "type": "uint256"},
            {"indexed": False, "name": "issuer", "type": "address"},
            {"indexed": False, "name": "expiresAt", "type": "uint256"},
        ],
        "name": "SealIssued",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "holder", "type": "address"},
            {"indexed": True, "name": "sealTypeId", "type": "uint256"},
            {"indexed": False, "name": "reason", "type": "string"},
        ],
        "name": "SealRevoked",
        "type": "event",
    },
]


# =============================================================================
# SEAL TYPE ID MAPPING
# =============================================================================

# Map seal type strings to on-chain uint256 IDs
SEAL_TYPE_IDS: Dict[str, int] = {
    # Skill seals: 1-99
    SkillSealType.PHOTOGRAPHY_VERIFIED.value: 1,
    SkillSealType.PHOTOGRAPHY_PROFESSIONAL.value: 2,
    SkillSealType.VIDEO_VERIFIED.value: 3,
    SkillSealType.DOCUMENT_HANDLING.value: 10,
    SkillSealType.NOTARY_CERTIFIED.value: 11,
    SkillSealType.DELIVERY_CERTIFIED.value: 20,
    SkillSealType.DRIVING_VERIFIED.value: 21,
    SkillSealType.TECHNICAL_BASIC.value: 30,
    SkillSealType.TECHNICAL_ADVANCED.value: 31,
    SkillSealType.BILINGUAL_EN_ES.value: 40,
    SkillSealType.TRILINGUAL.value: 41,
    SkillSealType.MEDICAL_CERTIFIED.value: 50,
    SkillSealType.LEGAL_CERTIFIED.value: 51,
    SkillSealType.FINANCIAL_CERTIFIED.value: 52,
    # Work seals: 100-199
    WorkSealType.TASKS_10.value: 100,
    WorkSealType.TASKS_25.value: 101,
    WorkSealType.TASKS_50.value: 102,
    WorkSealType.TASKS_100.value: 103,
    WorkSealType.TASKS_250.value: 104,
    WorkSealType.TASKS_500.value: 105,
    WorkSealType.TASKS_1000.value: 106,
    WorkSealType.EARNED_100_USD.value: 110,
    WorkSealType.EARNED_500_USD.value: 111,
    WorkSealType.EARNED_1000_USD.value: 112,
    WorkSealType.EARNED_5000_USD.value: 113,
    WorkSealType.EARNED_10000_USD.value: 114,
    WorkSealType.DELIVERY_10.value: 120,
    WorkSealType.DELIVERY_50.value: 121,
    WorkSealType.DELIVERY_100.value: 122,
    WorkSealType.PHOTO_10.value: 130,
    WorkSealType.PHOTO_50.value: 131,
    WorkSealType.PHOTO_100.value: 132,
    WorkSealType.ACTIVE_30_DAYS.value: 140,
    WorkSealType.ACTIVE_90_DAYS.value: 141,
    WorkSealType.ACTIVE_180_DAYS.value: 142,
    WorkSealType.ACTIVE_365_DAYS.value: 143,
    # Behavior seals: 200-299
    BehaviorSealType.FAST_RESPONDER.value: 200,
    BehaviorSealType.INSTANT_RESPONDER.value: 201,
    BehaviorSealType.NEVER_CANCELLED.value: 210,
    BehaviorSealType.ALWAYS_ON_TIME.value: 211,
    BehaviorSealType.HIGH_QUALITY.value: 220,
    BehaviorSealType.EXCEPTIONAL_QUALITY.value: 221,
    BehaviorSealType.CONSISTENT_PERFORMER.value: 230,
    BehaviorSealType.HELPFUL_REVIEWER.value: 240,
    BehaviorSealType.MENTOR.value: 241,
}

# Reverse mapping
SEAL_ID_TO_TYPE: Dict[int, str] = {v: k for k, v in SEAL_TYPE_IDS.items()}


def get_seal_type_id(seal_type: str) -> Optional[int]:
    """Get on-chain ID for seal type string."""
    return SEAL_TYPE_IDS.get(seal_type)


def get_seal_type_from_id(seal_id: int) -> Optional[str]:
    """Get seal type string from on-chain ID."""
    return SEAL_ID_TO_TYPE.get(seal_id)


# =============================================================================
# SEAL REGISTRY CLIENT
# =============================================================================


class SealRegistry:
    """
    On-chain Seal Registry client.

    Handles all interactions with the SealRegistry smart contract:
    - Query seals by holder
    - Issue new seals
    - Revoke seals
    - Renew expiring seals

    Example:
        >>> registry = SealRegistry(network="base-sepolia")
        >>> seals = await registry.get_seals("0x1234...")
        >>> print(f"Worker has {len(seals)} seals")
    """

    # Contract addresses by network
    CONTRACTS = {
        "sepolia": "0x2345678901234567890123456789012345678901",
        "base": "0x3456789012345678901234567890123456789012",
        "base-sepolia": "0x4567890123456789012345678901234567890123",
    }

    # RPC endpoints
    RPC_URLS = {
        "sepolia": "https://rpc.sepolia.org",
        "base": "https://mainnet.base.org",
        "base-sepolia": "https://sepolia.base.org",
    }

    def __init__(
        self,
        network: str = "base-sepolia",
        private_key: Optional[str] = None,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
    ):
        """
        Initialize Seal Registry client.

        Args:
            network: Network name (sepolia, base, base-sepolia)
            private_key: Private key for write operations
            rpc_url: Custom RPC URL
            contract_address: Custom contract address
        """
        self.network = network
        self.private_key = private_key or os.getenv("SEAL_REGISTRY_PRIVATE_KEY")

        # Setup Web3
        rpc = (
            rpc_url or os.getenv("SEAL_REGISTRY_RPC_URL") or self.RPC_URLS.get(network)
        )
        if not rpc:
            raise ValueError(f"No RPC URL for network: {network}")

        self.w3 = Web3(Web3.HTTPProvider(rpc))

        # Add POA middleware for Base (if available)
        if "base" in network.lower() and ExtraDataToPOAMiddleware:
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Setup contract
        addr = (
            contract_address
            or os.getenv("SEAL_REGISTRY_CONTRACT")
            or self.CONTRACTS.get(network)
        )
        if not addr:
            raise ValueError(f"No contract address for network: {network}")

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(addr), abi=SEAL_REGISTRY_ABI
        )

        # Setup account for write operations
        self.account = None
        if self.private_key:
            self.account = self.w3.eth.account.from_key(self.private_key)

        logger.info(f"SealRegistry initialized on {network}")

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def has_seal(self, holder_address: str, seal_type: str) -> bool:
        """
        Check if a holder has a specific seal.

        Args:
            holder_address: Worker's wallet address
            seal_type: Seal type string (e.g., "tasks_100_completed")

        Returns:
            True if holder has an active seal of this type
        """
        try:
            checksum_addr = Web3.to_checksum_address(holder_address)
            seal_id = get_seal_type_id(seal_type)

            if seal_id is None:
                logger.warning(f"Unknown seal type: {seal_type}")
                return False

            return self.contract.functions.hasSeal(checksum_addr, seal_id).call()

        except Exception as e:
            logger.error(f"Error checking seal: {e}")
            return False

    async def get_seals(self, holder_address: str) -> List[Seal]:
        """
        Get all seals for a holder.

        Args:
            holder_address: Worker's wallet address

        Returns:
            List of Seal objects
        """
        try:
            checksum_addr = Web3.to_checksum_address(holder_address)

            # Query contract
            result = self.contract.functions.getSeals(checksum_addr).call()
            seal_type_ids, issued_ats, expires_ats, is_actives = result

            seals = []
            for i, type_id in enumerate(seal_type_ids):
                seal_type = get_seal_type_from_id(type_id)
                if not seal_type:
                    continue

                # Determine category
                req = get_requirement(seal_type)
                category = req.category if req else SealCategory.WORK

                # Parse timestamps
                issued_at = datetime.fromtimestamp(issued_ats[i], tz=UTC)
                expires_at = None
                if expires_ats[i] > 0:
                    expires_at = datetime.fromtimestamp(expires_ats[i], tz=UTC)

                seal = Seal(
                    id=Seal.generate_id(holder_address, seal_type, issued_at),
                    category=category,
                    seal_type=seal_type,
                    holder_id=holder_address,
                    issued_at=issued_at,
                    expires_at=expires_at,
                    revoked_at=None if is_actives[i] else datetime.now(UTC),
                )
                seals.append(seal)

            return seals

        except Exception as e:
            logger.error(f"Error getting seals: {e}")
            return []

    async def get_seal_bundle(self, holder_address: str) -> SealBundle:
        """
        Get all seals organized by category.

        Args:
            holder_address: Worker's wallet address

        Returns:
            SealBundle with seals organized by category
        """
        seals = await self.get_seals(holder_address)

        bundle = SealBundle(holder_id=holder_address)

        for seal in seals:
            if seal.category == SealCategory.SKILL:
                bundle.skill_seals.append(seal)
            elif seal.category == SealCategory.WORK:
                bundle.work_seals.append(seal)
            elif seal.category == SealCategory.BEHAVIOR:
                bundle.behavior_seals.append(seal)

        return bundle

    async def get_seal_details(
        self, holder_address: str, seal_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific seal.

        Args:
            holder_address: Worker's wallet address
            seal_type: Seal type string

        Returns:
            Dict with seal details or None if not found
        """
        try:
            checksum_addr = Web3.to_checksum_address(holder_address)
            seal_id = get_seal_type_id(seal_type)

            if seal_id is None:
                return None

            result = self.contract.functions.getSealDetails(
                checksum_addr, seal_id
            ).call()

            issued_at, expires_at, is_active, issuer, metadata_hash = result

            return {
                "seal_type": seal_type,
                "seal_id": seal_id,
                "holder": holder_address,
                "issued_at": datetime.fromtimestamp(issued_at, tz=UTC).isoformat(),
                "expires_at": datetime.fromtimestamp(expires_at, tz=UTC).isoformat()
                if expires_at > 0
                else None,
                "is_active": is_active,
                "issuer": issuer,
                "metadata_hash": metadata_hash.hex() if metadata_hash else None,
            }

        except Exception as e:
            logger.error(f"Error getting seal details: {e}")
            return None

    async def get_seal_count(self, holder_address: str) -> int:
        """Get total number of seals for a holder."""
        try:
            checksum_addr = Web3.to_checksum_address(holder_address)
            return self.contract.functions.getSealCount(checksum_addr).call()
        except Exception as e:
            logger.error(f"Error getting seal count: {e}")
            return 0

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================

    async def issue_seal(
        self,
        holder_address: str,
        seal_type: str,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        gas_limit: int = 150000,
    ) -> Optional[str]:
        """
        Issue a new seal to a holder.

        Args:
            holder_address: Worker's wallet address
            seal_type: Seal type string
            expires_at: Optional expiration timestamp
            metadata: Optional metadata to hash and store
            gas_limit: Gas limit for transaction

        Returns:
            Transaction hash or None on failure
        """
        if not self.account:
            raise ValueError("Private key required for issuing seals")

        try:
            checksum_addr = Web3.to_checksum_address(holder_address)
            seal_id = get_seal_type_id(seal_type)

            if seal_id is None:
                raise ValueError(f"Unknown seal type: {seal_type}")

            # Calculate expires timestamp
            expires_timestamp = 0
            if expires_at:
                expires_timestamp = int(expires_at.timestamp())

            # Calculate metadata hash
            metadata_hash = bytes(32)  # Zero hash if no metadata
            if metadata:
                metadata_str = json.dumps(metadata, sort_keys=True)
                metadata_hash = Web3.keccak(text=metadata_str)

            # Build transaction
            tx = self.contract.functions.issueSeal(
                checksum_addr, seal_id, expires_timestamp, metadata_hash
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": gas_limit,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                logger.info(f"Seal issued: {seal_type} to {holder_address}")
                return tx_hash.hex()
            else:
                logger.error("Seal issuance transaction failed")
                return None

        except Exception as e:
            logger.error(f"Error issuing seal: {e}")
            return None

    async def batch_issue_seals(
        self,
        issuances: List[Dict[str, Any]],
        gas_limit: int = 500000,
    ) -> Optional[str]:
        """
        Issue multiple seals in a single transaction.

        Args:
            issuances: List of dicts with 'holder', 'seal_type', 'expires_at'
            gas_limit: Gas limit for transaction

        Returns:
            Transaction hash or None on failure
        """
        if not self.account:
            raise ValueError("Private key required for issuing seals")

        try:
            holders = []
            seal_ids = []
            expires_ats = []
            metadata_hashes = []

            for issuance in issuances:
                holder = Web3.to_checksum_address(issuance["holder"])
                seal_id = get_seal_type_id(issuance["seal_type"])

                if seal_id is None:
                    logger.warning(
                        f"Skipping unknown seal type: {issuance['seal_type']}"
                    )
                    continue

                expires_at = issuance.get("expires_at")
                expires_timestamp = int(expires_at.timestamp()) if expires_at else 0

                holders.append(holder)
                seal_ids.append(seal_id)
                expires_ats.append(expires_timestamp)
                metadata_hashes.append(bytes(32))

            if not holders:
                raise ValueError("No valid issuances")

            # Build transaction
            tx = self.contract.functions.batchIssueSeal(
                holders, seal_ids, expires_ats, metadata_hashes
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": gas_limit,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

            if receipt["status"] == 1:
                logger.info(f"Batch issued {len(holders)} seals")
                return tx_hash.hex()
            else:
                logger.error("Batch seal issuance failed")
                return None

        except Exception as e:
            logger.error(f"Error batch issuing seals: {e}")
            return None

    async def revoke_seal(
        self,
        holder_address: str,
        seal_type: str,
        reason: str = "Administrative revocation",
        gas_limit: int = 100000,
    ) -> Optional[str]:
        """
        Revoke a seal from a holder.

        Args:
            holder_address: Worker's wallet address
            seal_type: Seal type string
            reason: Reason for revocation
            gas_limit: Gas limit for transaction

        Returns:
            Transaction hash or None on failure
        """
        if not self.account:
            raise ValueError("Private key required for revoking seals")

        try:
            checksum_addr = Web3.to_checksum_address(holder_address)
            seal_id = get_seal_type_id(seal_type)

            if seal_id is None:
                raise ValueError(f"Unknown seal type: {seal_type}")

            tx = self.contract.functions.revokeSeal(
                checksum_addr, seal_id, reason
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": gas_limit,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                logger.info(f"Seal revoked: {seal_type} from {holder_address}")
                return tx_hash.hex()
            else:
                logger.error("Seal revocation failed")
                return None

        except Exception as e:
            logger.error(f"Error revoking seal: {e}")
            return None

    async def renew_seal(
        self,
        holder_address: str,
        seal_type: str,
        new_expires_at: datetime,
        gas_limit: int = 100000,
    ) -> Optional[str]:
        """
        Renew an expiring seal.

        Args:
            holder_address: Worker's wallet address
            seal_type: Seal type string
            new_expires_at: New expiration timestamp
            gas_limit: Gas limit for transaction

        Returns:
            Transaction hash or None on failure
        """
        if not self.account:
            raise ValueError("Private key required for renewing seals")

        try:
            checksum_addr = Web3.to_checksum_address(holder_address)
            seal_id = get_seal_type_id(seal_type)

            if seal_id is None:
                raise ValueError(f"Unknown seal type: {seal_type}")

            tx = self.contract.functions.renewSeal(
                checksum_addr, seal_id, int(new_expires_at.timestamp())
            ).build_transaction(
                {
                    "from": self.account.address,
                    "gas": gas_limit,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                }
            )

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                logger.info(f"Seal renewed: {seal_type} for {holder_address}")
                return tx_hash.hex()
            else:
                logger.error("Seal renewal failed")
                return None

        except Exception as e:
            logger.error(f"Error renewing seal: {e}")
            return None


# =============================================================================
# MOCK REGISTRY FOR TESTING
# =============================================================================


class MockSealRegistry:
    """
    In-memory mock registry for testing.

    Simulates on-chain storage without actual blockchain interaction.
    """

    def __init__(self):
        self._seals: Dict[str, List[Seal]] = {}  # holder -> seals
        self._tx_counter = 0

    def _generate_tx_hash(self) -> str:
        """Generate mock transaction hash."""
        self._tx_counter += 1
        return f"0x{'0' * 62}{self._tx_counter:02x}"

    async def has_seal(self, holder_address: str, seal_type: str) -> bool:
        holder_seals = self._seals.get(holder_address.lower(), [])
        return any(s.seal_type == seal_type and s.is_valid for s in holder_seals)

    async def get_seals(self, holder_address: str) -> List[Seal]:
        return self._seals.get(holder_address.lower(), [])

    async def get_seal_bundle(self, holder_address: str) -> SealBundle:
        seals = await self.get_seals(holder_address)
        bundle = SealBundle(holder_id=holder_address)

        for seal in seals:
            if seal.category == SealCategory.SKILL:
                bundle.skill_seals.append(seal)
            elif seal.category == SealCategory.WORK:
                bundle.work_seals.append(seal)
            elif seal.category == SealCategory.BEHAVIOR:
                bundle.behavior_seals.append(seal)

        return bundle

    async def get_seal_details(
        self, holder_address: str, seal_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific seal (mock implementation)."""
        holder_key = holder_address.lower()
        holder_seals = self._seals.get(holder_key, [])

        for seal in holder_seals:
            if seal.seal_type == seal_type:
                return {
                    "seal_type": seal_type,
                    "holder": holder_address,
                    "issued_at": seal.issued_at.isoformat(),
                    "expires_at": seal.expires_at.isoformat()
                    if seal.expires_at
                    else None,
                    "is_active": seal.is_valid,
                    "issuer": "0x0000000000000000000000000000000000000000",
                    "metadata_hash": None,
                }

        return None

    async def issue_seal(
        self,
        holder_address: str,
        seal_type: str,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[str]:
        holder_key = holder_address.lower()

        if holder_key not in self._seals:
            self._seals[holder_key] = []

        # Check for duplicate
        if await self.has_seal(holder_address, seal_type):
            logger.warning(f"Seal already exists: {seal_type}")
            return None

        req = get_requirement(seal_type)
        category = req.category if req else SealCategory.WORK

        now = datetime.now(UTC)
        seal = Seal(
            id=Seal.generate_id(holder_address, seal_type, now),
            category=category,
            seal_type=seal_type,
            holder_id=holder_address,
            issued_at=now,
            expires_at=expires_at,
            tx_hash=self._generate_tx_hash(),
            block_number=1000000 + self._tx_counter,
            metadata=metadata or {},
        )

        self._seals[holder_key].append(seal)
        return seal.tx_hash

    async def revoke_seal(
        self, holder_address: str, seal_type: str, reason: str = "", **kwargs
    ) -> Optional[str]:
        holder_key = holder_address.lower()
        holder_seals = self._seals.get(holder_key, [])

        for seal in holder_seals:
            if seal.seal_type == seal_type and seal.is_valid:
                seal.revoked_at = datetime.now(UTC)
                return self._generate_tx_hash()

        return None

    async def get_seal_count(self, holder_address: str) -> int:
        return len(await self.get_seals(holder_address))
