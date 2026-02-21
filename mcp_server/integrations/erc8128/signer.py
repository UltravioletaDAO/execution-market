"""
ERC-8128 HTTP Message Signature Signer

Signs HTTP requests per ERC-8128 (Signed HTTP Requests with Ethereum).

Flow:
  1. Fetch a fresh nonce from the server's /auth/erc8128/nonce endpoint
  2. Build RFC 9421 signature base from request components
  3. Sign with EIP-191 personal_sign
  4. Produce Signature + Signature-Input headers

Usage::

    from integrations.erc8128.signer import sign_request, fetch_nonce

    nonce = await fetch_nonce("https://api.execution.market")
    headers = sign_request(
        private_key="0x...",
        method="POST",
        url="https://api.execution.market/api/v1/tasks",
        body='{"title": "test"}',
        nonce=nonce,
        chain_id=8453,
    )
    # headers = {"Signature": "...", "Signature-Input": "...", "Content-Digest": "..."}

Reference:
  - ERC-8128: https://eip.tools/eip/8128
  - RFC 9421: https://www.rfc-editor.org/rfc/rfc9421
  - ERC-191: https://eips.ethereum.org/EIPS/eip-191
"""

import base64
import hashlib
import time
from typing import Optional
from urllib.parse import urlparse

from eth_account import Account
from eth_account.messages import encode_defunct


# Default label for ERC-8128 signatures
DEFAULT_LABEL = "eth"

# Default validity window (seconds)
DEFAULT_VALIDITY_SEC = 300


def sign_request(
    private_key: str,
    method: str,
    url: str,
    body: Optional[str] = None,
    nonce: Optional[str] = None,
    chain_id: int = 8453,
    label: str = DEFAULT_LABEL,
    validity_sec: int = DEFAULT_VALIDITY_SEC,
) -> dict[str, str]:
    """
    Sign an HTTP request per ERC-8128.

    Parameters
    ----------
    private_key : str
        Hex-encoded private key (with or without 0x prefix).
    method : str
        HTTP method (GET, POST, etc.).
    url : str
        Full URL of the request.
    body : str, optional
        Request body (for POST/PUT/PATCH). None for bodyless requests.
    nonce : str, optional
        Single-use nonce from the server. Required by most servers.
    chain_id : int
        EVM chain ID for the keyid (default: 8453 = Base).
    label : str
        Signature label (default: "eth").
    validity_sec : int
        Signature validity window in seconds (default: 300).

    Returns
    -------
    dict with keys: "Signature", "Signature-Input", and optionally "Content-Digest".
    These should be merged into the request headers before sending.
    """
    account = Account.from_key(private_key)
    address = account.address.lower()

    parsed = urlparse(url)
    authority = parsed.netloc
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else None

    now = int(time.time())
    created = now
    expires = now + validity_sec

    keyid = f"erc8128:{chain_id}:{address}"

    # Determine covered components
    covered = ["@method", "@authority", "@path"]
    if query:
        covered.append("@query")

    extra_headers = {}

    if body is not None:
        digest = _compute_content_digest(body)
        extra_headers["Content-Digest"] = digest
        covered.append("content-digest")

    # Build signature base
    sig_base = _build_signature_base(
        method=method,
        authority=authority,
        path=path,
        query=query,
        content_digest=extra_headers.get("Content-Digest"),
        label=label,
        covered=covered,
        created=created,
        expires=expires,
        nonce=nonce,
        keyid=keyid,
    )

    # EIP-191 personal_sign
    msg = encode_defunct(text=sig_base)
    signed = account.sign_message(msg)
    sig_bytes = signed.signature

    # Encode signature as base64 (RFC 8941 byte sequence)
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    # Build headers
    sig_params = _build_signature_params(
        covered=covered,
        created=created,
        expires=expires,
        nonce=nonce,
        keyid=keyid,
    )

    extra_headers["Signature"] = f"{label}=:{sig_b64}:"
    extra_headers["Signature-Input"] = f"{label}={sig_params}"

    return extra_headers


async def fetch_nonce(api_base: str, timeout: float = 10.0) -> str:
    """
    Fetch a fresh single-use nonce from the server.

    Parameters
    ----------
    api_base : str
        Base URL of the API (e.g., "https://api.execution.market").
    timeout : float
        Request timeout in seconds.

    Returns
    -------
    str : The nonce value.
    """
    import httpx

    url = f"{api_base.rstrip('/')}/api/v1/auth/erc8128/nonce"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data["nonce"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_content_digest(body: str) -> str:
    """Compute Content-Digest header value (SHA-256)."""
    digest = hashlib.sha256(body.encode("utf-8")).digest()
    b64 = base64.b64encode(digest).decode("ascii")
    return f"sha-256=:{b64}:"


def _build_signature_base(
    method: str,
    authority: str,
    path: str,
    query: Optional[str],
    content_digest: Optional[str],
    label: str,
    covered: list[str],
    created: int,
    expires: int,
    nonce: Optional[str],
    keyid: str,
) -> str:
    """Build the RFC 9421 signature base string."""
    lines = []

    for component in covered:
        if component == "@method":
            lines.append(f'"@method": {method.upper()}')
        elif component == "@authority":
            lines.append(f'"@authority": {authority}')
        elif component == "@path":
            lines.append(f'"@path": {path}')
        elif component == "@query":
            lines.append(f'"@query": {query or "?"}')
        elif component == "content-digest":
            lines.append(f'"content-digest": {content_digest or ""}')

    sig_params = _build_signature_params(
        covered=covered,
        created=created,
        expires=expires,
        nonce=nonce,
        keyid=keyid,
    )
    lines.append(f'"@signature-params": {sig_params}')

    return "\n".join(lines)


def _build_signature_params(
    covered: list[str],
    created: int,
    expires: int,
    nonce: Optional[str],
    keyid: str,
) -> str:
    """Build the @signature-params value per RFC 9421."""
    comp_str = " ".join(f'"{c}"' for c in covered)
    parts = [f"({comp_str})"]
    parts.append(f"created={created}")
    parts.append(f"expires={expires}")
    if nonce:
        parts.append(f'nonce="{nonce}"')
    parts.append(f'keyid="{keyid}"')
    return ";".join(parts)
