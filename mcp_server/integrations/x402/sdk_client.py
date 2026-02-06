"""
x402 SDK Integration for Execution Market (NOW-202)

Uses the official uvd-x402-sdk for payment processing with the Ultravioleta DAO facilitator.
This module replaces the custom client implementation with the standardized SDK.

The SDK provides:
- Gasless EIP-3009 payments
- Automatic facilitator integration
- FastAPI native support
- Multi-network support (18+ chains)

Facilitator: https://facilitator.ultravioletadao.xyz
"""

import os
import json
import logging
import secrets
import base64
from decimal import Decimal
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone

from eth_account import Account
from fastapi import FastAPI, Request, Response, Depends
from pydantic import BaseModel

# Import from uvd-x402-sdk
try:
    from uvd_x402_sdk import (
        X402Client as SDKClient,
        X402Config,
        PaymentResult as SDKPaymentResult,
    )
    from uvd_x402_sdk.integrations import FastAPIX402
    from uvd_x402_sdk.exceptions import (
        X402Error as SDKError,
        PaymentRequiredError,
        PaymentVerificationError,
        PaymentSettlementError,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    # Provide stubs for type hints
    SDKClient = None
    X402Config = None
    SDKPaymentResult = None
    FastAPIX402 = None
    SDKError = Exception
    PaymentRequiredError = Exception
    PaymentVerificationError = Exception
    PaymentSettlementError = Exception

# EscrowClient for gasless refunds via facilitator
try:
    from uvd_x402_sdk.escrow import EscrowClient as SDKEscrowClient
    ESCROW_SDK_AVAILABLE = True
except ImportError:
    SDKEscrowClient = None
    ESCROW_SDK_AVAILABLE = False


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Default facilitator URL (Ultravioleta DAO production)
FACILITATOR_URL = os.environ.get(
    "X402_FACILITATOR_URL",
    "https://facilitator.ultravioletadao.xyz"
)

# Execution Market treasury address for fee collection
EM_TREASURY = os.environ.get(
    "EM_TREASURY_ADDRESS",
    "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"
)

# Default network for payments
DEFAULT_NETWORK = os.environ.get("X402_NETWORK", "base")

# Escrow service URL (for gasless refunds via facilitator)
ESCROW_URL = os.environ.get(
    "X402_ESCROW_URL",
    "https://escrow.ultravioletadao.xyz"
)

# API key for escrow service (reuse main API key if not set separately)
ESCROW_API_KEY = os.environ.get("X402_ESCROW_API_KEY", os.environ.get("X402_API_KEY"))

# Platform fee percentage
PLATFORM_FEE_PERCENT = Decimal(os.environ.get("EM_PLATFORM_FEE", "0.08"))


# =============================================================================
# Payment Models
# =============================================================================

class EMPaymentConfig(BaseModel):
    """Configuration for Execution Market payment endpoints."""
    recipient_address: str
    description: str = "Execution Market task payment"
    network: str = DEFAULT_NETWORK
    resource: Optional[str] = None


class TaskPaymentResult(BaseModel):
    """Result of a task payment verification."""
    success: bool
    payer_address: str
    amount_usd: Decimal
    tx_hash: Optional[str] = None
    network: str
    timestamp: datetime
    task_id: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# SDK Wrapper Class
# =============================================================================

class EMX402SDK:
    """
    Wrapper around uvd-x402-sdk for Execution Market-specific functionality.

    Provides:
    - FastAPI integration for payment-gated endpoints
    - Task-specific payment processing
    - Fee calculation and collection
    - Multi-network support
    """

    def __init__(
        self,
        app: Optional[FastAPI] = None,
        recipient_address: Optional[str] = None,
        facilitator_url: Optional[str] = None,
        network: str = DEFAULT_NETWORK,
    ):
        """
        Initialize Execution Market x402 SDK wrapper.

        Args:
            app: FastAPI application (for automatic integration)
            recipient_address: Default recipient for payments (treasury)
            facilitator_url: Facilitator URL (default: Ultravioleta DAO)
            network: Default network for payments
        """
        if not SDK_AVAILABLE:
            raise ImportError(
                "uvd-x402-sdk not installed. "
                "Install with: pip install uvd-x402-sdk[fastapi]"
            )

        self.recipient_address = recipient_address or EM_TREASURY
        self.facilitator_url = facilitator_url or FACILITATOR_URL
        self.network = network

        # Create SDK config
        self.config = X402Config(
            recipient_evm=self.recipient_address,
            facilitator_url=self.facilitator_url,
            supported_networks=[network],
        )

        # Create SDK client
        self.client = SDKClient(config=self.config)

        # FastAPI integration (if app provided)
        self.fastapi_x402: Optional[FastAPIX402] = None
        if app:
            self._setup_fastapi(app)

        logger.info(
            "EMX402SDK initialized: facilitator=%s, network=%s",
            self.facilitator_url,
            self.network
        )

    def _setup_fastapi(self, app: FastAPI) -> None:
        """Setup FastAPI integration with x402."""
        self.fastapi_x402 = FastAPIX402(
            app,
            recipient_address=self.recipient_address,
            facilitator_url=self.facilitator_url,
        )
        logger.info("FastAPI x402 integration enabled")

    # =========================================================================
    # Payment Dependencies
    # =========================================================================

    def require_payment(
        self,
        amount_usd: str,
        description: Optional[str] = None,
        network: Optional[str] = None,
    ) -> Callable:
        """
        FastAPI dependency that requires payment for endpoint access.

        Usage:
            @app.get("/api/premium")
            async def premium(
                payment: PaymentResult = Depends(x402.require_payment(amount_usd="5.00"))
            ):
                return {"payer": payment.payer_address}

        Args:
            amount_usd: Payment amount in USD (string for precision)
            description: Payment description
            network: Network for payment (default: configured network)

        Returns:
            FastAPI dependency function
        """
        if not self.fastapi_x402:
            raise RuntimeError("FastAPI integration not configured")

        return self.fastapi_x402.require_payment(
            amount_usd=amount_usd,
            description=description or "Execution Market payment",
            network=network or self.network,
        )

    def optional_payment(
        self,
        amount_usd: str,
        description: Optional[str] = None,
    ) -> Callable:
        """
        FastAPI dependency for optional payments.

        Returns payment result if provided, None otherwise.
        """
        if not self.fastapi_x402:
            raise RuntimeError("FastAPI integration not configured")

        return self.fastapi_x402.optional_payment(
            amount_usd=amount_usd,
            description=description or "Execution Market optional payment",
        )

    # =========================================================================
    # EIP-3009 Signing for Worker Disbursement
    # =========================================================================

    # USDC EIP-712 domain on Base
    USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    USDC_DOMAIN = {
        "name": "USD Coin",
        "version": "2",
        "chainId": 8453,
        "verifyingContract": USDC_ADDRESS,
    }
    TRANSFER_WITH_AUTH_TYPES = {
        "TransferWithAuthorization": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"},
        ],
    }

    def _get_agent_account(self) -> Account:
        """Get the agent wallet Account from WALLET_PRIVATE_KEY."""
        pk = os.environ.get("WALLET_PRIVATE_KEY")
        if not pk:
            raise RuntimeError("WALLET_PRIVATE_KEY not set — cannot sign disbursement")
        return Account.from_key(pk)

    def _sign_eip3009_transfer(
        self,
        to_address: str,
        amount_usdc: Decimal,
        valid_for_seconds: int = 3600,
    ) -> Dict[str, Any]:
        """
        Sign an EIP-3009 TransferWithAuthorization for USDC on Base.

        Returns dict with 'authorization' and 'signature' fields.
        """
        account = self._get_agent_account()
        value = int(amount_usdc * Decimal(10 ** 6))
        now = int(datetime.now(timezone.utc).timestamp())
        nonce = "0x" + secrets.token_hex(32)

        message = {
            "from": account.address,
            "to": to_address,
            "value": value,
            "validAfter": 0,
            "validBefore": now + valid_for_seconds,
            "nonce": nonce,
        }

        # Sign EIP-712 typed data
        signed = account.sign_typed_data(
            domain_data=self.USDC_DOMAIN,
            message_types=self.TRANSFER_WITH_AUTH_TYPES,
            message_data=message,
        )

        authorization = {
            "from": account.address,
            "to": to_address,
            "value": str(value),
            "validAfter": "0",
            "validBefore": str(now + valid_for_seconds),
            "nonce": nonce,
        }

        return {
            "authorization": authorization,
            "signature": signed.signature.hex() if hasattr(signed.signature, 'hex') else hex(signed.signature),
        }

    def _build_x402_header(self, auth_data: Dict[str, Any]) -> str:
        """Build a base64-encoded X-Payment header from authorization + signature."""
        payload = {
            "x402Version": 1,
            "scheme": "exact",
            "network": "base",
            "payload": {
                "signature": auth_data["signature"],
                "authorization": auth_data["authorization"],
            },
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()

    def _settle_signed_auth(
        self,
        auth_data: Dict[str, Any],
        amount_usdc: Decimal,
        pay_to: str,
    ) -> Dict[str, Any]:
        """
        Settle a locally-signed EIP-3009 auth via direct HTTP to the facilitator.

        Used for worker disbursement and fee collection where the platform wallet
        signs NEW auths (not the agent's original). For settling the agent's original
        auth, use self.client.settle_payment() (SDK v0.8.1+ with pay_to support).
        """
        import httpx

        header = self._build_x402_header(auth_data)
        payload_data = json.loads(base64.b64decode(header))

        value_wei = int(amount_usdc * Decimal(10 ** 6))
        settle_request = {
            "x402Version": 1,
            "paymentPayload": payload_data,
            "paymentRequirements": {
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": str(value_wei),
                "resource": "https://api.execution.market/api/v1/tasks",
                "description": "Execution Market payment",
                "mimeType": "application/json",
                "payTo": pay_to,
                "maxTimeoutSeconds": 300,
                "asset": self.USDC_ADDRESS,
                "extra": {"name": "USD Coin", "version": "2"},
            },
        }

        resp = httpx.post(
            f"{self.facilitator_url}/settle",
            json=settle_request,
            timeout=30.0,
        )

        if resp.status_code != 200:
            error_body = resp.text[:500]
            logger.error("Facilitator settle HTTP %d: %s", resp.status_code, error_body)
            return {"success": False, "error": f"Facilitator HTTP {resp.status_code}: {error_body}"}

        data = resp.json()
        tx_hash = data.get("transaction") or data.get("tx_hash") or data.get("transaction_hash")

        return {
            "success": data.get("success", bool(tx_hash)),
            "tx_hash": tx_hash,
            "payer": data.get("payer"),
        }

    async def disburse_to_worker(
        self,
        worker_address: str,
        amount_usdc: Decimal,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        Sign a new EIP-3009 auth from agent wallet to worker and settle via facilitator.

        This is GASLESS — the facilitator pays gas on behalf of the agent.
        """
        try:
            auth = self._sign_eip3009_transfer(
                to_address=worker_address,
                amount_usdc=amount_usdc,
            )
            result = self._settle_signed_auth(auth, amount_usdc, pay_to=worker_address)

            if result.get("success"):
                logger.info(
                    "Worker disbursement OK: task=%s, worker=%s, amount=%.6f, tx=%s",
                    task_id, worker_address[:10], float(amount_usdc),
                    result.get("tx_hash"),
                )
            else:
                logger.error(
                    "Worker disbursement FAILED: task=%s, error=%s",
                    task_id, result.get("error"),
                )

            return {
                **result,
                "recipient": worker_address,
                "amount": float(amount_usdc),
                "type": "worker_payout",
            }

        except Exception as e:
            logger.error("Worker disbursement error: %s", e)
            return {"success": False, "error": str(e), "type": "worker_payout"}

    async def collect_platform_fee(
        self,
        fee_amount: Decimal,
        task_id: str,
        treasury_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sign a new EIP-3009 auth from agent wallet to treasury for the platform fee.

        This is GASLESS — the facilitator pays gas on behalf of the agent.
        """
        treasury = treasury_address or EM_TREASURY
        if not treasury or treasury == "0x0000000000000000000000000000000000000000":
            logger.warning("No treasury address configured — skipping fee collection for task %s", task_id)
            return {"success": True, "tx_hash": None, "skipped": True, "type": "platform_fee"}

        if fee_amount <= 0:
            logger.info("Fee is zero for task %s — skipping fee collection", task_id)
            return {"success": True, "tx_hash": None, "skipped": True, "type": "platform_fee"}

        try:
            auth = self._sign_eip3009_transfer(
                to_address=treasury,
                amount_usdc=fee_amount,
            )
            result = self._settle_signed_auth(auth, fee_amount, pay_to=treasury)

            if result.get("success"):
                logger.info(
                    "Fee collection OK: task=%s, fee=%.6f, tx=%s",
                    task_id, float(fee_amount), result.get("tx_hash"),
                )
            else:
                logger.warning(
                    "Fee collection FAILED (non-blocking): task=%s, error=%s",
                    task_id, result.get("error"),
                )

            return {
                **result,
                "recipient": treasury,
                "amount": float(fee_amount),
                "type": "platform_fee",
            }

        except Exception as e:
            logger.warning("Fee collection error (non-blocking): %s", e)
            return {"success": False, "error": str(e), "type": "platform_fee"}

    # =========================================================================
    # Task Payment Processing
    # =========================================================================

    @staticmethod
    def _extract_settlement_tx_hash(settle_response: Any) -> Optional[str]:
        """
        Extract tx hash from SDK settle response across SDK versions.

        Handles both model methods (`get_transaction_hash`) and direct attrs
        that can vary between releases (`transaction`, `tx_hash`,
        `transaction_hash`).
        """
        if settle_response is None:
            return None

        tx_candidates = []

        getter = getattr(settle_response, "get_transaction_hash", None)
        if callable(getter):
            try:
                tx_candidates.append(getter())
            except Exception:
                pass

        for attr in ("tx_hash", "transaction_hash", "transaction", "hash"):
            try:
                tx_candidates.append(getattr(settle_response, attr, None))
            except Exception:
                continue

        for value in tx_candidates:
            if isinstance(value, str) and value.startswith("0x") and len(value) == 66:
                return value

        return None

    async def verify_task_payment(
        self,
        task_id: str,
        payment_header: str,
        expected_amount: Decimal,
        worker_address: str,
    ) -> TaskPaymentResult:
        """
        Verify a payment for task completion.

        Args:
            task_id: Task identifier
            payment_header: x402 payment header from request
            expected_amount: Expected payment amount
            worker_address: Worker's wallet address (recipient)

        Returns:
            TaskPaymentResult with verification details
        """
        try:
            # Extract and validate payment payload from X-Payment header
            payload = self.client.extract_payload(payment_header)

            # Get payer address from the payload
            payer_address, payer_network = self.client.get_payer_address(payment_header)

            # Verify with facilitator (validates signature on-chain without settling)
            verify_response = self.client.verify_payment(payload, expected_amount)

            if not verify_response.isValid:
                return TaskPaymentResult(
                    success=False,
                    payer_address=verify_response.payer or payer_address or "unknown",
                    amount_usd=expected_amount,
                    network=payload.network,
                    timestamp=datetime.now(timezone.utc),
                    task_id=task_id,
                    error=verify_response.invalidReason or verify_response.message or "Payment verification failed",
                )

            return TaskPaymentResult(
                success=True,
                payer_address=verify_response.payer or payer_address,
                amount_usd=expected_amount,
                tx_hash=None,  # No tx_hash until settlement
                network=payload.network,
                timestamp=datetime.now(timezone.utc),
                task_id=task_id,
            )

        except Exception as e:
            logger.error("Task payment verification failed: %s", str(e))
            return TaskPaymentResult(
                success=False,
                payer_address="unknown",
                amount_usd=Decimal("0"),
                network=self.network,
                timestamp=datetime.now(timezone.utc),
                task_id=task_id,
                error=str(e),
            )

    async def settle_task_payment(
        self,
        task_id: str,
        payment_header: str,
        worker_address: str,
        bounty_amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Settle a task payment: collect from agent, then disburse to worker.

        Three-step flow:
        0. Settle agent's original EIP-3009 auth (agent → platform wallet)
        1. Sign new auth: platform wallet → worker (bounty minus fee)
        2. Sign new auth: platform wallet → treasury (platform fee)

        Step 0 is skipped when agent wallet == platform wallet (test scenario).
        All settlements are GASLESS via the Ultravioleta facilitator.
        """
        try:
            # Step 0: Settle agent's original auth to collect USDC
            agent_settle_tx = None
            try:
                payer_address, _ = self.client.get_payer_address(payment_header)
                platform_address = self._get_agent_account().address

                if payer_address.lower() != platform_address.lower():
                    # Real external agent — settle their auth to collect payment
                    payload = self.client.extract_payload(payment_header)
                    settle_resp = self.client.settle_payment(payload, bounty_amount)
                    agent_settle_tx = self._extract_settlement_tx_hash(settle_resp)
                    logger.info(
                        "Agent auth settled: task=%s, agent=%s, tx=%s",
                        task_id, payer_address[:10], agent_settle_tx,
                    )
                else:
                    logger.info(
                        "Skipping agent auth settlement for task %s (agent == platform wallet)",
                        task_id,
                    )
            except Exception as e:
                # Log but continue — agent may have already paid, or auth expired
                logger.warning(
                    "Agent auth settlement failed for task %s (continuing): %s",
                    task_id, e,
                )

            # Calculate fee breakdown
            platform_fee = (bounty_amount * PLATFORM_FEE_PERCENT).quantize(Decimal("0.01"))
            worker_net = bounty_amount - platform_fee

            # Step 1: Pay the worker
            worker_result = await self.disburse_to_worker(
                worker_address=worker_address,
                amount_usdc=worker_net,
                task_id=task_id,
            )

            worker_tx = worker_result.get("tx_hash")
            if not worker_result.get("success") or not worker_tx:
                # Worker payment failed — don't collect fee either
                return {
                    "success": False,
                    "task_id": task_id,
                    "error": worker_result.get("error", "Worker disbursement failed"),
                    "agent_settle_tx": agent_settle_tx,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Step 2: Collect platform fee (non-blocking — worker already paid)
            fee_result = await self.collect_platform_fee(
                fee_amount=platform_fee,
                task_id=task_id,
            )

            fee_tx = fee_result.get("tx_hash")
            if not fee_result.get("success"):
                logger.warning(
                    "Worker paid but fee collection failed for task %s: %s",
                    task_id, fee_result.get("error"),
                )

            return {
                "success": True,
                "task_id": task_id,
                "worker_address": worker_address,
                "gross_amount": float(bounty_amount),
                "platform_fee": float(platform_fee),
                "net_to_worker": float(worker_net),
                "tx_hash": worker_tx,
                "fee_tx_hash": fee_tx,
                "agent_settle_tx": agent_settle_tx,
                "network": "base",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error("Task payment settlement failed: %s", str(e))
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def refund_task_payment(
        self,
        task_id: str,
        escrow_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a task payment back to the agent via the facilitator (gasless).

        Uses the uvd-x402-sdk EscrowClient.request_refund() which calls the
        escrow service. The facilitator pays gas — the agent recovers USDC
        without spending anything on gas.

        Falls back to direct contract call (x402r_escrow) only if the SDK
        EscrowClient is not available.

        Args:
            task_id: Task identifier
            escrow_id: Escrow/deposit identifier
            reason: Optional refund reason for logs/audit

        Returns:
            Dict with refund details
        """
        if not escrow_id:
            return {
                "success": False,
                "task_id": task_id,
                "escrow_id": escrow_id,
                "error": "Missing escrow_id",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Primary path: gasless refund via EscrowClient (facilitator pays gas)
        if ESCROW_SDK_AVAILABLE:
            try:
                async with SDKEscrowClient(
                    base_url=ESCROW_URL,
                    api_key=ESCROW_API_KEY,
                ) as escrow_client:
                    refund_result = await escrow_client.request_refund(
                        escrow_id=escrow_id,
                        reason=reason or f"Task {task_id} cancelled",
                    )

                tx_hash = getattr(refund_result, "transaction_hash", None)

                logger.info(
                    "Gasless refund succeeded: task=%s, escrow=%s, tx=%s, status=%s",
                    task_id, escrow_id, tx_hash, refund_result.status,
                )

                return {
                    "success": True,
                    "task_id": task_id,
                    "escrow_id": escrow_id,
                    "refund_id": refund_result.id,
                    "tx_hash": tx_hash,
                    "status": refund_result.status.value if hasattr(refund_result.status, "value") else str(refund_result.status),
                    "amount_requested": getattr(refund_result, "amount_requested", None),
                    "reason": reason,
                    "method": "facilitator",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as e:
                logger.warning(
                    "Gasless refund failed for task %s (escrow %s), "
                    "falling back to direct contract: %s",
                    task_id, escrow_id, str(e),
                )
                # Fall through to legacy path below

        # Legacy fallback: direct contract call (agent pays gas)
        try:
            from .x402r_escrow import refund_payment
        except Exception:
            return {
                "success": False,
                "task_id": task_id,
                "escrow_id": escrow_id,
                "error": "Neither EscrowClient nor x402r refund integration available",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        try:
            logger.warning(
                "Using legacy direct-contract refund for task %s (agent pays gas)",
                task_id,
            )
            refund_result = await refund_payment(deposit_id=escrow_id)
            amount = getattr(refund_result, "amount", None)
            return {
                "success": bool(getattr(refund_result, "success", False)),
                "task_id": task_id,
                "escrow_id": escrow_id,
                "tx_hash": getattr(refund_result, "tx_hash", None),
                "payer": getattr(refund_result, "payer", None),
                "amount": str(amount) if amount is not None else None,
                "reason": reason,
                "method": "direct_contract",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Task payment refund failed (all paths): %s", str(e))
            return {
                "success": False,
                "task_id": task_id,
                "escrow_id": escrow_id,
                "error": str(e),
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check x402 SDK and facilitator health.

        Returns:
            Dict with health status
        """
        try:
            import httpx
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{self.facilitator_url}/health",
                    timeout=10.0,
                )
                facilitator_health = response.json() if response.status_code == 200 else {}

            return {
                "sdk_available": True,
                "facilitator_url": self.facilitator_url,
                "facilitator_healthy": response.status_code == 200,
                "facilitator_status": facilitator_health.get("status", "unknown"),
                "escrow_url": ESCROW_URL,
                "escrow_sdk_available": ESCROW_SDK_AVAILABLE,
                "network": self.network,
                "recipient": self.recipient_address,
            }
        except Exception as e:
            return {
                "sdk_available": True,
                "facilitator_url": self.facilitator_url,
                "facilitator_healthy": False,
                "error": str(e),
                "network": self.network,
            }


# =============================================================================
# Module-Level Functions
# =============================================================================

_default_sdk: Optional[EMX402SDK] = None


def get_sdk() -> EMX402SDK:
    """Get or create the default EMX402SDK instance."""
    global _default_sdk
    if _default_sdk is None:
        _default_sdk = EMX402SDK()
    return _default_sdk


def setup_x402_for_app(
    app: FastAPI,
    recipient_address: Optional[str] = None,
    network: str = DEFAULT_NETWORK,
) -> EMX402SDK:
    """
    Setup x402 integration for a FastAPI app.

    Usage:
        from integrations.x402.sdk_client import setup_x402_for_app

        app = FastAPI()
        x402 = setup_x402_for_app(app, recipient_address="0x...")

        @app.get("/paid")
        async def paid_endpoint(payment = Depends(x402.require_payment("1.00"))):
            return {"paid_by": payment.payer_address}

    Args:
        app: FastAPI application
        recipient_address: Payment recipient address
        network: Default network

    Returns:
        Configured EMX402SDK instance
    """
    global _default_sdk
    _default_sdk = EMX402SDK(
        app=app,
        recipient_address=recipient_address,
        network=network,
    )
    return _default_sdk


async def verify_x402_payment(
    request: Request,
    expected_amount: Decimal,
) -> TaskPaymentResult:
    """
    Verify x402 payment from request headers.

    Args:
        request: FastAPI request object
        expected_amount: Expected payment amount

    Returns:
        TaskPaymentResult
    """
    sdk = get_sdk()

    # Get x402 payment header
    payment_header = request.headers.get("X-Payment") or request.headers.get("x-payment")

    if not payment_header:
        return TaskPaymentResult(
            success=False,
            payer_address="none",
            amount_usd=Decimal("0"),
            network=sdk.network,
            timestamp=datetime.now(timezone.utc),
            error="No X-Payment header provided",
        )

    return await sdk.verify_task_payment(
        task_id="direct",
        payment_header=payment_header,
        expected_amount=expected_amount,
        worker_address=sdk.recipient_address,
    )


# =============================================================================
# Check SDK Availability
# =============================================================================

def check_sdk_available() -> bool:
    """Check if uvd-x402-sdk is available."""
    return SDK_AVAILABLE


def get_sdk_info() -> Dict[str, Any]:
    """Get information about SDK installation."""
    if not SDK_AVAILABLE:
        return {
            "available": False,
            "error": "uvd-x402-sdk not installed",
            "install": "pip install uvd-x402-sdk[fastapi]",
        }

    try:
        import uvd_x402_sdk
        return {
            "available": True,
            "version": getattr(uvd_x402_sdk, "__version__", "unknown"),
            "facilitator_url": FACILITATOR_URL,
        }
    except Exception as e:
        return {
            "available": True,
            "error": str(e),
        }
