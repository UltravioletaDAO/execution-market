"""
Tests for VerificationAdapter → DecisionSynthesizer → SwarmIntegrator Integration
==================================================================================

Signal #13: Verification Quality from PHOTINT evidence forensics.

Tests prove:
1. VerificationAdapter scores flow into DecisionSynthesizer
2. DecisionSynthesizer routes differently with/without verification signal
3. SwarmIntegrator wires both components together
4. Workers with better evidence quality get higher composite scores
5. Default weights give verification 8% of routing weight
6. Category-specific scoring works through the full pipeline
7. Trust tiers influence routing recommendations
8. Fleet diagnostics accessible through integrator
"""

import pytest
import time

from mcp_server.swarm.decision_synthesizer import (
    DecisionSynthesizer,
    SignalType,
    SignalValue,
    DecisionOutcome,
    ConfidenceLevel,
    DEFAULT_WEIGHTS,
)
from mcp_server.swarm.verification_adapter import (
    VerificationAdapter,
    VerificationTrust,
    VerificationInference,
)
from mcp_server.swarm.integrator import (
    SwarmIntegrator,
    SwarmMode,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def adapter():
    """Fresh VerificationAdapter with default config."""
    return VerificationAdapter()


@pytest.fixture
def adapter_with_data():
    """VerificationAdapter pre-loaded with diverse worker data."""
    a = VerificationAdapter(min_inferences_for_signal=3)

    # Worker A: Exceptional quality (25 clean submissions)
    for i in range(25):
        a.ingest_inference("0xExceptional", {
            "submission_id": f"sub_ex_{i}",
            "task_id": f"task_{i}",
            "tier": "tier_1",
            "score": 0.92 + (i % 5) * 0.01,
            "decision": "approved",
            "category": "physical_verification",
            "has_exif": True,
            "has_gps": True,
            "photo_source": "camera",
            "cost_usd": 0.002,
            "was_escalated": False,
            "consensus_used": False,
            "timestamp": time.time() - (25 - i) * 3600,
        })

    # Worker B: Standard quality (10 mixed submissions)
    for i in range(10):
        a.ingest_inference("0xStandard", {
            "submission_id": f"sub_st_{i}",
            "task_id": f"task_{100 + i}",
            "tier": "tier_1" if i % 3 != 0 else "tier_2",
            "score": 0.65 + (i % 3) * 0.05,
            "decision": "approved" if i % 4 != 3 else "rejected",
            "category": "physical_verification",
            "has_exif": i % 2 == 0,
            "has_gps": i % 3 == 0,
            "photo_source": "camera" if i % 2 == 0 else "screenshot",
            "cost_usd": 0.005,
            "was_escalated": i % 3 == 0,
            "timestamp": time.time() - (10 - i) * 3600,
        })

    # Worker C: Low quality (8 poor submissions)
    for i in range(8):
        a.ingest_inference("0xLow", {
            "submission_id": f"sub_lo_{i}",
            "task_id": f"task_{200 + i}",
            "tier": "tier_2",
            "score": 0.30 + (i % 3) * 0.05,
            "decision": "rejected" if i % 2 == 0 else "approved",
            "category": "physical_verification",
            "has_exif": False,
            "has_gps": False,
            "photo_source": "screenshot",
            "cost_usd": 0.01,
            "was_escalated": True,
            "timestamp": time.time() - (8 - i) * 3600,
        })

    # Worker D: Unknown (only 1 submission, below min_inferences)
    a.ingest_inference("0xUnknown", {
        "submission_id": "sub_un_0",
        "task_id": "task_300",
        "tier": "tier_1",
        "score": 0.80,
        "decision": "approved",
        "category": "physical_verification",
        "has_exif": True,
        "has_gps": True,
        "photo_source": "camera",
        "cost_usd": 0.002,
    })

    return a


@pytest.fixture
def task():
    """Standard physical verification task."""
    return {
        "id": "task_integration_001",
        "title": "Verify storefront signage",
        "category": "physical_verification",
        "bounty_usd": 5.0,
    }


@pytest.fixture
def candidates():
    """Candidates matching the adapter workers."""
    return [
        {"id": "0xExceptional", "wallet": "0xExceptional", "skills": ["photography"]},
        {"id": "0xStandard", "wallet": "0xStandard", "skills": ["photography"]},
        {"id": "0xLow", "wallet": "0xLow", "skills": ["photography"]},
        {"id": "0xUnknown", "wallet": "0xUnknown", "skills": ["photography"]},
    ]


# ── 1. Signal Registration ──────────────────────────────────


class TestSignalRegistration:
    """VerificationAdapter registers as Signal #13 in DecisionSynthesizer."""

    def test_verification_quality_in_signal_type(self):
        """VERIFICATION_QUALITY exists in SignalType enum."""
        assert hasattr(SignalType, "VERIFICATION_QUALITY")
        assert SignalType.VERIFICATION_QUALITY.value == "verification_quality"

    def test_default_weight_is_eight_percent(self):
        """Default routing weight for verification is 0.08 (8%)."""
        assert SignalType.VERIFICATION_QUALITY in DEFAULT_WEIGHTS
        assert DEFAULT_WEIGHTS[SignalType.VERIFICATION_QUALITY] == 0.08

    def test_weights_still_sum_to_one(self):
        """All default weights still sum to 1.0 after adding verification."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_register_adapter_as_signal(self, adapter):
        """Adapter.score can be registered as a DecisionSynthesizer signal."""
        synth = DecisionSynthesizer()
        synth.register_signal(SignalType.VERIFICATION_QUALITY, adapter.score)

        # Verify it's registered (uses _providers internally)
        assert SignalType.VERIFICATION_QUALITY in synth._providers

    def test_unregister_adapter_signal(self, adapter):
        """Signal can be unregistered cleanly."""
        synth = DecisionSynthesizer()
        synth.register_signal(SignalType.VERIFICATION_QUALITY, adapter.score)
        synth.unregister_signal(SignalType.VERIFICATION_QUALITY)
        assert SignalType.VERIFICATION_QUALITY not in synth._providers


# ── 2. Score Flow Through Pipeline ───────────────────────────


class TestScoreFlow:
    """Verification scores flow correctly through DecisionSynthesizer."""

    def test_adapter_scores_reach_synthesizer(self, adapter_with_data, task, candidates):
        """Scores from adapter.score() reach DecisionSynthesizer's synthesis."""
        synth = DecisionSynthesizer()

        # Register verification as the ONLY signal (isolate its effect)
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)
        assert decision is not None
        assert len(decision.rankings) == len(candidates)

    def test_exceptional_worker_scores_highest(self, adapter_with_data, task, candidates):
        """With only verification signal, exceptional worker ranks #1."""
        synth = DecisionSynthesizer()
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)
        # Best candidate should be exceptional (highest verification quality)
        assert decision.rankings[0].candidate_id == "0xExceptional"

    def test_low_worker_scores_lower_than_standard(self, adapter_with_data, task, candidates):
        """Low-quality worker ranks below standard-quality."""
        synth = DecisionSynthesizer()
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)
        ranking_ids = [r.candidate_id for r in decision.rankings]

        std_idx = ranking_ids.index("0xStandard")
        low_idx = ranking_ids.index("0xLow")
        assert std_idx < low_idx, "Standard worker should rank above low worker"

    def test_unknown_worker_gets_default_score(self, adapter_with_data, task):
        """Worker with insufficient data gets default 50.0 score."""
        score = adapter_with_data.score("0xUnknown", task)
        assert score == 50.0

    def test_nonexistent_worker_gets_default(self, adapter_with_data, task):
        """Worker with zero history gets default score."""
        score = adapter_with_data.score("0xGhost", task)
        assert score == 50.0


# ── 3. Multi-Signal Integration ──────────────────────────────


class TestMultiSignalIntegration:
    """Verification signal works alongside other signals."""

    def test_verification_changes_ranking_order(self, adapter_with_data, task, candidates):
        """Adding verification signal can change relative rankings."""
        # Synth with only skill_match (everyone equal skills)
        synth_without = DecisionSynthesizer()
        synth_without.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 70.0,  # Equal for everyone
        )
        synth_without.register_signal(
            SignalType.REPUTATION,
            lambda t, c: 60.0,  # Equal for everyone
        )
        decision_without = synth_without.synthesize(task, candidates)

        # Synth WITH verification (differentiates workers)
        synth_with = DecisionSynthesizer()
        synth_with.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 70.0,
        )
        synth_with.register_signal(
            SignalType.REPUTATION,
            lambda t, c: 60.0,
        )
        synth_with.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )
        decision_with = synth_with.synthesize(task, candidates)

        # Without verification: all scores identical
        scores_without = [r.composite_score for r in decision_without.rankings]
        # With verification: scores differ
        scores_with = [r.composite_score for r in decision_with.rankings]

        # With verification should show more spread
        spread_without = max(scores_without) - min(scores_without)
        spread_with = max(scores_with) - min(scores_with)
        assert spread_with > spread_without, (
            f"Verification should increase score spread: with={spread_with}, without={spread_without}"
        )

    def test_verification_boosts_exceptional_worker(self, adapter_with_data, task, candidates):
        """Exceptional verification quality boosts composite score."""
        synth = DecisionSynthesizer()

        # Equal base signals
        synth.register_signal(SignalType.SKILL_MATCH, lambda t, c: 60.0)
        synth.register_signal(SignalType.REPUTATION, lambda t, c: 60.0)
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)

        # Find exceptional and low worker scores
        score_map = {
            r.candidate_id: r.composite_score
            for r in decision.rankings
        }

        assert score_map["0xExceptional"] > score_map["0xLow"]
        # The gap should be meaningful (verification is 8% weight)
        gap = score_map["0xExceptional"] - score_map["0xLow"]
        assert gap > 0.01, f"Expected meaningful gap, got {gap}"


# ── 4. SwarmIntegrator Wiring ─────────────────────────────────


class TestIntegratorWiring:
    """SwarmIntegrator correctly wires VerificationAdapter."""

    def test_set_verification_adapter(self, adapter):
        """Can register VerificationAdapter with integrator."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        result = integrator.set_verification_adapter(adapter)
        assert result is integrator  # Fluent API
        assert integrator._verification_adapter is adapter
        assert "verification_adapter" in integrator._component_statuses

    def test_set_decision_synthesizer(self):
        """Can register DecisionSynthesizer with integrator."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        synth = DecisionSynthesizer()
        result = integrator.set_decision_synthesizer(synth)
        assert result is integrator
        assert integrator._decision_synthesizer is synth
        assert "decision_synthesizer" in integrator._component_statuses

    def test_auto_wire_adapter_into_synthesizer(self, adapter):
        """Setting adapter after synthesizer auto-wires the signal."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        synth = DecisionSynthesizer()

        # Set synthesizer first, then adapter
        integrator.set_decision_synthesizer(synth)
        integrator.set_verification_adapter(adapter)

        # Verify signal was registered
        assert SignalType.VERIFICATION_QUALITY in synth._providers

    def test_adapter_without_synthesizer_no_error(self, adapter):
        """Setting adapter without synthesizer doesn't crash."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.set_verification_adapter(adapter)  # No synthesizer yet
        assert integrator._verification_adapter is adapter

    def test_create_with_components_includes_verification(self, adapter):
        """create_with_components accepts verification_adapter."""
        synth = DecisionSynthesizer()
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.PASSIVE,
            components={
                "decision_synthesizer": synth,
                "verification_adapter": adapter,
            },
        )
        assert integrator._verification_adapter is adapter
        assert integrator._decision_synthesizer is synth

    def test_health_includes_verification_adapter(self, adapter):
        """Health check reports verification_adapter status."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.set_verification_adapter(adapter)

        health = integrator.health()
        assert "verification_adapter" in health["components"]["details"]
        assert health["components"]["details"]["verification_adapter"]["healthy"]

    def test_health_includes_decision_synthesizer(self):
        """Health check reports decision_synthesizer status."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        synth = DecisionSynthesizer()
        integrator.set_decision_synthesizer(synth)

        health = integrator.health()
        assert "decision_synthesizer" in health["components"]["details"]
        assert health["components"]["details"]["decision_synthesizer"]["healthy"]


# ── 5. Category-Specific Scoring ──────────────────────────────


class TestCategorySpecificScoring:
    """Verification signal respects task category context."""

    def test_category_affects_score(self):
        """Workers with category-specific history get adjusted scores."""
        adapter = VerificationAdapter(min_inferences_for_signal=2)

        # Worker good at physical, bad at bureaucratic
        for i in range(5):
            adapter.ingest_inference("0xPhysical", {
                "score": 0.95,
                "decision": "approved",
                "category": "physical_verification",
                "has_exif": True,
                "has_gps": True,
                "photo_source": "camera",
            })
        for i in range(5):
            adapter.ingest_inference("0xPhysical", {
                "score": 0.40,
                "decision": "rejected",
                "category": "bureaucratic",
                "has_exif": False,
                "has_gps": False,
                "photo_source": "screenshot",
            })

        physical_task = {"category": "physical_verification"}
        bureau_task = {"category": "bureaucratic"}

        score_physical = adapter.score("0xPhysical", physical_task)
        score_bureau = adapter.score("0xPhysical", bureau_task)

        assert score_physical > score_bureau, (
            f"Physical score ({score_physical}) should exceed bureaucratic ({score_bureau})"
        )

    def test_category_flows_through_synthesizer(self):
        """Category-specific scoring works through full pipeline."""
        adapter = VerificationAdapter(min_inferences_for_signal=2)

        # Worker A: expert in physical
        for i in range(5):
            adapter.ingest_inference("0xPhysExpert", {
                "score": 0.95, "decision": "approved",
                "category": "physical_verification",
                "has_exif": True, "has_gps": True, "photo_source": "camera",
            })

        # Worker B: expert in bureaucratic
        for i in range(5):
            adapter.ingest_inference("0xBureauExpert", {
                "score": 0.95, "decision": "approved",
                "category": "bureaucratic",
                "has_exif": True, "has_gps": False, "photo_source": "camera",
            })
            # Give both some general submissions too
            adapter.ingest_inference("0xPhysExpert", {
                "score": 0.55, "decision": "approved",
                "category": "bureaucratic",
                "has_exif": False, "has_gps": False, "photo_source": "screenshot",
            })
            adapter.ingest_inference("0xBureauExpert", {
                "score": 0.55, "decision": "approved",
                "category": "physical_verification",
                "has_exif": False, "has_gps": False, "photo_source": "screenshot",
            })

        synth = DecisionSynthesizer()
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter.score(c.get("id", ""), t),
        )

        # Physical task: PhysExpert should rank higher
        phys_task = {"id": "t1", "category": "physical_verification", "bounty_usd": 5.0}
        candidates = [
            {"id": "0xPhysExpert", "wallet": "0xPhysExpert"},
            {"id": "0xBureauExpert", "wallet": "0xBureauExpert"},
        ]

        decision = synth.synthesize(phys_task, candidates)
        assert decision.rankings[0].candidate_id == "0xPhysExpert"


# ── 6. Trust Tier Integration ────────────────────────────────


class TestTrustTierIntegration:
    """Trust tiers from adapter influence routing recommendations."""

    def test_exceptional_worker_tier(self, adapter_with_data):
        """Worker with 25 clean submissions gets high trust."""
        state = adapter_with_data.get_state("0xExceptional")
        assert state.trust in (VerificationTrust.HIGH, VerificationTrust.EXCEPTIONAL)

    def test_low_worker_tier(self, adapter_with_data):
        """Worker with poor history gets low trust."""
        state = adapter_with_data.get_state("0xLow")
        assert state.trust == VerificationTrust.LOW

    def test_unknown_worker_tier(self, adapter_with_data):
        """Worker with insufficient history gets unknown."""
        state = adapter_with_data.get_state("0xUnknown")
        assert state.trust == VerificationTrust.UNKNOWN

    def test_tier_1_recommended_for_trusted(self, adapter_with_data):
        """Trusted workers get tier_1 verification recommendation."""
        tier = adapter_with_data.recommend_tier("0xExceptional")
        assert tier == "tier_1"

    def test_tier_2_recommended_for_low_trust(self, adapter_with_data):
        """Low-trust workers get tier_2 verification (more scrutiny)."""
        tier = adapter_with_data.recommend_tier("0xLow")
        assert tier == "tier_2"

    def test_cost_savings_for_trusted_fleet(self, adapter_with_data):
        """Fleet with trusted workers shows verification cost savings."""
        diag = adapter_with_data.diagnose()
        # Should have cost analysis
        assert "cost_analysis" in diag
        cost = diag["cost_analysis"]
        assert cost["actual_cost"] < cost["baseline_cost"]
        assert cost["savings_pct"] > 0


# ── 7. Fleet Diagnostics Through Integrator ───────────────────


class TestFleetDiagnostics:
    """Fleet-level metrics accessible through the integration."""

    def test_fleet_metrics_counts(self, adapter_with_data):
        """Fleet metrics report correct worker and inference counts."""
        metrics = adapter_with_data.get_fleet_metrics()
        assert metrics["total_workers"] == 4
        assert metrics["total_inferences"] == 25 + 10 + 8 + 1  # 44

    def test_fleet_trust_distribution(self, adapter_with_data):
        """Fleet trust distribution is reported."""
        metrics = adapter_with_data.get_fleet_metrics()
        dist = metrics["trust_distribution"]
        assert "unknown" in dist  # 0xUnknown
        assert "low" in dist  # 0xLow

    def test_category_performance(self, adapter_with_data):
        """Category performance breakdown is available."""
        perf = adapter_with_data.get_category_performance()
        assert "physical_verification" in perf

    def test_improving_declining_workers(self, adapter_with_data):
        """Trend detection works at fleet level."""
        metrics = adapter_with_data.get_fleet_metrics()
        # At minimum, counts should be non-negative
        assert metrics["workers_improving"] >= 0
        assert metrics["workers_declining"] >= 0

    def test_diagnostics_full_snapshot(self, adapter_with_data):
        """Full diagnostic snapshot includes all sections."""
        diag = adapter_with_data.diagnose()
        assert "fleet_metrics" in diag
        assert "category_performance" in diag
        assert "cost_analysis" in diag
        assert "adapter_config" in diag


# ── 8. End-to-End Integration ─────────────────────────────────


class TestEndToEndIntegration:
    """Full pipeline: Integrator → Synthesizer → Adapter → Score → Route."""

    def test_full_pipeline_route_decision(self, adapter_with_data, task, candidates):
        """Complete routing decision through fully-wired pipeline."""
        synth = DecisionSynthesizer()
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)

        # Wire everything
        integrator.set_decision_synthesizer(synth)
        integrator.set_verification_adapter(adapter_with_data)

        # Verify wiring
        assert SignalType.VERIFICATION_QUALITY in synth._providers

        # Add a base signal so routing produces decisions
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: 65.0,
        )

        # Route
        decision = synth.synthesize(task, candidates)

        assert decision.outcome == DecisionOutcome.ROUTED
        assert len(decision.rankings) == 4
        # Exceptional worker should be #1 or close (verification + skill equal base)
        top = decision.rankings[0].candidate_id
        assert top == "0xExceptional", f"Expected 0xExceptional at top, got {top}"

    def test_pipeline_with_all_signals(self, adapter_with_data, task, candidates):
        """Multiple signals all contribute to final decision."""
        synth = DecisionSynthesizer()

        # Register multiple signals
        synth.register_signal(SignalType.SKILL_MATCH, lambda t, c: 70.0)
        synth.register_signal(SignalType.REPUTATION, lambda t, c: 60.0)
        synth.register_signal(SignalType.RELIABILITY, lambda t, c: 75.0)
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)

        # Decision should have signal vectors with signal info
        for ranking in decision.rankings:
            assert hasattr(ranking, "signals")
            assert ranking.signal_count >= 1

        # Exceptional worker should still come out ahead
        assert decision.rankings[0].candidate_id == "0xExceptional"

    def test_pipeline_graceful_degradation(self, task, candidates):
        """Pipeline works with no verification data (adapter returns defaults)."""
        adapter = VerificationAdapter()  # Empty, no data
        synth = DecisionSynthesizer()

        synth.register_signal(SignalType.SKILL_MATCH, lambda t, c: 70.0)
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)

        # Should still produce a decision (all get default 50.0)
        assert decision is not None
        assert decision.outcome == DecisionOutcome.ROUTED

    def test_integrator_health_with_full_wiring(self, adapter_with_data):
        """Fully-wired integrator reports all components healthy."""
        synth = DecisionSynthesizer()
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.set_decision_synthesizer(synth)
        integrator.set_verification_adapter(adapter_with_data)

        health = integrator.health()
        assert health["status"] == "healthy"
        details = health["components"]["details"]
        assert "verification_adapter" in details
        assert "decision_synthesizer" in details
        assert details["verification_adapter"]["healthy"]
        assert details["decision_synthesizer"]["healthy"]


# ── 9. Weight Sensitivity ──────────────────────────────────────


class TestWeightSensitivity:
    """Verification weight appropriately sized relative to other signals."""

    def test_verification_not_dominant(self, adapter_with_data, task, candidates):
        """Verification at 8% doesn't overwhelm other 92% of signals."""
        synth = DecisionSynthesizer()

        # Skill match says 0xLow is the best by far
        skill_scores = {
            "0xExceptional": 30.0,
            "0xStandard": 30.0,
            "0xLow": 95.0,
            "0xUnknown": 30.0,
        }
        synth.register_signal(
            SignalType.SKILL_MATCH,
            lambda t, c: skill_scores.get(c.get("id", ""), 50.0),
        )
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)

        # 0xLow should still win because skill_match (28%) >> verification (8%)
        top = decision.rankings[0].candidate_id
        assert top == "0xLow", (
            f"Skill-match dominant signal should win, got {top}"
        )

    def test_verification_breaks_ties(self, adapter_with_data, task, candidates):
        """When other signals are equal, verification breaks the tie."""
        synth = DecisionSynthesizer()

        # All signals equal
        synth.register_signal(SignalType.SKILL_MATCH, lambda t, c: 70.0)
        synth.register_signal(SignalType.REPUTATION, lambda t, c: 70.0)
        synth.register_signal(SignalType.RELIABILITY, lambda t, c: 70.0)

        # Verification is the tiebreaker
        synth.register_signal(
            SignalType.VERIFICATION_QUALITY,
            lambda t, c: adapter_with_data.score(c.get("id", ""), t),
        )

        decision = synth.synthesize(task, candidates)
        # Exceptional worker should win (verification breaks the tie)
        assert decision.rankings[0].candidate_id == "0xExceptional"


# ── 10. Regression Safety ────────────────────────────────────


class TestRegressionSafety:
    """Adding Signal #13 doesn't break existing functionality."""

    def test_synthesizer_works_without_verification(self, task, candidates):
        """DecisionSynthesizer still works without verification signal."""
        synth = DecisionSynthesizer()
        synth.register_signal(SignalType.SKILL_MATCH, lambda t, c: 70.0)
        synth.register_signal(SignalType.REPUTATION, lambda t, c: 60.0)

        decision = synth.synthesize(task, candidates)
        assert decision is not None
        assert decision.outcome == DecisionOutcome.ROUTED

    def test_integrator_works_without_verification(self):
        """SwarmIntegrator functions without verification adapter."""
        integrator = SwarmIntegrator.create_minimal()
        health = integrator.health()
        assert "verification_adapter" not in health["components"]["details"]

    def test_original_signal_weights_redistributed(self):
        """Original signals still sum properly with verification added."""
        # Core signals (excluding verification)
        core_signals = {k: v for k, v in DEFAULT_WEIGHTS.items()
                       if k != SignalType.VERIFICATION_QUALITY}
        core_sum = sum(core_signals.values())
        # Core should be 92% (leaving 8% for verification)
        assert abs(core_sum - 0.92) < 0.001

    def test_all_signal_types_accounted(self):
        """Every weighted signal has a valid SignalType."""
        for signal_type in DEFAULT_WEIGHTS:
            assert isinstance(signal_type, SignalType)
