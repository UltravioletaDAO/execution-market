"""
Escrow API Routes

Provides REST endpoints for escrow configuration and refunds.
All payments go through the x402 SDK + Ultravioleta Facilitator (gasless).
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from pydantic import BaseModel, Field

# x402 SDK (facilitator-backed, gasless)
try:
    from integrations.x402.sdk_client import get_sdk, SDK_AVAILABLE

    X402_SDK_AVAILABLE = SDK_AVAILABLE
except ImportError:
    X402_SDK_AVAILABLE = False

# x402r direct escrow (REMOVED — all payments go through SDK + facilitator now)

from .auth import verify_api_key, APIKeyData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/escrow", tags=["Escrow"])


# =============================================================================
# MODELS
# =============================================================================


class EscrowConfigResponse(BaseModel):
    """x402r escrow configuration."""

    available: bool
    network: str
    chain_id: int
    factory_address: str
    escrow_address: str
    usdc_address: str
    merchant_address: Optional[str] = None
    proxy_address: Optional[str] = None
    signer_address: Optional[str] = None


class DepositResponse(BaseModel):
    """Information about a deposit in escrow."""

    deposit_id: str
    payer: str
    merchant: str
    amount: str = Field(description="Amount in USDC")
    token: str
    state: str = Field(description="NON_EXISTENT, IN_ESCROW, RELEASED, or REFUNDED")
    created_at: str


class BalanceResponse(BaseModel):
    """Merchant balance in escrow."""

    merchant: str
    balance_usdc: str
    network: str


class ReleaseRequest(BaseModel):
    """Request to release funds from escrow."""

    deposit_id: str = Field(
        ...,
        min_length=64,
        max_length=66,
        description="Deposit ID (bytes32 hex, with or without 0x prefix)",
    )
    worker_address: str = Field(
        ..., min_length=40, max_length=42, description="Worker's wallet address"
    )
    amount: str = Field(..., description="Amount to release in USDC (e.g., '10.00')")


class RefundRequest(BaseModel):
    """Request to refund funds to original payer."""

    deposit_id: str = Field(
        ...,
        min_length=64,
        max_length=66,
        description="Deposit ID (bytes32 hex, with or without 0x prefix)",
    )


class ReleaseResponse(BaseModel):
    """Result of release operation."""

    success: bool
    tx_hash: Optional[str] = None
    deposit_id: str
    recipient: str
    amount: str
    error: Optional[str] = None


class RefundResponse(BaseModel):
    """Result of refund operation."""

    success: bool
    tx_hash: Optional[str] = None
    deposit_id: str
    payer: str
    amount: str
    error: Optional[str] = None


class PaymentExtensionResponse(BaseModel):
    """x402r payment extension for agents."""

    refund: Dict[str, Any]


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================


@router.get(
    "/config",
    response_model=EscrowConfigResponse,
    responses={
        200: {"description": "Escrow configuration"},
    },
)
async def get_escrow_config() -> EscrowConfigResponse:
    """
    Get x402r escrow configuration.

    Returns contract addresses and current merchant setup.
    Useful for agents to know where to send payments.
    """
    # Config is now static — all payments go through SDK + facilitator
    return EscrowConfigResponse(
        available=X402_SDK_AVAILABLE,
        network="base",
        chain_id=8453,
        factory_address="0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814",
        escrow_address="0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC",
        usdc_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )


@router.get(
    "/payment-extension",
    response_model=PaymentExtensionResponse,
    responses={
        200: {"description": "Payment extension for x402"},
        503: {"description": "Escrow not configured"},
    },
)
async def get_payment_extension() -> PaymentExtensionResponse:
    """
    Get the x402r refund extension for payment payloads.

    Agents should include this extension when making payments to Execution Market
    to enable trustless refunds via the escrow contract.

    Example usage in x402 payment:
    ```json
    {
      "paymentPayload": {
        "x402Version": 2,
        "accepted": {
          "payTo": "<proxy_address>",
          "amount": "10000000"
        },
        "extensions": { ... response from this endpoint ... }
      }
    }
    ```
    """
    # Payment extensions are no longer needed — SDK + facilitator handles everything
    raise HTTPException(
        status_code=410,
        detail="Payment extensions deprecated. Use x402 SDK + facilitator for all payments.",
    )


@router.get(
    "/deposits/{deposit_id}",
    response_model=DepositResponse,
    responses={
        200: {"description": "Deposit info"},
        404: {"description": "Deposit not found"},
        503: {"description": "Escrow not available"},
    },
)
async def get_deposit(
    deposit_id: str = Path(
        ..., min_length=64, max_length=66, description="Deposit ID (bytes32 hex)"
    ),
) -> DepositResponse:
    """
    Get information about a deposit in escrow.

    Returns the deposit state, payer, amount, and timestamp.
    """
    # Direct contract queries removed — deposits are tracked in the escrows DB table
    raise HTTPException(
        status_code=410,
        detail="Direct deposit lookup deprecated. Use /api/v1/tasks/{id} for escrow status.",
    )


@router.get(
    "/balance",
    response_model=BalanceResponse,
    responses={
        200: {"description": "Merchant balance"},
        503: {"description": "Escrow not available"},
    },
)
async def get_merchant_balance(
    merchant: Optional[str] = Query(
        None, description="Merchant address (defaults to Execution Market's address)"
    ),
) -> BalanceResponse:
    """
    Get the USDC balance held in escrow for a merchant.

    If no merchant address is provided, returns Execution Market's balance.
    """
    # Direct contract balance queries removed — use block explorer instead
    raise HTTPException(
        status_code=410,
        detail="Direct balance lookup deprecated. Check balances via block explorer.",
    )


# =============================================================================
# ADMIN ENDPOINTS (Authenticated)
# =============================================================================


@router.post(
    "/release",
    response_model=ReleaseResponse,
    responses={
        200: {"description": "Release executed"},
        401: {"description": "Unauthorized"},
        400: {"description": "Invalid request"},
        503: {"description": "Escrow not available"},
    },
    deprecated=True,
)
async def release_to_worker(
    request: ReleaseRequest, api_key: APIKeyData = Depends(verify_api_key)
) -> ReleaseResponse:
    """
    Release escrowed funds to a worker.

    **Deprecated**: Use `POST /api/v1/submissions/{id}/approve` instead.
    The approval endpoint handles settlement via the x402 facilitator (gasless).

    This legacy endpoint calls the escrow contract directly (agent pays gas).
    """
    raise HTTPException(
        status_code=410,
        detail="Direct contract release removed. Use POST /api/v1/submissions/{id}/approve instead.",
    )


@router.post(
    "/refund",
    response_model=RefundResponse,
    responses={
        200: {"description": "Refund executed"},
        401: {"description": "Unauthorized"},
        503: {"description": "Escrow not available"},
    },
)
async def refund_to_agent(
    request: RefundRequest, api_key: APIKeyData = Depends(verify_api_key)
) -> RefundResponse:
    """
    Refund escrowed funds to the original payer (agent).

    **Requires authentication**: Only the Execution Market backend can refund.

    Uses the x402 SDK + facilitator (gasless) as the primary path.
    Falls back to direct contract call only if the SDK is unavailable.

    This is called when:
    1. Task is cancelled
    2. Dispute resolved in agent's favor
    3. No worker accepted the task before deadline
    """
    if not X402_SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="x402 SDK not available")

    try:
        sdk = get_sdk()
        result = await sdk.refund_task_payment(
            task_id=f"escrow-{request.deposit_id[:16]}",
            escrow_id=request.deposit_id,
            reason=f"Refund requested by agent {api_key.agent_id}",
        )

        tx_hash = result.get("tx_hash")
        success = result.get("success", False)
        method = result.get("method", "facilitator")

        logger.info(
            "Refund via %s by %s: deposit=%s, success=%s, tx=%s",
            method,
            api_key.agent_id,
            request.deposit_id[:16],
            success,
            tx_hash,
        )

        return RefundResponse(
            success=success,
            tx_hash=tx_hash,
            deposit_id=request.deposit_id,
            payer=result.get("payer", ""),
            amount=str(result.get("amount_requested", result.get("amount", "0"))),
            error=result.get("error"),
        )
    except Exception as sdk_err:
        logger.error(
            "SDK refund failed for deposit %s: %s",
            request.deposit_id[:16],
            sdk_err,
        )
        raise HTTPException(status_code=500, detail=f"Refund failed: {sdk_err}")
