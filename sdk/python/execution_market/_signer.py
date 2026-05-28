"""
ERC-8128 wallet signing via Open Wallet Standard (OWS).

The private key NEVER leaves the OWS vault — every signature is produced by
shelling out to `ows sign message`, which decrypts the key in memory, signs,
and wipes. The Python process only ever sees the signature bytes.

This module is the canonical Python signer for Execution Market clients. It
is the literal port of the `OwsEM8128Client` documented in the canonical
skill (`dashboard/public/skill.md`, STEP 1c Option A) at version 10.0.0.

Public surface:
    OwsEM8128Client(wallet_name, wallet_address, chain_id=8453, api_url=...)
        .get(path)                                  -> dict
        .post(path, data=None, extra_headers=None)  -> dict

    task_fingerprint(body)   -> hex digest, deterministic over identity fields
    with_backoff(fn, ...)    -> async retry helper with jitter

Why the prefix `_`: this is the internal implementation. The supported public
import is `from execution_market import OwsEM8128Client` (re-exported in
`__init__.py`). The internal module is here so the wire format can evolve
behind a stable public name.

Operational invariants (do NOT change without coordinating with the skill):
- keyid is ALWAYS lowercase ("erc8128:{chain_id}:{wallet.lower()}").
- alg is ALWAYS "eip191" (the only algorithm the backend verifier accepts;
  see mcp_server/integrations/erc8128/verifier.py:152/249/779).
- A fresh nonce is fetched immediately before each signed call (no caching
  — the server's nonce TTL is 5 min and the cost of fetching is one cheap
  round-trip).
- `extra_headers` are NOT part of ERC-8128's covered components, so adding
  them (e.g. X-Idempotency-Key) never breaks the signature.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import random
import subprocess
import time
from typing import Any, Awaitable, Callable, Mapping, Optional, TypeVar
from urllib.parse import urlparse

import httpx

# Path to the OWS CLI. Override via $OWS_BIN if installed elsewhere.
# Default matches the skill's documented npm global install path.
OWS_BIN = os.environ.get("OWS_BIN") or os.path.expanduser("~/.npm-global/bin/ows")

# Default API base. Override per-client via api_url=.
DEFAULT_API_URL = "https://api.execution.market"

# Nonce endpoint TTL is 5 min server-side; we don't cache — fetch per call.
_NONCE_PATH = "/api/v1/auth/erc8128/nonce"

# Signature is valid for 5 min (matches the skill's documented value).
_SIG_TTL_SECONDS = 300

T = TypeVar("T")


class OwsSignError(RuntimeError):
    """Raised when the OWS CLI subprocess fails to produce a signature."""


class OwsEM8128Client:
    """Signed HTTP client for Execution Market — keyless (OWS vault holds the key).

    Args:
        wallet_name: name as shown by `ows wallet list`.
        wallet_address: the EVM 0x... address (same on every EVM chain). The
            keyid sent to the server is always lowercased.
        chain_id: EVM chain id of the task's payment_network (default 8453 = Base).
            This is part of the keyid the server uses to resolve your identity;
            change it if you're paying on a different chain.
        api_url: API base URL (no trailing slash).

    Example:
        >>> client = OwsEM8128Client(
        ...     wallet_name="my-agent",
        ...     wallet_address="0xYOUR_EVM_ADDR",
        ...     chain_id=8453,
        ... )
        >>> task = await client.post(
        ...     "/api/v1/tasks",
        ...     {"title": "...", "bounty_usd": 0.10, ...},
        ...     extra_headers={"X-Idempotency-Key": task_fingerprint(body)},
        ... )
    """

    def __init__(
        self,
        wallet_name: str,
        wallet_address: str,
        chain_id: int = 8453,
        api_url: str = DEFAULT_API_URL,
    ) -> None:
        if not wallet_name:
            raise ValueError("wallet_name is required (see `ows wallet list`)")
        if not wallet_address or not wallet_address.startswith("0x") or len(wallet_address) != 42:
            raise ValueError(f"wallet_address must be a 42-char 0x... EVM address, got {wallet_address!r}")
        self.wallet_name = wallet_name
        self.wallet = wallet_address
        self.chain_id = chain_id
        self.api_url = api_url.rstrip("/")

    # ------------------------------------------------------------------
    # Signature primitives
    # ------------------------------------------------------------------

    def _sign_eip191(self, message: str) -> bytes:
        """Shell out to `ows sign message` and return the 65-byte signature.

        Uses --encoding hex to avoid shell-escape traps on the multi-line
        signature base (which contains newlines, quotes, parentheses).
        """
        hex_msg = message.encode("utf-8").hex()
        try:
            proc = subprocess.run(
                [
                    OWS_BIN, "sign", "message",
                    "--chain", "base",
                    "--wallet", self.wallet_name,
                    "--message", hex_msg,
                    "--encoding", "hex",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as e:
            raise OwsSignError(
                f"OWS CLI not found at {OWS_BIN!r}. Install with "
                "`npm install -g @open-wallet-standard/core` or set $OWS_BIN."
            ) from e
        except subprocess.CalledProcessError as e:
            raise OwsSignError(
                f"`ows sign message` failed (exit {e.returncode}): {e.stderr.strip() or e.stdout.strip()}"
            ) from e

        try:
            sig_hex = json.loads(proc.stdout)["signature"]
        except (json.JSONDecodeError, KeyError) as e:
            raise OwsSignError(f"Unexpected OWS output: {proc.stdout!r}") from e
        sig = bytes.fromhex(sig_hex)
        if len(sig) != 65:
            raise OwsSignError(
                f"OWS returned a {len(sig)}-byte signature; expected 65 "
                "(r||s||v). Upgrade OWS CLI to >= v1.2.4 — earlier versions "
                "had a missing-v byte bug."
            )
        return sig

    def _build_sig_params(self, covered: list[str], params: Mapping[str, Any]) -> str:
        """Render the @signature-params line per RFC 9421.

        Order matters for the signature base. Keep the order documented in
        the skill: covered components first, then created/expires/nonce/keyid/alg.
        """
        joined = " ".join(chr(34) + c + chr(34) for c in covered)
        parts = [f"({joined})"]
        for k in ("created", "expires", "nonce", "keyid", "alg"):
            if k in params:
                v = params[k]
                parts.append(f"{k}={v}" if isinstance(v, int) else f'{k}="{v}"')
        return ";".join(parts)

    async def _sign_headers(
        self,
        method: str,
        url: str,
        body: Optional[bytes | str] = None,
    ) -> dict[str, str]:
        """Build the {Signature, Signature-Input, Content-Digest?} headers."""
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{self.api_url}{_NONCE_PATH}")
            r.raise_for_status()
            nonce = r.json()["nonce"]

        parsed = urlparse(url)
        created = int(time.time())
        covered = ["@method", "@authority", "@path"]
        content_digest: Optional[str] = None

        if parsed.query:
            covered.append("@query")
        if body:
            b = body.encode() if isinstance(body, str) else body
            digest_b64 = base64.b64encode(hashlib.sha256(b).digest()).decode()
            content_digest = f"sha-256=:{digest_b64}:"
            covered.append("content-digest")

        params: dict[str, Any] = {
            "created": created,
            "expires": created + _SIG_TTL_SECONDS,
            "nonce": nonce,
            # CRITICAL: lowercase. Backend normalizes both sides to lowercase
            # (verifier.py:152/249/779). Sending checksum here causes drift
            # — see INC where Option C in v9.x had the bug.
            "keyid": f"erc8128:{self.chain_id}:{self.wallet.lower()}",
            "alg": "eip191",
        }
        sig_params = self._build_sig_params(covered, params)

        lines: list[str] = []
        for comp in covered:
            if comp == "@method":
                lines.append(f'"@method": {method.upper()}')
            elif comp == "@authority":
                lines.append(f'"@authority": {parsed.netloc}')
            elif comp == "@path":
                lines.append(f'"@path": {parsed.path}')
            elif comp == "@query":
                lines.append(f'"@query": ?{parsed.query}')
            elif comp == "content-digest":
                lines.append(f'"content-digest": {content_digest}')
        lines.append(f'"@signature-params": {sig_params}')

        sig_bytes = self._sign_eip191("\n".join(lines))
        sig_b64 = base64.b64encode(sig_bytes).decode()
        headers = {
            "Signature": f"eth=:{sig_b64}:",
            "Signature-Input": f"eth={sig_params}",
        }
        if content_digest:
            headers["Content-Digest"] = content_digest
        return headers

    # ------------------------------------------------------------------
    # HTTP surface
    # ------------------------------------------------------------------

    async def post(
        self,
        path: str,
        data: Any = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Signed POST returning the parsed JSON body."""
        url = f"{self.api_url}{path}"
        body = json.dumps(data) if data is not None else None
        auth = await self._sign_headers("POST", url, body)
        # extra_headers (e.g. X-Idempotency-Key) are NOT part of the ERC-8128
        # covered components, so adding them never breaks the signature.
        headers = {"Content-Type": "application/json", **auth, **(dict(extra_headers) if extra_headers else {})}
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(url, content=body, headers=headers)
            return r.json()

    async def get(self, path: str) -> Any:
        """Signed GET returning the parsed JSON body."""
        url = f"{self.api_url}{path}"
        auth = await self._sign_headers("GET", url)
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, headers=auth)
            return r.json()


# ----------------------------------------------------------------------
# Idempotency helper
# ----------------------------------------------------------------------

# Fields that define task identity for dedupe. Anything outside this set
# (e.g. agent_name, skills_required, arbiter_mode) is metadata that the
# server allows to vary without producing a "different task".
_FINGERPRINT_KEYS = (
    "title",
    "instructions",
    "location_hint",
    "location_lat",
    "location_lng",
    "bounty_usd",
    "deadline_hours",
    "evidence_required",
    "payment_network",
)


def task_fingerprint(body: Mapping[str, Any]) -> str:
    """Deterministic SHA-256 of the fields that define task identity.

    Use the result as the value of the `X-Idempotency-Key` header on
    `POST /api/v1/tasks`. The backend dedupes on this key
    (mcp_server/api/routers/tasks.py:531-589) and returns the original
    task with `X-Idempotent: true` instead of creating a duplicate —
    so a retry after a timeout is safe.

    The normalization is intentional and minimal: strings are stripped
    and lowercased so cosmetic whitespace/case changes don't fork the
    fingerprint, but the schema (sorted keys + JSON encoding) is
    pinned so the same body always produces the same digest across
    Python versions.
    """
    norm: dict[str, Any] = {}
    for k in _FINGERPRINT_KEYS:
        v = body.get(k)
        if isinstance(v, str):
            norm[k] = v.strip().lower()
        else:
            norm[k] = v
    blob = json.dumps(norm, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ----------------------------------------------------------------------
# Retry helper
# ----------------------------------------------------------------------


async def with_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    tries: int = 4,
    base: float = 0.5,
) -> T:
    """Run `fn` with exponential backoff + jitter; raise the last error.

    Use around any signed call that could hit a transient 429/5xx:

        >>> result = await with_backoff(lambda: client.post("/api/v1/tasks", body))

    `tries=4, base=0.5` produces sleeps of roughly 0.5-1.0s, 1.0-1.5s,
    2.0-2.5s before the final attempt — well within the server's nonce
    TTL (5 min) and well clear of "retry storm" territory.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(tries):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            if attempt == tries - 1:
                raise
            await asyncio.sleep(base * (2 ** attempt) + random.uniform(0, base))
    # Unreachable (the loop either returns or re-raises on the last attempt).
    assert last_exc is not None
    raise last_exc
