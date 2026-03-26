"""
Comprehensive test suite for EvidenceParser — the swarm's learning engine.

Tests cover:
- SkillSignal data model
- QualityAssessment data model
- SkillDNA: update_dimension, apply_signals, get_top_skills, get_weakness, to_dict
- EvidenceParser: evidence type → skill mappings
- Quality assessment: scoring, diversity bonus, quantity bonus
- Suspicious content detection
- Task context signal extraction
- update_skill_dna: EMA update, running average
- WorkerRegistry: CRUD, specialists, category search, persistence
"""

import os
import tempfile

import pytest

from mcp_server.swarm.evidence_parser import (
    EvidenceParser,
    EvidenceQuality,
    QualityAssessment,
    SkillDNA,
    SkillDimension,
    SkillSignal,
    WorkerRegistry,
)


# ─── SkillSignal Tests ───────────────────────────────────────────────────


class TestSkillSignal:
    def test_to_dict(self):
        signal = SkillSignal(
            dimension=SkillDimension.GEO_MOBILITY,
            strength=0.85,
            source="photo_geo",
            detail="geo_verified",
        )
        d = signal.to_dict()
        assert d["dimension"] == "geo_mobility"
        assert d["strength"] == 0.85
        assert d["source"] == "photo_geo"
        assert d["detail"] == "geo_verified"

    def test_strength_rounding(self):
        signal = SkillSignal(
            dimension=SkillDimension.SPEED,
            strength=0.33333333,
            source="test",
        )
        d = signal.to_dict()
        assert d["strength"] == 0.333


# ─── SkillDNA Tests ──────────────────────────────────────────────────────


class TestSkillDNA:
    def test_initial_state(self):
        dna = SkillDNA(worker_id="w1")
        assert dna.dimensions == {}
        assert dna.task_count == 0
        assert dna.evidence_count == 0
        assert dna.categories_seen == set()
        assert dna.avg_quality == 0.0

    def test_update_dimension_first_time(self):
        dna = SkillDNA(worker_id="w1")
        dna.update_dimension(SkillDimension.SPEED, 0.8, decay=0.9)
        # EMA: 0.9 * 0 + 0.1 * 0.8 = 0.08
        assert abs(dna.dimensions["speed"] - 0.08) < 1e-9

    def test_update_dimension_accumulates(self):
        dna = SkillDNA(worker_id="w1")
        dna.update_dimension(SkillDimension.SPEED, 0.8, decay=0.9)
        # First: 0.08
        dna.update_dimension(SkillDimension.SPEED, 0.8, decay=0.9)
        # Second: 0.9 * 0.08 + 0.1 * 0.8 = 0.072 + 0.08 = 0.152
        assert abs(dna.dimensions["speed"] - 0.152) < 1e-9

    def test_apply_signals(self):
        dna = SkillDNA(worker_id="w1")
        signals = [
            SkillSignal(SkillDimension.SPEED, 0.7, "test"),
            SkillSignal(SkillDimension.THOROUGHNESS, 0.5, "test"),
        ]
        dna.apply_signals(signals, decay=0.9)
        assert "speed" in dna.dimensions
        assert "thoroughness" in dna.dimensions

    def test_get_top_skills_empty(self):
        dna = SkillDNA(worker_id="w1")
        assert dna.get_top_skills() == []

    def test_get_top_skills_sorted(self):
        dna = SkillDNA(worker_id="w1")
        dna.dimensions = {"speed": 0.9, "thoroughness": 0.5, "communication": 0.7}
        top = dna.get_top_skills(2)
        assert len(top) == 2
        assert top[0] == ("speed", 0.9)
        assert top[1] == ("communication", 0.7)

    def test_get_weakness_empty(self):
        dna = SkillDNA(worker_id="w1")
        assert dna.get_weakness() is None

    def test_get_weakness(self):
        dna = SkillDNA(worker_id="w1")
        dna.dimensions = {"speed": 0.9, "thoroughness": 0.1}
        weakness = dna.get_weakness()
        assert weakness == ("thoroughness", 0.1)

    def test_to_dict(self):
        dna = SkillDNA(worker_id="w1")
        dna.dimensions = {"speed": 0.85555, "communication": 0.3}
        dna.task_count = 5
        dna.evidence_count = 12
        dna.categories_seen = {"photo", "delivery"}
        dna.avg_quality = 0.75
        d = dna.to_dict()
        assert d["worker_id"] == "w1"
        assert d["task_count"] == 5
        assert d["dimensions"]["speed"] == 0.856  # Rounded
        assert set(d["categories"]) == {"photo", "delivery"}
        assert len(d["top_skills"]) == 2
        assert d["top_skills"][0]["skill"] == "speed"


# ─── EvidenceParser._normalize_type Tests ────────────────────────────────


class TestNormalizeType:
    def setup_method(self):
        self.parser = EvidenceParser()

    def test_standard_type(self):
        assert self.parser._normalize_type({"type": "photo_geo"}) == "photo_geo"

    def test_alternative_key(self):
        assert self.parser._normalize_type({"evidence_type": "VIDEO"}) == "video"

    def test_whitespace_stripped(self):
        assert self.parser._normalize_type({"type": " photo "}) == "photo"

    def test_missing_type(self):
        assert self.parser._normalize_type({}) == "unknown"


# ─── EvidenceParser._check_suspicious Tests ──────────────────────────────


class TestCheckSuspicious:
    def setup_method(self):
        self.parser = EvidenceParser()

    def test_normal_content(self):
        assert not self.parser._check_suspicious("Task completed at main street")

    def test_lorem_ipsum(self):
        assert self.parser._check_suspicious("Lorem ipsum dolor sit amet")

    def test_test_evidence(self):
        assert self.parser._check_suspicious("This is test evidence")

    def test_placeholder(self):
        assert self.parser._check_suspicious("placeholder data here")

    def test_empty_string(self):
        assert not self.parser._check_suspicious("")

    def test_none_content(self):
        # _check_suspicious receives a string, but let's verify robustness
        assert not self.parser._check_suspicious("")

    def test_asdf(self):
        assert self.parser._check_suspicious("asdf")

    def test_xxx(self):
        assert self.parser._check_suspicious("xxxx")


# ─── EvidenceParser._parse_single_evidence Tests ────────────────────────


class TestParseSingleEvidence:
    def setup_method(self):
        self.parser = EvidenceParser()

    def test_photo_signals(self):
        signals = self.parser._parse_single_evidence({"content": "pic"}, "photo")
        dims = {s.dimension for s in signals}
        assert SkillDimension.PHYSICAL_EXECUTION in dims
        assert SkillDimension.THOROUGHNESS in dims

    def test_photo_geo_signals(self):
        signals = self.parser._parse_single_evidence(
            {"content": "pic", "metadata": {"latitude": 25.7}}, "photo_geo"
        )
        dims = {s.dimension for s in signals}
        assert SkillDimension.GEO_MOBILITY in dims
        assert SkillDimension.VERIFICATION_SKILL in dims
        # geo_verified boost
        geo_signal = [s for s in signals if s.dimension == SkillDimension.GEO_MOBILITY][
            0
        ]
        assert geo_signal.strength > 0.8  # Base 0.8 + 0.15 boost

    def test_rich_content_boosts_strength(self):
        short = self.parser._parse_single_evidence({"content": "ok"}, "text_response")
        long_content = "x" * 200
        long = self.parser._parse_single_evidence(
            {"content": long_content}, "text_response"
        )
        # Long content should boost communication signal
        comm_short = [s for s in short if s.dimension == SkillDimension.COMMUNICATION][
            0
        ]
        comm_long = [s for s in long if s.dimension == SkillDimension.COMMUNICATION][0]
        assert comm_long.strength > comm_short.strength

    def test_rich_metadata_boosts(self):
        signals = self.parser._parse_single_evidence(
            {"content": "data", "metadata": {"a": 1, "b": 2, "c": 3}}, "document"
        )
        # With 3 metadata keys → rich_metadata boost
        assert any("rich_metadata" in s.detail for s in signals)

    def test_unknown_type_fallback(self):
        signals = self.parser._parse_single_evidence({"content": "?"}, "alien_type")
        assert len(signals) == 1
        assert signals[0].dimension == SkillDimension.THOROUGHNESS
        assert signals[0].strength == 0.3

    def test_video_signals(self):
        signals = self.parser._parse_single_evidence({"content": "vid"}, "video")
        dims = {s.dimension for s in signals}
        assert SkillDimension.THOROUGHNESS in dims
        assert SkillDimension.COMMUNICATION in dims

    def test_screenshot_signals(self):
        signals = self.parser._parse_single_evidence({"content": "ss"}, "screenshot")
        dims = {s.dimension for s in signals}
        assert SkillDimension.DIGITAL_PROFICIENCY in dims
        assert SkillDimension.VERIFICATION_SKILL in dims

    def test_timestamp_speed_boost(self):
        signals = self.parser._parse_single_evidence(
            {"content": "proof", "metadata": {"timestamp": "2026-03-23T04:00:00Z"}},
            "timestamp_proof",
        )
        speed_signal = [s for s in signals if s.dimension == SkillDimension.SPEED][0]
        assert speed_signal.strength >= 0.5  # Base 0.4 + 0.1 timestamp boost


# ─── EvidenceParser._assess_item_quality Tests ──────────────────────────


class TestAssessItemQuality:
    def setup_method(self):
        self.parser = EvidenceParser()

    def test_empty_evidence_baseline(self):
        score = self.parser._assess_item_quality({}, "photo")
        assert abs(score - 0.5) < 1e-9  # Just baseline

    def test_content_present_boosts(self):
        score = self.parser._assess_item_quality({"content": "present"}, "photo")
        assert score > 0.5

    def test_long_content_extra_boost(self):
        short = self.parser._assess_item_quality({"content": "a" * 30}, "photo")
        long = self.parser._assess_item_quality({"content": "a" * 250}, "photo")
        assert long > short

    def test_photo_geo_with_coords_premium(self):
        score = self.parser._assess_item_quality(
            {"content": "photo", "metadata": {"latitude": 25.7}}, "photo_geo"
        )
        assert score >= 0.75  # Base 0.5 + content 0.1 + geo 0.15

    def test_notarized_premium(self):
        score = self.parser._assess_item_quality({"content": "doc"}, "notarized")
        assert score >= 0.7  # Base 0.5 + content 0.1 + notarized 0.2

    def test_score_capped_at_one(self):
        score = self.parser._assess_item_quality(
            {
                "content": "x" * 300,
                "metadata": {"a": 1, "b": 2, "c": 3, "d": 4, "latitude": 25.7},
            },
            "photo_geo",
        )
        assert score <= 1.0


# ─── EvidenceParser.parse_evidence (Full Pipeline) Tests ─────────────────


class TestParseEvidence:
    def setup_method(self):
        self.parser = EvidenceParser()

    def test_empty_evidence_list(self):
        result = self.parser.parse_evidence([])
        assert result.quality == EvidenceQuality.POOR
        assert result.score == 0.0
        assert result.evidence_count == 0
        assert "no_evidence_submitted" in result.flags

    def test_single_photo(self):
        result = self.parser.parse_evidence(
            [{"type": "photo", "content": "storefront picture"}]
        )
        assert result.evidence_count == 1
        assert result.quality in (EvidenceQuality.ADEQUATE, EvidenceQuality.GOOD)
        assert result.score > 0.0

    def test_rich_multi_type_evidence(self):
        result = self.parser.parse_evidence(
            [
                {
                    "type": "photo_geo",
                    "content": "geo photo",
                    "metadata": {"latitude": 25.7},
                },
                {
                    "type": "text_response",
                    "content": "Detailed report of what I found at the location including measurements and observations",
                },
                {"type": "screenshot", "content": "verification screenshot"},
            ]
        )
        assert result.evidence_count == 3
        assert len(set(result.evidence_types)) == 3
        # Should get diversity bonus
        assert result.details["diversity_bonus"] > 0
        assert result.score > 0.6

    def test_suspicious_content_flagged(self):
        result = self.parser.parse_evidence(
            [
                {"type": "text_response", "content": "Lorem ipsum dolor sit amet"},
            ]
        )
        assert any("suspicious" in f for f in result.flags)
        assert result.quality == EvidenceQuality.SUSPICIOUS

    def test_quantity_bonus(self):
        single = self.parser.parse_evidence(
            [
                {"type": "photo", "content": "one photo"},
            ]
        )
        multiple = self.parser.parse_evidence(
            [
                {"type": "photo", "content": "photo 1"},
                {"type": "photo", "content": "photo 2"},
                {"type": "photo", "content": "photo 3"},
            ]
        )
        assert multiple.details["quantity_bonus"] > single.details["quantity_bonus"]

    def test_quality_assessment_to_dict(self):
        result = self.parser.parse_evidence(
            [
                {"type": "photo", "content": "test pic"},
            ]
        )
        d = result.to_dict()
        assert "quality" in d
        assert "score" in d
        assert "evidence_count" in d
        assert "signals" in d
        assert isinstance(d["signals"], list)

    def test_signals_extracted(self):
        result = self.parser.parse_evidence(
            [
                {
                    "type": "photo_geo",
                    "content": "location photo",
                    "metadata": {"latitude": 25.7},
                },
            ]
        )
        assert len(result.signals) > 0
        dims = {s.dimension for s in result.signals}
        assert SkillDimension.GEO_MOBILITY in dims

    def test_task_context_signals(self):
        result = self.parser.parse_evidence(
            [{"type": "text_response", "content": "code review done"}],
            task_data={"category": "coding", "bounty_amount": 100},
        )
        dims = {s.dimension for s in result.signals}
        assert SkillDimension.DIGITAL_PROFICIENCY in dims
        assert SkillDimension.TECHNICAL_SKILL in dims

    def test_task_context_delivery(self):
        result = self.parser.parse_evidence(
            [{"type": "photo", "content": "delivered"}],
            task_data={"category": "delivery"},
        )
        context_signals = [s for s in result.signals if s.source == "task_context"]
        assert any(
            s.dimension == SkillDimension.PHYSICAL_EXECUTION for s in context_signals
        )

    def test_task_context_blockchain(self):
        result = self.parser.parse_evidence(
            [{"type": "text_response", "content": "tx confirmed"}],
            task_data={"category": "blockchain"},
        )
        context_signals = [s for s in result.signals if s.source == "task_context"]
        assert any(
            s.dimension == SkillDimension.BLOCKCHAIN_LITERACY for s in context_signals
        )

    def test_task_context_design(self):
        result = self.parser.parse_evidence(
            [{"type": "document", "content": "design mockup"}],
            task_data={"category": "design"},
        )
        context_signals = [s for s in result.signals if s.source == "task_context"]
        assert any(
            s.dimension == SkillDimension.CREATIVE_SKILL for s in context_signals
        )

    def test_task_context_low_bounty_no_technical_signal(self):
        result = self.parser.parse_evidence(
            [{"type": "text_response", "content": "done"}],
            task_data={"bounty_amount": 5},
        )
        context_signals = [s for s in result.signals if s.source == "task_context"]
        assert not any(
            s.dimension == SkillDimension.TECHNICAL_SKILL for s in context_signals
        )


# ─── EvidenceParser.update_skill_dna Tests ───────────────────────────────


class TestUpdateSkillDNA:
    def setup_method(self):
        self.parser = EvidenceParser()

    def test_first_update(self):
        dna = SkillDNA(worker_id="w1")
        assessment = QualityAssessment(
            quality=EvidenceQuality.GOOD,
            score=0.7,
            evidence_count=3,
            evidence_types=["photo", "text_response"],
            signals=[
                SkillSignal(SkillDimension.PHYSICAL_EXECUTION, 0.6, "photo"),
                SkillSignal(SkillDimension.COMMUNICATION, 0.7, "text_response"),
            ],
        )
        updated = self.parser.update_skill_dna(
            dna, assessment, task_categories=["delivery"]
        )
        assert updated.task_count == 1
        assert updated.evidence_count == 3
        assert "delivery" in updated.categories_seen
        assert updated.avg_quality == 0.7
        assert "physical_execution" in updated.dimensions
        assert "communication" in updated.dimensions

    def test_running_average_quality(self):
        dna = SkillDNA(worker_id="w1")
        a1 = QualityAssessment(
            quality=EvidenceQuality.GOOD,
            score=0.8,
            evidence_count=1,
            evidence_types=["photo"],
        )
        a2 = QualityAssessment(
            quality=EvidenceQuality.ADEQUATE,
            score=0.4,
            evidence_count=1,
            evidence_types=["photo"],
        )
        self.parser.update_skill_dna(dna, a1)
        assert dna.task_count == 1
        assert dna.avg_quality == 0.8
        self.parser.update_skill_dna(dna, a2)
        assert dna.task_count == 2
        assert abs(dna.avg_quality - 0.6) < 1e-9  # (0.8+0.4)/2

    def test_categories_accumulate(self):
        dna = SkillDNA(worker_id="w1")
        a1 = QualityAssessment(
            quality=EvidenceQuality.GOOD,
            score=0.7,
            evidence_count=1,
            evidence_types=["photo"],
        )
        self.parser.update_skill_dna(dna, a1, task_categories=["delivery"])
        self.parser.update_skill_dna(dna, a1, task_categories=["photo_verification"])
        assert dna.categories_seen == {"delivery", "photo_verification"}


# ─── WorkerRegistry Tests ────────────────────────────────────────────────


class TestWorkerRegistry:
    def test_get_or_create_new(self):
        registry = WorkerRegistry()
        dna = registry.get_or_create("w1")
        assert dna.worker_id == "w1"
        assert dna.task_count == 0

    def test_get_or_create_existing(self):
        registry = WorkerRegistry()
        dna1 = registry.get_or_create("w1")
        dna1.task_count = 5
        dna2 = registry.get_or_create("w1")
        assert dna2.task_count == 5  # Same object

    def test_get_worker_missing(self):
        registry = WorkerRegistry()
        assert registry.get_worker("nonexistent") is None

    def test_get_worker_present(self):
        registry = WorkerRegistry()
        registry.get_or_create("w1")
        assert registry.get_worker("w1") is not None

    def test_list_workers(self):
        registry = WorkerRegistry()
        registry.get_or_create("w1")
        registry.get_or_create("w2")
        workers = registry.list_workers()
        assert len(workers) == 2

    def test_process_completion(self):
        registry = WorkerRegistry()
        evidence = [
            {
                "type": "photo_geo",
                "content": "verified",
                "metadata": {"latitude": 25.7},
            },
            {"type": "text_response", "content": "Detailed report with observations"},
        ]
        dna, assessment = registry.process_completion(
            worker_id="w1",
            evidence=evidence,
            task_categories=["photo_verification"],
        )
        assert dna.task_count == 1
        assert dna.evidence_count == 2
        assert assessment.evidence_count == 2
        assert assessment.score > 0

    def test_get_specialists(self):
        registry = WorkerRegistry()
        dna1 = registry.get_or_create("w1")
        dna1.dimensions = {"geo_mobility": 0.9, "speed": 0.3}
        dna2 = registry.get_or_create("w2")
        dna2.dimensions = {"geo_mobility": 0.6, "speed": 0.8}
        dna3 = registry.get_or_create("w3")
        dna3.dimensions = {"speed": 0.9}

        geo_specialists = registry.get_specialists(
            SkillDimension.GEO_MOBILITY, min_score=0.5
        )
        assert len(geo_specialists) == 2
        assert geo_specialists[0].worker_id == "w1"  # Highest geo score

    def test_get_specialists_none_qualify(self):
        registry = WorkerRegistry()
        dna = registry.get_or_create("w1")
        dna.dimensions = {"speed": 0.3}
        result = registry.get_specialists(SkillDimension.GEO_MOBILITY, min_score=0.5)
        assert result == []

    def test_get_best_for_category(self):
        registry = WorkerRegistry()
        dna1 = registry.get_or_create("w1")
        dna1.categories_seen = {"delivery", "photo"}
        dna1.avg_quality = 0.9
        dna2 = registry.get_or_create("w2")
        dna2.categories_seen = {"delivery"}
        dna2.avg_quality = 0.5
        dna3 = registry.get_or_create("w3")
        dna3.categories_seen = {"coding"}
        dna3.avg_quality = 1.0

        best = registry.get_best_for_category("delivery")
        assert len(best) == 2
        assert best[0].worker_id == "w1"  # Higher quality
        assert best[1].worker_id == "w2"

    def test_save_and_load(self):
        registry = WorkerRegistry()
        evidence = [
            {
                "type": "photo_geo",
                "content": "verified",
                "metadata": {"latitude": 25.7},
            },
        ]
        registry.process_completion("w1", evidence, task_categories=["photo"])
        registry.process_completion("w2", evidence, task_categories=["delivery"])

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            registry.save(path)
            loaded = WorkerRegistry.load(path)
            assert len(loaded.list_workers()) == 2
            w1 = loaded.get_worker("w1")
            assert w1 is not None
            assert w1.task_count == 1
            assert "photo" in w1.categories_seen
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        loaded = WorkerRegistry.load("/tmp/nonexistent_registry.json")
        assert len(loaded.list_workers()) == 0

    def test_to_dict(self):
        registry = WorkerRegistry()
        registry.get_or_create("w1")
        registry.get_or_create("w2")
        d = registry.to_dict()
        assert d["worker_count"] == 2
        assert "w1" in d["workers"]
        assert "w2" in d["workers"]


# ─── Evidence Type Coverage Tests ────────────────────────────────────────


class TestEvidenceTypeCoverage:
    """Verify all 11 evidence types produce correct signals."""

    def setup_method(self):
        self.parser = EvidenceParser()

    @pytest.mark.parametrize(
        "ev_type,expected_dims",
        [
            ("photo", {SkillDimension.PHYSICAL_EXECUTION, SkillDimension.THOROUGHNESS}),
            (
                "photo_geo",
                {
                    SkillDimension.GEO_MOBILITY,
                    SkillDimension.VERIFICATION_SKILL,
                    SkillDimension.PHYSICAL_EXECUTION,
                },
            ),
            (
                "video",
                {
                    SkillDimension.THOROUGHNESS,
                    SkillDimension.COMMUNICATION,
                    SkillDimension.PHYSICAL_EXECUTION,
                },
            ),
            (
                "document",
                {
                    SkillDimension.DIGITAL_PROFICIENCY,
                    SkillDimension.COMMUNICATION,
                    SkillDimension.THOROUGHNESS,
                },
            ),
            (
                "receipt",
                {SkillDimension.THOROUGHNESS, SkillDimension.PHYSICAL_EXECUTION},
            ),
            (
                "text_response",
                {SkillDimension.COMMUNICATION, SkillDimension.DIGITAL_PROFICIENCY},
            ),
            (
                "screenshot",
                {SkillDimension.DIGITAL_PROFICIENCY, SkillDimension.VERIFICATION_SKILL},
            ),
            (
                "measurement",
                {SkillDimension.TECHNICAL_SKILL, SkillDimension.THOROUGHNESS},
            ),
            ("signature", {SkillDimension.VERIFICATION_SKILL}),
            (
                "notarized",
                {SkillDimension.VERIFICATION_SKILL, SkillDimension.THOROUGHNESS},
            ),
            (
                "timestamp_proof",
                {SkillDimension.VERIFICATION_SKILL, SkillDimension.SPEED},
            ),
        ],
    )
    def test_evidence_type_mapping(self, ev_type, expected_dims):
        signals = self.parser._parse_single_evidence({"content": "data"}, ev_type)
        produced_dims = {s.dimension for s in signals}
        assert produced_dims == expected_dims

    def test_all_evidence_types_in_map(self):
        expected_types = {
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
        }
        assert set(EvidenceParser.EVIDENCE_SKILL_MAP.keys()) == expected_types


# ─── Quality Tier Determination Tests ────────────────────────────────────


class TestQualityTiers:
    def setup_method(self):
        self.parser = EvidenceParser()

    def test_excellent_tier(self):
        # Multiple diverse evidence types with rich content
        result = self.parser.parse_evidence(
            [
                {
                    "type": "photo_geo",
                    "content": "Detailed storefront photo with exact location marker "
                    * 4,
                    "metadata": {"latitude": 25.7, "a": 1, "b": 2, "c": 3},
                },
                {
                    "type": "text_response",
                    "content": "Comprehensive field report documenting all observations at the site "
                    * 5,
                },
                {
                    "type": "video",
                    "content": "Video walkthrough of the entire property showing condition "
                    * 4,
                },
                {
                    "type": "measurement",
                    "content": "Precise measurements taken with calibrated equipment readings "
                    * 2,
                },
            ]
        )
        assert result.quality == EvidenceQuality.EXCELLENT

    def test_poor_tier_minimal(self):
        result = self.parser.parse_evidence(
            [
                {"type": "unknown_type", "content": ""},
            ]
        )
        assert result.quality in (EvidenceQuality.POOR, EvidenceQuality.ADEQUATE)

    def test_suspicious_overrides_other_tiers(self):
        result = self.parser.parse_evidence(
            [
                {
                    "type": "photo_geo",
                    "content": "lorem ipsum verified",
                    "metadata": {"latitude": 25.7},
                },
            ]
        )
        assert result.quality == EvidenceQuality.SUSPICIOUS
