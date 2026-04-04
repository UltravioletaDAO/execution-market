"""
World ID 4.0 Client — RP Signing + Cloud API Verification

Implements the v4 RP signing spec:
  message = version(0x01) || nonce(32B) || createdAt(8B) || expiresAt(8B) || action(32B)
  msgHash = keccak256(EIP-191 prefix + message)
  signature = secp256k1_sign_recoverable(msgHash, signing_key)

Cloud API v4: POST https://developer.world.org/api/v4/verify/{rp_id}
"""

import logging
import os
import struct
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (from env vars)
# ---------------------------------------------------------------------------

WORLD_ID_APP_ID = os.environ.get("WORLD_ID_APP_ID", "")
WORLD_ID_RP_ID = os.environ.get("WORLD_ID_RP_ID", "")
WORLD_ID_SIGNING_KEY = os.environ.get("WORLD_ID_SIGNING_KEY", "")

WORLD_CLOUD_API_URL = "https://developer.world.org/api/v4/verify"

# Default action string used for worker verification
DEFAULT_ACTION = "verify-worker"

# RP signature validity window (seconds)
RP_SIGNATURE_TTL = 300  # 5 minutes


@dataclass
class RPSignatureResult:
    """Result of RP signing — sent to frontend for IDKit."""

    nonce: str  # hex-encoded 32-byte nonce
    created_at: int  # unix timestamp (seconds)
    expires_at: int  # unix timestamp (seconds)
    action: str  # e.g. "verify-worker"
    signature: str  # hex-encoded recoverable signature (65 bytes = r+s+v)
    rp_id: str  # the RP ID for IDKit config


@dataclass
class VerificationResult:
    """Result of World ID proof verification."""

    success: bool
    nullifier_hash: Optional[str] = None
    verification_level: Optional[str] = None  # "orb" | "device"
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Cryptographic helpers
# ---------------------------------------------------------------------------


def _keccak256(data: bytes) -> bytes:
    """Compute keccak256 hash."""
    from Crypto.Hash import keccak

    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()


def _hash_to_field(input_bytes: bytes) -> bytes:
    """
    Hash input to a BN254 field element (254 bits).

    hashToField(x) = keccak256(x) >> 8
    Returns 32 bytes, but the top byte is zeroed (right-shift by 8 bits).
    """
    h = _keccak256(input_bytes)
    # Shift right by 8 bits: prepend a zero byte, drop the last byte
    return b"\x00" + h[:31]


def _hash_ethereum_message(message: bytes) -> bytes:
    """
    EIP-191 personal_sign hash.

    keccak256("\\x19Ethereum Signed Message:\\n" + len(message) + message)
    """
    prefix = f"\x19Ethereum Signed Message:\n{len(message)}".encode("utf-8")
    return _keccak256(prefix + message)


def _compute_rp_signature_message(
    nonce: bytes,
    created_at: int,
    expires_at: int,
    action: str,
) -> bytes:
    """
    Build the RP signature message per World ID v4 spec.

    Layout (binary):
      version     = 0x01                          (1 byte)
      nonce       = hashToField(random_32_bytes)  (32 bytes)
      createdAt   = uint64 big-endian             (8 bytes)
      expiresAt   = uint64 big-endian             (8 bytes)
      action      = hashToField(utf8_bytes)       (32 bytes)
    Total: 81 bytes
    """
    version = b"\x01"
    created_bytes = struct.pack(">Q", created_at)  # uint64 big-endian
    expires_bytes = struct.pack(">Q", expires_at)  # uint64 big-endian
    action_hash = _hash_to_field(action.encode("utf-8"))

    return version + nonce + created_bytes + expires_bytes + action_hash


def sign_request(action: str = DEFAULT_ACTION) -> RPSignatureResult:
    """
    Generate a signed RP request for IDKit.

    Creates a fresh nonce, builds the v4 message, signs it with
    the RP signing key, and returns all data needed by the frontend.

    Raises ValueError if WORLD_ID_SIGNING_KEY is not configured.
    """
    if not WORLD_ID_SIGNING_KEY:
        raise ValueError(
            "WORLD_ID_SIGNING_KEY not configured. "
            "Set it in .env.local or ECS task definition."
        )

    from coincurve import PrivateKey

    # 1. Generate random nonce and hash to field
    random_bytes = os.urandom(32)
    nonce = _hash_to_field(random_bytes)

    # 2. Timestamps
    created_at = int(time.time())
    expires_at = created_at + RP_SIGNATURE_TTL

    # 3. Build message
    message = _compute_rp_signature_message(nonce, created_at, expires_at, action)

    # 4. EIP-191 hash
    msg_hash = _hash_ethereum_message(message)

    # 5. Sign with secp256k1 (recoverable)
    signing_key_bytes = bytes.fromhex(WORLD_ID_SIGNING_KEY.replace("0x", ""))
    pk = PrivateKey(signing_key_bytes)
    sig = pk.sign_recoverable(msg_hash, hasher=None)
    # coincurve returns 65 bytes: [r(32) + s(32) + v(1)]

    return RPSignatureResult(
        nonce=nonce.hex(),
        created_at=created_at,
        expires_at=expires_at,
        action=action,
        signature=sig.hex(),
        rp_id=WORLD_ID_RP_ID,
    )


# ---------------------------------------------------------------------------
# Cloud API v4 Verification
# ---------------------------------------------------------------------------


async def verify_world_id_proof(
    nullifier_hash: str,
    verification_level: str,
    protocol_version: str = "3.0",
    nonce: str = "",
    responses: Optional[list] = None,
    proof: str = "",
    merkle_root: str = "",
    action: str = DEFAULT_ACTION,
    signal: str = "",
) -> VerificationResult:
    """
    Verify a World ID proof via the Cloud API v4.

    Calls POST https://developer.world.org/api/v4/verify/{rp_id}

    The v4 endpoint expects the IDKit result forwarded as-is:
      { protocol_version, nonce, action, responses[] }

    signal_hash is already inside each responses[i] — do NOT add it top-level.
    Individual fields (proof, merkle_root) are for DB storage only.
    """
    if not WORLD_ID_RP_ID:
        return VerificationResult(
            success=False,
            error="WORLD_ID_RP_ID not configured",
        )

    url = f"{WORLD_CLOUD_API_URL}/{WORLD_ID_RP_ID}"

    if responses:
        # v4 Cloud API: forward IDKit result structure as-is
        # Required: protocol_version, nonce, action, responses[]
        # signal_hash is inside each response item (IDKit computed it)
        payload: dict = {
            "protocol_version": protocol_version,
            "nonce": nonce,
            "action": action,
            "responses": responses,
        }
    else:
        # Fallback: v2 legacy endpoint (should not happen with current frontend)
        signal_str = signal or ""
        signal_hash = "0x" + _keccak256(signal_str.encode("utf-8")).hex()
        url = f"https://developer.world.org/api/v2/verify/{WORLD_ID_APP_ID}"
        payload = {
            "proof": proof,
            "merkle_root": merkle_root,
            "nullifier_hash": nullifier_hash,
            "verification_level": verification_level,
            "action": action,
            "signal_hash": signal_hash,
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                # v4 response uses "nullifier" (not "nullifier_hash")
                resp_nullifier = data.get("nullifier", nullifier_hash)
                logger.info(
                    "World ID proof verified: nullifier=%s...%s",
                    resp_nullifier[:10] if resp_nullifier else "?",
                    resp_nullifier[-6:] if resp_nullifier else "?",
                )
                return VerificationResult(
                    success=True,
                    nullifier_hash=resp_nullifier,
                    verification_level=verification_level,
                )
            else:
                detail = data.get("detail", "Proof verification failed")
                logger.warning("World ID proof REJECTED: %s", detail)
                return VerificationResult(success=False, error=str(detail))

        else:
            body = resp.text
            logger.error(
                "World ID Cloud API error: status=%d body=%s",
                resp.status_code,
                body[:200],
            )
            return VerificationResult(
                success=False,
                error=f"Cloud API returned {resp.status_code}: {body[:100]}",
            )

    except Exception as exc:
        logger.error("World ID verification request failed: %s", exc)
        return VerificationResult(success=False, error=str(exc))
