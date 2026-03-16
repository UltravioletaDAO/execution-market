"""
Tests for EvidenceParser — Skill DNA extraction from task completion evidence.

Covers:
    - SkillSignal creation and serialization
    - QualityAssessment computation (scoring, diversity bonus, quantity bonus)
    - EvidenceParser parsing for all 11 evidence types
    - Fraud/suspicious content detection
    - SkillDNA exponential moving average updates
    - WorkerRegistry CRUD, specialists, save/load
    - Task context signal extraction (categories, bounty)
    - Edge cases: empty evidence, unknown types, malformed data
"""

import os
import tempfile

import pytest

from mcp_server.swarm.evidence_parser import (
    SkillDimension,
    EvidenceQuality,
    SkillSignal,
    QualityAssessment,
    SkillDNA,
    EvidenceParser,
    WorkerRegistry,
)


# ─── SkillSignal ──────────────────────────────────────────────────────────────


class TestSkillSignal:
    def test_creation(self):
        s = SkillSignal(
            dimension=SkillDimension.PHYSICAL_EXECUTION,
            strength=0.75,
            source="photo",
            detail="test detail",
        )
        assert s.dimension == SkillDimension.PHYSICAL_EXECUTION
        assert s.strength == 0.75
        assert s.source == "photo"
        assert s.detail == "test detail"

    def test_to_dict(self):
        s = SkillSignal(
            dimension=SkillDimension.GEO_MOBILITY,
            strength=0.8765,
            source="photo_geo",
        )
        d = s.to_dict()
        assert d["dimension"] == "geo_mobility"
        assert d["strength"] == 0.876  # rounded to 3 decimals (banker's rounding)
        assert d["source"] == "photo_geo"

    def test_default_detail(self):
        s = SkillSignal(
            dimension=SkillDimension.SPEED,
            strength=0.5,
            source="timestamp_proof",
        )
        assert s.detail == ""


# ─── QualityAssessment ────────────────────────────────────────────────────────


class TestQualityAssessment:
    def test_to_dict_basic(self):
        qa = QualityAssessment(
            quality=EvidenceQuality.GOOD,
            score=0.72,
            evidence_count=3,
            evidence_types=["photo", "text_response"],
            signals=[],
            flags=[],
        )
        d = qa.to_dict()
        assert d["quality"] == "good"
        assert d["score"] == 0.72
        assert d["evidence_count"] == 3
        assert d["evidence_types"] == ["photo", "text_response"]
        assert d["signals"] == []
        assert d["flags"] == []

    def test_to_dict_with_signals(self):
        sig = SkillSignal(
            dimension=SkillDimension.COMMUNICATION,
            strength=0.6,
            source="document",
        )
        qa = QualityAssessment(
            quality=EvidenceQuality.EXCELLENT,
            score=0.9,
            evidence_count=5,
            evidence_types=["photo", "document", "video"],
            signals=[sig],
        )
        d = qa.to_dict()
        assert len(d["signals"]) == 1
        assert d["signals"][0]["dimension"] == "communication"


# ─── SkillDNA ─────────────────────────────────────────────────────────────────


class TestSkillDNA:
    def test_creation(self):
        dna = SkillDNA(worker_id="w1")
        assert dna.worker_id == "w1"
        assert dna.dimensions == {}
        assert dna.task_count == 0
        assert dna.evidence_count == 0
        assert dna.avg_quality == 0.0
        assert len(dna.categories_seen) == 0

    def test_update_dimension_first_time(self):
        dna = SkillDNA(worker_id="w1")
        dna.update_dimension(SkillDimension.SPEED, 0.8, decay=0.9)
        # EMA: 0.9 * 0.0 + 0.1 * 0.8 = 0.08
        assert abs(dna.dimensions["speed"] - 0.08) < 0.001

    def test_update_dimension_cumulative(self):
        dna = SkillDNA(worker_id="w1")
        dna.update_dimension(SkillDimension.SPEED, 0.8, decay=0.9)
        # After first: 0.08
        dna.update_dimension(SkillDimension.SPEED, 0.9, decay=0.9)
        # After second: 0.9 * 0.08 + 0.1 * 0.9 = 0.072 + 0.09 = 0.162
        assert abs(dna.dimensions["speed"] - 0.162) < 0.001

    def test_apply_signals(self):
        dna = SkillDNA(worker_id="w1")
        signals = [
            SkillSignal(SkillDimension.PHYSICAL_EXECUTION, 0.6, "photo"),
            SkillSignal(SkillDimension.GEO_MOBILITY, 0.8, "photo_geo"),
        ]
        dna.apply_signals(signals)
        assert "physical_execution" in dna.dimensions
        assert "geo_mobility" in dna.dimensions

    def test_get_top_skills(self):
        dna = SkillDNA(worker_id="w1")
        dna.dimensions = {
            "speed": 0.3,
            "communication": 0.8,
            "physical_execution": 0.6,
            "thoroughness": 0.9,
        }
        top = dna.get_top_skills(2)
        assert len(top) == 2
        assert top[0] == ("thoroughness", 0.9)
        assert top[1] == ("communication", 0.8)

    def test_get_top_skills_empty(self):
        dna = SkillDNA(worker_id="w1")
        assert dna.get_top_skills() == []

    def test_get_weakness(self):
        dna = SkillDNA(worker_id="w1")
        dna.dimensions = {"speed": 0.3, "communication": 0.8}
        weak = dna.get_weakness()
        assert weak == ("speed", 0.3)

    def test_get_weakness_empty(self):
        dna = SkillDNA(worker_id="w1")
        assert dna.get_weakness() is None

    def test_to_dict(self):
        dna = SkillDNA(worker_id="w1")
        dna.dimensions = {"speed": 0.555, "communication": 0.777}
        dna.task_count = 5
        dna.evidence_count = 12
        dna.categories_seen = {"delivery", "errand"}
        dna.avg_quality = 0.6543

        d = dna.to_dict()
        assert d["worker_id"] == "w1"
        assert d["dimensions"]["speed"] == 0.555
        assert d["dimensions"]["communication"] == 0.777
        assert d["task_count"] == 5
        assert d["evidence_count"] == 12
        assert set(d["categories"]) == {"delivery", "errand"}
        assert d["avg_quality"] == 0.654
        assert len(d["top_skills"]) == 2
        assert "last_updated" in d


# ─── EvidenceParser ───────────────────────────────────────────────────────────


class TestEvidenceParser:
    @pytest.fixture
    def parser(self):
        return EvidenceParser()

    def test_empty_evidence(self, parser):
        qa = parser.parse_evidence([])
        assert qa.quality == EvidenceQuality.POOR
        assert qa.score == 0.0
        assert qa.evidence_count == 0
        assert "no_evidence_submitted" in qa.flags

    def test_single_photo(self, parser):
        evidence = [{"type": "photo", "content": "image data"}]
        qa = parser.parse_evidence(evidence)
        assert qa.evidence_count == 1
        assert "photo" in qa.evidence_types
        assert len(qa.signals) >= 2  # physical_execution + thoroughness
        assert qa.score > 0

    def test_photo_geo_with_coordinates(self, parser):
        evidence = [
            {
                "type": "photo_geo",
                "content": "geo tagged image",
                "metadata": {
                    "latitude": 25.7617,
                    "longitude": -80.1918,
                    "timestamp": "2026-03-16",
                },
            }
        ]
        qa = parser.parse_evidence(evidence)
        assert "photo_geo" in qa.evidence_types
        # Should have geo_mobility with geo_verified boost
        geo_signals = [
            s for s in qa.signals if s.dimension == SkillDimension.GEO_MOBILITY
        ]
        assert len(geo_signals) >= 1
        assert any("geo_verified" in s.detail for s in geo_signals)

    def test_all_evidence_types(self, parser):
        """Verify all 11 evidence types produce signals."""
        types = [
            "photo",
            "photo_geo",
            "video",
            "document",
            "receipt",
            "text_response",
            "screenshot",
            "measurement",
            "signature",
            "notarized",
            "timestamp_proof",
        ]
        for ev_type in types:
            qa = parser.parse_evidence([{"type": ev_type, "content": "test"}])
            assert len(qa.signals) > 0, f"No signals for {ev_type}"
            assert qa.evidence_count == 1

    def test_unknown_evidence_type(self, parser):
        evidence = [{"type": "alien_scan", "content": "data"}]
        qa = parser.parse_evidence(evidence)
        assert qa.evidence_count == 1
        # Should produce a default thoroughness signal
        assert any(s.dimension == SkillDimension.THOROUGHNESS for s in qa.signals)

    def test_diversity_bonus(self, parser):
        """Multiple evidence types should get a diversity bonus."""
        single = parser.parse_evidence([{"type": "photo", "content": "x"}])
        diverse = parser.parse_evidence(
            [
                {"type": "photo", "content": "x"},
                {"type": "text_response", "content": "detailed report"},
                {"type": "screenshot", "content": "screen capture"},
            ]
        )
        # Diverse should score higher than single (from diversity + quantity bonus)
        assert diverse.score >= single.score
        assert diverse.details.get("diversity_bonus", 0) > single.details.get(
            "diversity_bonus", 0
        )

    def test_quantity_bonus(self, parser):
        """More evidence items should get a quantity bonus."""
        few = parser.parse_evidence([{"type": "photo", "content": "x"}])
        many = parser.parse_evidence(
            [
                {"type": "photo", "content": "item1"},
                {"type": "photo", "content": "item2"},
                {"type": "photo", "content": "item3"},
                {"type": "photo", "content": "item4"},
                {"type": "photo", "content": "item5"},
            ]
        )
        assert many.details.get("quantity_bonus", 0) > few.details.get(
            "quantity_bonus", 0
        )

    def test_suspicious_content_lorem_ipsum(self, parser):
        evidence = [{"type": "text_response", "content": "Lorem ipsum dolor sit amet"}]
        qa = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in qa.flags)
        assert qa.quality == EvidenceQuality.SUSPICIOUS

    def test_suspicious_content_test_evidence(self, parser):
        evidence = [{"type": "photo", "content": "test evidence placeholder"}]
        qa = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in qa.flags)

    def test_suspicious_content_dummy(self, parser):
        evidence = [{"type": "document", "content": "dummy data for testing"}]
        qa = parser.parse_evidence(evidence)
        assert any("suspicious" in f for f in qa.flags)

    def test_clean_content_not_suspicious(self, parser):
        evidence = [
            {
                "type": "text_response",
                "content": "I completed the delivery to the specified address. Package left at front door.",
            }
        ]
        qa = parser.parse_evidence(evidence)
        assert not any("suspicious" in f for f in qa.flags)

    def test_rich_content_boosts_strength(self, parser):
        """Long content should boost signal strength."""
        short = parser.parse_evidence([{"type": "text_response", "content": "done"}])
        long_content = "A" * 150  # > 100 chars
        long = parser.parse_evidence(
            [{"type": "text_response", "content": long_content}]
        )

        # Find matching signals for comparison
        short_comm = [
            s for s in short.signals if s.dimension == SkillDimension.COMMUNICATION
        ]
        long_comm = [
            s for s in long.signals if s.dimension == SkillDimension.COMMUNICATION
        ]
        assert long_comm[0].strength >= short_comm[0].strength

    def test_rich_metadata_boosts_strength(self, parser):
        evidence_no_meta = [{"type": "photo", "content": "img"}]
        evidence_rich_meta = [
            {
                "type": "photo",
                "content": "img",
                "metadata": {"resolution": "4k", "format": "jpg", "size": 1024},
            }
        ]
        qa_no = parser.parse_evidence(evidence_no_meta)
        qa_rich = parser.parse_evidence(evidence_rich_meta)
        # Rich metadata version should have at least equal or better score
        assert qa_rich.score >= qa_no.score

    def test_notarized_quality_bonus(self, parser):
        """Notarized evidence should get a premium quality boost."""
        notarized = parser.parse_evidence([{"type": "notarized", "content": "doc"}])
        regular = parser.parse_evidence([{"type": "text_response", "content": "doc"}])
        # Notarized has +0.2 quality bonus
        assert notarized.score > regular.score

    def test_quality_tiers(self, parser):
        """Test that quality tiers are correctly assigned."""
        # Poor: no content
        poor = parser.parse_evidence([{"type": "text_response"}])
        assert poor.quality in (EvidenceQuality.POOR, EvidenceQuality.ADEQUATE)

        # Excellent: multiple rich evidence types (use realistic content, not "x"*N which triggers suspicious)
        excellent_evidence = [
            {
                "type": "photo_geo",
                "content": "Geo-tagged delivery photo at the customer's front door, package visible "
                * 3,
                "metadata": {
                    "latitude": 25.7,
                    "longitude": -80.1,
                    "timestamp": "2026-01-01",
                    "extra": "data",
                },
            },
            {
                "type": "notarized",
                "content": "Notarized document confirming delivery receipt signed by customer "
                * 3,
                "metadata": {"notary": "John", "date": "2026-01-01", "id": "123"},
            },
            {
                "type": "video",
                "content": "Video walkthrough of completed installation showing all components "
                * 3,
                "metadata": {"duration": 120},
            },
            {
                "type": "document",
                "content": "Detailed inspection report covering structural integrity and safety "
                * 3,
                "metadata": {"pages": 5},
            },
        ]
        excellent = parser.parse_evidence(excellent_evidence)
        assert excellent.quality in (EvidenceQuality.EXCELLENT, EvidenceQuality.GOOD)
        assert excellent.score > 0.6

    def test_normalize_type(self, parser):
        assert parser._normalize_type({"type": "Photo"}) == "photo"
        assert parser._normalize_type({"type": " VIDEO "}) == "video"
        assert parser._normalize_type({"evidence_type": "receipt"}) == "receipt"
        assert parser._normalize_type({}) == "unknown"

    def test_task_context_physical(self, parser):
        task = {"category": "delivery", "bounty_amount": 10}
        evidence = [{"type": "photo", "content": "delivered"}]
        qa = parser.parse_evidence(evidence, task_data=task)
        # Should have task_context signal for physical_execution
        ctx_signals = [s for s in qa.signals if s.source == "task_context"]
        assert any(
            s.dimension == SkillDimension.PHYSICAL_EXECUTION for s in ctx_signals
        )

    def test_task_context_digital(self, parser):
        task = {"category": "coding", "bounty_amount": 10}
        evidence = [{"type": "screenshot", "content": "code"}]
        qa = parser.parse_evidence(evidence, task_data=task)
        ctx_signals = [s for s in qa.signals if s.source == "task_context"]
        assert any(
            s.dimension == SkillDimension.DIGITAL_PROFICIENCY for s in ctx_signals
        )

    def test_task_context_creative(self, parser):
        task = {"category": "design", "bounty_amount": 10}
        evidence = [{"type": "screenshot", "content": "design"}]
        qa = parser.parse_evidence(evidence, task_data=task)
        ctx_signals = [s for s in qa.signals if s.source == "task_context"]
        assert any(s.dimension == SkillDimension.CREATIVE_SKILL for s in ctx_signals)

    def test_task_context_blockchain(self, parser):
        task = {"category": "defi", "bounty_amount": 10}
        evidence = [{"type": "screenshot", "content": "tx"}]
        qa = parser.parse_evidence(evidence, task_data=task)
        ctx_signals = [s for s in qa.signals if s.source == "task_context"]
        assert any(
            s.dimension == SkillDimension.BLOCKCHAIN_LITERACY for s in ctx_signals
        )

    def test_task_context_high_bounty(self, parser):
        task = {"category": "general", "bounty_amount": 75}
        evidence = [{"type": "text_response", "content": "done"}]
        qa = parser.parse_evidence(evidence, task_data=task)
        ctx_signals = [s for s in qa.signals if s.source == "task_context"]
        assert any(s.dimension == SkillDimension.TECHNICAL_SKILL for s in ctx_signals)

    def test_task_context_low_bounty_no_tech_signal(self, parser):
        task = {"category": "general", "bounty_amount": 5}
        evidence = [{"type": "text_response", "content": "done"}]
        qa = parser.parse_evidence(evidence, task_data=task)
        ctx_signals = [s for s in qa.signals if s.source == "task_context"]
        assert not any(
            s.dimension == SkillDimension.TECHNICAL_SKILL for s in ctx_signals
        )

    def test_update_skill_dna(self, parser):
        dna = SkillDNA(worker_id="w1")
        evidence = [
            {"type": "photo", "content": "pic"},
            {"type": "text_response", "content": "report"},
        ]
        qa = parser.parse_evidence(evidence)
        parser.update_skill_dna(dna, qa, task_categories=["delivery", "errand"])

        assert dna.task_count == 1
        assert dna.evidence_count == 2
        assert "delivery" in dna.categories_seen
        assert "errand" in dna.categories_seen
        assert dna.avg_quality == qa.score

    def test_update_skill_dna_running_average(self, parser):
        dna = SkillDNA(worker_id="w1")

        # First task
        qa1 = QualityAssessment(
            quality=EvidenceQuality.GOOD,
            score=0.8,
            evidence_count=2,
            evidence_types=["photo"],
            signals=[],
        )
        parser.update_skill_dna(dna, qa1)
        assert dna.avg_quality == 0.8

        # Second task
        qa2 = QualityAssessment(
            quality=EvidenceQuality.POOR,
            score=0.4,
            evidence_count=1,
            evidence_types=["text_response"],
            signals=[],
        )
        parser.update_skill_dna(dna, qa2)
        assert abs(dna.avg_quality - 0.6) < 0.001  # (0.8 + 0.4) / 2

    def test_timestamp_boosts_speed(self, parser):
        evidence = [
            {
                "type": "timestamp_proof",
                "content": "proof",
                "metadata": {"timestamp": "2026-03-16T02:00:00Z"},
            }
        ]
        qa = parser.parse_evidence(evidence)
        speed_signals = [s for s in qa.signals if s.dimension == SkillDimension.SPEED]
        assert any("timestamped" in s.detail for s in speed_signals)

    def test_score_clamped_to_one(self, parser):
        """Score should never exceed 1.0 even with many bonuses."""
        evidence = [
            {
                "type": "photo_geo",
                "content": "x" * 300,
                "metadata": {"latitude": 25, "longitude": -80, "ts": "t", "extra": "e"},
            },
            {
                "type": "notarized",
                "content": "x" * 300,
                "metadata": {"a": 1, "b": 2, "c": 3, "d": 4},
            },
            {
                "type": "video",
                "content": "x" * 300,
                "metadata": {"a": 1, "b": 2, "c": 3},
            },
            {
                "type": "document",
                "content": "x" * 300,
                "metadata": {"a": 1, "b": 2, "c": 3},
            },
            {
                "type": "measurement",
                "content": "x" * 300,
                "metadata": {"a": 1, "b": 2, "c": 3},
            },
        ]
        qa = parser.parse_evidence(evidence)
        assert qa.score <= 1.0


# ─── WorkerRegistry ──────────────────────────────────────────────────────────


class TestWorkerRegistry:
    def test_get_or_create_new(self):
        reg = WorkerRegistry()
        dna = reg.get_or_create("w1")
        assert dna.worker_id == "w1"
        assert dna.task_count == 0

    def test_get_or_create_existing(self):
        reg = WorkerRegistry()
        dna1 = reg.get_or_create("w1")
        dna1.task_count = 5
        dna2 = reg.get_or_create("w1")
        assert dna2.task_count == 5
        assert dna1 is dna2

    def test_process_completion(self):
        reg = WorkerRegistry()
        evidence = [
            {"type": "photo", "content": "pic"},
            {
                "type": "text_response",
                "content": "detailed report about the task completion",
            },
        ]
        dna, qa = reg.process_completion("w1", evidence, task_categories=["delivery"])
        assert dna.task_count == 1
        assert dna.evidence_count == 2
        assert "delivery" in dna.categories_seen
        assert qa.evidence_count == 2

    def test_process_completion_updates_dna(self):
        reg = WorkerRegistry()
        evidence1 = [
            {"type": "photo_geo", "content": "geo pic", "metadata": {"latitude": 25}}
        ]
        evidence2 = [{"type": "screenshot", "content": "screen cap"}]

        dna1, _ = reg.process_completion("w1", evidence1, task_categories=["delivery"])
        dna2, _ = reg.process_completion("w1", evidence2, task_categories=["coding"])

        assert dna2.task_count == 2
        assert "delivery" in dna2.categories_seen
        assert "coding" in dna2.categories_seen

    def test_get_worker_exists(self):
        reg = WorkerRegistry()
        reg.get_or_create("w1")
        assert reg.get_worker("w1") is not None

    def test_get_worker_missing(self):
        reg = WorkerRegistry()
        assert reg.get_worker("nonexistent") is None

    def test_list_workers(self):
        reg = WorkerRegistry()
        reg.get_or_create("w1")
        reg.get_or_create("w2")
        reg.get_or_create("w3")
        assert len(reg.list_workers()) == 3

    def test_get_specialists(self):
        reg = WorkerRegistry()
        # Worker 1: strong in geo_mobility
        dna1 = reg.get_or_create("w1")
        dna1.dimensions["geo_mobility"] = 0.8
        # Worker 2: weak in geo_mobility
        dna2 = reg.get_or_create("w2")
        dna2.dimensions["geo_mobility"] = 0.3
        # Worker 3: strong in geo_mobility
        dna3 = reg.get_or_create("w3")
        dna3.dimensions["geo_mobility"] = 0.9

        specialists = reg.get_specialists(SkillDimension.GEO_MOBILITY, min_score=0.5)
        assert len(specialists) == 2
        assert specialists[0].worker_id == "w3"  # highest first
        assert specialists[1].worker_id == "w1"

    def test_get_specialists_none_qualify(self):
        reg = WorkerRegistry()
        dna = reg.get_or_create("w1")
        dna.dimensions["speed"] = 0.2
        specialists = reg.get_specialists(SkillDimension.SPEED, min_score=0.5)
        assert len(specialists) == 0

    def test_get_best_for_category(self):
        reg = WorkerRegistry()
        dna1 = reg.get_or_create("w1")
        dna1.categories_seen = {"delivery"}
        dna1.avg_quality = 0.9
        dna2 = reg.get_or_create("w2")
        dna2.categories_seen = {"delivery"}
        dna2.avg_quality = 0.7
        dna3 = reg.get_or_create("w3")
        dna3.categories_seen = {"coding"}
        dna3.avg_quality = 0.95

        best = reg.get_best_for_category("delivery", top_n=5)
        assert len(best) == 2
        assert best[0].worker_id == "w1"  # highest quality first

    def test_get_best_for_category_none(self):
        reg = WorkerRegistry()
        reg.get_or_create("w1").categories_seen = {"coding"}
        assert reg.get_best_for_category("delivery") == []

    def test_save_and_load(self):
        reg = WorkerRegistry()
        dna = reg.get_or_create("w1")
        dna.dimensions = {"speed": 0.7, "communication": 0.5}
        dna.task_count = 10
        dna.evidence_count = 25
        dna.categories_seen = {"delivery", "errand"}
        dna.avg_quality = 0.65

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            reg.save(path)

            loaded = WorkerRegistry.load(path)
            w = loaded.get_worker("w1")
            assert w is not None
            assert w.dimensions["speed"] == 0.7
            assert w.dimensions["communication"] == 0.5
            assert w.task_count == 10
            assert w.evidence_count == 25
            assert w.categories_seen == {"delivery", "errand"}
            assert w.avg_quality == 0.65
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        reg = WorkerRegistry.load("/nonexistent/path.json")
        assert len(reg.list_workers()) == 0

    def test_load_corrupt_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not valid json {{{")
            path = f.name
        try:
            reg = WorkerRegistry.load(path)
            assert len(reg.list_workers()) == 0
        finally:
            os.unlink(path)

    def test_to_dict(self):
        reg = WorkerRegistry()
        reg.get_or_create("w1")
        reg.get_or_create("w2")
        d = reg.to_dict()
        assert d["worker_count"] == 2
        assert "w1" in d["workers"]
        assert "w2" in d["workers"]


# ─── Integration: Full Pipeline ───────────────────────────────────────────────


class TestFullPipeline:
    """End-to-end: evidence → signals → DNA → registry → specialists."""

    def test_delivery_worker_pipeline(self):
        """Simulate a delivery worker completing 3 tasks."""
        reg = WorkerRegistry()

        # Task 1: simple photo delivery
        dna, qa1 = reg.process_completion(
            "worker_delivery",
            [{"type": "photo", "content": "delivered at door"}],
            task_data={"category": "delivery", "bounty_amount": 5},
            task_categories=["delivery"],
        )
        assert qa1.evidence_count == 1
        assert dna.task_count == 1

        # Task 2: geo-verified delivery with receipt
        dna, qa2 = reg.process_completion(
            "worker_delivery",
            [
                {
                    "type": "photo_geo",
                    "content": "x" * 150,
                    "metadata": {"latitude": 25.7, "longitude": -80.1},
                },
                {"type": "receipt", "content": "receipt #12345"},
            ],
            task_data={"category": "delivery", "bounty_amount": 8},
            task_categories=["delivery", "logistics"],
        )
        assert dna.task_count == 2
        assert "logistics" in dna.categories_seen

        # Task 3: errand with detailed report
        dna, qa3 = reg.process_completion(
            "worker_delivery",
            [
                {"type": "photo", "content": "completed errand"},
                {
                    "type": "text_response",
                    "content": "Picked up groceries as requested. All items found and delivered.",
                },
            ],
            task_data={"category": "errand", "bounty_amount": 12},
            task_categories=["errand"],
        )
        assert dna.task_count == 3
        assert "errand" in dna.categories_seen

        # Worker should be a specialist in physical execution
        assert "physical_execution" in dna.dimensions
        assert "geo_mobility" in dna.dimensions

        # Top skills should reflect delivery/physical work
        top = dna.get_top_skills(3)
        top_dims = [t[0] for t in top]
        assert len(top_dims) >= 1

    def test_digital_worker_pipeline(self):
        """Simulate a coding/digital worker."""
        reg = WorkerRegistry()

        dna, _ = reg.process_completion(
            "worker_coder",
            [
                {"type": "screenshot", "content": "code review screenshot " * 5},
                {"type": "document", "content": "technical documentation " * 10},
            ],
            task_data={"category": "coding", "bounty_amount": 50},
            task_categories=["coding", "technical"],
        )

        assert "digital_proficiency" in dna.dimensions
        assert "communication" in dna.dimensions

    def test_suspicious_worker_pipeline(self):
        """Worker submitting suspicious evidence should get flagged."""
        reg = WorkerRegistry()

        dna, qa = reg.process_completion(
            "worker_fraud",
            [
                {"type": "text_response", "content": "lorem ipsum dolor sit amet"},
                {"type": "photo", "content": "test evidence"},
            ],
            task_categories=["delivery"],
        )

        assert qa.quality == EvidenceQuality.SUSPICIOUS
        assert len(qa.flags) >= 1
