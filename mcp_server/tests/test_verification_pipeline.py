"""
Tests for the evidence verification pipeline.

Covers: pipeline orchestrator, schema check, GPS check, timestamp check,
evidence hash check, metadata check, GPS extraction, datetime parsing.
"""

import pytest
from datetime import datetime, timezone, timedelta

pytestmark = pytest.mark.security

from verification.pipeline import (
    run_verification_pipeline,
    CheckResult,
    VerificationResult,
    _run_schema_check,
    _run_gps_check,
    _run_timestamp_check,
    _run_evidence_hash_check,
    _run_metadata_check,
    _extract_gps_from_evidence,
    _parse_datetime,
    CHECK_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(**overrides):
    """Create a minimal task dict with sensible defaults."""
    base = {
        "id": "task-001",
        "category": "knowledge_access",
        "evidence_schema": {"required": ["photo"], "optional": ["notes"]},
        "location_lat": None,
        "location_lng": None,
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "assigned_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    }
    base.update(overrides)
    return base


def _make_submission(**overrides):
    """Create a minimal submission dict with sensible defaults."""
    base = {
        "id": "sub-001",
        "evidence": {"photo": "https://cdn.example.com/photo.jpg"},
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


# ===========================================================================
# VerificationResult
# ===========================================================================


class TestVerificationResult:
    def test_to_dict_serialization(self):
        r = VerificationResult(
            passed=True,
            score=0.85432,
            checks=[
                CheckResult(name="schema", passed=True, score=1.0, reason="ok"),
            ],
            warnings=["GPS skipped"],
        )
        d = r.to_dict()
        assert d["passed"] is True
        assert d["score"] == 0.854
        assert len(d["checks"]) == 1
        assert d["checks"][0]["name"] == "schema"
        assert d["warnings"] == ["GPS skipped"]

    def test_to_dict_empty(self):
        r = VerificationResult(passed=False, score=0.0)
        d = r.to_dict()
        assert d["passed"] is False
        assert d["checks"] == []
        assert d["warnings"] == []


# ===========================================================================
# _parse_datetime
# ===========================================================================


class TestParseDatetime:
    def test_parses_isoformat(self):
        dt = _parse_datetime("2026-02-24T12:00:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_parses_z_suffix(self):
        dt = _parse_datetime("2026-02-24T12:00:00Z")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_parses_datetime_object(self):
        original = datetime(2026, 1, 1, tzinfo=timezone.utc)
        dt = _parse_datetime(original)
        assert dt is original

    def test_adds_utc_to_naive_datetime(self):
        naive = datetime(2026, 1, 1)
        dt = _parse_datetime(naive)
        assert dt.tzinfo == timezone.utc

    def test_adds_utc_to_naive_string(self):
        dt = _parse_datetime("2026-01-01T00:00:00")
        assert dt is not None
        assert dt.tzinfo == timezone.utc

    def test_returns_none_for_garbage(self):
        assert _parse_datetime("not-a-date") is None
        assert _parse_datetime(12345) is None
        assert _parse_datetime(None) is None


# ===========================================================================
# _extract_gps_from_evidence
# ===========================================================================


class TestExtractGPS:
    def test_direct_gps_field(self):
        lat, lng = _extract_gps_from_evidence({"gps": {"lat": 4.7110, "lng": -74.0721}})
        assert lat == pytest.approx(4.711)
        assert lng == pytest.approx(-74.0721)

    def test_location_field(self):
        lat, lng = _extract_gps_from_evidence(
            {"location": {"latitude": 4.7110, "longitude": -74.0721}}
        )
        assert lat == pytest.approx(4.711)

    def test_coordinates_field(self):
        lat, lng = _extract_gps_from_evidence(
            {"coordinates": {"lat": 4.7110, "lon": -74.0721}}
        )
        assert lat == pytest.approx(4.711)

    def test_photo_geo_field(self):
        lat, lng = _extract_gps_from_evidence(
            {"photo_geo": {"lat": 4.7110, "lng": -74.0721}}
        )
        assert lat == pytest.approx(4.711)

    def test_photo_geo_nested_metadata(self):
        lat, lng = _extract_gps_from_evidence(
            {"photo_geo": {"metadata": {"lat": 4.7110, "lng": -74.0721}}}
        )
        assert lat == pytest.approx(4.711)

    def test_forensic_metadata_location(self):
        lat, lng = _extract_gps_from_evidence(
            {"forensic_metadata": {"location": {"lat": 4.7110, "lng": -74.0721}}}
        )
        assert lat == pytest.approx(4.711)

    def test_device_info_gps(self):
        lat, lng = _extract_gps_from_evidence(
            {"device_info": {"gps": {"lat": 4.7110, "lng": -74.0721}}}
        )
        assert lat == pytest.approx(4.711)

    def test_no_gps_returns_none(self):
        lat, lng = _extract_gps_from_evidence(
            {"photo": "https://cdn.example.com/x.jpg"}
        )
        assert lat is None
        assert lng is None

    def test_empty_evidence(self):
        lat, lng = _extract_gps_from_evidence({})
        assert lat is None
        assert lng is None

    def test_string_coordinates_converted(self):
        lat, lng = _extract_gps_from_evidence(
            {"gps": {"lat": "4.711", "lng": "-74.072"}}
        )
        assert lat == pytest.approx(4.711)
        assert lng == pytest.approx(-74.072)

    def test_invalid_string_coordinates(self):
        lat, lng = _extract_gps_from_evidence({"gps": {"lat": "invalid", "lng": "bad"}})
        assert lat is None
        assert lng is None

    def test_nested_gps_in_photo(self):
        """Mobile app sends evidence.photo.gps = {lat, lng, accuracy}."""
        lat, lng = _extract_gps_from_evidence(
            {
                "photo": {
                    "url": "https://cdn.example.com/x.jpg",
                    "gps": {"lat": 4.7110, "lng": -74.0721, "accuracy": 10},
                    "timestamp": "2026-03-15T00:00:00Z",
                }
            }
        )
        assert lat == pytest.approx(4.711)
        assert lng == pytest.approx(-74.0721)

    def test_nested_gps_in_photo_geo(self):
        """Mobile app sends evidence.photo_geo.gps when photo_geo is required."""
        lat, lng = _extract_gps_from_evidence(
            {
                "photo_geo": {
                    "url": "https://cdn.example.com/x.jpg",
                    "gps": {"lat": 4.7110, "lng": -74.0721},
                }
            }
        )
        assert lat == pytest.approx(4.711)
        assert lng == pytest.approx(-74.0721)

    def test_device_metadata_gps(self):
        """Mobile app sends device_metadata.gps as fallback."""
        lat, lng = _extract_gps_from_evidence(
            {
                "photo": "https://cdn.example.com/x.jpg",
                "device_metadata": {
                    "platform": "ios",
                    "gps": {"lat": 4.7110, "lng": -74.0721, "accuracy": 15},
                },
            }
        )
        assert lat == pytest.approx(4.711)
        assert lng == pytest.approx(-74.0721)


# ===========================================================================
# _run_schema_check
# ===========================================================================


class TestSchemaCheck:
    def test_no_schema_defined(self):
        result = _run_schema_check(
            evidence={"photo": "url"},
            task={"evidence_schema": None},
        )
        assert result.passed is True
        assert result.score == 1.0
        assert result.name == "schema"

    def test_empty_required(self):
        result = _run_schema_check(
            evidence={"photo": "url"},
            task={"evidence_schema": {"required": [], "optional": []}},
        )
        assert result.passed is True
        assert result.score == 1.0

    def test_all_required_present(self):
        result = _run_schema_check(
            evidence={"photo": "https://cdn.example.com/pic.jpg", "notes": "done"},
            task={"evidence_schema": {"required": ["photo", "notes"], "optional": []}},
        )
        assert result.passed is True
        assert result.score == 1.0

    def test_missing_required_field(self):
        result = _run_schema_check(
            evidence={"notes": "done"},
            task={"evidence_schema": {"required": ["photo", "notes"], "optional": []}},
        )
        assert result.passed is False
        assert result.score < 1.0
        assert "photo" in result.details.get("missing", [])

    def test_partial_required(self):
        result = _run_schema_check(
            evidence={"photo": "url"},
            task={
                "evidence_schema": {
                    "required": ["photo", "gps", "timestamp"],
                    "optional": [],
                }
            },
        )
        assert result.score == pytest.approx(1 / 3, abs=0.01)


# ===========================================================================
# _run_gps_check
# ===========================================================================


class TestGPSCheck:
    def test_no_task_coords_with_evidence_gps_partial_pass(self):
        """Task has no coords but evidence has GPS -> partial pass (score 0.7)."""
        result = _run_gps_check(
            evidence={"gps": {"lat": 4.711, "lng": -74.072}},
            task={"location_lat": None, "location_lng": None},
            category="physical_presence",
        )
        assert result is not None
        assert result.passed is True
        assert result.score == 0.7
        assert "no task reference location" in result.reason

    def test_no_task_coords_no_evidence_gps_physical_fails(self):
        """Task has no coords AND evidence has no GPS for physical task -> fail."""
        result = _run_gps_check(
            evidence={"photo": "url"},
            task={"location_lat": None, "location_lng": None},
            category="physical_presence",
        )
        assert result is not None
        assert result.passed is False
        assert result.score == 0.0
        assert "No GPS coordinates found" in result.reason

    def test_no_task_coords_no_evidence_gps_nonphysical_skips(self):
        """Task has no coords AND evidence has no GPS for non-physical task -> None (skip)."""
        result = _run_gps_check(
            evidence={"photo": "url"},
            task={"location_lat": None, "location_lng": None},
            category="knowledge_access",
        )
        assert result is None

    def test_no_task_coords_with_evidence_gps_nonphysical_partial_pass(self):
        """Non-physical task has no coords but evidence has GPS -> partial pass."""
        result = _run_gps_check(
            evidence={"gps": {"lat": 4.711, "lng": -74.072}},
            task={"location_lat": None, "location_lng": None},
            category="knowledge_access",
        )
        assert result is not None
        assert result.passed is True
        assert result.score == 0.7

    def test_physical_task_no_evidence_gps_fails(self):
        result = _run_gps_check(
            evidence={"photo": "url"},
            task={"location_lat": 4.711, "location_lng": -74.072},
            category="physical_presence",
        )
        assert result is not None
        assert result.passed is False
        assert result.score == 0.0

    def test_nonphysical_task_no_evidence_gps_passes(self):
        result = _run_gps_check(
            evidence={"photo": "url"},
            task={"location_lat": 4.711, "location_lng": -74.072},
            category="knowledge_access",
        )
        assert result is not None
        assert result.passed is True
        assert result.score == 0.7

    def test_evidence_within_range(self):
        # Same point = 0m distance
        result = _run_gps_check(
            evidence={"gps": {"lat": 4.711, "lng": -74.072}},
            task={"location_lat": 4.711, "location_lng": -74.072},
            category="physical_presence",
        )
        assert result is not None
        assert result.passed is True
        assert result.score >= 0.9

    def test_evidence_out_of_range(self):
        # Bogota to Medellin ~400km
        result = _run_gps_check(
            evidence={"gps": {"lat": 6.2442, "lng": -75.5812}},
            task={"location_lat": 4.711, "location_lng": -74.072},
            category="physical_presence",
        )
        assert result is not None
        assert result.passed is False

    def test_simple_action_larger_threshold(self):
        # 800m away — should pass for simple_action (1000m threshold) but fail physical_presence (500m)
        # ~800m north of task
        result_simple = _run_gps_check(
            evidence={"gps": {"lat": 4.7182, "lng": -74.072}},
            task={"location_lat": 4.711, "location_lng": -74.072},
            category="simple_action",
        )
        result_physical = _run_gps_check(
            evidence={"gps": {"lat": 4.7182, "lng": -74.072}},
            task={"location_lat": 4.711, "location_lng": -74.072},
            category="physical_presence",
        )
        assert result_simple is not None
        assert result_physical is not None
        assert result_simple.passed is True
        assert result_physical.passed is False


# ===========================================================================
# _run_timestamp_check
# ===========================================================================


class TestTimestampCheck:
    def test_no_deadline_returns_none(self):
        result = _run_timestamp_check(
            submission={"submitted_at": datetime.now(timezone.utc).isoformat()},
            task={"deadline": None, "assigned_at": None},
        )
        assert result is None

    def test_no_submitted_at_returns_none(self):
        result = _run_timestamp_check(
            submission={"submitted_at": None},
            task={"deadline": "2026-12-31T23:59:59Z", "assigned_at": None},
        )
        assert result is None

    def test_within_deadline(self):
        now = datetime.now(timezone.utc)
        result = _run_timestamp_check(
            submission={"submitted_at": now.isoformat()},
            task={
                "deadline": (now + timedelta(hours=1)).isoformat(),
                "assigned_at": (now - timedelta(hours=1)).isoformat(),
            },
        )
        assert result is not None
        assert result.passed is True
        assert result.score == 1.0

    def test_past_deadline(self):
        now = datetime.now(timezone.utc)
        result = _run_timestamp_check(
            submission={"submitted_at": now.isoformat()},
            task={
                "deadline": (now - timedelta(hours=1)).isoformat(),
                "assigned_at": (now - timedelta(hours=2)).isoformat(),
            },
        )
        assert result is not None
        assert result.passed is False
        assert result.score == 0.0

    def test_without_assigned_at_checks_deadline_only(self):
        now = datetime.now(timezone.utc)
        result = _run_timestamp_check(
            submission={"submitted_at": now.isoformat()},
            task={
                "deadline": (now + timedelta(hours=1)).isoformat(),
            },
        )
        assert result is not None
        assert result.passed is True


# ===========================================================================
# _run_evidence_hash_check
# ===========================================================================


class TestEvidenceHashCheck:
    def test_no_hash_neutral_score(self):
        result = _run_evidence_hash_check({"photo": "url"})
        assert result is not None
        assert result.passed is True
        assert result.score == 0.5

    def test_sha256_present_but_wrong(self):
        """Hash present but does not match computed hash -> mismatch (score 0.0)."""
        result = _run_evidence_hash_check(
            {
                "sha256": "abc123def456abc123def456abc123def456abc123def456abc123def456abcd"
            }
        )
        # With actual verification, a mismatched hash now scores 0.0
        assert result.passed is False
        assert result.score == 0.0

    def test_evidence_hash_field_mismatch(self):
        """evidence_hash present but wrong -> mismatch."""
        result = _run_evidence_hash_check({"evidence_hash": "0xabc..."})
        assert result.passed is False
        assert result.score == 0.0

    def test_file_hash_field_mismatch(self):
        """file_hash present but wrong -> mismatch."""
        result = _run_evidence_hash_check({"file_hash": "sha256:abc"})
        assert result.passed is False
        assert result.score == 0.0

    def test_integrity_hash_field_mismatch(self):
        """integrity_hash present but wrong -> mismatch."""
        result = _run_evidence_hash_check({"integrity_hash": "sha256:abc"})
        assert result.passed is False
        assert result.score == 0.0


# ===========================================================================
# _run_metadata_check
# ===========================================================================


class TestMetadataCheck:
    def test_bare_evidence(self):
        result = _run_metadata_check({"photo": "url"}, "knowledge_access")
        assert result.passed is True
        # Base 0.5 + photo evidence 0.1 = 0.6
        assert result.score >= 0.5

    def test_forensic_metadata_bonus(self):
        result = _run_metadata_check(
            {"photo": "url", "forensic_metadata": {"device": "iPhone 15"}},
            "physical_presence",
        )
        # Base 0.5 + device 0.2 + photo 0.1 = 0.8
        assert result.score >= 0.7

    def test_timestamp_bonus(self):
        result = _run_metadata_check(
            {"captured_at": "2026-02-24T12:00:00Z"}, "knowledge_access"
        )
        assert result.score >= 0.6

    def test_notes_bonus(self):
        result = _run_metadata_check(
            {"notes": "Task completed as requested"}, "knowledge_access"
        )
        assert result.score >= 0.5

    def test_rich_evidence_high_score(self):
        result = _run_metadata_check(
            {
                "photo": "url",
                "forensic_metadata": {"device": "Pixel 9"},
                "timestamp": "2026-02-24T12:00:00Z",
                "notes": "Completed",
            },
            "physical_presence",
        )
        # Base 0.5 + device 0.2 + timestamp 0.1 + photo 0.1 + notes 0.05 = 0.95
        assert result.score >= 0.9

    def test_max_score_capped_at_1(self):
        result = _run_metadata_check(
            {
                "photo": "url",
                "screenshot": "url2",
                "forensic_metadata": {"device": "x"},
                "device_info": {"os": "y"},
                "timestamp": "now",
                "captured_at": "now2",
                "notes": "ok",
                "description": "desc",
            },
            "knowledge_access",
        )
        assert result.score <= 1.0


# ===========================================================================
# Full Pipeline (integration)
# ===========================================================================


class TestVerificationPipeline:
    @pytest.mark.asyncio
    async def test_minimal_submission_passes(self):
        """Submission with matching evidence and no strict checks passes."""
        task = _make_task(evidence_schema=None, category="knowledge_access")
        submission = _make_submission(
            evidence={"photo": "https://cdn.example.com/img.jpg"}
        )

        result = await run_verification_pipeline(submission, task)
        assert isinstance(result, VerificationResult)
        assert result.passed is True
        assert result.score > 0.0
        assert len(result.checks) >= 2  # schema + metadata at minimum

    @pytest.mark.asyncio
    async def test_empty_evidence_with_no_schema_passes(self):
        """If task has no schema requirements, empty evidence passes schema check."""
        task = _make_task(evidence_schema=None, category="digital_physical")
        submission = _make_submission(evidence={})

        result = await run_verification_pipeline(submission, task)
        schema_check = next(c for c in result.checks if c.name == "schema")
        assert schema_check.passed is True

    @pytest.mark.asyncio
    async def test_missing_required_evidence_lowers_score(self):
        """Missing required evidence fields lower the score."""
        task = _make_task(
            evidence_schema={"required": ["photo", "gps", "receipt"], "optional": []},
            category="simple_action",
        )
        submission = _make_submission(evidence={"photo": "url"})

        result = await run_verification_pipeline(submission, task)
        schema_check = next(c for c in result.checks if c.name == "schema")
        assert schema_check.passed is False
        assert schema_check.score < 1.0
        # Overall score should be lower
        assert result.score < 0.8

    @pytest.mark.asyncio
    async def test_physical_task_no_coords_no_evidence_gps_fails_check(self):
        """Physical task without task coords and no GPS in evidence -> GPS check fails."""
        task = _make_task(
            category="physical_presence",
            location_lat=None,
            location_lng=None,
        )
        submission = _make_submission()

        result = await run_verification_pipeline(submission, task)
        gps_check = next((c for c in result.checks if c.name == "gps"), None)
        assert gps_check is not None
        assert gps_check.passed is False
        assert gps_check.score == 0.0
        assert "No GPS coordinates found" in gps_check.reason

    @pytest.mark.asyncio
    async def test_physical_task_no_coords_with_evidence_gps_partial_pass(self):
        """Physical task without task coords but evidence has GPS -> partial pass."""
        task = _make_task(
            category="physical_presence",
            location_lat=None,
            location_lng=None,
        )
        submission = _make_submission(
            evidence={
                "photo": "url",
                "gps": {"lat": 4.711, "lng": -74.072},
            }
        )

        result = await run_verification_pipeline(submission, task)
        gps_check = next((c for c in result.checks if c.name == "gps"), None)
        assert gps_check is not None
        assert gps_check.passed is True
        assert gps_check.score == 0.7
        assert "no task reference location" in gps_check.reason

    @pytest.mark.asyncio
    async def test_physical_task_with_gps_match(self):
        """Physical task with matching GPS coords has a GPS check."""
        task = _make_task(
            category="physical_presence",
            location_lat=4.711,
            location_lng=-74.072,
        )
        submission = _make_submission(
            evidence={
                "photo": "url",
                "gps": {"lat": 4.711, "lng": -74.072},
            }
        )

        result = await run_verification_pipeline(submission, task)
        gps_check = next((c for c in result.checks if c.name == "gps"), None)
        assert gps_check is not None
        assert gps_check.passed is True

    @pytest.mark.asyncio
    async def test_timestamp_within_deadline_passes(self):
        """Submission within deadline passes timestamp check."""
        now = datetime.now(timezone.utc)
        task = _make_task(
            deadline=(now + timedelta(hours=1)).isoformat(),
            assigned_at=(now - timedelta(hours=1)).isoformat(),
        )
        submission = _make_submission(submitted_at=now.isoformat())

        result = await run_verification_pipeline(submission, task)
        ts_check = next((c for c in result.checks if c.name == "timestamp"), None)
        assert ts_check is not None
        assert ts_check.passed is True

    @pytest.mark.asyncio
    async def test_timestamp_past_deadline_fails(self):
        """Submission past deadline fails timestamp check."""
        now = datetime.now(timezone.utc)
        task = _make_task(
            deadline=(now - timedelta(hours=1)).isoformat(),
            assigned_at=(now - timedelta(hours=3)).isoformat(),
        )
        submission = _make_submission(submitted_at=now.isoformat())

        result = await run_verification_pipeline(submission, task)
        ts_check = next((c for c in result.checks if c.name == "timestamp"), None)
        assert ts_check is not None
        assert ts_check.passed is False

    @pytest.mark.asyncio
    async def test_evidence_hash_mismatch_lowers_score(self):
        """Providing a wrong evidence hash now flags mismatch (score 0.0)."""
        task = _make_task(evidence_schema=None)
        submission = _make_submission(
            evidence={"photo": "url", "sha256": "abc123def456"}
        )

        result = await run_verification_pipeline(submission, task)
        hash_check = next((c for c in result.checks if c.name == "evidence_hash"), None)
        assert hash_check is not None
        # Wrong hash -> mismatch -> score 0.0
        assert hash_check.score == 0.0

    @pytest.mark.asyncio
    async def test_rich_evidence_high_score(self):
        """Rich evidence with forensic metadata, GPS, hash gets high score."""
        now = datetime.now(timezone.utc)
        task = _make_task(
            category="physical_presence",
            evidence_schema={"required": ["photo"], "optional": ["notes"]},
            location_lat=4.711,
            location_lng=-74.072,
            deadline=(now + timedelta(hours=1)).isoformat(),
            assigned_at=(now - timedelta(hours=1)).isoformat(),
        )
        submission = _make_submission(
            evidence={
                "photo": "https://cdn.example.com/verified.jpg",
                "gps": {"lat": 4.711, "lng": -74.072},
                "sha256": "abc123def456abc123def456abc123def456",
                "forensic_metadata": {"device": "iPhone 15 Pro", "os": "iOS 19"},
                "timestamp": now.isoformat(),
                "notes": "Verified store is open.",
            },
            submitted_at=now.isoformat(),
        )

        result = await run_verification_pipeline(submission, task)
        assert result.passed is True
        assert result.score >= 0.8
        assert len(result.checks) >= 4

    @pytest.mark.asyncio
    async def test_schema_failure_blocks_pipeline(self):
        """Even with high aggregate score, schema failure blocks pipeline pass."""
        now = datetime.now(timezone.utc)
        task = _make_task(
            evidence_schema={"required": ["photo", "receipt", "gps"], "optional": []},
            deadline=(now + timedelta(hours=1)).isoformat(),
            assigned_at=(now - timedelta(hours=1)).isoformat(),
        )
        # Only submit notes — all 3 required fields missing
        submission = _make_submission(
            evidence={"notes": "I promise I did it"},
            submitted_at=now.isoformat(),
        )

        result = await run_verification_pipeline(submission, task)
        assert result.passed is False
        schema_check = next(c for c in result.checks if c.name == "schema")
        assert schema_check.passed is False

    @pytest.mark.asyncio
    async def test_to_dict_roundtrip(self):
        """Pipeline result serializes to dict properly for DB storage."""
        task = _make_task()
        submission = _make_submission()

        result = await run_verification_pipeline(submission, task)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "passed" in d
        assert "score" in d
        assert isinstance(d["checks"], list)
        assert isinstance(d["warnings"], list)
        for check in d["checks"]:
            assert "name" in check
            assert "passed" in check
            assert "score" in check

    @pytest.mark.asyncio
    async def test_no_evidence_field_doesnt_crash(self):
        """Submission with no evidence key doesn't crash the pipeline."""
        task = _make_task(evidence_schema=None)
        submission = {
            "id": "sub-x",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await run_verification_pipeline(submission, task)
        assert isinstance(result, VerificationResult)

    @pytest.mark.asyncio
    async def test_weights_sum_to_one(self):
        """CHECK_WEIGHTS (Phase A) should cover all 7 sync checks and sum to ~0.50."""
        assert set(CHECK_WEIGHTS.keys()) == {
            "schema",
            "gps",
            "gps_antispoofing",
            "timestamp",
            "evidence_hash",
            "metadata",
            "attestation",
        }
        # Phase A subtotal ~ 0.50 (Phase B adds another ~0.50)
        assert sum(CHECK_WEIGHTS.values()) == pytest.approx(0.50, abs=0.05)

    @pytest.mark.asyncio
    async def test_digital_task_without_gps_no_warning(self):
        """Non-physical task without GPS doesn't generate GPS warning."""
        task = _make_task(
            category="knowledge_access",
            location_lat=None,
            location_lng=None,
        )
        submission = _make_submission()

        result = await run_verification_pipeline(submission, task)
        assert not any("GPS" in w for w in result.warnings)
