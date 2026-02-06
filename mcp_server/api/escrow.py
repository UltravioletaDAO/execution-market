"""
x402r Escrow API Routes

Provides REST endpoints for escrow management.
Uses the x402 SDK + Ultravioleta Facilitator (gasless) as the primary path.
Falls back to direct contract calls only when the SDK is unavailable.

Contracts (Base Mainnet):
- Factory: 0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814
- Escrow: 0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from pydantic import BaseModel, Field

# x402 SDK (facilitator-backed, gasless) — PRIMARY path
try:
    from integrations.x402.sdk_client import get_sdk, SDK_AVAILABLE
    X402_SDK_AVAILABLE = SDK_AVAILABLE
except ImportError:
    X402_SDK_AVAILABLE = False

# x402r direct escrow client — FALLBACK only
try:
    from integrations.x402 import (
        get_x402r_escrow,
        release_payment,
        refund_payment,
        get_deposit_info,
        X402R_CONTRACTS,
        DepositState,
    )
    X402R_AVAILABLE = True
except ImportError:
    X402R_AVAILABLE = False
    DepositState = None

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
        description="Deposit ID (bytes32 hex, with or without 0x prefix)"
    )
    worker_address: str = Field(
        ...,
        min_length=40,
        max_length=42,
        description="Worker's wallet address"
    )
    amount: str = Field(
        ...,
        description="Amount to release in USDC (e.g., '10.00')"
    )


class RefundRequest(BaseModel):
    """Request to refund funds to original payer."""
    deposit_id: str = Field(
        ...,
        min_length=64,
        max_length=66,
        description="Deposit ID (bytes32 hex, with or without 0x prefix)"
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
    }
)
async def get_escrow_config() -> EscrowConfigResponse:
    """
    Get x402r escrow configuration.

    Returns contract addresses and current merchant setup.
    Useful for agents to know where to send payments.
    """
    if not X402R_AVAILABLE:
        return EscrowConfigResponse(
            available=False,
            network="base",
            chain_id=8453,
            factory_address="0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814",
            escrow_address="0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC",
            usdc_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        )

    try:
        escrow = get_x402r_escrow()
        config = escrow.get_config()

        return EscrowConfigResponse(
            available=True,
            network=config["network"],
            chain_id=config["chain_id"],
            factory_address=config["factory"],
            escrow_address=config["escrow"],
            usdc_address=config["usdc"],
            merchant_address=config.get("merchant"),
            proxy_address=config.get("proxy"),
            signer_address=config.get("account"),
        )
    except Exception as e:
        logger.error("Failed to get escrow config: %s", e)
        return EscrowConfigResponse(
            available=False,
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
    }
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
    if not X402R_AVAILABLE:
        raise HTTPException(status_code=503, detail="x402r escrow not available")

    try:
        escrow = get_x402r_escrow()
        extension = escrow.get_payment_extension()
        return PaymentExtensionResponse(**extension)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Failed to get payment extension: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate payment extension")


@router.get(
    "/deposits/{deposit_id}",
    response_model=DepositResponse,
    responses={
        200: {"description": "Deposit info"},
        404: {"description": "Deposit not found"},
        503: {"description": "Escrow not available"},
    }
)
async def get_deposit(
    deposit_id: str = Path(
        ...,
        min_length=64,
        max_length=66,
        description="Deposit ID (bytes32 hex)"
    )
) -> DepositResponse:
    """
    Get information about a deposit in escrow.

    Returns the deposit state, payer, amount, and timestamp.
    """
    if not X402R_AVAILABLE:
        raise HTTPException(status_code=503, detail="x402r escrow not available")

    deposit = get_deposit_info(deposit_id)
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    return DepositResponse(
        deposit_id=deposit.deposit_id,
        payer=deposit.payer,
        merchant=deposit.merchant,
        amount=str(deposit.amount),
        token=deposit.token,
        state=deposit.state.name,
        created_at=deposit.created_at.isoformat(),
    )


@router.get(
    "/balance",
    response_model=BalanceResponse,
    responses={
        200: {"description": "Merchant balance"},
        503: {"description": "Escrow not available"},
    }
)
async def get_merchant_balance(
    merchant: Optional[str] = Query(
        None,
        description="Merchant address (defaults to Execution Market's address)"
    )
) -> BalanceResponse:
    """
    Get the USDC balance held in escrow for a merchant.

    If no merchant address is provided, returns Execution Market's balance.
    """
    if not X402R_AVAILABLE:
        raise HTTPException(status_code=503, detail="x402r escrow not available")

    try:
        escrow = get_x402r_escrow()
        balance = escrow.get_merchant_balance(merchant)
        config = escrow.get_config()

        return BalanceResponse(
            merchant=merchant or config.get("merchant", ""),
            balance_usdc=str(balance),
            network=config["network"],
        )
    except Exception as e:
        logger.error("Failed to get balance: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get balance")


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
    request: ReleaseRequest,
    api_key: APIKeyData = Depends(verify_api_key)
) -> ReleaseResponse:
    """
    Release escrowed funds to a worker.

    **Deprecated**: Use `POST /api/v1/submissions/{id}/approve` instead.
    The approval endpoint handles settlement via the x402 facilitator (gasless).

    This legacy endpoint calls the escrow contract directly (agent pays gas).
    """
    if not X402R_AVAILABLE:
        raise HTTPException(status_code=503, detail="x402r escrow not available")

    logger.warning(
        "DEPRECATED: Direct contract release by %s — use /api/v1/submissions/{id}/approve instead",
        api_key.agent_id,
    )

    try:
        amount = Decimal(request.amount)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount format")

    result = await release_payment(
        deposit_id=request.deposit_id,
        worker_address=request.worker_address,
        amount=amount,
    )

    logger.info(
        "Release request by %s: deposit=%s, worker=%s, amount=%s, success=%s (DIRECT CONTRACT)",
        api_key.agent_id, request.deposit_id[:16], request.worker_address[:10],
        request.amount, result.success
    )

    return ReleaseResponse(
        success=result.success,
        tx_hash=result.tx_hash,
        deposit_id=result.deposit_id,
        recipient=result.recipient,
        amount=str(result.amount),
        error=result.error,
    )


@router.post(
    "/refund",
    response_model=RefundResponse,
    responses={
        200: {"description": "Refund executed"},
        401: {"description": "Unauthorized"},
        503: {"description": "Escrow not available"},
    }
)
async def refund_to_agent(
    request: RefundRequest,
    api_key: APIKeyData = Depends(verify_api_key)
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
    # Primary path: gasless refund via SDK + facilitator
    if X402_SDK_AVAILABLE:
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
                method, api_key.agent_id, request.deposit_id[:16],
                success, tx_hash,
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
            logger.warning(
                "SDK refund failed for deposit %s, falling back to direct contract: %s",
                request.deposit_id[:16], sdk_err,
            )
            # Fall through to direct contract below

    # Fallback: direct contract call (agent pays gas)
    if not X402R_AVAILABLE:
        raise HTTPException(status_code=503, detail="Neither SDK nor x402r escrow available")

    logger.warning(
        "Using direct contract refund (agent pays gas) for deposit %s by %s",
        request.deposit_id[:16], api_key.agent_id,
    )

    result = await refund_payment(deposit_id=request.deposit_id)

    logger.info(
        "Refund via direct contract by %s: deposit=%s, success=%s",
        api_key.agent_id, request.deposit_id[:16], result.success
    )

    return RefundResponse(
        success=result.success,
        tx_hash=result.tx_hash,
        deposit_id=result.deposit_id,
        payer=result.payer,
        amount=str(result.amount),
        error=result.error,
    )
