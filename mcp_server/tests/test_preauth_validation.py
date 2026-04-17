"""
Tests for P0-2: validate_agent_preauth temporal window validation.

Verifies that validate_agent_preauth rejects:
  - Expired pre-auths (validBefore <= now)
  - Premature pre-auths (validAfter > now + 30s clock skew tolerance)

And accepts:
  - Current valid pre-auths
  - Pre-auths with small clock skew on validAfter (within 30s tolerance)
"""

import json
import time
import pytest

from integrations.x402.payment_dispatcher import PaymentDispatcher


def _make_payload(valid_after, valid_before):
    return json.dumps(
        {
            "payload": {
                "authorization": {
                    "from": "0x" + "a" * 40,
                    "to": "0x" + "b" * 40,
                    "value": "100000",
                    "validAfter": str(valid_after),
                    "validBefore": str(valid_before),
                    "nonce": "0x" + "c" * 64,
                },
                "signature": "0x" + "d" * 130,
                "paymentInfo": {
                    "operator": "0x" + "e" * 40,
                    "token": "0x" + "f" * 40,
                    "maxAmount": "100000",
                },
            }
        }
    )


@pytest.mark.security
@pytest.mark.payments
def test_preauth_rejects_expired():
    """P0-2: validBefore in past must raise ValueError."""
    now = int(time.time())
    payload = _make_payload(valid_after=now - 3600, valid_before=now - 60)
    with pytest.raises(ValueError, match="expired"):
        PaymentDispatcher.validate_agent_preauth(payload)


@pytest.mark.security
@pytest.mark.payments
def test_preauth_rejects_premature():
    """P0-2: validAfter too far in future must raise ValueError."""
    now = int(time.time())
    payload = _make_payload(valid_after=now + 3600, valid_before=now + 7200)
    with pytest.raises(ValueError, match="not yet valid"):
        PaymentDispatcher.validate_agent_preauth(payload)


@pytest.mark.security
@pytest.mark.payments
def test_preauth_accepts_current():
    """P0-2: valid window around now passes."""
    now = int(time.time())
    payload = _make_payload(valid_after=now - 60, valid_before=now + 3600)
    result = PaymentDispatcher.validate_agent_preauth(payload)
    assert result["payload"]["authorization"]["from"].startswith("0x")


@pytest.mark.security
@pytest.mark.payments
def test_preauth_clock_skew_tolerance():
    """P0-2: 30s clock skew on validAfter is tolerated."""
    now = int(time.time())
    payload = _make_payload(valid_after=now + 15, valid_before=now + 3600)
    # Should not raise
    PaymentDispatcher.validate_agent_preauth(payload)
