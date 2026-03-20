"""
Tests for SourceHealthAdapter — bridges AutoJob health data to swarm intelligence.
"""

import pytest
from mcp_server.swarm.source_health_adapter import (
    SourceTier,
    SourceStatus,
    HealthSummary,
    SourceHealthAdapter,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_report():
    """A realistic health report from AutoJob's source_health_monitor."""
    return {
        "probed_at": "2026-03-20T06:00:00Z",
        "total_sources": 6,
        "healthy": 3,
        "degraded": 1,
        "error": 1,
        "empty": 1,
        "overall_system_health": 0.52,
        "probes": [
            {"name": "remoteok", "status": "healthy", "overall_health": 0.97,
             "data_quality_score": 0.94, "response_time_ms": 321, "job_count": 10},
            {"name": "greenhouse", "status": "healthy", "overall_health": 0.93,
             "data_quality_score": 0.95, "response_time_ms": 2330, "job_count": 25},
            {"name": "hn_hiring", "status": "healthy", "overall_health": 0.92,
             "data_quality_score": 0.95, "response_time_ms": 1045, "job_count": 9},
            {"name": "ashby", "status": "degraded", "overall_health": 0.67,
             "data_quality_score": 1.0, "response_time_ms": 11696, "job_count": 7},
            {"name": "graphqljobs", "status": "error", "overall_health": 0.0,
             "data_quality_score": 0.0, "response_time_ms": 975, "job_count": 0},
            {"name": "himalayas", "status": "empty", "overall_health": 0.1,
             "data_quality_score": 0.0, "response_time_ms": 347, "job_count": 0},
        ],
    }


@pytest.fixture
def adapter():
    return SourceHealthAdapter()


@pytest.fixture
def loaded_adapter(adapter, sample_report):
    adapter.ingest_health_report(sample_report)
    return adapter


# ──────────────────────────────────────────────────────────────
# SourceStatus
# ──────────────────────────────────────────────────────────────


class TestSourceStatus:
    def test_gold_is_usable(self):
        s = SourceStatus(name="test", tier=SourceTier.GOLD.value)
        assert s.is_usable() is True

    def test_silver_is_usable(self):
        s = SourceStatus(name="test", tier=SourceTier.SILVER.value)
        assert s.is_usable() is True

    def test_bronze_not_usable(self):
        s = SourceStatus(name="test", tier=SourceTier.BRONZE.value)
        assert s.is_usable() is False

    def test_dead_not_usable(self):
        s = SourceStatus(name="test", tier=SourceTier.DEAD.value)
        assert s.is_usable() is False

    def test_gold_confidence_factor(self):
        s = SourceStatus(name="test", tier=SourceTier.GOLD.value)
        assert s.confidence_factor() == 1.0

    def test_silver_confidence_factor(self):
        s = SourceStatus(name="test", tier=SourceTier.SILVER.value)
        assert s.confidence_factor() == 0.9

    def test_bronze_confidence_factor(self):
        s = SourceStatus(name="test", tier=SourceTier.BRONZE.value)
        assert s.confidence_factor() == 0.6

    def test_dead_confidence_factor(self):
        s = SourceStatus(name="test", tier=SourceTier.DEAD.value)
        assert s.confidence_factor() == 0.1

    def test_unknown_tier_confidence(self):
        s = SourceStatus(name="test", tier="unknown")
        assert s.confidence_factor() == 0.5


# ──────────────────────────────────────────────────────────────
# HealthSummary
# ──────────────────────────────────────────────────────────────


class TestHealthSummary:
    def test_system_usable_with_enough_sources(self):
        s = HealthSummary(gold_count=2, silver_count=2)
        assert s.system_usable() is True

    def test_system_not_usable_with_few_sources(self):
        s = HealthSummary(gold_count=1, silver_count=1)
        assert s.system_usable() is False

    def test_enrichment_quality_high(self):
        s = HealthSummary(gold_count=6)
        assert s.enrichment_quality() == "high"

    def test_enrichment_quality_medium(self):
        s = HealthSummary(gold_count=2, silver_count=4)
        assert s.enrichment_quality() == "medium"

    def test_enrichment_quality_low(self):
        s = HealthSummary(gold_count=1, silver_count=1)
        assert s.enrichment_quality() == "low"

    def test_enrichment_quality_unreliable(self):
        s = HealthSummary(gold_count=0, silver_count=1)
        assert s.enrichment_quality() == "unreliable"


# ──────────────────────────────────────────────────────────────
# Ingest health report
# ──────────────────────────────────────────────────────────────


class TestIngestReport:
    def test_basic_ingest(self, adapter, sample_report):
        adapter.ingest_health_report(sample_report)
        assert adapter.source_count == 6
        assert adapter.update_count == 1

    def test_source_tiers_classified(self, loaded_adapter):
        remoteok = loaded_adapter.get_source("remoteok")
        assert remoteok.tier == SourceTier.GOLD.value

        ashby = loaded_adapter.get_source("ashby")
        assert ashby.tier == SourceTier.SILVER.value

        graphql = loaded_adapter.get_source("graphqljobs")
        assert graphql.tier == SourceTier.DEAD.value

    def test_health_scores_stored(self, loaded_adapter):
        remoteok = loaded_adapter.get_source("remoteok")
        assert remoteok.health_score == 0.97
        assert remoteok.data_quality == 0.94
        assert remoteok.avg_response_ms == 321
        assert remoteok.last_job_count == 10

    def test_empty_report_no_crash(self, adapter):
        adapter.ingest_health_report({})
        assert adapter.source_count == 0

    def test_none_report_no_crash(self, adapter):
        adapter.ingest_health_report(None)
        assert adapter.source_count == 0

    def test_multiple_ingests_update(self, adapter, sample_report):
        adapter.ingest_health_report(sample_report)
        assert adapter.update_count == 1

        # Modify and re-ingest
        sample_report["probes"][0]["overall_health"] = 0.5
        adapter.ingest_health_report(sample_report)
        assert adapter.update_count == 2

        remoteok = adapter.get_source("remoteok")
        assert remoteok.health_score == 0.5
        assert remoteok.tier == SourceTier.SILVER.value

    def test_consecutive_failures_tracked(self, adapter):
        for i in range(3):
            adapter.ingest_health_report({
                "probed_at": f"2026-01-0{i+1}",
                "probes": [
                    {"name": "broken", "status": "error", "overall_health": 0.0,
                     "data_quality_score": 0.0, "response_time_ms": 0, "job_count": 0},
                ],
            })
        broken = adapter.get_source("broken")
        assert broken.consecutive_failures == 3

    def test_consecutive_failures_reset_on_success(self, adapter):
        adapter.ingest_health_report({
            "probes": [{"name": "flaky", "status": "error", "overall_health": 0.0,
                        "data_quality_score": 0, "response_time_ms": 0, "job_count": 0}],
        })
        assert adapter.get_source("flaky").consecutive_failures == 1

        adapter.ingest_health_report({
            "probes": [{"name": "flaky", "status": "healthy", "overall_health": 0.9,
                        "data_quality_score": 0.8, "response_time_ms": 200, "job_count": 10}],
        })
        assert adapter.get_source("flaky").consecutive_failures == 0


# ──────────────────────────────────────────────────────────────
# Query API
# ──────────────────────────────────────────────────────────────


class TestQueryAPI:
    def test_get_source_exists(self, loaded_adapter):
        s = loaded_adapter.get_source("remoteok")
        assert s is not None
        assert s.name == "remoteok"

    def test_get_source_missing(self, loaded_adapter):
        assert loaded_adapter.get_source("nonexistent") is None

    def test_get_usable_sources(self, loaded_adapter):
        usable = loaded_adapter.get_usable_sources()
        names = [s.name for s in usable]
        assert "remoteok" in names
        assert "greenhouse" in names
        assert "hn_hiring" in names
        assert "ashby" in names  # Silver tier
        assert "graphqljobs" not in names  # Dead
        assert "himalayas" not in names  # Dead

    def test_get_by_tier(self, loaded_adapter):
        gold = loaded_adapter.get_by_tier(SourceTier.GOLD.value)
        assert len(gold) == 3  # remoteok, greenhouse, hn_hiring
        assert all(s.tier == SourceTier.GOLD.value for s in gold)

    def test_get_summary(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        assert summary.total_sources == 6
        assert summary.gold_count == 3
        assert summary.silver_count == 1
        assert summary.dead_count == 2
        assert summary.total_available_jobs == 51  # 10+25+9+7+0+0
        assert summary.avg_system_health > 0

    def test_confidence_adjustment_known_source(self, loaded_adapter):
        assert loaded_adapter.confidence_adjustment("remoteok") == 1.0
        assert loaded_adapter.confidence_adjustment("ashby") == 0.9
        assert loaded_adapter.confidence_adjustment("graphqljobs") == 0.1

    def test_confidence_adjustment_unknown_source(self, loaded_adapter):
        assert loaded_adapter.confidence_adjustment("never_seen") == 0.5

    def test_should_query_healthy(self, loaded_adapter):
        assert loaded_adapter.should_query("remoteok") is True

    def test_should_query_dead(self, loaded_adapter):
        assert loaded_adapter.should_query("graphqljobs") is False

    def test_should_query_unknown(self, loaded_adapter):
        assert loaded_adapter.should_query("brand_new") is True

    def test_should_query_many_failures(self, adapter):
        for _ in range(6):
            adapter.ingest_health_report({
                "probes": [{"name": "unreliable", "status": "error",
                           "overall_health": 0.6, "data_quality_score": 0.5,
                           "response_time_ms": 1000, "job_count": 5}],
            })
        assert adapter.should_query("unreliable") is False

    def test_recommended_sources(self, loaded_adapter):
        recommended = loaded_adapter.get_recommended_sources(limit=3)
        assert len(recommended) <= 3
        # Top sources should be gold tier
        assert all(s.tier in (SourceTier.GOLD.value, SourceTier.SILVER.value)
                   for s in recommended)

    def test_recommended_sources_limit(self, loaded_adapter):
        all_recommended = loaded_adapter.get_recommended_sources(limit=100)
        # Only usable sources returned
        assert len(all_recommended) == 4  # 3 gold + 1 silver


# ──────────────────────────────────────────────────────────────
# History & Trends
# ──────────────────────────────────────────────────────────────


class TestHistoryAndTrends:
    def test_trend_computation_improving(self, adapter):
        # Feed improving health data
        for i in range(5):
            health = 0.3 + (i * 0.15)
            adapter.ingest_health_report({
                "probed_at": f"2026-01-0{i+1}",
                "probes": [
                    {"name": "improving_src", "status": "healthy",
                     "overall_health": health, "data_quality_score": health,
                     "response_time_ms": 500, "job_count": 10},
                ],
            })
        src = adapter.get_source("improving_src")
        assert src.trend == "improving"

    def test_trend_computation_declining(self, adapter):
        for i in range(5):
            health = 0.9 - (i * 0.15)
            adapter.ingest_health_report({
                "probed_at": f"2026-01-0{i+1}",
                "probes": [
                    {"name": "declining_src", "status": "healthy",
                     "overall_health": health, "data_quality_score": health,
                     "response_time_ms": 500, "job_count": 10},
                ],
            })
        src = adapter.get_source("declining_src")
        assert src.trend == "declining"

    def test_trend_stable(self, adapter):
        for i in range(5):
            adapter.ingest_health_report({
                "probed_at": f"2026-01-0{i+1}",
                "probes": [
                    {"name": "stable_src", "status": "healthy",
                     "overall_health": 0.8, "data_quality_score": 0.8,
                     "response_time_ms": 500, "job_count": 10},
                ],
            })
        src = adapter.get_source("stable_src")
        assert src.trend == "stable"

    def test_trend_unknown_with_few_data_points(self, adapter):
        adapter.ingest_health_report({
            "probes": [
                {"name": "new_src", "status": "healthy",
                 "overall_health": 0.8, "data_quality_score": 0.8,
                 "response_time_ms": 200, "job_count": 5},
            ],
        })
        src = adapter.get_source("new_src")
        assert src.trend == "unknown"

    def test_ingest_history(self, adapter):
        history = [
            {"ts": "2026-01-01", "sources": {
                "src1": {"status": "healthy", "health": 0.9},
                "src2": {"status": "error", "health": 0.0},
            }},
            {"ts": "2026-01-02", "sources": {
                "src1": {"status": "healthy", "health": 0.85},
                "src2": {"status": "healthy", "health": 0.7},
            }},
        ]
        adapter.ingest_history(history)
        assert adapter.source_count == 2


# ──────────────────────────────────────────────────────────────
# Tier classification
# ──────────────────────────────────────────────────────────────


class TestTierClassification:
    def test_gold_threshold(self, adapter):
        assert adapter._classify_tier(0.85) == SourceTier.GOLD.value
        assert adapter._classify_tier(0.80) == SourceTier.GOLD.value

    def test_silver_threshold(self, adapter):
        assert adapter._classify_tier(0.79) == SourceTier.SILVER.value
        assert adapter._classify_tier(0.50) == SourceTier.SILVER.value

    def test_bronze_threshold(self, adapter):
        assert adapter._classify_tier(0.49) == SourceTier.BRONZE.value
        assert adapter._classify_tier(0.20) == SourceTier.BRONZE.value

    def test_dead_threshold(self, adapter):
        assert adapter._classify_tier(0.19) == SourceTier.DEAD.value
        assert adapter._classify_tier(0.0) == SourceTier.DEAD.value

    def test_boundary_gold_silver(self, adapter):
        """Exactly at threshold → higher tier."""
        assert adapter._classify_tier(0.8) == SourceTier.GOLD.value

    def test_boundary_silver_bronze(self, adapter):
        assert adapter._classify_tier(0.5) == SourceTier.SILVER.value

    def test_boundary_bronze_dead(self, adapter):
        assert adapter._classify_tier(0.2) == SourceTier.BRONZE.value


# ──────────────────────────────────────────────────────────────
# Integration scenarios
# ──────────────────────────────────────────────────────────────


class TestIntegrationScenarios:
    def test_swarm_enrichment_decision(self, loaded_adapter):
        """Simulate swarm deciding which sources to use for enrichment."""
        summary = loaded_adapter.get_summary()
        assert summary.system_usable() is True
        assert summary.enrichment_quality() in ("low", "medium", "high")

        recommended = loaded_adapter.get_recommended_sources()
        assert len(recommended) >= 3

        # Each recommended source should have confidence factor >= 0.9
        for src in recommended:
            assert src.confidence_factor() >= 0.9

    def test_source_failure_cascading(self, adapter):
        """Test that sources degrade gracefully as they fail."""
        # Start healthy
        adapter.ingest_health_report({
            "probes": [
                {"name": "api1", "status": "healthy", "overall_health": 0.95,
                 "data_quality_score": 0.9, "response_time_ms": 200, "job_count": 20},
                {"name": "api2", "status": "healthy", "overall_health": 0.9,
                 "data_quality_score": 0.85, "response_time_ms": 300, "job_count": 15},
                {"name": "api3", "status": "healthy", "overall_health": 0.85,
                 "data_quality_score": 0.8, "response_time_ms": 500, "job_count": 10},
            ],
        })
        assert adapter.get_summary().gold_count == 3

        # Two sources degrade
        adapter.ingest_health_report({
            "probes": [
                {"name": "api1", "status": "healthy", "overall_health": 0.95,
                 "data_quality_score": 0.9, "response_time_ms": 200, "job_count": 20},
                {"name": "api2", "status": "error", "overall_health": 0.0,
                 "data_quality_score": 0.0, "response_time_ms": 0, "job_count": 0},
                {"name": "api3", "status": "empty", "overall_health": 0.1,
                 "data_quality_score": 0.0, "response_time_ms": 300, "job_count": 0},
            ],
        })
        summary = adapter.get_summary()
        assert summary.gold_count == 1
        assert summary.dead_count == 2
        assert summary.system_usable() is False  # Only 1 usable source

    def test_full_lifecycle(self, adapter):
        """Test: ingest → query → update → verify changes."""
        # Initial state
        assert adapter.source_count == 0

        # Ingest first report
        adapter.ingest_health_report({
            "probed_at": "2026-01-01",
            "probes": [
                {"name": "src1", "status": "healthy", "overall_health": 0.9,
                 "data_quality_score": 0.85, "response_time_ms": 200, "job_count": 15},
            ],
        })
        assert adapter.source_count == 1
        assert adapter.get_source("src1").tier == SourceTier.GOLD.value

        # Source degrades
        adapter.ingest_health_report({
            "probed_at": "2026-01-02",
            "probes": [
                {"name": "src1", "status": "degraded", "overall_health": 0.4,
                 "data_quality_score": 0.5, "response_time_ms": 8000, "job_count": 3},
            ],
        })
        assert adapter.get_source("src1").tier == SourceTier.BRONZE.value
        assert adapter.should_query("src1") is False
