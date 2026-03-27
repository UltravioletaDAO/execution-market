"""
Tests for SourceHealthAdapter — External source health intelligence.

Covers:
- SourceStatus: tier classification, usability, confidence factors
- HealthSummary: aggregation, system usability, enrichment quality
- Health report ingestion: probes → SourceStatus conversion
- Tier classification: GOLD/SILVER/BRONZE/DEAD thresholds
- Consecutive failure tracking
- History ingestion and reliability computation
- Trend analysis: improving, stable, declining
- Query API: get_source, get_usable_sources, get_by_tier
- Confidence adjustment per source
- Source querying decisions (should_query)
- Recommended sources ranking
- Edge cases: empty reports, missing fields, duplicate sources
"""

import pytest

from mcp_server.swarm.source_health_adapter import (
    SourceHealthAdapter,
    SourceStatus,
    SourceTier,
    HealthSummary,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def adapter():
    """Fresh SourceHealthAdapter."""
    return SourceHealthAdapter()


@pytest.fixture
def sample_report():
    """A health report with mixed source states."""
    return {
        "probed_at": "2026-03-27T01:00:00Z",
        "overall_system_health": 72,
        "probes": [
            {
                "name": "greenhouse",
                "status": "healthy",
                "overall_health": 0.95,
                "data_quality_score": 0.90,
                "response_time_ms": 120,
                "job_count": 45,
                "probed_at": "2026-03-27T01:00:00Z",
            },
            {
                "name": "arbeitnow",
                "status": "healthy",
                "overall_health": 0.82,
                "data_quality_score": 0.75,
                "response_time_ms": 200,
                "job_count": 30,
                "probed_at": "2026-03-27T01:00:00Z",
            },
            {
                "name": "ashby",
                "status": "degraded",
                "overall_health": 0.55,
                "data_quality_score": 0.50,
                "response_time_ms": 800,
                "job_count": 12,
                "probed_at": "2026-03-27T01:00:00Z",
            },
            {
                "name": "devto",
                "status": "degraded",
                "overall_health": 0.35,
                "data_quality_score": 0.30,
                "response_time_ms": 1500,
                "job_count": 5,
                "probed_at": "2026-03-27T01:00:00Z",
            },
            {
                "name": "graphql_jobs",
                "status": "error",
                "overall_health": 0.10,
                "data_quality_score": 0.0,
                "response_time_ms": 0,
                "job_count": 0,
                "probed_at": "2026-03-27T01:00:00Z",
            },
        ],
    }


@pytest.fixture
def loaded_adapter(adapter, sample_report):
    """Adapter with sample report ingested."""
    adapter.ingest_health_report(sample_report)
    return adapter


# ─── SourceStatus ──────────────────────────────────────────────────────────────


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

    def test_defaults(self):
        s = SourceStatus(name="test")
        assert s.health_score == 0.0
        assert s.consecutive_failures == 0
        assert s.trend == "unknown"


# ─── HealthSummary ─────────────────────────────────────────────────────────────


class TestHealthSummary:
    def test_system_usable_with_enough_good_sources(self):
        hs = HealthSummary(gold_count=2, silver_count=2)
        assert hs.system_usable() is True

    def test_system_not_usable_with_few_good_sources(self):
        hs = HealthSummary(gold_count=1, silver_count=1)
        assert hs.system_usable() is False

    def test_enrichment_quality_high(self):
        hs = HealthSummary(gold_count=5)
        assert hs.enrichment_quality() == "high"

    def test_enrichment_quality_medium(self):
        hs = HealthSummary(gold_count=2, silver_count=3)
        assert hs.enrichment_quality() == "medium"

    def test_enrichment_quality_low(self):
        hs = HealthSummary(gold_count=1, silver_count=1)
        assert hs.enrichment_quality() == "low"

    def test_enrichment_quality_unreliable(self):
        hs = HealthSummary(gold_count=0, silver_count=1)
        assert hs.enrichment_quality() == "unreliable"


# ─── Health Report Ingestion ──────────────────────────────────────────────────


class TestHealthReportIngestion:
    def test_ingest_populates_sources(self, loaded_adapter):
        assert loaded_adapter.source_count == 5

    def test_ingest_classifies_gold(self, loaded_adapter):
        source = loaded_adapter.get_source("greenhouse")
        assert source is not None
        assert source.tier == SourceTier.GOLD.value

    def test_ingest_classifies_silver(self, loaded_adapter):
        source = loaded_adapter.get_source("ashby")
        assert source is not None
        assert source.tier == SourceTier.SILVER.value

    def test_ingest_classifies_bronze(self, loaded_adapter):
        source = loaded_adapter.get_source("devto")
        assert source is not None
        assert source.tier == SourceTier.BRONZE.value

    def test_ingest_classifies_dead(self, loaded_adapter):
        source = loaded_adapter.get_source("graphql_jobs")
        assert source is not None
        assert source.tier == SourceTier.DEAD.value

    def test_ingest_captures_health_score(self, loaded_adapter):
        source = loaded_adapter.get_source("greenhouse")
        assert source.health_score == 0.95

    def test_ingest_captures_data_quality(self, loaded_adapter):
        source = loaded_adapter.get_source("arbeitnow")
        assert source.data_quality == 0.75

    def test_ingest_captures_response_time(self, loaded_adapter):
        source = loaded_adapter.get_source("ashby")
        assert source.avg_response_ms == 800

    def test_ingest_captures_job_count(self, loaded_adapter):
        source = loaded_adapter.get_source("greenhouse")
        assert source.last_job_count == 45

    def test_ingest_increments_update_count(self, loaded_adapter):
        assert loaded_adapter.update_count == 1

    def test_consecutive_failures_tracked(self, adapter):
        report = {
            "probes": [
                {
                    "name": "failing",
                    "status": "error",
                    "overall_health": 0.1,
                },
            ]
        }
        adapter.ingest_health_report(report)
        assert adapter.get_source("failing").consecutive_failures == 1

        adapter.ingest_health_report(report)
        assert adapter.get_source("failing").consecutive_failures == 2

    def test_consecutive_failures_reset_on_success(self, adapter):
        error_report = {
            "probes": [
                {"name": "flaky", "status": "error", "overall_health": 0.1}
            ]
        }
        adapter.ingest_health_report(error_report)
        adapter.ingest_health_report(error_report)
        assert adapter.get_source("flaky").consecutive_failures == 2

        ok_report = {
            "probes": [
                {"name": "flaky", "status": "healthy", "overall_health": 0.9}
            ]
        }
        adapter.ingest_health_report(ok_report)
        assert adapter.get_source("flaky").consecutive_failures == 0

    def test_empty_report(self, adapter):
        adapter.ingest_health_report({})
        assert adapter.source_count == 0

    def test_none_report(self, adapter):
        adapter.ingest_health_report(None)
        assert adapter.source_count == 0

    def test_probes_without_name_skipped(self, adapter):
        report = {
            "probes": [
                {"status": "healthy", "overall_health": 0.9},
                {"name": "", "status": "healthy", "overall_health": 0.9},
                {"name": "valid", "status": "healthy", "overall_health": 0.9},
            ]
        }
        adapter.ingest_health_report(report)
        assert adapter.source_count == 1
        assert adapter.get_source("valid") is not None


# ─── Tier Classification ──────────────────────────────────────────────────────


class TestTierClassification:
    def test_gold_boundary(self, adapter):
        assert adapter._classify_tier(0.8) == SourceTier.GOLD.value
        assert adapter._classify_tier(1.0) == SourceTier.GOLD.value

    def test_silver_boundary(self, adapter):
        assert adapter._classify_tier(0.5) == SourceTier.SILVER.value
        assert adapter._classify_tier(0.79) == SourceTier.SILVER.value

    def test_bronze_boundary(self, adapter):
        assert adapter._classify_tier(0.2) == SourceTier.BRONZE.value
        assert adapter._classify_tier(0.49) == SourceTier.BRONZE.value

    def test_dead_boundary(self, adapter):
        assert adapter._classify_tier(0.19) == SourceTier.DEAD.value
        assert adapter._classify_tier(0.0) == SourceTier.DEAD.value


# ─── Query API ─────────────────────────────────────────────────────────────────


class TestQueryAPI:
    def test_get_source_exists(self, loaded_adapter):
        source = loaded_adapter.get_source("greenhouse")
        assert source is not None
        assert source.name == "greenhouse"

    def test_get_source_nonexistent(self, loaded_adapter):
        assert loaded_adapter.get_source("nonexistent") is None

    def test_get_usable_sources(self, loaded_adapter):
        usable = loaded_adapter.get_usable_sources()
        names = {s.name for s in usable}
        assert "greenhouse" in names  # gold
        assert "arbeitnow" in names  # gold
        assert "ashby" in names  # silver
        assert "devto" not in names  # bronze
        assert "graphql_jobs" not in names  # dead

    def test_get_by_tier_gold(self, loaded_adapter):
        gold = loaded_adapter.get_by_tier(SourceTier.GOLD.value)
        names = {s.name for s in gold}
        assert "greenhouse" in names
        assert "arbeitnow" in names

    def test_get_by_tier_dead(self, loaded_adapter):
        dead = loaded_adapter.get_by_tier(SourceTier.DEAD.value)
        names = {s.name for s in dead}
        assert "graphql_jobs" in names

    def test_get_by_tier_empty(self, loaded_adapter):
        result = loaded_adapter.get_by_tier("nonexistent_tier")
        assert result == []


# ─── Summary ──────────────────────────────────────────────────────────────────


class TestSummary:
    def test_summary_counts(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        assert summary.total_sources == 5
        assert summary.gold_count == 2
        assert summary.silver_count == 1
        assert summary.bronze_count == 1
        assert summary.dead_count == 1

    def test_summary_total_jobs(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        assert summary.total_available_jobs == 45 + 30 + 12 + 5 + 0

    def test_summary_avg_health(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        expected = (0.95 + 0.82 + 0.55 + 0.35 + 0.10) / 5
        assert abs(summary.avg_system_health - expected) < 0.01

    def test_summary_best_sources(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        assert summary.best_sources[0] == "greenhouse"  # Highest health

    def test_summary_worst_sources(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        assert summary.worst_sources[-1] == "graphql_jobs"  # Lowest health

    def test_summary_system_usable(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        assert summary.system_usable() is True  # 2 gold + 1 silver ≥ 3

    def test_summary_enrichment_quality(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        # 2 gold + 1 silver = 3 total good → "low" (needs 5 for medium)
        assert summary.enrichment_quality() in ("low", "medium")

    def test_summary_updated_at(self, loaded_adapter):
        summary = loaded_adapter.get_summary()
        assert summary.updated_at != ""

    def test_empty_summary(self, adapter):
        summary = adapter.get_summary()
        assert summary.total_sources == 0
        assert summary.avg_system_health == 0.0


# ─── Confidence Adjustment ────────────────────────────────────────────────────


class TestConfidenceAdjustment:
    def test_gold_source_full_confidence(self, loaded_adapter):
        assert loaded_adapter.confidence_adjustment("greenhouse") == 1.0

    def test_silver_source_slight_penalty(self, loaded_adapter):
        assert loaded_adapter.confidence_adjustment("ashby") == 0.9

    def test_bronze_source_moderate_penalty(self, loaded_adapter):
        assert loaded_adapter.confidence_adjustment("devto") == 0.6

    def test_dead_source_heavy_penalty(self, loaded_adapter):
        assert loaded_adapter.confidence_adjustment("graphql_jobs") == 0.1

    def test_unknown_source_default(self, loaded_adapter):
        assert loaded_adapter.confidence_adjustment("unknown") == 0.5


# ─── Should Query ─────────────────────────────────────────────────────────────


class TestShouldQuery:
    def test_gold_source_queryable(self, loaded_adapter):
        assert loaded_adapter.should_query("greenhouse") is True

    def test_silver_source_queryable(self, loaded_adapter):
        assert loaded_adapter.should_query("ashby") is True

    def test_bronze_source_not_queryable(self, loaded_adapter):
        assert loaded_adapter.should_query("devto") is False

    def test_dead_source_not_queryable(self, loaded_adapter):
        assert loaded_adapter.should_query("graphql_jobs") is False

    def test_unknown_source_queryable(self, loaded_adapter):
        # Unknown sources should be tried
        assert loaded_adapter.should_query("brand_new") is True

    def test_too_many_failures_not_queryable(self, adapter):
        report = {
            "probes": [
                {"name": "flaky", "status": "healthy", "overall_health": 0.9}
            ]
        }
        adapter.ingest_health_report(report)
        adapter._sources["flaky"].consecutive_failures = 5
        assert adapter.should_query("flaky") is False


# ─── Recommended Sources ──────────────────────────────────────────────────────


class TestRecommendedSources:
    def test_recommended_returns_usable_only(self, loaded_adapter):
        recommended = loaded_adapter.get_recommended_sources()
        tiers = [s.tier for s in recommended]
        assert SourceTier.DEAD.value not in tiers
        assert SourceTier.BRONZE.value not in tiers

    def test_recommended_ordered_by_quality(self, loaded_adapter):
        recommended = loaded_adapter.get_recommended_sources()
        if len(recommended) >= 2:
            # First should have better combined score than second
            assert recommended[0].health_score >= recommended[1].health_score

    def test_recommended_respects_limit(self, loaded_adapter):
        recommended = loaded_adapter.get_recommended_sources(limit=2)
        assert len(recommended) <= 2

    def test_recommended_empty_when_no_usable(self, adapter):
        report = {
            "probes": [
                {"name": "dead1", "status": "error", "overall_health": 0.1},
                {"name": "dead2", "status": "error", "overall_health": 0.05},
            ]
        }
        adapter.ingest_health_report(report)
        assert len(adapter.get_recommended_sources()) == 0


# ─── Trend Analysis ───────────────────────────────────────────────────────────


class TestTrendAnalysis:
    def test_improving_trend(self, adapter):
        # Feed 5 reports with improving health for one source
        for i in range(5):
            health = 0.3 + i * 0.15  # 0.3, 0.45, 0.6, 0.75, 0.9
            report = {
                "probes": [
                    {"name": "improving", "status": "healthy", "overall_health": health}
                ]
            }
            adapter.ingest_health_report(report)

        source = adapter.get_source("improving")
        assert source.trend == "improving"

    def test_declining_trend(self, adapter):
        for i in range(5):
            health = 0.9 - i * 0.15  # 0.9, 0.75, 0.6, 0.45, 0.3
            report = {
                "probes": [
                    {"name": "declining", "status": "healthy", "overall_health": health}
                ]
            }
            adapter.ingest_health_report(report)

        source = adapter.get_source("declining")
        assert source.trend == "declining"

    def test_stable_trend(self, adapter):
        for _ in range(5):
            report = {
                "probes": [
                    {"name": "stable", "status": "healthy", "overall_health": 0.8}
                ]
            }
            adapter.ingest_health_report(report)

        source = adapter.get_source("stable")
        assert source.trend == "stable"

    def test_unknown_trend_insufficient_data(self, adapter):
        report = {
            "probes": [
                {"name": "new", "status": "healthy", "overall_health": 0.8}
            ]
        }
        adapter.ingest_health_report(report)
        source = adapter.get_source("new")
        assert source.trend == "unknown"


# ─── Multiple Report Updates ──────────────────────────────────────────────────


class TestMultipleUpdates:
    def test_source_updated_on_second_report(self, adapter):
        report1 = {
            "probes": [
                {"name": "changing", "status": "healthy", "overall_health": 0.9}
            ]
        }
        adapter.ingest_health_report(report1)
        assert adapter.get_source("changing").tier == SourceTier.GOLD.value

        report2 = {
            "probes": [
                {"name": "changing", "status": "degraded", "overall_health": 0.4}
            ]
        }
        adapter.ingest_health_report(report2)
        assert adapter.get_source("changing").tier == SourceTier.BRONZE.value

    def test_new_source_added_in_later_report(self, loaded_adapter):
        assert loaded_adapter.source_count == 5

        new_report = {
            "probes": [
                {"name": "new_source", "status": "healthy", "overall_health": 0.85}
            ]
        }
        loaded_adapter.ingest_health_report(new_report)
        assert loaded_adapter.source_count == 6

    def test_update_count_tracks_reports(self, adapter):
        for i in range(5):
            adapter.ingest_health_report(
                {"probes": [{"name": "src", "status": "healthy", "overall_health": 0.8}]}
            )
        assert adapter.update_count == 5


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_probe_missing_optional_fields(self, adapter):
        report = {
            "probes": [
                {"name": "minimal", "overall_health": 0.7}
            ]
        }
        adapter.ingest_health_report(report)
        source = adapter.get_source("minimal")
        assert source is not None
        assert source.tier == SourceTier.SILVER.value
        assert source.avg_response_ms == 0.0

    def test_zero_health_score(self, adapter):
        report = {
            "probes": [
                {"name": "zero", "overall_health": 0.0}
            ]
        }
        adapter.ingest_health_report(report)
        source = adapter.get_source("zero")
        assert source.tier == SourceTier.DEAD.value

    def test_perfect_health_score(self, adapter):
        report = {
            "probes": [
                {"name": "perfect", "overall_health": 1.0}
            ]
        }
        adapter.ingest_health_report(report)
        source = adapter.get_source("perfect")
        assert source.tier == SourceTier.GOLD.value

    def test_many_sources(self, adapter):
        probes = [
            {"name": f"source_{i}", "overall_health": i / 100, "status": "healthy"}
            for i in range(50)
        ]
        adapter.ingest_health_report({"probes": probes})
        assert adapter.source_count == 50
        summary = adapter.get_summary()
        assert summary.total_sources == 50
