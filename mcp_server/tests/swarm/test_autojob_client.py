"""
Tests for AutoJobClient — EM ↔ AutoJob intelligence bridge.

Covers:
  1. AutoJobEnrichment dataclass & composite_boost
  2. AutoJobRouteResult construction
  3. AutoJobHealth dataclass
  4. AutoJobClient HTTP methods (mocked)
  5. EnrichedOrchestrator caching & fallback
  6. Error handling & retries
  7. Availability caching
  8. Worker profile retrieval
"""

import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

import pytest

from mcp_server.swarm.autojob_client import (
    AutoJobClient,
    AutoJobEnrichment,
    AutoJobHealth,
    AutoJobRouteResult,
    EnrichedOrchestrator,
)


# ─── Section 1: AutoJobEnrichment ─────────────────────────────

class TestAutoJobEnrichment:
    def test_default_values(self):
        e = AutoJobEnrichment(wallet="0xABC")
        assert e.wallet == "0xABC"
        assert e.match_score == 0.0
        assert e.tier == "Unranked"
        assert e.on_chain_registered is False

    def test_composite_boost_zero_score(self):
        e = AutoJobEnrichment(wallet="0xABC")
        boost = e.to_composite_boost()
        assert boost["total_boost"] == 0.0
        assert boost["confidence"] == 0.0
        assert boost["skill_boost"] == 0.0

    def test_composite_boost_high_score(self):
        e = AutoJobEnrichment(
            wallet="0xABC",
            match_score=0.9,
            skill_match=80.0,
            reputation_score=90.0,
            reliability_score=85.0,
        )
        boost = e.to_composite_boost()
        assert boost["total_boost"] == 0.9 * 15  # 13.5
        assert boost["skill_boost"] == 80.0 * 0.5
        assert boost["reputation_boost"] == 90.0 * 0.3
        assert boost["reliability_boost"] == 85.0 * 0.2

    def test_composite_boost_confidence_capped(self):
        e = AutoJobEnrichment(wallet="0x1", match_score=1.0)
        boost = e.to_composite_boost()
        assert boost["confidence"] == 1.0  # min(1.5, 1.0) = 1.0

    def test_composite_boost_confidence_scales(self):
        e = AutoJobEnrichment(wallet="0x1", match_score=0.5)
        boost = e.to_composite_boost()
        assert boost["confidence"] == 0.75  # 0.5 * 1.5

    def test_enrichment_with_explanation(self):
        e = AutoJobEnrichment(
            wallet="0xDEF",
            match_score=0.85,
            match_explanation="High skill match for photography",
        )
        assert "photography" in e.match_explanation


# ─── Section 2: AutoJobRouteResult ────────────────────────────

class TestAutoJobRouteResult:
    def test_empty_result(self):
        r = AutoJobRouteResult(
            task_id="t1",
            task_category="photo",
            total_candidates=0,
            qualified_candidates=0,
            match_time_ms=0,
        )
        assert r.best_match is None
        assert r.rankings == []

    def test_result_with_rankings(self):
        r = AutoJobRouteResult(
            task_id="t1",
            task_category="delivery",
            total_candidates=10,
            qualified_candidates=3,
            match_time_ms=45.2,
            best_match={"wallet": "0xBEST", "score": 0.95},
            rankings=[
                {"wallet": "0xBEST", "score": 0.95},
                {"wallet": "0xGOOD", "score": 0.80},
            ],
        )
        assert r.qualified_candidates == 3
        assert len(r.rankings) == 2


# ─── Section 3: AutoJobHealth ─────────────────────────────────

class TestAutoJobHealth:
    def test_defaults(self):
        h = AutoJobHealth()
        assert h.overall == "unknown"
        assert h.workers_total == 0
        assert h.matching_ready is False

    def test_healthy_state(self):
        h = AutoJobHealth(
            overall="optimal",
            workers_total=6,
            erc8004_coverage_pct=83.0,
            matching_ready=True,
            checks={"skill_data": "green", "evidence": "green"},
        )
        assert h.overall == "optimal"
        assert h.erc8004_coverage_pct == 83.0
        assert len(h.checks) == 2


# ─── Section 4: AutoJobClient HTTP (Mocked) ──────────────────

class TestAutoJobClientMocked:
    """Test client with mocked HTTP responses."""

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_enrich_agents_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "enrichments": {
                "0xAAA": {
                    "wallet": "0xAAA",
                    "match_score": 0.85,
                    "predicted_quality": 0.90,
                    "tier": "Gold",
                    "on_chain_registered": True,
                },
            },
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient(base_url="http://localhost:8765")
        result = client.enrich_agents(
            task={"id": "t1", "category": "photo"},
            wallets=["0xAAA"],
        )
        assert "0xAAA" in result
        assert result["0xAAA"].match_score == 0.85
        assert result["0xAAA"].tier == "Gold"

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_enrich_agents_failure_fallback(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": False,
            "error": "internal error",
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        result = client.enrich_agents(
            task={"id": "t1"},
            wallets=["0xBBB", "0xCCC"],
        )
        # Fallback: empty enrichments for all wallets
        assert len(result) == 2
        assert result["0xBBB"].match_score == 0.0
        assert result["0xCCC"].tier == "Unranked"

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_route_task_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "task_id": "t1",
            "task_category": "delivery",
            "total_candidates": 5,
            "qualified_candidates": 2,
            "match_time_ms": 32.5,
            "best_match": {"wallet": "0xTOP", "score": 92.3},
            "rankings": [{"wallet": "0xTOP"}, {"wallet": "0x2ND"}],
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        result = client.route_task(task={"id": "t1", "category": "delivery"})
        assert result.task_id == "t1"
        assert result.qualified_candidates == 2
        assert result.best_match["wallet"] == "0xTOP"

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_route_task_failure(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": False}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        result = client.route_task(task={"id": "t2", "category": "photo"})
        assert result.total_candidates == 0
        assert result.best_match is None

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_health_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "health": {"overall": "optimal", "checks": {"data": "green"}},
            "status": {
                "workers": {"total": 6},
                "erc8004": {"coverage_pct": 83.3},
                "matching": {"ready": True},
            },
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        health = client.get_health()
        assert health.overall == "optimal"
        assert health.workers_total == 6
        assert health.matching_ready is True

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_health_failure(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": False}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        health = client.get_health()
        assert health.overall == "unknown"
        assert health.matching_ready is False

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_worker_profile(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "worker": {
                "wallet": "0x52E0",
                "skills": {"photography": {"level": "EXPERT"}},
            },
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        profile = client.get_worker_profile("0x52E0")
        assert profile is not None
        assert profile["wallet"] == "0x52E0"

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_worker_profile_not_found(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": False}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        profile = client.get_worker_profile("0xNONE")
        assert profile is None


# ─── Section 5: Availability Caching ──────────────────────────

class TestAvailabilityCaching:
    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_availability_caches_result(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        
        # First call hits the API
        assert client.is_available() is True
        assert mock_urlopen.call_count == 1

        # Second call uses cache
        assert client.is_available() is True
        assert mock_urlopen.call_count == 1  # Not incremented

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_availability_force_check(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = AutoJobClient()
        client.is_available()
        client.is_available(force_check=True)
        assert mock_urlopen.call_count == 2  # Forced second call

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_availability_handles_exception(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        client = AutoJobClient()
        assert client.is_available() is False


# ─── Section 6: Error Handling & Retries ──────────────────────

class TestErrorHandling:
    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_network_error_with_fallback(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        client = AutoJobClient(fallback_on_error=True, retries=0)
        result = client.enrich_agents({"id": "t1"}, ["0xABC"])
        # Should fallback to empty enrichments
        assert "0xABC" in result
        assert result["0xABC"].match_score == 0.0

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_network_error_without_fallback(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        client = AutoJobClient(fallback_on_error=False, retries=0)
        with pytest.raises(URLError):
            client._post("/api/test", {})

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_retry_on_failure(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Timeout")

        client = AutoJobClient(retries=2, fallback_on_error=True)
        # Should attempt 3 times (initial + 2 retries)
        client._post("/api/test", {})
        assert mock_urlopen.call_count == 3

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_timeout_handling(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("Read timed out")

        client = AutoJobClient(retries=0, fallback_on_error=True)
        result = client._get("/api/health")
        assert result["success"] is False


# ─── Section 7: EnrichedOrchestrator ──────────────────────────

class TestEnrichedOrchestrator:
    def _make_mock_orchestrator(self):
        orch = MagicMock()
        orch._internal = {}
        return orch

    def test_constructor(self):
        orch = self._make_mock_orchestrator()
        client = MagicMock()
        enriched = EnrichedOrchestrator(orch, client, enrichment_weight=0.4)
        assert enriched.enrichment_weight == 0.4

    def test_route_requires_task_request(self):
        orch = self._make_mock_orchestrator()
        client = MagicMock()
        enriched = EnrichedOrchestrator(orch, client)

        with pytest.raises(TypeError, match="Expected TaskRequest"):
            enriched.route_task({"id": "t1"})  # dict, not TaskRequest

    def test_cache_eviction(self):
        orch = self._make_mock_orchestrator()
        client = MagicMock()
        enriched = EnrichedOrchestrator(orch, client)
        enriched._cache_maxsize = 3

        # Fill cache
        for i in range(5):
            enriched._enrichment_cache[f"key_{i}"] = {"data": i}
            while len(enriched._enrichment_cache) > enriched._cache_maxsize:
                enriched._enrichment_cache.popitem(last=False)

        assert len(enriched._enrichment_cache) == 3
        assert "key_0" not in enriched._enrichment_cache
        assert "key_4" in enriched._enrichment_cache


# ─── Section 8: Client Configuration ─────────────────────────

class TestClientConfiguration:
    def test_base_url_trailing_slash(self):
        client = AutoJobClient(base_url="http://localhost:8765/")
        assert client.base_url == "http://localhost:8765"

    def test_default_configuration(self):
        client = AutoJobClient()
        assert client.base_url == "http://localhost:8765"
        assert client.timeout == 5.0
        assert client.retries == 1
        assert client.fallback_on_error is True

    def test_custom_configuration(self):
        client = AutoJobClient(
            base_url="http://autojob:9000",
            timeout_seconds=10.0,
            retries=3,
            fallback_on_error=False,
        )
        assert client.base_url == "http://autojob:9000"
        assert client.timeout == 10.0
        assert client.retries == 3
        assert client.fallback_on_error is False
