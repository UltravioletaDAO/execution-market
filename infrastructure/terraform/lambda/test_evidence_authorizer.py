"""Unit tests for evidence_presign_authorizer.

Run standalone:

    pytest infrastructure/terraform/lambda/test_evidence_authorizer.py -v

Not collected by the main backend suite (pytest.ini scopes to mcp_server/tests).
Pure stdlib — no dependencies beyond pytest.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pytest


# Load the module directly by path so this test file does not require the
# infrastructure/terraform/lambda directory to be a Python package.
_MODULE_PATH = Path(__file__).parent / "evidence_presign_authorizer.py"
_SPEC = importlib.util.spec_from_file_location("evidence_presign_authorizer", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
authorizer = importlib.util.module_from_spec(_SPEC)
sys.modules["evidence_presign_authorizer"] = authorizer
_SPEC.loader.exec_module(authorizer)  # type: ignore[attr-defined]


SECRET = "test-secret-do-not-use-in-production"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _mint(
    claims: dict,
    secret: str = SECRET,
    alg: str = "HS256",
    typ: str = "JWT",
) -> str:
    header = {"alg": alg, "typ": typ}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    monkeypatch.setenv("EM_EVIDENCE_JWT_SECRET", SECRET)
    # Reset the module-level cache so each test re-reads the environment.
    authorizer._cached_secret = None
    yield
    authorizer._cached_secret = None


def _event(token: str, task_id: str | None = None) -> dict:
    headers = {}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    qs = {}
    if task_id is not None:
        qs["taskId"] = task_id
    return {
        "headers": headers,
        "queryStringParameters": qs or None,
        "pathParameters": None,
    }


def test_valid_token_returns_authorized():
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        }
    )
    response = authorizer.lambda_handler(_event(token, task_id="task-abc"), None)
    assert response["isAuthorized"] is True
    assert response["context"] == {
        "task_id": "task-abc",
        "submission_id": "sub-xyz",
        "actor_id": "executor-123",
    }


def test_valid_token_no_task_id_in_request_still_authorized():
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        }
    )
    # No taskId in the request — authorizer should still accept (cross-check is optional)
    response = authorizer.lambda_handler(_event(token, task_id=None), None)
    assert response["isAuthorized"] is True


def test_expired_token_denied():
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) - 10,  # expired 10s ago
        }
    )
    response = authorizer.lambda_handler(_event(token, task_id="task-abc"), None)
    assert response == {"isAuthorized": False}


def test_missing_claims_denied():
    token = _mint(
        {
            "task_id": "task-abc",
            # submission_id omitted
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        }
    )
    response = authorizer.lambda_handler(_event(token, task_id="task-abc"), None)
    assert response == {"isAuthorized": False}


def test_wrong_route_task_id_denied():
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        }
    )
    # Token says task-abc, request is for task-HIJACK
    response = authorizer.lambda_handler(_event(token, task_id="task-HIJACK"), None)
    assert response == {"isAuthorized": False}


def test_wrong_signature_denied():
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        },
        secret="attacker-secret",
    )
    response = authorizer.lambda_handler(_event(token, task_id="task-abc"), None)
    assert response == {"isAuthorized": False}


def test_missing_authorization_header_denied():
    response = authorizer.lambda_handler(
        {"headers": {}, "queryStringParameters": {"taskId": "task-abc"}, "pathParameters": None},
        None,
    )
    assert response == {"isAuthorized": False}


def test_empty_bearer_denied():
    response = authorizer.lambda_handler(
        {
            "headers": {"authorization": "Bearer "},
            "queryStringParameters": {"taskId": "task-abc"},
            "pathParameters": None,
        },
        None,
    )
    assert response == {"isAuthorized": False}


def test_malformed_token_denied():
    response = authorizer.lambda_handler(_event("not.a.valid.jwt", task_id="task-abc"), None)
    assert response == {"isAuthorized": False}


def test_alg_none_rejected():
    # "alg": "none" attack — ensure we never accept unsigned tokens.
    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "task_id": "task-abc",
        "submission_id": "sub-xyz",
        "actor_id": "executor-123",
        "exp": int(time.time()) + 300,
    }
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    token = f"{header_b64}.{payload_b64}."
    response = authorizer.lambda_handler(_event(token, task_id="task-abc"), None)
    assert response == {"isAuthorized": False}


def test_missing_secret_env_fails_closed(monkeypatch):
    monkeypatch.delenv("EM_EVIDENCE_JWT_SECRET", raising=False)
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        }
    )
    response = authorizer.lambda_handler(_event(token, task_id="task-abc"), None)
    assert response == {"isAuthorized": False}


def test_nbf_in_future_denied():
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 600,
            "nbf": int(time.time()) + 300,  # not valid for 5 more minutes
        }
    )
    response = authorizer.lambda_handler(_event(token, task_id="task-abc"), None)
    assert response == {"isAuthorized": False}


def test_path_and_query_both_checked():
    """If both path and query contain task_id, EVERY value must match the JWT."""
    token = _mint(
        {
            "task_id": "task-path",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        }
    )
    # Path matches, query mismatches — must deny (smuggling defense).
    event = {
        "headers": {"authorization": f"Bearer {token}"},
        "pathParameters": {"task_id": "task-path"},
        "queryStringParameters": {"taskId": "task-other"},
    }
    response = authorizer.lambda_handler(event, None)
    assert response == {"isAuthorized": False}


def test_path_and_query_both_match():
    """If both path and query carry task_id and both match, accept."""
    token = _mint(
        {
            "task_id": "task-abc",
            "submission_id": "sub-xyz",
            "actor_id": "executor-123",
            "exp": int(time.time()) + 300,
        }
    )
    event = {
        "headers": {"authorization": f"Bearer {token}"},
        "pathParameters": {"task_id": "task-abc"},
        "queryStringParameters": {"taskId": "task-abc"},
    }
    response = authorizer.lambda_handler(event, None)
    assert response["isAuthorized"] is True
    assert response["context"]["task_id"] == "task-abc"
