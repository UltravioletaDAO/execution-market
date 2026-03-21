"""
Tests for AutoJobClient — Enrichment bridge between EM Swarm and AutoJob.

Covers:
    - AutoJobEnrichment data class and composite boost
    - AutoJobRouteResult and AutoJobHealth data classes
    - AutoJobClient HTTP methods with mocked responses
    - AutoJobClient error handling and fallback
    - AutoJobClient availability caching
    - EnrichedOrchestrator routing with/without AutoJob
    - EnrichedOrchestrator LRU enrichment cache
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.swarm.autojob_client import (
    AutoJobEnrichment,
    AutoJobRouteResult,
    AutoJobHealth,
    AutoJobClient,
    EnrichedOrchestrator,
)


# ─── AutoJobEnrichment ───────────────────────────────────────────────────────


class TestAutoJobEnrichment:
    def test_default_values(self):
        e = AutoJobEnrichment(wallet="0xABC")
        assert e.wallet == "0xABC"
        assert e.match_score == 0.0
        assert e.predicted_quality == 0.0
        assert e.predicted_success == 0.0
        assert e.tier == "Unranked"
        assert e.skill_match == 0.0
        assert e.on_chain_registered is False

    def test_full_construction(self):
        e = AutoJobEnrichment(
            wallet="0xDEF",
            match_score=0.85,
            predicted_quality=0.9,
            predicted_success=0.75,
            tier="Gold",
            skill_match=82.5,
            reputation_score=90.0,
            reliability_score=88.0,
            recency_score=70.0,
            on_chain_registered=True,
            category_experience=0.6,
            match_explanation="Strong delivery history",
        )
        assert e.match_score == 0.85
        assert e.tier == "Gold"
        assert e.on_chain_registered is True

    def test_composite_boost(self):
        e = AutoJobEnrichment(
            wallet="0x123",
            match_score=0.8,
            skill_match=80.0,
            reputation_score=70.0,
            reliability_score=60.0,
        )
        boost = e.to_composite_boost()
        assert "skill_boost" in boost
        assert "reputation_boost" in boost
        assert "reliability_boost" in boost
        assert "total_boost" in boost
        assert "confidence" in boost
        assert boost["total_boost"] == 0.8 * 15  # 12.0
        assert boost["skill_boost"] == 80.0 * 0.5  # 40.0
        assert boost["reputation_boost"] == 70.0 * 0.3  # 21.0
        assert boost["reliability_boost"] == 60.0 * 0.2  # 12.0

    def test_composite_boost_confidence_capped(self):
        e = AutoJobEnrichment(wallet="0x1", match_score=0.9)
        boost = e.to_composite_boost()
        assert boost["confidence"] == min(0.9 * 1.5, 1.0)  # 1.0

    def test_composite_boost_zero_match(self):
        e = AutoJobEnrichment(wallet="0x0")
        boost = e.to_composite_boost()
        assert boost["total_boost"] == 0.0
        assert boost["confidence"] == 0.0


# ─── AutoJobRouteResult ──────────────────────────────────────────────────────


class TestAutoJobRouteResult:
    def test_defaults(self):
        r = AutoJobRouteResult(
            task_id="t1",
            task_category="delivery",
            total_candidates=10,
            qualified_candidates=3,
            match_time_ms=45.2,
        )
        assert r.task_id == "t1"
        assert r.best_match is None
        assert r.rankings == []

    def test_with_rankings(self):
        r = AutoJobRouteResult(
            task_id="t1",
            task_category="coding",
            total_candidates=5,
            qualified_candidates=2,
            match_time_ms=12.0,
            best_match={"wallet": "0xBest", "score": 92},
            rankings=[
                {"wallet": "0xBest", "score": 92},
                {"wallet": "0xSecond", "score": 78},
            ],
        )
        assert len(r.rankings) == 2
        assert r.best_match["wallet"] == "0xBest"


# ─── AutoJobHealth ────────────────────────────────────────────────────────────


class TestAutoJobHealth:
    def test_defaults(self):
        h = AutoJobHealth()
        assert h.overall == "unknown"
        assert h.workers_total == 0
        assert h.erc8004_coverage_pct == 0.0
        assert h.matching_ready is False

    def test_full(self):
        h = AutoJobHealth(
            overall="optimal",
            workers_total=24,
            erc8004_coverage_pct=87.5,
            matching_ready=True,
            checks={"sync": "pass", "db": "pass"},
        )
        assert h.overall == "optimal"
        assert h.workers_total == 24


# ─── AutoJobClient ────────────────────────────────────────────────────────────


class TestAutoJobClient:
    @pytest.fixture
    def client(self):
        return AutoJobClient(
            base_url="http://localhost:8765",
            timeout_seconds=2.0,
            retries=0,
            fallback_on_error=True,
        )

    def test_init(self, client):
        assert client.base_url == "http://localhost:8765"
        assert client.timeout == 2.0
        assert client.retries == 0
        assert client.fallback_on_error is True

    def test_init_strips_trailing_slash(self):
        c = AutoJobClient(base_url="http://localhost:8765/")
        assert c.base_url == "http://localhost:8765"

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_enrich_agents_success(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "success": True,
                "enrichments": {
                    "0xABC": {
                        "wallet": "0xABC",
                        "match_score": 0.85,
                        "predicted_quality": 0.9,
                        "tier": "Gold",
                        "skill_match": 82.5,
                        "reputation_score": 90.0,
                        "reliability_score": 88.0,
                        "on_chain_registered": True,
                    },
                    "0xDEF": {
                        "wallet": "0xDEF",
                        "match_score": 0.4,
                        "tier": "Bronze",
                    },
                },
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.enrich_agents(
            task={"id": "t1", "category": "delivery"},
            wallets=["0xABC", "0xDEF"],
        )

        assert len(result) == 2
        assert result["0xABC"].match_score == 0.85
        assert result["0xABC"].tier == "Gold"
        assert result["0xDEF"].match_score == 0.4

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_enrich_agents_failure_fallback(self, mock_urlopen, client):
        """On failure, returns empty enrichments for all wallets."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "success": False,
                "error": "service unavailable",
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.enrich_agents(
            task={"id": "t1"},
            wallets=["0xABC", "0xDEF"],
        )
        assert len(result) == 2
        assert result["0xABC"].match_score == 0.0
        assert result["0xDEF"].tier == "Unranked"

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_enrich_agents_network_error(self, mock_urlopen, client):
        """Network error with fallback_on_error=True should not raise."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("connection refused")

        result = client.enrich_agents(
            task={"id": "t1"},
            wallets=["0xABC"],
        )
        assert len(result) == 1
        assert result["0xABC"].match_score == 0.0

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_route_task_success(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "success": True,
                "task_id": "t1",
                "task_category": "delivery",
                "total_candidates": 24,
                "qualified_candidates": 8,
                "match_time_ms": 32.5,
                "best_match": {"wallet": "0xBest", "score": 95},
                "rankings": [
                    {"wallet": "0xBest", "score": 95},
                    {"wallet": "0xSecond", "score": 80},
                ],
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.route_task(task={"id": "t1", "category": "delivery"})
        assert isinstance(result, AutoJobRouteResult)
        assert result.task_id == "t1"
        assert result.total_candidates == 24
        assert result.qualified_candidates == 8
        assert result.best_match["wallet"] == "0xBest"
        assert len(result.rankings) == 2

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_route_task_failure(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "success": False,
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.route_task(task={"id": "t1", "category": "general"})
        assert result.total_candidates == 0
        assert result.qualified_candidates == 0

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_health_success(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "success": True,
                "health": {
                    "overall": "optimal",
                    "checks": {"sync": "pass"},
                },
                "status": {
                    "workers": {"total": 24},
                    "erc8004": {"coverage_pct": 87.5},
                    "matching": {"ready": True},
                },
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        health = client.get_health()
        assert isinstance(health, AutoJobHealth)
        assert health.overall == "optimal"
        assert health.workers_total == 24
        assert health.erc8004_coverage_pct == 87.5
        assert health.matching_ready is True

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_health_failure(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": False}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        health = client.get_health()
        assert health.overall == "unknown"

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_is_available_caches_result(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # First call hits API
        assert client.is_available() is True
        # Second call should use cache (within 60s)
        assert client.is_available() is True
        # Only one actual API call
        assert mock_urlopen.call_count == 1

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_is_available_force_check(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client.is_available()
        client.is_available(force_check=True)
        assert mock_urlopen.call_count == 2

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_is_available_network_error(self, mock_urlopen, client):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("refused")

        assert client.is_available() is False

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_worker_profile_success(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "success": True,
                "worker": {
                    "wallet": "0xABC",
                    "skills": {"delivery": 0.8},
                    "task_count": 15,
                },
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        profile = client.get_worker_profile("0xABC")
        assert profile is not None
        assert profile["wallet"] == "0xABC"
        assert profile["task_count"] == 15

    @patch("mcp_server.swarm.autojob_client.urlopen")
    def test_get_worker_profile_not_found(self, mock_urlopen, client):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": False}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        profile = client.get_worker_profile("0xNonexistent")
        assert profile is None

    def test_retry_disabled(self):
        """With retries=0, should only attempt once."""
        client = AutoJobClient(retries=0, fallback_on_error=True)
        with patch("mcp_server.swarm.autojob_client.urlopen") as mock_url:
            from urllib.error import URLError

            mock_url.side_effect = URLError("refused")
            result = client._get("/test")
            assert mock_url.call_count == 1
            assert result.get("success") is False

    def test_retries_enabled(self):
        """With retries=2, should attempt 3 times total."""
        client = AutoJobClient(retries=2, timeout_seconds=0.1, fallback_on_error=True)
        with patch("mcp_server.swarm.autojob_client.urlopen") as mock_url:
            from urllib.error import URLError

            mock_url.side_effect = URLError("refused")
            with patch("time.sleep"):  # Don't actually sleep
                client._get("/test")
            assert mock_url.call_count == 3

    def test_no_fallback_raises(self):
        """With fallback_on_error=False, should raise on error."""
        client = AutoJobClient(retries=0, fallback_on_error=False)
        with patch("mcp_server.swarm.autojob_client.urlopen") as mock_url:
            from urllib.error import URLError

            mock_url.side_effect = URLError("refused")
            with pytest.raises(URLError):
                client._get("/test")


# ─── EnrichedOrchestrator ────────────────────────────────────────────────────


class TestEnrichedOrchestrator:
    def _make_mock_orchestrator(self):
        orch = MagicMock()
        orch.lifecycle = MagicMock()
        orch._internal = {}
        return orch

    def _make_task_request(
        self, task_id="t1", categories=None, title="Test", bounty=5.0
    ):
        """Create a TaskRequest-compatible mock."""
        from mcp_server.swarm.orchestrator import TaskRequest, TaskPriority

        return TaskRequest(
            task_id=task_id,
            title=title,
            categories=categories or ["delivery"],
            bounty_usd=bounty,
            priority=TaskPriority.NORMAL,
        )

    def test_route_without_autojob(self):
        """When AutoJob is unavailable, falls through to native routing."""
        orch = self._make_mock_orchestrator()
        orch.route_task.return_value = MagicMock()  # Assignment
        autojob = MagicMock()
        autojob.is_available.return_value = False

        enriched = EnrichedOrchestrator(orch, autojob)
        task = self._make_task_request()
        enriched.route_task(task)

        orch.route_task.assert_called_once()
        # No enrichment should have happened
        autojob.enrich_agents.assert_not_called()

    def test_route_with_autojob(self):
        """When AutoJob is available, enriches before routing."""
        orch = self._make_mock_orchestrator()
        orch.route_task.return_value = MagicMock()

        # Mock lifecycle.get_available_agents
        agent = MagicMock()
        agent.agent_id = 1
        agent.wallet_address = "0xABC"
        orch.lifecycle.get_available_agents.return_value = [agent]

        autojob = MagicMock()
        autojob.is_available.return_value = True
        autojob.enrich_agents.return_value = {
            "0xABC": AutoJobEnrichment(
                wallet="0xABC", match_score=0.7, category_experience=0.6
            ),
        }

        enriched = EnrichedOrchestrator(orch, autojob, enrichment_weight=0.3)
        task = self._make_task_request()
        enriched.route_task(task)

        autojob.enrich_agents.assert_called_once()
        orch.route_task.assert_called_once()

    def test_route_with_autojob_updates_internal_reputation(self):
        """Enrichment should blend category scores into internal reputation."""
        orch = self._make_mock_orchestrator()
        orch.route_task.return_value = MagicMock()

        agent = MagicMock()
        agent.agent_id = 1
        agent.wallet_address = "0xABC"
        orch.lifecycle.get_available_agents.return_value = [agent]

        # Set up internal reputation
        internal = MagicMock()
        internal.category_scores = {"delivery": 50}
        orch._internal = {1: internal}

        autojob = MagicMock()
        autojob.is_available.return_value = True
        autojob.enrich_agents.return_value = {
            "0xABC": AutoJobEnrichment(
                wallet="0xABC",
                match_score=0.8,
                category_experience=0.9,
            ),
        }

        enriched = EnrichedOrchestrator(orch, autojob, enrichment_weight=0.3)
        task = self._make_task_request(categories=["delivery"])
        enriched.route_task(task)

        # Category score should be blended: 50 * 0.7 + 90 * 0.3 = 35 + 27 = 62
        assert internal.category_scores["delivery"] == pytest.approx(62.0, abs=0.1)

    def test_enrichment_caching(self):
        """Same task+wallets should use cached enrichments."""
        orch = self._make_mock_orchestrator()
        orch.route_task.return_value = MagicMock()

        agent = MagicMock()
        agent.agent_id = 1
        agent.wallet_address = "0xABC"
        orch.lifecycle.get_available_agents.return_value = [agent]
        orch._internal = {}

        autojob = MagicMock()
        autojob.is_available.return_value = True
        autojob.enrich_agents.return_value = {
            "0xABC": AutoJobEnrichment(wallet="0xABC"),
        }

        enriched = EnrichedOrchestrator(orch, autojob)
        task = self._make_task_request()

        enriched.route_task(task)
        enriched.route_task(task)  # Same task, same wallets

        # AutoJob should only be called once (cached)
        assert autojob.enrich_agents.call_count == 1

    def test_cache_eviction(self):
        """Cache should evict oldest entries when full."""
        orch = self._make_mock_orchestrator()
        orch.route_task.return_value = MagicMock()
        orch.lifecycle.get_available_agents.return_value = []
        orch._internal = {}

        autojob = MagicMock()
        autojob.is_available.return_value = True
        autojob.enrich_agents.return_value = {}

        enriched = EnrichedOrchestrator(orch, autojob)
        enriched._cache_maxsize = 3

        # Fill cache beyond maxsize
        for i in range(5):
            task = self._make_task_request(task_id=f"t{i}")
            enriched.route_task(task)

        assert len(enriched._enrichment_cache) <= 3

    def test_no_wallets_skips_enrichment(self):
        """If no agents have wallets, skip enrichment."""
        orch = self._make_mock_orchestrator()
        orch.route_task.return_value = MagicMock()

        agent = MagicMock()
        agent.agent_id = 1
        agent.wallet_address = ""  # No wallet
        orch.lifecycle.get_available_agents.return_value = [agent]

        autojob = MagicMock()
        autojob.is_available.return_value = True

        enriched = EnrichedOrchestrator(orch, autojob)
        task = self._make_task_request()
        enriched.route_task(task)

        autojob.enrich_agents.assert_not_called()

    def test_rejects_non_taskrequest(self):
        """Should raise TypeError for non-TaskRequest input."""
        orch = self._make_mock_orchestrator()
        autojob = MagicMock()
        enriched = EnrichedOrchestrator(orch, autojob)

        with pytest.raises(TypeError):
            enriched.route_task({"task_id": "t1"})

    def test_zero_match_score_skips_blending(self):
        """Enrichments with 0 match_score should not modify reputation."""
        orch = self._make_mock_orchestrator()
        orch.route_task.return_value = MagicMock()

        agent = MagicMock()
        agent.agent_id = 1
        agent.wallet_address = "0xABC"
        orch.lifecycle.get_available_agents.return_value = [agent]

        internal = MagicMock()
        internal.category_scores = {"delivery": 50}
        orch._internal = {1: internal}

        autojob = MagicMock()
        autojob.is_available.return_value = True
        autojob.enrich_agents.return_value = {
            "0xABC": AutoJobEnrichment(wallet="0xABC", match_score=0.0),
        }

        enriched = EnrichedOrchestrator(orch, autojob)
        task = self._make_task_request()
        enriched.route_task(task)

        # Should remain unchanged
        assert internal.category_scores["delivery"] == 50
