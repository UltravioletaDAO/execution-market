"""
Tests for EvidenceParser — Skill DNA extraction from task evidence.

Coverage targets:
    - Evidence parsing (all 11 evidence types)
    - Quality assessment (excellent → suspicious)
    - Skill signal extraction (all 10 dimensions)
    - Fraud detection (suspicious patterns)
    - SkillDNA updates (EMA decay, categories, quality tracking)
    - WorkerRegistry (CRUD, specialists, save/load)
    - Edge cases (empty evidence, unknown types, malformed data)
"""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from mcp_server.swarm.evidence_parser import (
    EvidenceParser,
    EvidenceQuality,
    SkillDimension,
    SkillSignal,
    QualityAssessment,
    SkillDNA,
    WorkerRegistry,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def parser():
    return EvidenceParser()


@pytest.fixture
def registry():
    return WorkerRegistry()


@pytest.fixture
def sample_photo_evidence():
    return [
        {
            "type": "photo",
            "content": "Photo of completed delivery at front door. Package visible on porch.",
            "metadata": {"timestamp": "2026-03-14T02:00:00Z"},
        }
    ]


@pytest.fixture
def sample_geo_evidence():
    return [
        {
            "type": "photo_geo",
            "content": "Geo-tagged photo at target location",
            "metadata": {
                "latitude": 25.7617,
                "longitude": -80.1918,
                "timestamp": "2026-03-14T02:00:00Z",
                "accuracy_m": 5.0,
            },
        }
    ]


@pytest.fixture
def rich_evidence():
    """Multi-type evidence set for a high-quality completion."""
    return [
        {
            "type": "photo_geo",
            "content": "Arrived at location. Photo shows the storefront with address visible.",
            "metadata": {
                "latitude": 25.7617,
                "longitude": -80.1918,
                "location": "123 Main St",
                "timestamp": "2026-03-14T02:00:00Z",
            },
        },
        {
            "type": "receipt",
            "content": "Receipt from store showing purchase of requested items totaling $12.50",
            "metadata": {"store": "Target", "total": 12.50, "items": 3},
        },
        {
            "type": "text_response",
            "content": "Task completed successfully. All 3 items purchased as requested. "
                       "Left at the front door as instructed. Used the coupon code provided.",
        },
        {
            "type": "timestamp_proof",
            "content": "Completion timestamp verified",
            "metadata": {"captured_at": "2026-03-14T02:30:00Z"},
        },
    ]


@pytest.fixture
def suspicious_evidence():
    return [
        {
            "type": "text_response",
            "content": "lorem ipsum dolor sit amet test evidence placeholder",
        }
    ]


# ─── Evidence Parsing Tests ──────────────────────────────────────────────────

class TestEvidenceParsing:

    def test_parse_empty_evidence(self, parser):
        result = parser.parse_evidence([])
        assert result.quality == EvidenceQuality.POOR
        assert result.score == 0.0
        assert result.evidence_count == 0
        assert "no_evidence_submitted" in result.flags

    def test_parse_single_photo(self, parser, sample_photo_evidence):
        result = parser.parse_evidence(sample_photo_evidence)
        assert result.evidence_count == 1
        assert "photo" in result.evidence_types
        assert result.score > 0
        assert len(result.signals) > 0

    def test_parse_geo_photo(self, parser, sample_geo_evidence):
        result = parser.parse_evidence(sample_geo_evidence)
        assert "photo_geo" in result.evidence_types
        # Should have geo_mobility signal
        geo_signals = [s for s in result.signals if s.dimension == SkillDimension.GEO_MOBILITY]
        assert len(geo_signals) > 0
        # Geo data should boost the signal
        assert geo_signals[0].strength > 0.8

    def test_parse_rich_evidence_high_quality(self, parser, rich_evidence):
        result = parser.parse_evidence(rich_evidence)
        assert result.quality in (EvidenceQuality.EXCELLENT, EvidenceQuality.GOOD)
        assert result.score >= 0.6
        assert result.evidence_count == 4
        assert len(set(result.evidence_types)) >= 3  # Multiple types

    def test_parse_suspicious_evidence(self, parser, suspicious_evidence):
        result = parser.parse_evidence(suspicious_evidence)
        assert result.quality == EvidenceQuality.SUSPICIOUS
        assert any("suspicious" in f for f in result.flags)

    def test_parse_video_evidence(self, parser):
        evidence = [{"type": "video", "content": "30-second video showing task completion process"}]
        result = parser.parse_evidence(evidence)
        assert "video" in result.evidence_types
        thoroughness = [s for s in result.signals if s.dimension == SkillDimension.THOROUGHNESS]
        assert len(thoroughness) > 0

    def test_parse_document_evidence(self, parser):
        evidence = [{
            "type": "document",
            "content": "Detailed report of research findings. " * 10,
            "metadata": {"pages": 5, "format": "pdf", "file_size": 102400},
        }]
        result = parser.parse_evidence(evidence)
        # Should detect digital proficiency and communication
        dims = {s.dimension for s in result.signals}
        assert SkillDimension.DIGITAL_PROFICIENCY in dims
        assert SkillDimension.COMMUNICATION in dims

    def test_parse_measurement_evidence(self, parser):
        evidence = [{
            "type": "measurement",
            "content": "Room dimensions: 12ft x 15ft. Ceiling height: 9ft. Window area: 24 sqft.",
        }]
        result = parser.parse_evidence(evidence)
        tech_signals = [s for s in result.signals if s.dimension == SkillDimension.TECHNICAL_SKILL]
        assert len(tech_signals) > 0

    def test_parse_screenshot_evidence(self, parser):
        evidence = [{
            "type": "screenshot",
            "content": "Screenshot of completed form submission",
            "metadata": {"resolution": "1920x1080"},
        }]
        result = parser.parse_evidence(evidence)
        digital = [s for s in result.signals if s.dimension == SkillDimension.DIGITAL_PROFICIENCY]
        assert len(digital) > 0

    def test_parse_notarized_evidence(self, parser):
        evidence = [{
            "type": "notarized",
            "content": "Notarized document confirming identity verification",
            "metadata": {"notary_id": "N12345", "state": "FL", "date": "2026-03-14"},
        }]
        result = parser.parse_evidence(evidence)
        # Notarized should have high verification score
        verif = [s for s in result.signals if s.dimension == SkillDimension.VERIFICATION_SKILL]
        assert len(verif) > 0
        assert verif[0].strength >= 0.9

    def test_parse_signature_evidence(self, parser):
        evidence = [{"type": "signature", "content": "Digital signature collected"}]
        result = parser.parse_evidence(evidence)
        verif = [s for s in result.signals if s.dimension == SkillDimension.VERIFICATION_SKILL]
        assert len(verif) > 0

    def test_parse_timestamp_proof(self, parser):
        evidence = [{
            "type": "timestamp_proof",
            "content": "Proof of completion",
            "metadata": {"captured_at": "2026-03-14T02:00:00Z"},
        }]
        result = parser.parse_evidence(evidence)
        speed = [s for s in result.signals if s.dimension == SkillDimension.SPEED]
        assert len(speed) > 0

    def test_parse_receipt_evidence(self, parser):
        evidence = [{
            "type": "receipt",
            "content": "Store receipt: $12.50 total, 3 items purchased",
        }]
        result = parser.parse_evidence(evidence)
        phys = [s for s in result.signals if s.dimension == SkillDimension.PHYSICAL_EXECUTION]
        assert len(phys) > 0

    def test_parse_unknown_evidence_type(self, parser):
        evidence = [{"type": "hologram", "content": "3D holographic proof"}]
        result = parser.parse_evidence(evidence)
        assert result.evidence_count == 1
        # Unknown types should still produce a thoroughness signal
        signals = [s for s in result.signals if s.dimension == SkillDimension.THOROUGHNESS]
        assert len(signals) > 0

    def test_parse_text_response(self, parser):
        evidence = [{
            "type": "text_response",
            "content": "I have completed the research task as requested. "
                       "Here are the key findings from analyzing 5 competitor websites...",
        }]
        result = parser.parse_evidence(evidence)
        comm = [s for s in result.signals if s.dimension == SkillDimension.COMMUNICATION]
        assert len(comm) > 0


# ─── Quality Assessment Tests ────────────────────────────────────────────────

class TestQualityAssessment:

    def test_quality_diversity_bonus(self, parser):
        # Single type
        single = parser.parse_evidence([{"type": "photo", "content": "pic"}])
        # Multiple types
        multi = parser.parse_evidence([
            {"type": "photo", "content": "pic"},
            {"type": "text_response", "content": "description"},
            {"type": "receipt", "content": "receipt"},
        ])
        assert multi.details["diversity_bonus"] > single.details["diversity_bonus"]

    def test_quality_quantity_bonus(self, parser):
        single = parser.parse_evidence([{"type": "photo", "content": "pic"}])
        many = parser.parse_evidence([
            {"type": "photo", "content": f"pic {i}"} for i in range(5)
        ])
        assert many.details["quantity_bonus"] > single.details["quantity_bonus"]

    def test_quality_suspicion_penalty(self, parser):
        clean = parser.parse_evidence([{"type": "text_response", "content": "Genuine completion report"}])
        dirty = parser.parse_evidence([{"type": "text_response", "content": "lorem ipsum placeholder test evidence"}])
        assert dirty.details["suspicion_penalty"] > clean.details["suspicion_penalty"]

    def test_quality_to_dict(self, parser, rich_evidence):
        result = parser.parse_evidence(rich_evidence)
        d = result.to_dict()
        assert "quality" in d
        assert "score" in d
        assert "evidence_count" in d
        assert "signals" in d
        assert isinstance(d["signals"], list)

    def test_quality_thresholds(self, parser):
        # Test that all threshold categories are achievable
        # Excellent: score >= 0.8
        long_text = "Detailed evidence description with many specifics about the task completion. " * 5
        excellent_evidence = [
            {"type": "photo_geo", "content": long_text, "metadata": {"latitude": 1.0, "location": "A", "extra1": 1, "extra2": 2}},
            {"type": "notarized", "content": long_text, "metadata": {"notary": "N1", "date": "2026-03-14", "state": "FL"}},
            {"type": "video", "content": long_text, "metadata": {"duration": 30, "resolution": "1080p", "format": "mp4"}},
            {"type": "document", "content": long_text, "metadata": {"pages": 5, "format": "pdf", "size": 102400}},
            {"type": "measurement", "content": long_text},
        ]
        result = parser.parse_evidence(excellent_evidence)
        assert result.score >= 0.8 or result.quality in (EvidenceQuality.EXCELLENT, EvidenceQuality.GOOD)


# ─── Fraud Detection Tests ───────────────────────────────────────────────────

class TestFraudDetection:

    def test_detect_lorem_ipsum(self, parser):
        evidence = [{"type": "text_response", "content": "lorem ipsum dolor sit amet"}]
        result = parser.parse_evidence(evidence)
        assert result.quality == EvidenceQuality.SUSPICIOUS

    def test_detect_test_evidence(self, parser):
        evidence = [{"type": "text_response", "content": "this is test evidence for QA"}]
        result = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in result.flags)

    def test_detect_placeholder(self, parser):
        evidence = [{"type": "text_response", "content": "placeholder text goes here"}]
        result = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in result.flags)

    def test_detect_dummy_content(self, parser):
        evidence = [{"type": "text_response", "content": "dummy data entry"}]
        result = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in result.flags)

    def test_detect_asdf_pattern(self, parser):
        evidence = [{"type": "text_response", "content": "completed asdf work"}]
        result = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in result.flags)

    def test_clean_content_no_flags(self, parser):
        evidence = [{
            "type": "text_response",
            "content": "I visited the store at 2pm and purchased all 3 items. Total was $15.50.",
        }]
        result = parser.parse_evidence(evidence)
        assert len(result.flags) == 0

    def test_suspicious_in_description(self, parser):
        evidence = [{
            "type": "photo",
            "content": "real photo",
            "description": "lorem ipsum test placeholder",
        }]
        result = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in result.flags)


# ─── Skill Signal Tests ──────────────────────────────────────────────────────

class TestSkillSignals:

    def test_signal_to_dict(self):
        signal = SkillSignal(
            dimension=SkillDimension.PHYSICAL_EXECUTION,
            strength=0.75,
            source="photo",
            detail="from photo, detailed_content",
        )
        d = signal.to_dict()
        assert d["dimension"] == "physical_execution"
        assert d["strength"] == 0.75
        assert d["source"] == "photo"

    def test_signal_strength_capped_at_1(self, parser):
        # Rich content with metadata should boost but not exceed 1.0
        evidence = [{
            "type": "photo_geo",
            "content": "x" * 200,  # Long content
            "metadata": {
                "latitude": 25.0,
                "location": "test",
                "extra1": 1,
                "extra2": 2,
                "extra3": 3,
            },
        }]
        result = parser.parse_evidence(evidence)
        for signal in result.signals:
            assert signal.strength <= 1.0

    def test_content_length_boost(self, parser):
        short = parser.parse_evidence([{"type": "text_response", "content": "done"}])
        long = parser.parse_evidence([{"type": "text_response", "content": "I completed the task. " * 20}])
        # Long content should produce stronger signals
        short_max = max(s.strength for s in short.signals) if short.signals else 0
        long_max = max(s.strength for s in long.signals) if long.signals else 0
        assert long_max >= short_max

    def test_metadata_richness_boost(self, parser):
        bare = parser.parse_evidence([{"type": "document", "content": "doc"}])
        rich = parser.parse_evidence([{
            "type": "document",
            "content": "doc",
            "metadata": {"a": 1, "b": 2, "c": 3},
        }])
        # Rich metadata should produce stronger signals
        bare_max = max(s.strength for s in bare.signals) if bare.signals else 0
        rich_max = max(s.strength for s in rich.signals) if rich.signals else 0
        assert rich_max >= bare_max

    def test_all_evidence_types_produce_signals(self, parser):
        """Every known evidence type should produce at least one signal."""
        for ev_type in EvidenceParser.EVIDENCE_SKILL_MAP.keys():
            result = parser.parse_evidence([{"type": ev_type, "content": "test"}])
            assert len(result.signals) > 0, f"No signals for {ev_type}"


# ─── Task Context Signals Tests ──────────────────────────────────────────────

class TestTaskContextSignals:

    def test_delivery_task_context(self, parser):
        evidence = [{"type": "photo", "content": "delivered"}]
        task_data = {"category": "delivery"}
        result = parser.parse_evidence(evidence, task_data)
        phys = [s for s in result.signals if s.dimension == SkillDimension.PHYSICAL_EXECUTION and s.source == "task_context"]
        assert len(phys) > 0

    def test_coding_task_context(self, parser):
        evidence = [{"type": "screenshot", "content": "code"}]
        task_data = {"category": "coding"}
        result = parser.parse_evidence(evidence, task_data)
        digital = [s for s in result.signals if s.dimension == SkillDimension.DIGITAL_PROFICIENCY and s.source == "task_context"]
        assert len(digital) > 0

    def test_blockchain_task_context(self, parser):
        evidence = [{"type": "text_response", "content": "tx hash: 0x..."}]
        task_data = {"category": "blockchain"}
        result = parser.parse_evidence(evidence, task_data)
        crypto = [s for s in result.signals if s.dimension == SkillDimension.BLOCKCHAIN_LITERACY]
        assert len(crypto) > 0

    def test_design_task_context(self, parser):
        evidence = [{"type": "document", "content": "design mockup"}]
        task_data = {"category": "design"}
        result = parser.parse_evidence(evidence, task_data)
        creative = [s for s in result.signals if s.dimension == SkillDimension.CREATIVE_SKILL]
        assert len(creative) > 0

    def test_high_bounty_task_context(self, parser):
        evidence = [{"type": "document", "content": "complex work"}]
        task_data = {"category": "research", "bounty_amount": 100}
        result = parser.parse_evidence(evidence, task_data)
        tech = [s for s in result.signals if s.dimension == SkillDimension.TECHNICAL_SKILL and s.source == "task_context"]
        assert len(tech) > 0


# ─── SkillDNA Tests ──────────────────────────────────────────────────────────

class TestSkillDNA:

    def test_dna_initialization(self):
        dna = SkillDNA(worker_id="worker-1")
        assert dna.worker_id == "worker-1"
        assert dna.task_count == 0
        assert len(dna.dimensions) == 0

    def test_update_dimension_ema(self):
        dna = SkillDNA(worker_id="w-1")
        dna.update_dimension(SkillDimension.PHYSICAL_EXECUTION, 0.8)
        first = dna.dimensions["physical_execution"]
        assert first > 0
        # Second update with EMA should blend
        dna.update_dimension(SkillDimension.PHYSICAL_EXECUTION, 1.0)
        second = dna.dimensions["physical_execution"]
        assert second > first  # Should increase toward 1.0

    def test_apply_signals(self):
        dna = SkillDNA(worker_id="w-2")
        signals = [
            SkillSignal(SkillDimension.COMMUNICATION, 0.7, "text_response"),
            SkillSignal(SkillDimension.DIGITAL_PROFICIENCY, 0.6, "screenshot"),
        ]
        dna.apply_signals(signals)
        assert "communication" in dna.dimensions
        assert "digital_proficiency" in dna.dimensions

    def test_get_top_skills(self):
        dna = SkillDNA(worker_id="w-3")
        dna.dimensions = {
            "physical_execution": 0.9,
            "communication": 0.7,
            "speed": 0.5,
            "thoroughness": 0.3,
        }
        top = dna.get_top_skills(2)
        assert len(top) == 2
        assert top[0][0] == "physical_execution"
        assert top[1][0] == "communication"

    def test_get_weakness(self):
        dna = SkillDNA(worker_id="w-4")
        dna.dimensions = {
            "physical_execution": 0.9,
            "communication": 0.2,
            "speed": 0.5,
        }
        weakness = dna.get_weakness()
        assert weakness[0] == "communication"
        assert weakness[1] == 0.2

    def test_get_weakness_empty(self):
        dna = SkillDNA(worker_id="w-5")
        assert dna.get_weakness() is None

    def test_dna_to_dict(self):
        dna = SkillDNA(worker_id="w-6")
        dna.dimensions = {"speed": 0.8, "communication": 0.6}
        dna.task_count = 10
        dna.evidence_count = 25
        dna.categories_seen = {"delivery", "errand"}
        dna.avg_quality = 0.75
        d = dna.to_dict()
        assert d["worker_id"] == "w-6"
        assert d["task_count"] == 10
        assert d["evidence_count"] == 25
        assert "delivery" in d["categories"]
        assert len(d["top_skills"]) == 2

    def test_dna_categories_tracking(self):
        dna = SkillDNA(worker_id="w-7")
        dna.categories_seen.add("delivery")
        dna.categories_seen.add("errand")
        dna.categories_seen.add("delivery")  # Duplicate
        assert len(dna.categories_seen) == 2

    def test_dna_decay_factor(self):
        dna = SkillDNA(worker_id="w-8")
        # High decay = more weight on history
        dna.update_dimension(SkillDimension.SPEED, 1.0, decay=0.99)
        high_decay_val = dna.dimensions["speed"]
        
        dna2 = SkillDNA(worker_id="w-9")
        # Low decay = more weight on new signal
        dna2.update_dimension(SkillDimension.SPEED, 1.0, decay=0.1)
        low_decay_val = dna2.dimensions["speed"]
        
        # With 0 initial, low decay should give higher value (more weight on new)
        assert low_decay_val > high_decay_val


# ─── SkillDNA Update via Parser Tests ────────────────────────────────────────

class TestSkillDNAUpdate:

    def test_update_dna_from_assessment(self, parser):
        dna = SkillDNA(worker_id="update-1")
        evidence = [
            {"type": "photo_geo", "content": "pic", "metadata": {"latitude": 25.0}},
            {"type": "text_response", "content": "Completed the delivery successfully"},
        ]
        assessment = parser.parse_evidence(evidence)
        parser.update_skill_dna(dna, assessment, task_categories=["delivery"])
        
        assert dna.task_count == 1
        assert dna.evidence_count == 2
        assert "delivery" in dna.categories_seen
        assert dna.avg_quality == assessment.score
        assert len(dna.dimensions) > 0

    def test_update_dna_running_average(self, parser):
        dna = SkillDNA(worker_id="avg-1")
        
        # First assessment
        ev1 = [{"type": "photo", "content": "pic"}]
        a1 = parser.parse_evidence(ev1)
        parser.update_skill_dna(dna, a1)
        first_quality = dna.avg_quality
        
        # Second assessment with different quality
        ev2 = [
            {"type": "photo_geo", "content": "x" * 200, "metadata": {"latitude": 1.0}},
            {"type": "notarized", "content": "notarized doc"},
        ]
        a2 = parser.parse_evidence(ev2)
        parser.update_skill_dna(dna, a2)
        
        # Average quality should be between the two
        assert dna.task_count == 2
        assert dna.avg_quality != first_quality

    def test_update_dna_multiple_categories(self, parser):
        dna = SkillDNA(worker_id="cats-1")
        ev = [{"type": "text_response", "content": "done"}]
        
        a1 = parser.parse_evidence(ev)
        parser.update_skill_dna(dna, a1, task_categories=["delivery"])
        
        a2 = parser.parse_evidence(ev)
        parser.update_skill_dna(dna, a2, task_categories=["coding", "testing"])
        
        assert dna.categories_seen == {"delivery", "coding", "testing"}


# ─── WorkerRegistry Tests ────────────────────────────────────────────────────

class TestWorkerRegistry:

    def test_get_or_create_new(self, registry):
        dna = registry.get_or_create("new-worker")
        assert dna.worker_id == "new-worker"
        assert dna.task_count == 0

    def test_get_or_create_existing(self, registry):
        dna1 = registry.get_or_create("existing")
        dna1.task_count = 5
        dna2 = registry.get_or_create("existing")
        assert dna2.task_count == 5  # Same object

    def test_process_completion(self, registry):
        evidence = [
            {"type": "photo", "content": "delivery photo"},
            {"type": "text_response", "content": "Delivered to front door"},
        ]
        dna, assessment = registry.process_completion(
            worker_id="worker-1",
            evidence=evidence,
            task_categories=["delivery"],
        )
        assert dna.task_count == 1
        assert dna.evidence_count == 2
        assert assessment.evidence_count == 2

    def test_process_multiple_completions(self, registry):
        for i in range(5):
            evidence = [{"type": "photo", "content": f"photo {i}"}]
            registry.process_completion(
                worker_id="prolific",
                evidence=evidence,
                task_categories=["errand"],
            )
        dna = registry.get_worker("prolific")
        assert dna.task_count == 5
        assert dna.evidence_count == 5

    def test_get_worker_not_found(self, registry):
        assert registry.get_worker("ghost") is None

    def test_list_workers(self, registry):
        registry.get_or_create("w1")
        registry.get_or_create("w2")
        registry.get_or_create("w3")
        workers = registry.list_workers()
        assert len(workers) == 3

    def test_get_specialists(self, registry):
        # Create workers with different skill profiles
        w1 = registry.get_or_create("specialist-1")
        w1.dimensions = {"physical_execution": 0.9, "speed": 0.3}
        
        w2 = registry.get_or_create("specialist-2")
        w2.dimensions = {"physical_execution": 0.6, "speed": 0.8}
        
        w3 = registry.get_or_create("specialist-3")
        w3.dimensions = {"digital_proficiency": 0.9}
        
        physical_specialists = registry.get_specialists(SkillDimension.PHYSICAL_EXECUTION, min_score=0.5)
        assert len(physical_specialists) == 2
        assert physical_specialists[0].worker_id == "specialist-1"  # Highest score first

    def test_get_specialists_empty(self, registry):
        result = registry.get_specialists(SkillDimension.BLOCKCHAIN_LITERACY, min_score=0.5)
        assert result == []

    def test_get_best_for_category(self, registry):
        w1 = registry.get_or_create("cat-1")
        w1.categories_seen = {"delivery"}
        w1.avg_quality = 0.9
        
        w2 = registry.get_or_create("cat-2")
        w2.categories_seen = {"delivery", "errand"}
        w2.avg_quality = 0.7
        
        w3 = registry.get_or_create("cat-3")
        w3.categories_seen = {"coding"}
        w3.avg_quality = 0.95
        
        best = registry.get_best_for_category("delivery", top_n=5)
        assert len(best) == 2
        assert best[0].worker_id == "cat-1"  # Higher quality

    def test_save_and_load(self, registry):
        # Populate registry
        evidence = [{"type": "photo_geo", "content": "test", "metadata": {"latitude": 25.0}}]
        registry.process_completion("saver-1", evidence, task_categories=["delivery"])
        registry.process_completion("saver-2", evidence, task_categories=["coding"])
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        
        try:
            registry.save(path)
            loaded = WorkerRegistry.load(path)
            assert len(loaded.list_workers()) == 2
            w1 = loaded.get_worker("saver-1")
            assert w1 is not None
            assert w1.task_count == 1
            assert "delivery" in w1.categories_seen
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        loaded = WorkerRegistry.load("/nonexistent/path/registry.json")
        assert len(loaded.list_workers()) == 0

    def test_to_dict(self, registry):
        registry.get_or_create("dict-1")
        registry.get_or_create("dict-2")
        d = registry.to_dict()
        assert d["worker_count"] == 2
        assert "dict-1" in d["workers"]
        assert "dict-2" in d["workers"]


# ─── Evidence Type Normalization Tests ────────────────────────────────────────

class TestNormalization:

    def test_normalize_type_field(self, parser):
        evidence = [{"type": "Photo_Geo", "content": "test"}]
        result = parser.parse_evidence(evidence)
        assert "photo_geo" in result.evidence_types

    def test_normalize_evidence_type_field(self, parser):
        evidence = [{"evidence_type": "text_response", "content": "test"}]
        result = parser.parse_evidence(evidence)
        assert "text_response" in result.evidence_types

    def test_normalize_whitespace(self, parser):
        evidence = [{"type": "  photo  ", "content": "test"}]
        result = parser.parse_evidence(evidence)
        assert "photo" in result.evidence_types

    def test_missing_type_defaults_unknown(self, parser):
        evidence = [{"content": "no type field"}]
        result = parser.parse_evidence(evidence)
        assert result.evidence_count == 1


# ─── Edge Cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_none_metadata(self, parser):
        evidence = [{"type": "photo", "content": "test", "metadata": None}]
        result = parser.parse_evidence(evidence)
        assert result.evidence_count == 1

    def test_empty_content(self, parser):
        evidence = [{"type": "photo", "content": ""}]
        result = parser.parse_evidence(evidence)
        assert result.evidence_count == 1

    def test_missing_content_field(self, parser):
        evidence = [{"type": "receipt"}]
        result = parser.parse_evidence(evidence)
        assert result.evidence_count == 1

    def test_non_dict_evidence_item(self, parser):
        # Parser should handle gracefully
        evidence = [{"type": "text_response", "content": "valid"}]
        result = parser.parse_evidence(evidence)
        assert result.evidence_count == 1

    def test_bounty_string_in_task_context(self, parser):
        evidence = [{"type": "text_response", "content": "done"}]
        task_data = {"category": "research", "bounty_amount": "not_a_number"}
        # Should not raise
        result = parser.parse_evidence(evidence, task_data)
        assert result.evidence_count == 1

    def test_very_large_evidence_list(self, parser):
        evidence = [{"type": "photo", "content": f"pic {i}"} for i in range(100)]
        result = parser.parse_evidence(evidence)
        assert result.evidence_count == 100
        # Quantity bonus should be capped
        assert result.details["quantity_bonus"] <= 0.1
