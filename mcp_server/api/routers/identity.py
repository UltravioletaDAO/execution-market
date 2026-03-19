"""
IRC Identity Sync REST Endpoints (Phase 2, Task 2.6)

Bidirectional identity sync between EM Supabase and MRServ SQLite.
Provides lookup, sync push, and server-side challenge verification.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_api_key, APIKeyData
import supabase_client as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/identity", tags=["Identity"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class IdentityLookupResponse(BaseModel):
    irc_nick: str
    wallet_address: str
    trust_level: int = Field(ge=0, le=3)
    agent_id: Optional[int] = None
    verified_at: Optional[str] = None
    preferred_channel: str = "both"
    last_seen_at: Optional[str] = None


class IdentitySyncRequest(BaseModel):
    irc_nick: str = Field(min_length=1, max_length=64)
    wallet_address: str = Field(min_length=42, max_length=42)
    trust_level: int = Field(ge=0, le=3, default=1)
    nickserv_account: Optional[str] = None
    agent_id: Optional[int] = None

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Must be a valid Ethereum address (0x + 40 hex chars)")
        return v.lower()

    @field_validator("irc_nick")
    @classmethod
    def validate_nick(cls, v: str) -> str:
        return v.lower()


class IdentitySyncResponse(BaseModel):
    status: str  # "created" or "updated"
    irc_nick: str
    trust_level: int


class VerifyChallengeRequest(BaseModel):
    irc_nick: str
    wallet_address: str
    signature: str
    nonce: str

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        return v.lower()


class VerifyChallengeResponse(BaseModel):
    verified: bool
    trust_level: int
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/lookup",
    response_model=IdentityLookupResponse,
    summary="Lookup IRC identity by nick or wallet",
)
async def lookup_identity(
    nick: Optional[str] = Query(None, description="IRC nick to look up"),
    wallet: Optional[str] = Query(None, description="Wallet address to look up"),
    api_key: APIKeyData = Depends(verify_api_key),
):
    """Look up an IRC identity by nick or wallet address."""
    if not nick and not wallet:
        raise HTTPException(status_code=400, detail="Provide 'nick' or 'wallet' query parameter")

    try:
        query = db.client.table("irc_identities").select(
            "irc_nick, wallet_address, trust_level, agent_id, verified_at, preferred_channel, last_seen_at"
        )

        if nick:
            query = query.eq("irc_nick", nick.lower())
        else:
            query = query.eq("wallet_address", wallet.lower())

        result = query.execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Identity not found")

        row = result.data[0]
        return IdentityLookupResponse(**row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Identity lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Lookup failed")


@router.post(
    "/sync",
    response_model=IdentitySyncResponse,
    summary="Push identity update from MRServ",
)
async def sync_identity(
    req: IdentitySyncRequest,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """
    MRServ pushes identity updates to EM Supabase.
    Upserts by irc_nick — creates if new, updates if existing.
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "irc_nick": req.irc_nick,
            "wallet_address": req.wallet_address,
            "trust_level": req.trust_level,
            "last_seen_at": now,
            "updated_at": now,
        }
        if req.nickserv_account:
            row["nickserv_account"] = req.nickserv_account
        if req.agent_id is not None:
            row["agent_id"] = req.agent_id

        # Check if exists
        existing = (
            db.client.table("irc_identities")
            .select("id")
            .eq("irc_nick", req.irc_nick)
            .execute()
        )

        if existing.data:
            # Update
            db.client.table("irc_identities").update(row).eq(
                "irc_nick", req.irc_nick
            ).execute()
            status = "updated"
        else:
            # Insert
            row["created_at"] = now
            db.client.table("irc_identities").insert(row).execute()
            status = "created"

        logger.info(
            "Identity sync: %s nick=%s trust=%d",
            status,
            req.irc_nick,
            req.trust_level,
        )

        return IdentitySyncResponse(
            status=status,
            irc_nick=req.irc_nick,
            trust_level=req.trust_level,
        )

    except Exception as e:
        logger.error("Identity sync failed: %s", e)
        raise HTTPException(status_code=500, detail="Sync failed")


@router.post(
    "/verify-challenge",
    response_model=VerifyChallengeResponse,
    summary="Server-side signature verification for identity challenges",
)
async def verify_challenge(
    req: VerifyChallengeRequest,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """
    Server-side nonce verification for when MRServ handles the challenge flow.
    Verifies EIP-191 signature and upgrades trust level to VERIFIED (2).
    """
    try:
        from eth_account.messages import encode_defunct
        from eth_account import Account
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="eth_account not available for server-side verification",
        )

    try:
        # Look up identity
        result = (
            db.client.table("irc_identities")
            .select("id, wallet_address, challenge_nonce, challenge_expires_at, trust_level")
            .eq("irc_nick", req.irc_nick.lower())
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Identity not found")

        identity = result.data[0]

        # Check nonce matches
        if identity.get("challenge_nonce") != req.nonce:
            return VerifyChallengeResponse(
                verified=False,
                trust_level=identity["trust_level"],
                message="Nonce mismatch",
            )

        # Check expiry
        if identity.get("challenge_expires_at"):
            expires = datetime.fromisoformat(
                identity["challenge_expires_at"].replace("Z", "+00:00")
            )
            if datetime.now(timezone.utc) > expires:
                return VerifyChallengeResponse(
                    verified=False,
                    trust_level=identity["trust_level"],
                    message="Challenge expired",
                )

        # Verify signature
        message = encode_defunct(text=f"EM-VERIFY:{req.nonce}:{req.irc_nick.lower()}")
        recovered = Account.recover_message(message, signature=req.signature)

        if recovered.lower() != req.wallet_address.lower():
            return VerifyChallengeResponse(
                verified=False,
                trust_level=identity["trust_level"],
                message="Signature does not match wallet",
            )

        # Upgrade trust level
        now = datetime.now(timezone.utc).isoformat()
        db.client.table("irc_identities").update(
            {
                "trust_level": 2,
                "verified_at": now,
                "challenge_nonce": None,
                "challenge_expires_at": None,
                "updated_at": now,
            }
        ).eq("irc_nick", req.irc_nick.lower()).execute()

        logger.info("Identity verified server-side: nick=%s", req.irc_nick)

        return VerifyChallengeResponse(
            verified=True,
            trust_level=2,
            message="Wallet verified successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Challenge verification failed: %s", e)
        raise HTTPException(status_code=500, detail="Verification failed")
