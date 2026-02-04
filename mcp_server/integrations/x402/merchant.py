"""
x402 Merchant Registration for Execution Market (NOW-019, NOW-020)

Registers Execution Market as merchant and deploys relay proxy.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

# Base Mainnet contracts
MERCHANT_ROUTER = "0xa48E8AdcA504D2f48e5AF6be49039354e922913F"
DEPOSIT_RELAY_FACTORY = "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Minimal ABIs
MERCHANT_ROUTER_ABI = [
    {
        "inputs": [
            {"name": "merchant", "type": "address"},
            {"name": "tokens", "type": "address[]"}
        ],
        "name": "registerMerchant",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "merchant", "type": "address"}],
        "name": "isMerchant",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

RELAY_FACTORY_ABI = [
    {
        "inputs": [
            {"name": "merchant", "type": "address"},
            {"name": "token", "type": "address"}
        ],
        "name": "createRelay",
        "outputs": [{"name": "relay", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "merchant", "type": "address"},
            {"name": "token", "type": "address"}
        ],
        "name": "getRelay",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


@dataclass
class MerchantConfig:
    """Merchant configuration."""
    address: str
    relay_address: Optional[str] = None
    is_registered: bool = False
    tokens: List[str] = None

    def __post_init__(self):
        if self.tokens is None:
            self.tokens = [USDC_BASE]


class X402Merchant:
    """
    Manages Execution Market's x402 merchant registration.

    Flow:
    1. Register as merchant on MerchantRouter
    2. Deploy relay proxy via DepositRelayFactory
    3. Use relay for escrow deposits
    """

    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        merchant_address: Optional[str] = None
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key)
        self.merchant_address = merchant_address or self.account.address

        # Initialize contracts
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(MERCHANT_ROUTER),
            abi=MERCHANT_ROUTER_ABI
        )
        self.factory = self.w3.eth.contract(
            address=Web3.to_checksum_address(DEPOSIT_RELAY_FACTORY),
            abi=RELAY_FACTORY_ABI
        )

        self._relay_cache: Dict[str, str] = {}

    async def is_registered(self) -> bool:
        """Check if Execution Market is registered as merchant."""
        return self.router.functions.isMerchant(
            Web3.to_checksum_address(self.merchant_address)
        ).call()

    async def register_merchant(
        self,
        tokens: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Register Execution Market as x402 merchant (NOW-019).

        Args:
            tokens: List of token addresses to accept

        Returns:
            Transaction result
        """
        if await self.is_registered():
            logger.info("Already registered as merchant")
            return {"status": "already_registered"}

        tokens = tokens or [USDC_BASE]
        token_addresses = [Web3.to_checksum_address(t) for t in tokens]

        # Build transaction
        tx = self.router.functions.registerMerchant(
            Web3.to_checksum_address(self.merchant_address),
            token_addresses
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 200000,
            "maxFeePerGas": self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei")
        })

        # Sign and send
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        logger.info(f"Merchant registered: {tx_hash.hex()}")
        return {
            "status": "registered",
            "tx_hash": tx_hash.hex(),
            "block": receipt.blockNumber
        }

    async def get_relay(self, token: str = USDC_BASE) -> Optional[str]:
        """Get existing relay address for token."""
        token_checksum = Web3.to_checksum_address(token)

        if token_checksum in self._relay_cache:
            return self._relay_cache[token_checksum]

        relay = self.factory.functions.getRelay(
            Web3.to_checksum_address(self.merchant_address),
            token_checksum
        ).call()

        if relay != "0x0000000000000000000000000000000000000000":
            self._relay_cache[token_checksum] = relay
            return relay

        return None

    async def deploy_relay(
        self,
        token: str = USDC_BASE
    ) -> Dict[str, Any]:
        """
        Deploy relay proxy via DepositRelayFactory (NOW-020).

        Args:
            token: Token address for relay

        Returns:
            Relay address and transaction
        """
        token_checksum = Web3.to_checksum_address(token)

        # Check existing relay
        existing = await self.get_relay(token)
        if existing:
            logger.info(f"Relay already exists: {existing}")
            return {"status": "exists", "relay": existing}

        # Deploy new relay
        tx = self.factory.functions.createRelay(
            Web3.to_checksum_address(self.merchant_address),
            token_checksum
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gas": 500000,
            "maxFeePerGas": self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei")
        })

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Get relay address from logs
        relay_address = await self.get_relay(token)
        self._relay_cache[token_checksum] = relay_address

        logger.info(f"Relay deployed: {relay_address}, tx: {tx_hash.hex()}")
        return {
            "status": "deployed",
            "relay": relay_address,
            "tx_hash": tx_hash.hex(),
            "block": receipt.blockNumber
        }

    async def setup_complete(
        self,
        tokens: Optional[List[str]] = None
    ) -> MerchantConfig:
        """
        Complete merchant setup (register + deploy relay).

        Returns:
            MerchantConfig with all addresses
        """
        tokens = tokens or [USDC_BASE]

        # Step 1: Register
        await self.register_merchant(tokens)

        # Step 2: Deploy relay for primary token
        relay_result = await self.deploy_relay(tokens[0])

        return MerchantConfig(
            address=self.merchant_address,
            relay_address=relay_result.get("relay"),
            is_registered=True,
            tokens=tokens
        )


# CLI helper
async def setup_em_merchant():
    """CLI command to setup Execution Market merchant."""
    import os

    rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
    private_key = os.getenv("X402_PRIVATE_KEY")

    if not private_key:
        raise ValueError("X402_PRIVATE_KEY required")

    merchant = X402Merchant(rpc_url, private_key)
    config = await merchant.setup_complete()

    print(f"Merchant setup complete!")
    print(f"  Address: {config.address}")
    print(f"  Relay: {config.relay_address}")
    print(f"  Registered: {config.is_registered}")

    return config


if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_em_merchant())
