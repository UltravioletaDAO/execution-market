# NOW-024: x402 SDK client para Python

## Metadata
- **Prioridad**: P0
- **Fase**: 2 - x402 Integration
- **Dependencias**: NOW-019
- **Archivos a crear**: `mcp_server/integrations/x402/client.py`
- **Tiempo estimado**: 3-4 horas

## Descripción
Crear un cliente Python para interactuar con x402-rs (escrow, payments, refunds).

## Contexto Técnico
- **Protocol**: x402 HTTP API + on-chain transactions
- **SDK existente**: uvd-x402-sdk-python (verificar si usable)
- **Networks**: Base Mainnet (primary)

## Estructura de Archivos

```
mcp_server/
└── integrations/
    └── x402/
        ├── __init__.py
        ├── client.py      # Main client class
        ├── types.py       # Type definitions
        ├── escrow.py      # Escrow operations
        └── payments.py    # Payment operations
```

## Código de Referencia

### client.py
```python
"""
x402 SDK Client for Chamba
"""
import os
import json
from decimal import Decimal
from typing import Optional
from web3 import Web3
from eth_account import Account

class X402Client:
    """Client for x402 payment operations"""

    # Contract addresses (Base Mainnet)
    MERCHANT_ROUTER = "0xa48E8AdcA504D2f48e5AF6be49039354e922913F"
    DEPOSIT_RELAY_FACTORY = "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814"
    USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        merchant_address: Optional[str] = None,
        relay_address: Optional[str] = None
    ):
        self.rpc_url = rpc_url or os.environ["X402_RPC_URL"]
        self.private_key = private_key or os.environ["X402_PRIVATE_KEY"]
        self.merchant_address = merchant_address or os.environ.get("X402_MERCHANT_ADDRESS")
        self.relay_address = relay_address or os.environ.get("X402_RELAY_ADDRESS")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = Account.from_key(self.private_key)

        # Load contract ABIs
        self._load_abis()

    def _load_abis(self):
        """Load contract ABIs"""
        # Simplified ABIs for key functions
        self.usdc_abi = [
            {
                "name": "transfer",
                "type": "function",
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"type": "bool"}]
            },
            {
                "name": "approve",
                "type": "function",
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"type": "bool"}]
            },
            {
                "name": "balanceOf",
                "type": "function",
                "inputs": [{"name": "account", "type": "address"}],
                "outputs": [{"type": "uint256"}]
            }
        ]

        self.usdc = self.w3.eth.contract(
            address=self.USDC_BASE,
            abi=self.usdc_abi
        )

    async def send_payment(
        self,
        to_address: str,
        amount_usdc: float,
        memo: Optional[str] = None
    ) -> dict:
        """
        Send USDC payment to an address

        Args:
            to_address: Recipient wallet address
            amount_usdc: Amount in USDC (e.g., 5.50)
            memo: Optional memo for the transaction

        Returns:
            dict with tx_hash, amount, status
        """
        # Convert to wei (USDC has 6 decimals)
        amount_wei = int(Decimal(str(amount_usdc)) * Decimal(10**6))

        # Check balance
        balance = self.usdc.functions.balanceOf(self.account.address).call()
        if balance < amount_wei:
            raise ValueError(f"Insufficient USDC balance: {balance / 10**6} < {amount_usdc}")

        # Build transaction
        tx = self.usdc.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "tx_hash": tx_hash.hex(),
            "amount_usdc": amount_usdc,
            "to_address": to_address,
            "status": "completed" if receipt["status"] == 1 else "failed",
            "gas_used": receipt["gasUsed"],
            "memo": memo
        }

    async def create_escrow(
        self,
        task_id: str,
        amount_usdc: float,
        beneficiary: str,
        timeout_hours: int = 48
    ) -> dict:
        """
        Create escrow for a task

        Args:
            task_id: Task identifier
            amount_usdc: Escrow amount
            beneficiary: Worker address who will receive on release
            timeout_hours: Auto-release timeout

        Returns:
            dict with escrow_id, tx_hash
        """
        # For MVP, we use simple transfer to relay
        # Full escrow contract integration in future

        amount_wei = int(Decimal(str(amount_usdc)) * Decimal(10**6))

        # Approve relay to spend
        approve_tx = self.usdc.functions.approve(
            self.relay_address,
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 60000,
            'gasPrice': self.w3.eth.gas_price
        })

        signed_approve = self.w3.eth.account.sign_transaction(approve_tx, self.private_key)
        self.w3.eth.send_raw_transaction(signed_approve.rawTransaction)

        # Transfer to relay (escrow)
        transfer_tx = self.usdc.functions.transfer(
            self.relay_address,
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price
        })

        signed_transfer = self.w3.eth.account.sign_transaction(transfer_tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_transfer.rawTransaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "escrow_id": f"{task_id}-escrow",
            "tx_hash": tx_hash.hex(),
            "amount_usdc": amount_usdc,
            "beneficiary": beneficiary,
            "status": "locked" if receipt["status"] == 1 else "failed"
        }

    async def release_escrow(
        self,
        escrow_id: str,
        to_address: str,
        amount_usdc: float
    ) -> dict:
        """
        Release escrowed funds to beneficiary

        Args:
            escrow_id: Escrow identifier
            to_address: Recipient address
            amount_usdc: Amount to release

        Returns:
            dict with tx_hash, status
        """
        # In MVP, this is a direct transfer from relay
        # In production, this would call escrow contract release function

        return await self.send_payment(to_address, amount_usdc, memo=f"Release: {escrow_id}")

    async def refund_escrow(
        self,
        escrow_id: str,
        to_address: str,
        amount_usdc: float
    ) -> dict:
        """
        Refund escrowed funds to agent

        Args:
            escrow_id: Escrow identifier
            to_address: Agent's address
            amount_usdc: Amount to refund

        Returns:
            dict with tx_hash, status
        """
        return await self.send_payment(to_address, amount_usdc, memo=f"Refund: {escrow_id}")

    def get_balance(self, address: Optional[str] = None) -> float:
        """Get USDC balance of an address"""
        addr = address or self.account.address
        balance_wei = self.usdc.functions.balanceOf(
            Web3.to_checksum_address(addr)
        ).call()
        return float(balance_wei) / 10**6
```

### types.py
```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class PaymentResult:
    tx_hash: str
    amount_usdc: float
    to_address: str
    status: str  # "completed" | "failed" | "pending"
    gas_used: int
    memo: Optional[str] = None

@dataclass
class EscrowResult:
    escrow_id: str
    tx_hash: str
    amount_usdc: float
    beneficiary: str
    status: str  # "locked" | "released" | "refunded" | "failed"
    created_at: datetime = None
```

## Criterios de Éxito
- [ ] Cliente inicializa correctamente
- [ ] `send_payment` funciona
- [ ] `create_escrow` funciona
- [ ] `release_escrow` funciona
- [ ] `refund_escrow` funciona
- [ ] Error handling robusto
- [ ] Logging de transacciones

## Test Cases
```python
# Test 1: Send payment
client = X402Client()
result = await client.send_payment("0x...", 1.00)
assert result["status"] == "completed"

# Test 2: Check balance
balance = client.get_balance()
assert balance >= 0

# Test 3: Create escrow
escrow = await client.create_escrow("task-123", 5.00, "0xworker...")
assert escrow["status"] == "locked"

# Test 4: Release escrow
release = await client.release_escrow("task-123-escrow", "0xworker...", 5.00)
assert release["status"] == "completed"
```

## Dependencies
```
# requirements.txt additions
web3>=6.0.0
eth-account>=0.10.0
```
