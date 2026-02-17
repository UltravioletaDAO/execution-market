"""
ERC-8128 HTTP Message Signature Verifier

Verifies HTTP requests signed per ERC-8128 (Signed HTTP Requests with Ethereum).

Flow:
  1. Parse Signature-Input header (RFC 8941 structured dictionary)
  2. Extract keyid (erc8128:<chainId>:<address>), nonce, created, expires
  3. Reconstruct RFC 9421 signature base from the HTTP request
  4. Verify Content-Digest (SHA-256) for body integrity
  5. Apply EIP-191 prefix and ecrecover signer address
  6. Validate: signature matches keyid address, timestamps valid, nonce fresh

Reference:
  - ERC-8128: https://eip.tools/eip/8128
  - RFC 9421: https://www.rfc-editor.org/rfc/rfc9421
  - ERC-191: https://eips.ethereum.org/EIPS/eip-191
"""

import base64
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from eth_account.messages import encode_defunct
from eth_account import Account

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types & Configuration
# ---------------------------------------------------------------------------

# Covered components required for Request-Bound signatures (Section 3.1.1)
REQUEST_BOUND_COMPONENTS = {"@method", "@authority", "@path"}
# Additionally required if present:
#   @query       — if request has a query string
#   content-digest — if request has a body

# keyid format: erc8128:<chain-id>:<0x address>
KEYID_RE = re.compile(
    r'^erc8128:(\d+):(0x[0-9a-fA-F]{40})$'
)


@dataclass
class VerifyPolicy:
    """Verifier acceptance policy (Section 3.2)."""

    max_validity_sec: int = 300       # 5 minutes max window
    clock_skew_sec: int = 30          # 30s clock drift tolerance
    strict_label: bool = False        # Require "eth" label
    allow_replayable: bool = False    # Reject nonce-less by default
    allow_class_bound: bool = False   # Reject class-bound by default
    required_components: set[str] = field(default_factory=set)  # Extra required


DEFAULT_POLICY = VerifyPolicy()


@dataclass
class ERC8128Result:
    """Result of ERC-8128 verification."""

    ok: bool
    address: Optional[str] = None       # Recovered wallet address (lowercase)
    chain_id: Optional[int] = None      # From keyid
    reason: Optional[str] = None        # Error reason if not ok
    binding: str = "request-bound"      # or "class-bound"
    replayable: bool = False            # True if no nonce was present
    label: Optional[str] = None         # Signature label used (e.g. "eth")


class NonceStoreProtocol(Protocol):
    """Protocol for nonce stores (duck-typed)."""

    async def consume(self, key: str, ttl_seconds: int) -> bool: ...


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def verify_erc8128_request(
    request: Any,
    nonce_store: Optional[NonceStoreProtocol] = None,
    policy: Optional[VerifyPolicy] = None,
) -> ERC8128Result:
    """
    Verify an ERC-8128 signed HTTP request.

    Parameters
    ----------
    request:
        A request-like object with `.headers` (dict-like), `.method` (str),
        `.url` (.path, .query, host/authority), and `.body()` async method.
    nonce_store:
        NonceStore for replay protection. Required if policy disallows
        replayable signatures.
    policy:
        Verification policy. Defaults to DEFAULT_POLICY.

    Returns
    -------
    ERC8128Result with ok=True and recovered address, or ok=False with reason.
    """
    pol = policy or DEFAULT_POLICY

    try:
        # 1. Extract Signature and Signature-Input headers
        sig_input_raw = _get_header(request, "signature-input")
        sig_raw = _get_header(request, "signature")

        if not sig_input_raw:
            return ERC8128Result(ok=False, reason="Missing Signature-Input header")
        if not sig_raw:
            return ERC8128Result(ok=False, reason="Missing Signature header")

        # 2. Parse Signature-Input → find label + params + covered components
        label, covered_components, params = _parse_signature_input(
            sig_input_raw, strict_label=pol.strict_label
        )
        if label is None:
            return ERC8128Result(
                ok=False,
                reason="Could not parse Signature-Input header",
            )

        # 3. Extract signature bytes for the label
        sig_bytes = _extract_signature_bytes(sig_raw, label)
        if sig_bytes is None:
            return ERC8128Result(
                ok=False,
                reason=f"No signature found for label '{label}'",
            )

        # 4. Parse & validate keyid
        keyid = params.get("keyid")
        if not keyid:
            return ERC8128Result(ok=False, reason="Missing keyid parameter")

        m = KEYID_RE.match(keyid)
        if not m:
            return ERC8128Result(
                ok=False,
                reason=f"Invalid keyid format: {keyid}",
            )
        chain_id = int(m.group(1))
        claimed_address = m.group(2).lower()

        # 5. Validate created/expires
        created = params.get("created")
        expires = params.get("expires")
        if created is None or expires is None:
            return ERC8128Result(
                ok=False,
                reason="Missing created or expires parameter",
                chain_id=chain_id,
            )

        ts_err = _validate_timestamps(created, expires, pol)
        if ts_err:
            return ERC8128Result(ok=False, reason=ts_err, chain_id=chain_id)

        # 6. Determine binding & replay properties
        nonce_value = params.get("nonce")
        is_replayable = nonce_value is None
        binding = _determine_binding(request, covered_components)

        if is_replayable and not pol.allow_replayable:
            return ERC8128Result(
                ok=False,
                reason="Replayable signatures not accepted (missing nonce)",
                chain_id=chain_id,
            )

        if binding == "class-bound" and not pol.allow_class_bound:
            return ERC8128Result(
                ok=False,
                reason="Class-bound signatures not accepted (missing required components)",
                chain_id=chain_id,
            )

        # 7. Check extra required components
        for comp in pol.required_components:
            if comp not in covered_components:
                return ERC8128Result(
                    ok=False,
                    reason=f"Required component '{comp}' not covered",
                    chain_id=chain_id,
                )

        # 8. Verify Content-Digest if covered
        if "content-digest" in covered_components:
            digest_err = await _verify_content_digest(request)
            if digest_err:
                return ERC8128Result(
                    ok=False, reason=digest_err, chain_id=chain_id
                )

        # 9. Reconstruct the signature base (RFC 9421)
        sig_base = await _build_signature_base(
            request, label, covered_components, params
        )

        # 10. EIP-191 ecrecover
        recovered = _eip191_recover(sig_base, sig_bytes)
        if recovered is None:
            return ERC8128Result(
                ok=False,
                reason="Signature recovery failed",
                chain_id=chain_id,
            )

        if recovered.lower() != claimed_address:
            # ERC-1271 fallback: the claimed address may be a smart contract wallet
            erc1271_valid = await _try_erc1271_fallback(
                claimed_address, sig_base, sig_bytes, chain_id
            )
            if not erc1271_valid:
                return ERC8128Result(
                    ok=False,
                    reason=f"Signer mismatch: recovered {recovered}, expected {claimed_address}",
                    chain_id=chain_id,
                )
            # ERC-1271 verified — use the claimed address
            recovered = claimed_address

        # 11. Consume nonce (replay protection)
        if not is_replayable and nonce_store is not None:
            nonce_key = f"erc8128:{chain_id}:{claimed_address}:{nonce_value}"
            ttl = int(expires) - int(created) + pol.clock_skew_sec
            consumed = await nonce_store.consume(nonce_key, ttl)
            if not consumed:
                return ERC8128Result(
                    ok=False,
                    reason="Nonce already consumed (replay attempt)",
                    chain_id=chain_id,
                    address=recovered,
                )

        logger.info(
            "ERC-8128 verified: address=%s chain=%d binding=%s replayable=%s label=%s",
            recovered,
            chain_id,
            binding,
            is_replayable,
            label,
        )

        return ERC8128Result(
            ok=True,
            address=recovered,
            chain_id=chain_id,
            binding=binding,
            replayable=is_replayable,
            label=label,
        )

    except Exception as exc:
        logger.exception("ERC-8128 verification error: %s", exc)
        return ERC8128Result(ok=False, reason=f"Verification error: {exc}")


# ---------------------------------------------------------------------------
# ERC-1271 Smart Contract Account Fallback
# ---------------------------------------------------------------------------


async def _try_erc1271_fallback(
    address: str, message: str, signature: bytes, chain_id: int
) -> bool:
    """
    Attempt ERC-1271 on-chain verification when ecrecover doesn't match.

    This handles smart contract wallets (Safe, ERC-4337) that cannot use
    ecrecover. The contract's isValidSignature method is called instead.
    """
    try:
        from .erc1271 import verify_erc1271_signature
        from eth_account.messages import encode_defunct
        from eth_hash.auto import keccak

        # Hash the EIP-191 prefixed message (same as what was signed)
        msg = encode_defunct(text=message)
        # keccak256 of the prefixed message
        message_hash = keccak(
            b"\x19Ethereum Signed Message:\n"
            + str(len(message)).encode()
            + message.encode()
        )

        return await verify_erc1271_signature(
            address, message_hash, signature, chain_id
        )
    except ImportError:
        logger.debug("ERC-1271 module not available for fallback")
        return False
    except Exception as e:
        logger.warning("ERC-1271 fallback failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Header helpers
# ---------------------------------------------------------------------------


def _get_header(request: Any, name: str) -> Optional[str]:
    """Get a header value case-insensitively."""
    headers = getattr(request, "headers", {})
    if hasattr(headers, "get"):
        val = headers.get(name)
        if val:
            return val
        # Try case-insensitive lookup
        for k, v in headers.items():
            if k.lower() == name.lower():
                return v
    return None


# ---------------------------------------------------------------------------
# RFC 8941 Structured Field parsing (minimal subset for Signature-Input)
# ---------------------------------------------------------------------------


def _parse_signature_input(
    raw: str, strict_label: bool = False
) -> tuple[Optional[str], list[str], dict[str, Any]]:
    """
    Parse Signature-Input header into (label, covered_components, params).

    Supports the subset of RFC 8941 Structured Dictionary needed for ERC-8128:
      label=(component1 component2 ...);param1=val1;param2=val2

    Returns (None, [], {}) on parse failure.
    """
    entries = _split_dict_members(raw)

    label = None
    entry_value = None

    if strict_label:
        if "eth" in entries:
            label = "eth"
            entry_value = entries["eth"]
    else:
        # Prefer "eth", otherwise take the first
        if "eth" in entries:
            label = "eth"
            entry_value = entries["eth"]
        elif entries:
            label = next(iter(entries))
            entry_value = entries[label]

    if label is None or entry_value is None:
        return None, [], {}

    covered, params = _parse_inner_list_with_params(entry_value)
    return label, covered, params


def _split_dict_members(raw: str) -> dict[str, str]:
    """
    Split a structured dictionary into label -> value.

    Handles parentheses and quoted strings within values.
    """
    result = {}
    remaining = raw.strip()

    while remaining:
        eq_idx = remaining.find("=")
        if eq_idx < 0:
            break
        lbl = remaining[:eq_idx].strip()
        remaining = remaining[eq_idx + 1:]

        value, remaining = _extract_dict_value(remaining)
        result[lbl] = value.strip()

    return result


def _extract_dict_value(s: str) -> tuple[str, str]:
    """
    Extract a dictionary member value, respecting parentheses and quoted strings.
    Returns (value, remaining).
    """
    depth = 0
    in_quotes = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '"' and (i == 0 or s[i - 1] != '\\'):
            in_quotes = not in_quotes
        elif not in_quotes:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 0:
                return s[:i], s[i + 1:]
        i += 1
    return s, ""


def _parse_inner_list_with_params(
    value: str,
) -> tuple[list[str], dict[str, Any]]:
    """
    Parse an inner list with parameters:
      ("@method" "@authority" "content-digest");created=123;nonce="abc";keyid="erc8128:1:0x..."
    """
    paren_start = value.find("(")
    paren_end = value.find(")")
    if paren_start < 0 or paren_end < 0:
        return [], {}

    inner = value[paren_start + 1: paren_end]
    components = _parse_component_list(inner)

    params_str = value[paren_end + 1:]
    params = _parse_params(params_str)

    return components, params


def _parse_component_list(inner: str) -> list[str]:
    """Parse a space-separated list of quoted component identifiers."""
    components = []
    for token in re.findall(r'"([^"]*)"', inner):
        components.append(token)
    return components


def _parse_params(params_str: str) -> dict[str, Any]:
    """Parse semicolon-separated parameters."""
    params: dict[str, Any] = {}
    for part in _split_params(params_str):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, val = part.partition("=")
        key = key.strip()
        val = val.strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        else:
            try:
                val = int(val)
            except ValueError:
                pass
        params[key] = val
    return params


def _split_params(s: str) -> list[str]:
    """Split parameter string on semicolons, respecting quotes."""
    parts = []
    current = ""
    in_quotes = False
    for ch in s:
        if ch == '"':
            in_quotes = not in_quotes
            current += ch
        elif ch == ';' and not in_quotes:
            if current.strip():
                parts.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current)
    return parts


# ---------------------------------------------------------------------------
# Signature bytes extraction
# ---------------------------------------------------------------------------


def _extract_signature_bytes(sig_header: str, label: str) -> Optional[bytes]:
    """
    Extract signature bytes for a given label from the Signature header.
    Format: label=:base64:
    """
    entries = _split_dict_members(sig_header)
    value = entries.get(label)
    if not value:
        return None

    value = value.strip()
    if value.startswith(":") and value.endswith(":"):
        b64_data = value[1:-1]
    else:
        b64_data = value

    try:
        return base64.b64decode(b64_data)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Timestamp validation
# ---------------------------------------------------------------------------


def _validate_timestamps(
    created: Any, expires: Any, policy: VerifyPolicy
) -> Optional[str]:
    """Validate created/expires timestamps. Returns error string or None."""
    try:
        created_ts = int(created)
        expires_ts = int(expires)
    except (ValueError, TypeError):
        return "created/expires must be integer Unix timestamps"

    if expires_ts <= created_ts:
        return "expires must be greater than created"

    now = int(time.time())

    validity = expires_ts - created_ts
    if validity > policy.max_validity_sec:
        return (
            f"Validity window too large: {validity}s "
            f"(max {policy.max_validity_sec}s)"
        )

    if created_ts > now + policy.clock_skew_sec:
        return "Signature not yet valid (created is in the future)"

    if expires_ts < now - policy.clock_skew_sec:
        return "Signature has expired"

    return None


# ---------------------------------------------------------------------------
# Binding determination
# ---------------------------------------------------------------------------


def _determine_binding(request: Any, covered: list[str]) -> str:
    """
    Determine if signature is Request-Bound or Class-Bound (Section 3.1.1).
    """
    covered_set = set(covered)

    if not REQUEST_BOUND_COMPONENTS.issubset(covered_set):
        return "class-bound"

    url = getattr(request, "url", None)
    query = ""
    if url is not None:
        query = getattr(url, "query", "") or ""
    if query and "@query" not in covered_set:
        return "class-bound"

    return "request-bound"


# ---------------------------------------------------------------------------
# Content-Digest verification (RFC 9530)
# ---------------------------------------------------------------------------


async def _verify_content_digest(request: Any) -> Optional[str]:
    """
    Verify the Content-Digest header matches the request body.
    Returns error string or None on success.
    """
    digest_header = _get_header(request, "content-digest")
    if not digest_header:
        return "content-digest covered but Content-Digest header missing"

    m = re.match(r'sha-256=:([A-Za-z0-9+/=]+):', digest_header)
    if not m:
        return "Unsupported Content-Digest format (only sha-256 supported)"

    expected_b64 = m.group(1)
    try:
        expected_hash = base64.b64decode(expected_b64)
    except Exception:
        return "Invalid Content-Digest base64 encoding"

    body = await _get_body(request)
    actual_hash = hashlib.sha256(body).digest()

    if actual_hash != expected_hash:
        return "Content-Digest mismatch: body has been tampered with"

    return None


async def _get_body(request: Any) -> bytes:
    """Read the request body. Handles FastAPI Request and test mocks."""
    if hasattr(request, "_body"):
        return request._body
    if hasattr(request, "body"):
        result = request.body()
        if hasattr(result, "__await__"):
            return await result
        return result
    return b""


# ---------------------------------------------------------------------------
# RFC 9421 Signature Base Construction
# ---------------------------------------------------------------------------


async def _build_signature_base(
    request: Any,
    label: str,
    covered_components: list[str],
    params: dict[str, Any],
) -> str:
    """
    Build the signature base string per RFC 9421 Section 2.5.

    Format:
        "@method": POST
        "@authority": api.example.com
        "@path": /foo
        "@query": ?a=1&b=two
        "content-digest": sha-256=:...:
        "@signature-params": ("@method" "@authority" ...);created=...;expires=...
    """
    lines = []

    for component in covered_components:
        value = await _resolve_component(request, component)
        lines.append(f'"{component}": {value}')

    sig_params = _build_signature_params(covered_components, params)
    lines.append(f'"@signature-params": {sig_params}')

    return "\n".join(lines)


async def _resolve_component(request: Any, component: str) -> str:
    """Resolve a covered component's value from the request."""
    if component == "@method":
        return getattr(request, "method", "GET").upper()

    if component == "@authority":
        url = getattr(request, "url", None)
        if url is not None:
            if hasattr(url, "netloc"):
                return str(url.netloc)
            if hasattr(url, "hostname"):
                host = str(url.hostname)
                port = getattr(url, "port", None)
                if port and port not in (80, 443):
                    host = f"{host}:{port}"
                return host
        host = _get_header(request, "host")
        return host or ""

    if component == "@path":
        url = getattr(request, "url", None)
        if url is not None and hasattr(url, "path"):
            return str(url.path)
        return "/"

    if component == "@query":
        url = getattr(request, "url", None)
        if url is not None:
            query = getattr(url, "query", "") or ""
            if query:
                return f"?{query}"
        return "?"

    # Regular header field
    value = _get_header(request, component)
    return value or ""


def _build_signature_params(
    covered: list[str], params: dict[str, Any]
) -> str:
    """Build the @signature-params value."""
    comp_str = " ".join(f'"{c}"' for c in covered)
    parts = [f"({comp_str})"]

    ordered_keys = ["created", "expires", "nonce", "keyid"]
    for key in ordered_keys:
        if key in params:
            parts.append(_format_param(key, params[key]))
    for key in sorted(params.keys()):
        if key not in ordered_keys:
            parts.append(_format_param(key, params[key]))

    return ";".join(parts)


def _format_param(key: str, value: Any) -> str:
    """Format a single parameter for @signature-params."""
    if isinstance(value, int):
        return f"{key}={value}"
    return f'{key}="{value}"'


# ---------------------------------------------------------------------------
# EIP-191 Signature Recovery
# ---------------------------------------------------------------------------


def _eip191_recover(message: str, signature: bytes) -> Optional[str]:
    """
    Recover the signer address from an EIP-191 personal_sign signature.

    Per ERC-8128 Section 3.4.3:
      H = keccak256("\\x19Ethereum Signed Message:\\n" + len(M) + M)
    """
    try:
        msg = encode_defunct(text=message)
        address = Account.recover_message(msg, signature=signature)
        return address.lower()
    except Exception as e:
        logger.debug("EIP-191 recovery failed: %s", e)
        return None
