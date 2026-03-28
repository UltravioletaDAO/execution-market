"""
Tests for PHOTINT Verification Prompt Library.

Covers:
- PromptLibrary: category listing, prompt generation, hashing, context injection
- ExifData: to_prompt_context formatting, forensic flag detection
- Version: format and generation
- Schemas: VerificationOutput and ForensicAnalysis validation

All tests are standalone -- no external services or databases required.
"""

import hashlib

import pytest

pytestmark = pytest.mark.verification

# Add parent to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.prompts import PromptLibrary, PromptResult, get_prompt_library
from verification.prompts.version import prompt_version, VERSION, MAJOR, MINOR
from verification.prompts.schemas import VerificationOutput, ForensicAnalysis
from verification.exif_extractor import ExifData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def library():
    """Fresh PromptLibrary instance."""
    return PromptLibrary()


@pytest.fixture
def test_task():
    """Standard task dict for testing."""
    return {
        "title": "Verify coffee shop is open",
        "category": "physical_presence",
        "description": "Take a photo showing the storefront of Bean Counter Coffee at 123 Main St.",
        "location": "123 Main St, Springfield",
        "deadline": "2026-03-28T18:00:00Z",
        "evidence_schema": {
            "required": ["photo", "gps_coordinates"],
            "optional": ["video"],
        },
    }


@pytest.fixture
def test_evidence():
    """Standard evidence dict for testing."""
    return {
        "gps": "39.7817, -89.6501",
        "timestamp": "2026-03-28T14:32:00Z",
        "notes": "Shop was open, photo taken from across the street.",
    }


# ---------------------------------------------------------------------------
# PromptLibrary — Category Registry
# ---------------------------------------------------------------------------


class TestPromptLibraryCategories:
    """Tests for PromptLibrary category listing and lookup."""

    def test_list_categories_returns_21(self, library):
        categories = library.list_categories()
        assert len(categories) == 21

    def test_list_categories_is_sorted(self, library):
        categories = library.list_categories()
        assert categories == sorted(categories)

    def test_has_category_known(self, library):
        assert library.has_category("physical_presence") is True
        assert library.has_category("knowledge_access") is True
        assert library.has_category("simple_action") is True

    def test_has_category_unknown(self, library):
        assert library.has_category("nonexistent_category") is False
        assert library.has_category("") is False
        assert library.has_category("PHYSICAL_PRESENCE") is False  # case sensitive

    def test_digital_fallback_categories_registered(self, library):
        """Digital-only categories should all be registered via digital_fallback."""
        for cat in [
            "data_processing",
            "api_integration",
            "content_generation",
            "code_execution",
            "research",
            "multi_step_workflow",
        ]:
            assert library.has_category(cat), f"{cat} should be registered"

    def test_all_expected_categories_present(self, library):
        expected = {
            "physical_presence",
            "knowledge_access",
            "human_authority",
            "simple_action",
            "digital_physical",
            "location_based",
            "verification",
            "social_proof",
            "data_collection",
            "sensory",
            "social",
            "proxy",
            "bureaucratic",
            "emergency",
            "creative",
            "data_processing",
            "api_integration",
            "content_generation",
            "code_execution",
            "research",
            "multi_step_workflow",
        }
        actual = set(library.list_categories())
        assert actual == expected


# ---------------------------------------------------------------------------
# PromptLibrary — Prompt Generation
# ---------------------------------------------------------------------------


class TestPromptGeneration:
    """Tests for PromptLibrary.get_prompt()."""

    def test_returns_prompt_result(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        assert isinstance(result, PromptResult)
        assert isinstance(result.text, str)
        assert isinstance(result.version, str)
        assert isinstance(result.hash, str)
        assert result.category == "physical_presence"

    def test_all_categories_generate_prompts(self, library, test_task, test_evidence):
        """Every registered category must produce a valid prompt without error."""
        for category in library.list_categories():
            result = library.get_prompt(category, test_task, test_evidence)
            assert len(result.text) > 100, f"{category} prompt is too short"
            assert result.version.startswith("photint-v")
            assert len(result.hash) == 64  # SHA-256 hex digest

    def test_prompt_contains_photint_layers(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        text = result.text
        assert "Layer 1: Authenticity Assessment" in text
        assert "Layer 2: Provenance & Platform Chain" in text
        assert "Layer 3: Geospatial Verification" in text
        assert "Layer 4: Temporal Verification" in text
        assert "Layer 5: Task Completion Assessment" in text

    def test_prompt_contains_confidence_system(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        text = result.text
        assert "CONFIRMED" in text
        assert "HIGH" in text
        assert "MODERATE" in text
        assert "LOW" in text
        assert "CONFIDENCE RATING SYSTEM" in text

    def test_prompt_contains_fraud_indicators(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        text = result.text
        assert "FRAUD INDICATORS" in text
        assert "screenshot" in text.lower()

    def test_prompt_includes_task_context(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        assert test_task["title"] in result.text
        assert test_task["location"] in result.text

    def test_different_categories_produce_different_hashes(
        self, library, test_task, test_evidence
    ):
        result_pp = library.get_prompt("physical_presence", test_task, test_evidence)
        result_ka = library.get_prompt("knowledge_access", test_task, test_evidence)
        assert result_pp.hash != result_ka.hash
        assert result_pp.text != result_ka.text

    def test_version_format_matches_category(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        assert result.version == "photint-v1.0-physical_presence"

    def test_unknown_category_uses_default_checks(
        self, library, test_task, test_evidence
    ):
        """Unknown categories should still produce a prompt using fallback checks."""
        result = library.get_prompt("totally_unknown", test_task, test_evidence)
        assert isinstance(result, PromptResult)
        assert result.category == "totally_unknown"
        assert "Does the photo clearly show what the task requested?" in result.text
        # Version uses "general" for unknown categories
        assert result.version == "photint-v1.0-general"

    def test_hash_is_deterministic(self, library, test_task, test_evidence):
        r1 = library.get_prompt("physical_presence", test_task, test_evidence)
        r2 = library.get_prompt("physical_presence", test_task, test_evidence)
        assert r1.hash == r2.hash

    def test_hash_matches_sha256_of_text(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        expected = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
        assert result.hash == expected

    def test_empty_task_and_evidence(self, library):
        """Empty dicts should not crash -- graceful degradation."""
        result = library.get_prompt("physical_presence", {}, {})
        assert isinstance(result, PromptResult)
        assert len(result.text) > 100
        assert result.hash  # non-empty

    def test_exif_context_injection(self, library, test_task, test_evidence):
        exif_text = "- Camera: Apple iPhone 15 Pro\n- GPS: 39.781700, -89.650100"
        result = library.get_prompt(
            "physical_presence", test_task, test_evidence, exif_context=exif_text
        )
        assert "Pre-Extracted Technical Metadata (EXIF)" in result.text
        assert "Apple iPhone 15 Pro" in result.text

    def test_rekognition_context_injection(self, library, test_task, test_evidence):
        rek_text = "Labels: coffee_shop (98.5%), building (97.2%), storefront (96.1%)"
        result = library.get_prompt(
            "physical_presence",
            test_task,
            test_evidence,
            rekognition_context=rek_text,
        )
        assert "Pre-Analysis (Object/Scene Detection)" in result.text
        assert "coffee_shop" in result.text

    def test_both_contexts_injected(self, library, test_task, test_evidence):
        exif_text = "- Camera: Samsung Galaxy S24"
        rek_text = "Labels: person (99.0%)"
        result = library.get_prompt(
            "physical_presence",
            test_task,
            test_evidence,
            exif_context=exif_text,
            rekognition_context=rek_text,
        )
        assert "Pre-Extracted Technical Metadata (EXIF)" in result.text
        assert "Pre-Analysis (Object/Scene Detection)" in result.text

    def test_no_context_injection_when_empty(self, library, test_task, test_evidence):
        result = library.get_prompt("physical_presence", test_task, test_evidence)
        assert "Pre-Extracted Technical Metadata (EXIF)" not in result.text
        assert "Pre-Analysis (Object/Scene Detection)" not in result.text


# ---------------------------------------------------------------------------
# PromptLibrary — Singleton
# ---------------------------------------------------------------------------


class TestGetPromptLibrary:
    """Tests for get_prompt_library() singleton."""

    def test_returns_prompt_library_instance(self):
        lib = get_prompt_library()
        assert isinstance(lib, PromptLibrary)

    def test_returns_same_instance(self):
        lib1 = get_prompt_library()
        lib2 = get_prompt_library()
        assert lib1 is lib2


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersion:
    """Tests for prompt versioning."""

    def test_version_format(self):
        assert VERSION == f"{MAJOR}.{MINOR}"
        assert VERSION == "1.0"

    def test_prompt_version_with_category(self):
        assert prompt_version("physical_presence") == "photint-v1.0-physical_presence"

    def test_prompt_version_format_structure(self):
        result = prompt_version("social")
        assert result.startswith("photint-v")
        assert result.endswith("-social")
        parts = result.split("-")
        assert len(parts) == 3  # photint, vX.Y, category


# ---------------------------------------------------------------------------
# ExifData — to_prompt_context
# ---------------------------------------------------------------------------


class TestExifDataPromptContext:
    """Tests for ExifData.to_prompt_context() formatting."""

    def test_full_context_all_fields(self):
        exif = ExifData(
            camera_make="Apple",
            camera_model="iPhone 15 Pro",
            gps_latitude=39.7817,
            gps_longitude=-89.6501,
            gps_altitude=190.5,
            datetime_original="2026:03:28 14:32:00",
            datetime_modified="2026:03:28 14:33:00",
            software="Camera App",
            has_exif=True,
            width=4032,
            height=3024,
            megapixels=12.2,
            focal_length=6.86,
            iso=100,
            container_type="EXIF",
        )
        ctx = exif.to_prompt_context()
        assert "Apple iPhone 15 Pro" in ctx
        assert "39.781700" in ctx
        assert "-89.650100" in ctx
        assert "altitude: 190.5m" in ctx
        assert "2026:03:28 14:32:00" in ctx
        assert "4032x3024" in ctx
        assert "12.2 MP" in ctx
        assert "6.86mm" in ctx
        assert "ISO: 100" in ctx
        assert "Container: EXIF" in ctx
        assert "EXIF Status: Present" in ctx

    def test_missing_fields_graceful(self):
        exif = ExifData()
        ctx = exif.to_prompt_context()
        assert "UNKNOWN (no EXIF metadata)" in ctx
        assert "GPS: NOT PRESENT" in ctx
        assert "Capture time: NOT PRESENT" in ctx
        assert "EXIF Status: Absent" in ctx

    def test_editing_software_detection_photoshop(self):
        exif = ExifData(
            software="Adobe Photoshop CC 2024",
            has_editing_software=True,
            editing_indicators=["Software: Adobe Photoshop CC 2024"],
            has_exif=True,
        )
        ctx = exif.to_prompt_context()
        assert "[EDITING SOFTWARE DETECTED]" in ctx
        assert "Editing indicators" in ctx

    def test_editing_software_detection_gimp(self):
        exif = ExifData(
            software="GIMP 2.10",
            has_editing_software=True,
            editing_indicators=["Software: GIMP 2.10"],
            has_exif=True,
        )
        ctx = exif.to_prompt_context()
        assert "[EDITING SOFTWARE DETECTED]" in ctx

    def test_editing_software_detection_snapseed(self):
        exif = ExifData(
            software="Snapseed 2.21",
            has_editing_software=True,
            editing_indicators=["Software: Snapseed 2.21"],
            has_exif=True,
        )
        ctx = exif.to_prompt_context()
        assert "[EDITING SOFTWARE DETECTED]" in ctx

    def test_stripped_metadata(self):
        exif = ExifData(metadata_stripped=True)
        ctx = exif.to_prompt_context()
        assert "STRIPPED" in ctx
        assert "processed through a platform" in ctx

    def test_low_resolution_warning(self):
        exif = ExifData(
            width=1280,
            height=720,
            megapixels=0.9,
            editing_indicators=[
                "Low resolution (0.9 MP) -- likely processed through messaging platform"
            ],
        )
        ctx = exif.to_prompt_context()
        assert "Low resolution" in ctx

    def test_timestamp_inconsistency(self):
        exif = ExifData(
            datetime_original="2026:03:28 14:32:00",
            datetime_modified="2026:03:25 10:00:00",
            timestamp_inconsistency=True,
            has_exif=True,
        )
        ctx = exif.to_prompt_context()
        assert "Timestamp inconsistency detected" in ctx

    def test_container_type_jfif(self):
        exif = ExifData(container_type="JFIF", has_exif=True)
        ctx = exif.to_prompt_context()
        assert "Container: JFIF" in ctx

    def test_container_type_exif(self):
        exif = ExifData(container_type="EXIF", has_exif=True)
        ctx = exif.to_prompt_context()
        assert "Container: EXIF" in ctx


# ---------------------------------------------------------------------------
# Schemas — Pydantic Validation
# ---------------------------------------------------------------------------


class TestVerificationOutput:
    """Tests for VerificationOutput schema validation."""

    def test_valid_approved(self):
        output = VerificationOutput(
            decision="approved",
            confidence=0.92,
            explanation="Photo clearly shows the storefront at the correct address.",
            issues=[],
            forensic=ForensicAnalysis(
                photo_authentic=True,
                photo_source="camera",
                exif_consistent=True,
                location_match=True,
                temporal_match=True,
                platform_chain="original",
                manipulation_indicators=[],
                confidence_factors={"location": "CONFIRMED", "time": "HIGH"},
            ),
            task_checks={"subject_at_location": True, "business_verified": True},
        )
        assert output.decision == "approved"
        assert output.confidence == 0.92
        assert output.forensic.photo_authentic is True

    def test_valid_rejected(self):
        output = VerificationOutput(
            decision="rejected",
            confidence=0.85,
            explanation="Photo is a screenshot, not a live capture.",
            issues=["Screenshot detected", "Status bar visible"],
            forensic=ForensicAnalysis(
                photo_authentic=False,
                photo_source="screenshot",
                manipulation_indicators=["status_bar_visible", "rounded_corners"],
                confidence_factors={"authenticity": "CONFIRMED"},
            ),
            task_checks={"live_photo": False},
        )
        assert output.decision == "rejected"
        assert len(output.issues) == 2

    def test_valid_needs_human(self):
        output = VerificationOutput(
            decision="needs_human",
            confidence=0.55,
            explanation="Ambiguous -- location partially visible but unconfirmed.",
            forensic=ForensicAnalysis(
                photo_authentic=True,
                photo_source="camera",
                confidence_factors={"location": "LOW"},
            ),
        )
        assert output.decision == "needs_human"

    def test_invalid_decision_value(self):
        with pytest.raises(Exception):  # Pydantic ValidationError
            VerificationOutput(
                decision="maybe",
                confidence=0.5,
                explanation="Test",
                forensic=ForensicAnalysis(
                    photo_authentic=True,
                    photo_source="camera",
                ),
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(Exception):
            VerificationOutput(
                decision="approved",
                confidence=1.5,
                explanation="Test",
                forensic=ForensicAnalysis(
                    photo_authentic=True,
                    photo_source="camera",
                ),
            )


class TestForensicAnalysis:
    """Tests for ForensicAnalysis schema validation."""

    def test_minimal_valid(self):
        fa = ForensicAnalysis(
            photo_authentic=True,
            photo_source="camera",
        )
        assert fa.photo_authentic is True
        assert fa.exif_consistent is None  # optional defaults to None
        assert fa.manipulation_indicators == []  # default_factory
        assert fa.confidence_factors == {}

    def test_full_fields(self):
        fa = ForensicAnalysis(
            photo_authentic=False,
            photo_source="ai_generated",
            exif_consistent=False,
            location_match=False,
            temporal_match=False,
            platform_chain="whatsapp",
            manipulation_indicators=["texture_anomaly", "impossible_geometry"],
            confidence_factors={
                "authenticity": "CONFIRMED",
                "ai_generation": "HIGH",
            },
        )
        assert fa.photo_source == "ai_generated"
        assert len(fa.manipulation_indicators) == 2
        assert fa.platform_chain == "whatsapp"
