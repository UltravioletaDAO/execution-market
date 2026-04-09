"""
Phase 0 GR-0.4 — tests for the hardened /api/v1/evidence/verify endpoint.

Covers:
  - Auth required (anonymous callers rejected with 401)
  - SSRF blocked: raw IPs, http://, javascript:, file://, VPC hosts
  - Host allowlist enforced
  - Redirects rejected (follow_redirects=False)
  - Oversized response body rejected (10 MB cap)

See docs/reports/security-audit-2026-04-07/specialists/SC_05_BACKEND_API.md [API-004]
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.security, pytest.mark.core]

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_auth(anonymous: bool = False):
    from api.auth import AgentAuth

    if anonymous:
        return AgentAuth(
            agent_id="2106",
            tier="free",
            auth_method="anonymous",
        )
    return AgentAuth(
        agent_id="0xabc1234567890abc1234567890abc1234567890a",
        wallet_address="0xabc1234567890abc1234567890abc1234567890a",
        auth_method="erc8128",
    )


def _make_request(url: str):
    from api.routers._models import VerifyEvidenceRequest

    return VerifyEvidenceRequest(
        task_id="11111111-2222-3333-4444-555555555555",
        evidence_url=url,
        evidence_type="photo",
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestEvidenceVerifyAuth:
    @pytest.mark.asyncio
    async def test_anonymous_caller_rejected_401(self, monkeypatch):
        """Anonymous callers MUST be rejected — closes API-004."""
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence

        monkeypatch.setenv("EM_EVIDENCE_ALLOWED_HOSTS", "cdn.execution.market")
        # Re-import to pick up env var if needed — not strictly required
        # because we are blocked on auth before host validation.

        req = _make_request("https://cdn.execution.market/evidence/ok.jpg")
        auth = _make_auth(anonymous=True)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticated_caller_passes_auth_gate(self, monkeypatch):
        """An ERC-8128 authenticated caller does NOT 401."""
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        # Make sure allowlist contains our test host.
        monkeypatch.setattr(
            misc,
            "ALLOWED_EVIDENCE_HOSTS",
            frozenset({"cdn.execution.market"}),
        )

        req = _make_request("https://cdn.execution.market/evidence/ok.jpg")
        auth = _make_auth(anonymous=False)

        mock_task = {
            "id": req.task_id,
            "title": "t",
            "category": "general",
            "instructions": "",
            "evidence_schema": {},
        }

        mock_verifier = MagicMock()
        mock_verifier.is_available = False

        with (
            patch(
                "api.routers.misc.db.get_task", new=AsyncMock(return_value=mock_task)
            ),
            patch(
                "api.verification_helpers.get_verifier",
                return_value=mock_verifier,
            ),
        ):
            response = await verify_evidence(req, auth)

        assert response.verified is True  # verifier unavailable fallback
        assert response.decision == "approved"


# ---------------------------------------------------------------------------
# SSRF / host allowlist
# ---------------------------------------------------------------------------


class TestEvidenceVerifyHostAllowlist:
    def setup_method(self):
        from api.routers.misc import _validate_evidence_url  # noqa: F401

    @pytest.mark.asyncio
    async def test_rejects_raw_ipv4(self, monkeypatch):
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        # AWS instance metadata
        req = _make_request("https://169.254.169.254/latest/meta-data/")
        auth = _make_auth(anonymous=False)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)
        assert exc.value.status_code == 400
        assert "IP" in exc.value.detail or "allowlist" in exc.value.detail

    @pytest.mark.asyncio
    async def test_rejects_ipv6_localhost(self, monkeypatch):
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        req = _make_request("https://[::1]/internal")
        auth = _make_auth(anonymous=False)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_http_scheme(self, monkeypatch):
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        req = _make_request("http://cdn.execution.market/evidence/ok.jpg")
        auth = _make_auth(anonymous=False)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)
        assert exc.value.status_code == 400
        assert "https" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_file_scheme(self, monkeypatch):
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        req = _make_request("file:///etc/passwd")
        auth = _make_auth(anonymous=False)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_javascript_scheme(self, monkeypatch):
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        req = _make_request("javascript:alert(1)")
        auth = _make_auth(anonymous=False)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_unknown_host(self, monkeypatch):
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        req = _make_request("https://evil.example.com/pwn.jpg")
        auth = _make_auth(anonymous=False)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)
        assert exc.value.status_code == 400
        assert "allowlist" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_vpc_internal_host(self, monkeypatch):
        from fastapi import HTTPException
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        # ECS task metadata endpoint
        req = _make_request("https://169.254.170.2/v4/metadata")
        auth = _make_auth(anonymous=False)

        with pytest.raises(HTTPException) as exc:
            await verify_evidence(req, auth)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_allows_cdn_execution_market(self, monkeypatch):
        """Our own CDN must be allowed."""
        from api.routers.misc import verify_evidence
        import api.routers.misc as misc

        monkeypatch.setattr(
            misc, "ALLOWED_EVIDENCE_HOSTS", frozenset({"cdn.execution.market"})
        )

        req = _make_request("https://cdn.execution.market/evidence/ok.jpg")
        auth = _make_auth(anonymous=False)

        mock_task = {
            "id": req.task_id,
            "title": "t",
            "category": "general",
            "instructions": "",
            "evidence_schema": {},
        }

        mock_verifier = MagicMock()
        mock_verifier.is_available = False
        with (
            patch(
                "api.routers.misc.db.get_task", new=AsyncMock(return_value=mock_task)
            ),
            patch("api.verification_helpers.get_verifier", return_value=mock_verifier),
        ):
            response = await verify_evidence(req, auth)
        assert response.decision == "approved"  # verifier unavailable fallback


# ---------------------------------------------------------------------------
# Redirect & size cap (on the underlying _download_image)
# ---------------------------------------------------------------------------


class TestEvidenceDownloadHardening:
    @pytest.mark.asyncio
    async def test_download_rejects_3xx_redirect(self):
        """Redirect responses MUST be rejected."""
        import httpx

        from verification.ai_review import AIVerifier

        verifier = AIVerifier(provider=MagicMock())

        def mock_transport(request):
            return httpx.Response(
                302,
                headers={"Location": "http://169.254.169.254/"},
            )

        transport = httpx.MockTransport(mock_transport)
        # Patch AsyncClient to use our transport.
        real_client = httpx.AsyncClient

        class _FakeClient(real_client):
            def __init__(self, *a, **kw):
                kw["transport"] = transport
                super().__init__(*a, **kw)

        with patch("verification.ai_review.httpx.AsyncClient", _FakeClient):
            with pytest.raises(httpx.HTTPStatusError):
                await verifier._download_image(
                    "https://cdn.execution.market/evidence/x.jpg"
                )

    @pytest.mark.asyncio
    async def test_download_rejects_oversized_content_length(self):
        import httpx

        from verification.ai_review import AIVerifier, MAX_EVIDENCE_DOWNLOAD_BYTES

        verifier = AIVerifier(provider=MagicMock())

        too_big = str(MAX_EVIDENCE_DOWNLOAD_BYTES + 1)

        def mock_transport(request):
            return httpx.Response(
                200,
                headers={"content-length": too_big, "content-type": "image/jpeg"},
                content=b"x",
            )

        transport = httpx.MockTransport(mock_transport)
        real_client = httpx.AsyncClient

        class _FakeClient(real_client):
            def __init__(self, *a, **kw):
                kw["transport"] = transport
                super().__init__(*a, **kw)

        with patch("verification.ai_review.httpx.AsyncClient", _FakeClient):
            with pytest.raises(ValueError, match="too large"):
                await verifier._download_image(
                    "https://cdn.execution.market/evidence/x.jpg"
                )

    @pytest.mark.asyncio
    async def test_download_rejects_chunked_oversized(self):
        """Even without Content-Length, streaming cap must trip."""
        import httpx

        from verification.ai_review import AIVerifier, MAX_EVIDENCE_DOWNLOAD_BYTES

        verifier = AIVerifier(provider=MagicMock())

        huge = b"A" * (MAX_EVIDENCE_DOWNLOAD_BYTES + 100)

        def mock_transport(request):
            return httpx.Response(
                200,
                headers={"content-type": "image/jpeg"},
                content=huge,
            )

        transport = httpx.MockTransport(mock_transport)
        real_client = httpx.AsyncClient

        class _FakeClient(real_client):
            def __init__(self, *a, **kw):
                kw["transport"] = transport
                super().__init__(*a, **kw)

        with patch("verification.ai_review.httpx.AsyncClient", _FakeClient):
            with pytest.raises(ValueError, match="too large"):
                await verifier._download_image(
                    "https://cdn.execution.market/evidence/big.jpg"
                )

    @pytest.mark.asyncio
    async def test_download_accepts_small_image(self):
        """Normal small responses work fine."""
        import httpx

        from verification.ai_review import AIVerifier

        verifier = AIVerifier(provider=MagicMock())

        payload = b"\x89PNG\r\n\x1a\n" + b"x" * 1024  # ~1 KB

        def mock_transport(request):
            return httpx.Response(
                200,
                headers={"content-type": "image/png"},
                content=payload,
            )

        transport = httpx.MockTransport(mock_transport)
        real_client = httpx.AsyncClient

        class _FakeClient(real_client):
            def __init__(self, *a, **kw):
                kw["transport"] = transport
                super().__init__(*a, **kw)

        with patch("verification.ai_review.httpx.AsyncClient", _FakeClient):
            result = await verifier._download_image(
                "https://cdn.execution.market/evidence/tiny.png"
            )
        assert result == payload


# ---------------------------------------------------------------------------
# Host derivation from env
# ---------------------------------------------------------------------------


class TestAllowedHostsDerivation:
    def test_derive_includes_baseline(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("VITE_SUPABASE_URL", raising=False)
        monkeypatch.delenv("EVIDENCE_PUBLIC_BASE_URL", raising=False)
        monkeypatch.delenv("EVIDENCE_BUCKET", raising=False)
        monkeypatch.delenv("EM_EVIDENCE_ALLOWED_HOSTS", raising=False)

        from api.routers.misc import _derive_allowed_evidence_hosts

        hosts = _derive_allowed_evidence_hosts()
        assert "execution.market" in hosts
        assert "api.execution.market" in hosts
        assert "cdn.execution.market" in hosts

    def test_derive_adds_supabase_host(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://abcxyz.supabase.co")
        from api.routers.misc import _derive_allowed_evidence_hosts

        hosts = _derive_allowed_evidence_hosts()
        assert "abcxyz.supabase.co" in hosts

    def test_derive_adds_s3_bucket_host(self, monkeypatch):
        monkeypatch.setenv("EVIDENCE_BUCKET", "em-evidence-bucket")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-2")
        from api.routers.misc import _derive_allowed_evidence_hosts

        hosts = _derive_allowed_evidence_hosts()
        assert "em-evidence-bucket.s3.us-east-2.amazonaws.com" in hosts
        assert "em-evidence-bucket.s3.amazonaws.com" in hosts

    def test_derive_adds_extra_hosts(self, monkeypatch):
        monkeypatch.setenv("EM_EVIDENCE_ALLOWED_HOSTS", "foo.com, bar.com")
        from api.routers.misc import _derive_allowed_evidence_hosts

        hosts = _derive_allowed_evidence_hosts()
        assert "foo.com" in hosts
        assert "bar.com" in hosts
