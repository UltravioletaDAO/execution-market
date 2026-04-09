"""
Phase 0 GR-0.4 — tests for integrations.evidence.jwt_helper.

Covers:
  - Mint succeeds when EM_EVIDENCE_JWT_SECRET is set
  - Missing secret raises RuntimeError
  - Roundtrip mint -> decode preserves claims
  - Expired tokens are rejected
  - Issuer/audience mismatches are rejected
  - Empty required claims are rejected

See docs/reports/security-audit-2026-04-07/specialists/SC_05_BACKEND_API.md
"""

import sys
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.core]

sys.path.insert(0, str(Path(__file__).parent.parent))


# A dummy secret used only in tests. Never a real key — defense in depth
# against the Phase 0 hardcoded-key pre-commit hook.
_TEST_SECRET = "phase-0-test-secret-do-not-use-in-prod-aaaaaaaaaaaaaaaa"


def test_mint_requires_secret(monkeypatch):
    monkeypatch.delenv("EM_EVIDENCE_JWT_SECRET", raising=False)

    from integrations.evidence.jwt_helper import mint_evidence_jwt

    with pytest.raises(RuntimeError, match="EM_EVIDENCE_JWT_SECRET"):
        mint_evidence_jwt("task-1", "sub-1", "actor-1")


def test_mint_succeeds_with_secret(monkeypatch):
    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    from integrations.evidence.jwt_helper import mint_evidence_jwt

    token = mint_evidence_jwt(
        task_id="11111111-2222-3333-4444-555555555555",
        submission_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        actor_id="0xabc1234567890abc1234567890abc1234567890a",
    )

    assert isinstance(token, str)
    # JWT has 3 base64 segments separated by dots.
    assert token.count(".") == 2


def test_roundtrip_preserves_claims(monkeypatch):
    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    from integrations.evidence.jwt_helper import (
        mint_evidence_jwt,
        decode_evidence_jwt,
    )

    token = mint_evidence_jwt(
        task_id="task-abc",
        submission_id="sub-xyz",
        actor_id="executor-42",
    )

    decoded = decode_evidence_jwt(token)
    assert decoded["task_id"] == "task-abc"
    assert decoded["submission_id"] == "sub-xyz"
    assert decoded["actor_id"] == "executor-42"
    assert decoded["iss"] == "execution-market-backend"
    assert decoded["aud"] == "evidence-presign-lambda"
    assert "iat" in decoded
    assert "exp" in decoded
    assert decoded["exp"] > decoded["iat"]


def test_expired_token_rejected(monkeypatch):
    import jwt as pyjwt

    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    from integrations.evidence.jwt_helper import (
        mint_evidence_jwt,
        decode_evidence_jwt,
    )

    # Mint with ttl=1s, then wait it out.
    token = mint_evidence_jwt(
        task_id="t", submission_id="s", actor_id="a", ttl_seconds=1
    )
    time.sleep(2)

    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_evidence_jwt(token)


def test_wrong_secret_rejected(monkeypatch):
    import jwt as pyjwt

    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    from integrations.evidence.jwt_helper import mint_evidence_jwt

    token = mint_evidence_jwt("t", "s", "a")

    # Swap to a different secret and try to decode — must fail.
    monkeypatch.setenv(
        "EM_EVIDENCE_JWT_SECRET",
        "different-secret-also-dummy-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    from integrations.evidence.jwt_helper import decode_evidence_jwt

    with pytest.raises(pyjwt.InvalidSignatureError):
        decode_evidence_jwt(token)


def test_wrong_audience_rejected(monkeypatch):
    import jwt as pyjwt

    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    # Hand-craft a token with a different audience and verify rejection.
    bad_token = pyjwt.encode(
        {
            "task_id": "t",
            "submission_id": "s",
            "actor_id": "a",
            "iss": "execution-market-backend",
            "aud": "some-other-audience",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        _TEST_SECRET,
        algorithm="HS256",
    )

    from integrations.evidence.jwt_helper import decode_evidence_jwt

    with pytest.raises(pyjwt.InvalidAudienceError):
        decode_evidence_jwt(bad_token)


def test_wrong_issuer_rejected(monkeypatch):
    import jwt as pyjwt

    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    bad_token = pyjwt.encode(
        {
            "task_id": "t",
            "submission_id": "s",
            "actor_id": "a",
            "iss": "attacker",
            "aud": "evidence-presign-lambda",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        _TEST_SECRET,
        algorithm="HS256",
    )

    from integrations.evidence.jwt_helper import decode_evidence_jwt

    with pytest.raises(pyjwt.InvalidIssuerError):
        decode_evidence_jwt(bad_token)


def test_empty_claims_rejected(monkeypatch):
    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    from integrations.evidence.jwt_helper import mint_evidence_jwt

    with pytest.raises(ValueError, match="task_id"):
        mint_evidence_jwt("", "sub", "actor")
    with pytest.raises(ValueError, match="submission_id"):
        mint_evidence_jwt("task", "", "actor")
    with pytest.raises(ValueError, match="actor_id"):
        mint_evidence_jwt("task", "sub", "")


def test_default_ttl_is_five_minutes(monkeypatch):
    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", _TEST_SECRET)

    from integrations.evidence.jwt_helper import (
        mint_evidence_jwt,
        decode_evidence_jwt,
    )

    token = mint_evidence_jwt("t", "s", "a")
    decoded = decode_evidence_jwt(token)
    ttl = decoded["exp"] - decoded["iat"]
    assert ttl == 300  # 5 minutes


def test_public_reexport():
    """mint_evidence_jwt is exported at package level."""
    from integrations.evidence import mint_evidence_jwt  # noqa: F401
