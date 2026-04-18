"""PII truncation helpers for log output.

Wallet addresses (``0x`` + 40 hex chars) count as PII under the project's
streaming/GDPR policy. All ``logger.*`` callsites that include a wallet
should route it through :func:`truncate_wallet` (for single addresses
passed as an arg) or :func:`scrub_wallets_in_text` (for freeform strings
that may embed one or more wallets).

Design notes
------------
* Pass-through on non-wallet input — callers should not have to guard every
  call with ``if wallet:``. A ``None`` or obvious non-wallet string is
  returned unchanged so logs don't silently lose data.
* Display format is ``0xAbCdEfGh12...89ab`` — first 10 chars (``0x`` + 8 hex)
  plus last 4 hex, mirroring the ``mask_address`` helper already used in
  ``mcp_server/tests/e2e/shared.py``.
* Applied BEFORE logging — we never materialise a full wallet into a log
  record, so log aggregation systems (CloudWatch, Loki) never see the full
  address.
"""

from __future__ import annotations

import re
from typing import Optional

# 0x + 40 hex chars, NOT part of a longer alphanumeric run (so we don't
# truncate e.g. tx hashes or calldata by accident).
_WALLET_RE = re.compile(r"(?<![0-9a-fA-F])0x[a-fA-F0-9]{40}(?![0-9a-fA-F])")


def truncate_wallet(addr: Optional[str]) -> Optional[str]:
    """Return a log-safe form of a single wallet address.

    Examples
    --------
    >>> truncate_wallet("0x1234567890abcdef1234567890abcdef12345678")
    '0x12345678...5678'
    >>> truncate_wallet(None) is None
    True
    >>> truncate_wallet("not a wallet")
    'not a wallet'

    Parameters
    ----------
    addr:
        Candidate address. If it is not a 42-char ``0x``-prefixed hex string,
        it is returned unchanged so callers can pass through arbitrary values
        without a pre-check.
    """
    if addr is None:
        return None
    if not isinstance(addr, str):
        return addr
    s = addr.strip()
    if len(s) != 42 or not s.startswith("0x"):
        return addr  # Not a wallet — don't munge.
    # Verify the non-prefix part is hex; otherwise leave untouched.
    if not all(c in "0123456789abcdefABCDEF" for c in s[2:]):
        return addr
    return f"{s[:10]}...{s[-4:]}"


def scrub_wallets_in_text(text: Optional[str]) -> Optional[str]:
    """Replace every wallet address found in ``text`` with its truncated form.

    Use this for log messages that interpolate wallets into a longer
    freeform string (e.g. error messages bubbled up from downstream
    services).

    Examples
    --------
    >>> scrub_wallets_in_text("transfer from 0x11111111111111111111111111111111deadbeef to 0x22222222222222222222222222222222cafebabe")
    'transfer from 0x11111111...beef to 0x22222222...babe'
    >>> scrub_wallets_in_text("no wallets here")
    'no wallets here'
    >>> scrub_wallets_in_text(None) is None
    True
    """
    if text is None:
        return None
    if not isinstance(text, str):
        return text
    if not text:
        return text
    return _WALLET_RE.sub(lambda m: f"{m.group()[:10]}...{m.group()[-4:]}", text)
