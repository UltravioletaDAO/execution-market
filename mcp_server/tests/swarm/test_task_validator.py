"""
Tests for TaskValidator — Module #58
=====================================

Pre-routing task validation pipeline.

Test classes:
    1. TestRequiredFields — missing/empty required fields
    2. TestBountyValidation — min/max bounty rules
    3. TestDescriptionValidation — description length checks
    4. TestEvidenceTypes — valid/invalid evidence enums
    5. TestDeadlineValidation — past/future/reasonable deadlines
    6. TestNetworkValidation — supported/unsupported networks
    7. TestSkillValidation — skill parsing rules
    8. TestDuplicateDetection — exact and fuzzy duplicate detection
    9. TestBatchValidation — batch validation and reports
    10. TestRuleManagement — add/remove/enable/disable rules
    11. TestMetrics — validation metrics and diagnostics
    12. TestPersistence — save/load round-trip
    13. TestFailFast — fail-fast mode behavior
    14. TestCustomRules — custom validation rules
    15. TestEdgeCases — edge cases and error handling
"""

import time
import unittest
from datetime import datetime, timezone, timedelta

import sys
import os

# Ensure mcp_server package is importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", ".."),
)

from mcp_server.swarm.task_validator import (
    TaskValidator,
    ValidationFinding,
    ValidationSeverity,
    ValidationRuleId,
    ValidationRule,
    VALID_EVIDENCE_TYPES,
)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _valid_task(**overrides) -> dict:
    """Create a valid task dict with optional overrides."""
    future = datetime.now(timezone.utc) + timedelta(days=7)
    task = {
        "id": "task-001",
        "title": "Take a photo of the Miami skyline at sunset",
        "description": "Go to Brickell Key and photograph the Miami skyline during golden hour. Include at least 3 buildings in frame.",
        "bounty": 5.00,
        "evidence_types": ["photo", "photo_geo"],
        "deadline": future.isoformat(),
        "network": "base",
        "required_skills": ["photography", "local-knowledge"],
    }
    task.update(overrides)
    return task


# ──────────────────────────────────────────────────────────────
# Test Classes
# ──────────────────────────────────────────────────────────────


class TestRequiredFields(unittest.TestCase):
    """Test required field validation."""

    def setUp(self):
        self.v = TaskValidator()

    def test_valid_task_passes(self):
        result = self.v.validate(_valid_task())
        self.assertTrue(result.passed)
        self.assertEqual(len(result.rejections), 0)

    def test_missing_title_rejects(self):
        task = _valid_task()
        del task["title"]
        result = self.v.validate(task)
        self.assertFalse(result.passed)
        self.assertTrue(any("title" in f.message for f in result.rejections))

    def test_missing_description_rejects(self):
        task = _valid_task()
        del task["description"]
        result = self.v.validate(task)
        self.assertFalse(result.passed)
        self.assertTrue(any("description" in f.message for f in result.rejections))

    def test_missing_bounty_rejects(self):
        task = _valid_task()
        del task["bounty"]
        result = self.v.validate(task)
        self.assertFalse(result.passed)
        self.assertTrue(any("bounty" in f.message for f in result.rejections))

    def test_empty_title_rejects(self):
        result = self.v.validate(_valid_task(title=""))
        self.assertFalse(result.passed)

    def test_whitespace_title_rejects(self):
        result = self.v.validate(_valid_task(title="   "))
        self.assertFalse(result.passed)

    def test_empty_description_rejects(self):
        result = self.v.validate(_valid_task(description=""))
        self.assertFalse(result.passed)

    def test_all_missing_gives_three_rejections(self):
        result = self.v.validate({})
        self.assertFalse(result.passed)
        req_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.REQUIRED_FIELDS.value
        ]
        self.assertEqual(len(req_rejections), 3)  # title, desc, bounty


class TestBountyValidation(unittest.TestCase):
    """Test bounty min/max rules."""

    def setUp(self):
        self.v = TaskValidator(min_bounty=0.10, max_bounty=5000.0)

    def test_valid_bounty_passes(self):
        result = self.v.validate(_valid_task(bounty=10.00))
        # Only bounty-related findings should be absent
        bounty_rejections = [
            f
            for f in result.rejections
            if "bounty" in f.rule_id.lower() or "bounty" in f.message.lower()
        ]
        self.assertEqual(len(bounty_rejections), 0)

    def test_zero_bounty_rejects(self):
        result = self.v.validate(_valid_task(bounty=0))
        self.assertFalse(result.passed)

    def test_negative_bounty_rejects(self):
        result = self.v.validate(_valid_task(bounty=-5.00))
        self.assertFalse(result.passed)

    def test_below_minimum_rejects(self):
        result = self.v.validate(_valid_task(bounty=0.05))
        self.assertFalse(result.passed)
        self.assertTrue(any("minimum" in f.message.lower() for f in result.rejections))

    def test_above_maximum_warns(self):
        result = self.v.validate(_valid_task(bounty=6000.00))
        # Should warn, not reject
        self.assertTrue(result.passed)
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any("ceiling" in f.message.lower() for f in result.warnings))

    def test_non_numeric_bounty_rejects(self):
        result = self.v.validate(_valid_task(bounty="free"))
        self.assertFalse(result.passed)

    def test_string_numeric_bounty_passes(self):
        """String "10.00" should be parseable."""
        result = self.v.validate(_valid_task(bounty="10.00"))
        bounty_rejections = [
            f for f in result.rejections if "bounty" in f.rule_id.lower()
        ]
        self.assertEqual(len(bounty_rejections), 0)

    def test_exact_minimum_passes(self):
        result = self.v.validate(_valid_task(bounty=0.10))
        bounty_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.BOUNTY_MINIMUM.value
        ]
        self.assertEqual(len(bounty_rejections), 0)


class TestDescriptionValidation(unittest.TestCase):
    """Test description length rules."""

    def setUp(self):
        self.v = TaskValidator(max_description_length=500)

    def test_normal_description_passes(self):
        result = self.v.validate(
            _valid_task(description="A reasonable task description here")
        )
        desc_findings = [
            f
            for f in result.findings
            if f.rule_id == ValidationRuleId.DESCRIPTION_LENGTH.value
        ]
        self.assertEqual(len(desc_findings), 0)

    def test_very_short_description_warns(self):
        result = self.v.validate(_valid_task(description="Hi"))
        self.assertTrue(result.passed)  # Warning, not rejection
        self.assertTrue(any("short" in f.message.lower() for f in result.warnings))

    def test_very_long_description_warns(self):
        result = self.v.validate(_valid_task(description="x" * 600))
        self.assertTrue(result.passed)  # Warning, not rejection
        self.assertTrue(any("long" in f.message.lower() for f in result.warnings))

    def test_non_string_description_rejects(self):
        result = self.v.validate(_valid_task(description=12345))
        desc_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.DESCRIPTION_LENGTH.value
        ]
        self.assertEqual(len(desc_rejections), 1)


class TestEvidenceTypes(unittest.TestCase):
    """Test evidence type validation."""

    def setUp(self):
        self.v = TaskValidator()

    def test_valid_evidence_types_pass(self):
        result = self.v.validate(
            _valid_task(evidence_types=["photo", "video", "screenshot"])
        )
        et_findings = [
            f
            for f in result.findings
            if f.rule_id == ValidationRuleId.EVIDENCE_TYPES.value
        ]
        self.assertEqual(len(et_findings), 0)

    def test_invalid_evidence_type_rejects(self):
        result = self.v.validate(
            _valid_task(evidence_types=["photo", "gps_coordinates"])
        )
        self.assertFalse(result.passed)
        self.assertTrue(any("gps_coordinates" in f.message for f in result.rejections))

    def test_all_valid_types_pass(self):
        result = self.v.validate(_valid_task(evidence_types=list(VALID_EVIDENCE_TYPES)))
        et_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.EVIDENCE_TYPES.value
        ]
        self.assertEqual(len(et_rejections), 0)

    def test_string_evidence_type_treated_as_list(self):
        result = self.v.validate(_valid_task(evidence_types="photo"))
        et_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.EVIDENCE_TYPES.value
        ]
        self.assertEqual(len(et_rejections), 0)

    def test_non_list_evidence_rejects(self):
        result = self.v.validate(_valid_task(evidence_types=42))
        self.assertFalse(result.passed)

    def test_non_string_element_rejects(self):
        result = self.v.validate(_valid_task(evidence_types=[123]))
        self.assertFalse(result.passed)

    def test_no_evidence_types_passes(self):
        """No evidence types = optional, should pass."""
        task = _valid_task()
        del task["evidence_types"]
        result = self.v.validate(task)
        et_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.EVIDENCE_TYPES.value
        ]
        self.assertEqual(len(et_rejections), 0)

    def test_evidence_required_alias(self):
        """evidence_required is an alias for evidence_types."""
        task = _valid_task()
        del task["evidence_types"]
        task["evidence_required"] = ["photo"]
        result = self.v.validate(task)
        et_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.EVIDENCE_TYPES.value
        ]
        self.assertEqual(len(et_rejections), 0)


class TestDeadlineValidation(unittest.TestCase):
    """Test deadline validation rules."""

    def setUp(self):
        self.v = TaskValidator(max_deadline_days=365)

    def test_future_deadline_passes(self):
        future = datetime.now(timezone.utc) + timedelta(days=7)
        result = self.v.validate(_valid_task(deadline=future.isoformat()))
        dl_rejections = [
            f for f in result.rejections if "deadline" in f.rule_id.lower()
        ]
        self.assertEqual(len(dl_rejections), 0)

    def test_past_deadline_rejects(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        result = self.v.validate(_valid_task(deadline=past.isoformat()))
        self.assertFalse(result.passed)
        self.assertTrue(any("past" in f.message.lower() for f in result.rejections))

    def test_far_future_deadline_warns(self):
        far = datetime.now(timezone.utc) + timedelta(days=500)
        result = self.v.validate(_valid_task(deadline=far.isoformat()))
        self.assertTrue(result.passed)  # Warning not rejection
        self.assertTrue(any("500" in f.message for f in result.warnings))

    def test_unix_timestamp_works(self):
        future = time.time() + 86400 * 7
        result = self.v.validate(_valid_task(deadline=future))
        dl_rejections = [
            f for f in result.rejections if "deadline" in f.rule_id.lower()
        ]
        self.assertEqual(len(dl_rejections), 0)

    def test_invalid_deadline_string_rejects(self):
        result = self.v.validate(_valid_task(deadline="next tuesday"))
        self.assertFalse(result.passed)

    def test_invalid_deadline_type_rejects(self):
        result = self.v.validate(_valid_task(deadline=[2026, 3, 30]))
        self.assertFalse(result.passed)

    def test_no_deadline_passes(self):
        """No deadline = optional, should pass."""
        task = _valid_task()
        del task["deadline"]
        result = self.v.validate(task)
        dl_rejections = [
            f for f in result.rejections if "deadline" in f.rule_id.lower()
        ]
        self.assertEqual(len(dl_rejections), 0)

    def test_expires_at_alias(self):
        """expires_at is an alias for deadline."""
        task = _valid_task()
        del task["deadline"]
        future = datetime.now(timezone.utc) + timedelta(days=3)
        task["expires_at"] = future.isoformat()
        result = self.v.validate(task)
        dl_rejections = [
            f for f in result.rejections if "deadline" in f.rule_id.lower()
        ]
        self.assertEqual(len(dl_rejections), 0)

    def test_z_suffix_parsed(self):
        """ISO 8601 with Z suffix should parse."""
        future = datetime.now(timezone.utc) + timedelta(days=5)
        deadline_str = future.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = self.v.validate(_valid_task(deadline=deadline_str))
        dl_rejections = [
            f for f in result.rejections if "deadline" in f.rule_id.lower()
        ]
        self.assertEqual(len(dl_rejections), 0)


class TestNetworkValidation(unittest.TestCase):
    """Test network support validation."""

    def setUp(self):
        self.v = TaskValidator(enabled_networks={"base", "ethereum", "polygon"})

    def test_supported_network_passes(self):
        result = self.v.validate(_valid_task(network="base"))
        net_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.NETWORK_SUPPORTED.value
        ]
        self.assertEqual(len(net_rejections), 0)

    def test_unsupported_network_rejects(self):
        result = self.v.validate(_valid_task(network="solana"))
        self.assertFalse(result.passed)
        self.assertTrue(any("solana" in f.message.lower() for f in result.rejections))

    def test_case_insensitive(self):
        result = self.v.validate(_valid_task(network="Base"))
        net_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.NETWORK_SUPPORTED.value
        ]
        self.assertEqual(len(net_rejections), 0)

    def test_no_network_passes(self):
        """No network = defaults to base, should pass."""
        task = _valid_task()
        del task["network"]
        result = self.v.validate(task)
        net_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.NETWORK_SUPPORTED.value
        ]
        self.assertEqual(len(net_rejections), 0)

    def test_chain_alias(self):
        """chain is an alias for network."""
        task = _valid_task()
        del task["network"]
        task["chain"] = "polygon"
        result = self.v.validate(task)
        net_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.NETWORK_SUPPORTED.value
        ]
        self.assertEqual(len(net_rejections), 0)

    def test_non_string_network_rejects(self):
        result = self.v.validate(_valid_task(network=8453))
        self.assertFalse(result.passed)


class TestSkillValidation(unittest.TestCase):
    """Test skill parsing validation."""

    def setUp(self):
        self.v = TaskValidator()

    def test_valid_skills_pass(self):
        result = self.v.validate(
            _valid_task(required_skills=["photography", "gps-navigation"])
        )
        skill_findings = [
            f
            for f in result.findings
            if f.rule_id == ValidationRuleId.SKILL_PARSEABLE.value
        ]
        self.assertEqual(len(skill_findings), 0)

    def test_comma_separated_string(self):
        result = self.v.validate(_valid_task(required_skills="photography, editing"))
        skill_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.SKILL_PARSEABLE.value
        ]
        self.assertEqual(len(skill_rejections), 0)

    def test_non_string_skill_rejects(self):
        result = self.v.validate(_valid_task(required_skills=[123, "valid"]))
        skill_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.SKILL_PARSEABLE.value
        ]
        self.assertTrue(len(skill_rejections) > 0)

    def test_unusual_characters_warn(self):
        result = self.v.validate(_valid_task(required_skills=["ph🐍tography"]))
        skill_warnings = [
            f
            for f in result.warnings
            if f.rule_id == ValidationRuleId.SKILL_PARSEABLE.value
        ]
        self.assertTrue(len(skill_warnings) > 0)

    def test_empty_skill_warns(self):
        result = self.v.validate(_valid_task(required_skills=["", "valid"]))
        skill_warnings = [
            f
            for f in result.warnings
            if f.rule_id == ValidationRuleId.SKILL_PARSEABLE.value
        ]
        self.assertTrue(len(skill_warnings) > 0)

    def test_no_skills_passes(self):
        """No skills = optional, should pass."""
        task = _valid_task()
        del task["required_skills"]
        result = self.v.validate(task)
        skill_findings = [
            f
            for f in result.findings
            if f.rule_id == ValidationRuleId.SKILL_PARSEABLE.value
        ]
        self.assertEqual(len(skill_findings), 0)

    def test_skills_alias(self):
        task = _valid_task()
        del task["required_skills"]
        task["skills"] = ["valid-skill"]
        result = self.v.validate(task)
        skill_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.SKILL_PARSEABLE.value
        ]
        self.assertEqual(len(skill_rejections), 0)

    def test_invalid_skills_type_rejects(self):
        result = self.v.validate(_valid_task(required_skills=42))
        self.assertFalse(result.passed)


class TestDuplicateDetection(unittest.TestCase):
    """Test exact and fuzzy duplicate detection."""

    def setUp(self):
        self.v = TaskValidator()

    def test_first_task_always_passes(self):
        result = self.v.validate(_valid_task())
        dup_findings = [
            f
            for f in result.findings
            if f.rule_id == ValidationRuleId.DUPLICATE_DETECTION.value
        ]
        self.assertEqual(len(dup_findings), 0)

    def test_exact_duplicate_rejects(self):
        """Same title + description within 1 hour = reject."""
        task = _valid_task(id="task-dup-1")
        self.v.validate(task)
        task2 = _valid_task(id="task-dup-2")
        result = self.v.validate(task2)
        dup_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.DUPLICATE_DETECTION.value
        ]
        self.assertTrue(len(dup_rejections) > 0)

    def test_different_tasks_pass(self):
        task1 = _valid_task(
            title="Task A", description="Completely different content A"
        )
        task2 = _valid_task(title="Task B", description="Totally unrelated content B")
        self.v.validate(task1)
        result = self.v.validate(task2)
        dup_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.DUPLICATE_DETECTION.value
        ]
        self.assertEqual(len(dup_rejections), 0)

    def test_fuzzy_duplicate_warns(self):
        """Very similar tasks should warn."""
        task1 = _valid_task(
            id="task-fz-1",
            title="photograph miami skyline sunset brickell",
            description="go to brickell and take photos of the skyline at sunset golden hour from the bridge",
        )
        task2 = _valid_task(
            id="task-fz-2",
            title="photograph miami skyline sunset brickell",
            description="go to brickell and take photos of the skyline at sunset golden hour from the park",
        )
        self.v.validate(task1)
        result = self.v.validate(task2)
        # Should have either exact or fuzzy duplicate finding
        dup_findings = [
            f
            for f in result.findings
            if f.rule_id == ValidationRuleId.DUPLICATE_DETECTION.value
        ]
        self.assertTrue(len(dup_findings) > 0)

    def test_clear_duplicates_resets(self):
        self.v.validate(_valid_task(id="task-c1"))
        self.v.clear_duplicates()
        # Same task should pass now
        result = self.v.validate(_valid_task(id="task-c2"))
        dup_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.DUPLICATE_DETECTION.value
        ]
        self.assertEqual(len(dup_rejections), 0)

    def test_duplicate_window_bounded(self):
        """Oldest entries get evicted from deque."""
        v = TaskValidator(duplicate_window=3)
        for i in range(5):
            v.validate(
                _valid_task(
                    id=f"task-w-{i}",
                    title=f"Unique task number {i}",
                    description=f"This is a completely unique description for task {i}",
                )
            )
        # The deque should only have 3 entries
        self.assertLessEqual(len(v._recent_fingerprints), 3)


class TestBatchValidation(unittest.TestCase):
    """Test batch validation and reports."""

    def setUp(self):
        self.v = TaskValidator()

    def test_batch_all_valid(self):
        tasks = [
            _valid_task(
                id=f"batch-{i}",
                title=f"Task {i}",
                description=f"Description for task {i} is unique",
            )
            for i in range(5)
        ]
        report = self.v.validate_batch(tasks)
        self.assertEqual(report.total, 5)
        self.assertEqual(report.passed_count, 5)
        self.assertEqual(report.rejected_count, 0)
        self.assertAlmostEqual(report.pass_rate, 1.0)

    def test_batch_mixed_results(self):
        tasks = [
            _valid_task(
                id="good-1",
                title="Good task one",
                description="A perfectly fine description for task one",
            ),
            _valid_task(
                id="bad-1", title="", description="Missing title task"
            ),  # Missing title
            _valid_task(
                id="good-2",
                title="Good task two",
                description="Another valid description for task two",
            ),
        ]
        report = self.v.validate_batch(tasks)
        self.assertEqual(report.total, 3)
        self.assertEqual(report.passed_count, 2)
        self.assertEqual(report.rejected_count, 1)

    def test_batch_report_properties(self):
        tasks = [
            _valid_task(
                id="br-1",
                title="Report task one",
                description="Description for report task one",
            ),
            _valid_task(id="br-bad", bounty=-1),
        ]
        report = self.v.validate_batch(tasks)
        self.assertEqual(len(report.passed_tasks), 1)
        self.assertEqual(len(report.rejected_tasks), 1)
        self.assertTrue(report.total_duration_ms >= 0)

    def test_batch_summary(self):
        tasks = [
            _valid_task(
                id=f"sum-{i}", title=f"Summary task {i}", description=f"Unique desc {i}"
            )
            for i in range(3)
        ]
        report = self.v.validate_batch(tasks)
        summary = report.summary()
        self.assertIn("3", summary)
        self.assertIn("passed", summary.lower())

    def test_empty_batch(self):
        report = self.v.validate_batch([])
        self.assertEqual(report.total, 0)
        self.assertEqual(report.pass_rate, 0.0)

    def test_batch_to_dict(self):
        tasks = [
            _valid_task(
                id=f"d-{i}", title=f"Dict task {i}", description=f"Dict desc {i}"
            )
            for i in range(2)
        ]
        report = self.v.validate_batch(tasks)
        d = report.to_dict()
        self.assertIn("total", d)
        self.assertIn("passed", d)
        self.assertIn("results", d)
        self.assertEqual(len(d["results"]), 2)


class TestRuleManagement(unittest.TestCase):
    """Test rule add/remove/enable/disable."""

    def setUp(self):
        self.v = TaskValidator()

    def test_default_rules_exist(self):
        self.assertEqual(len(self.v.rules), 10)

    def test_all_default_rules_enabled(self):
        self.assertEqual(len(self.v.enabled_rules), 10)

    def test_disable_rule(self):
        self.v.disable_rule(ValidationRuleId.DUPLICATE_DETECTION.value)
        self.assertEqual(len(self.v.enabled_rules), 9)

    def test_enable_rule(self):
        self.v.disable_rule(ValidationRuleId.DUPLICATE_DETECTION.value)
        self.v.enable_rule(ValidationRuleId.DUPLICATE_DETECTION.value)
        self.assertEqual(len(self.v.enabled_rules), 10)

    def test_remove_rule(self):
        self.v.remove_rule(ValidationRuleId.DUPLICATE_DETECTION.value)
        self.assertEqual(len(self.v.rules), 9)

    def test_add_custom_rule(self):
        def custom_check(validator, task):
            if task.get("priority") == "URGENT":
                return [
                    ValidationFinding(
                        rule_id="custom_priority",
                        severity=ValidationSeverity.WARNING,
                        message="URGENT priority — fast-track routing",
                    )
                ]
            return []

        rule = ValidationRule(
            rule_id="custom_priority",
            name="Priority Check",
            description="Flags urgent tasks",
            check=custom_check,
            order=5,
        )
        self.v.add_rule(rule)
        self.assertEqual(len(self.v.rules), 11)
        # Check ordering — custom rule has order=5, so it should be first
        self.assertEqual(self.v.rules[0].rule_id, "custom_priority")

    def test_duplicate_rule_id_raises(self):
        rule = ValidationRule(
            rule_id=ValidationRuleId.REQUIRED_FIELDS.value,
            name="Duplicate",
            description="Should fail",
            check=lambda v, t: [],
        )
        with self.assertRaises(ValueError):
            self.v.add_rule(rule)

    def test_disabled_rule_not_run(self):
        self.v.disable_rule(ValidationRuleId.REQUIRED_FIELDS.value)
        result = self.v.validate({})  # Would normally fail required_fields
        req_rejections = [
            f
            for f in result.rejections
            if f.rule_id == ValidationRuleId.REQUIRED_FIELDS.value
        ]
        self.assertEqual(len(req_rejections), 0)

    def test_rules_sorted_by_order(self):
        orders = [r.order for r in self.v.rules]
        self.assertEqual(orders, sorted(orders))


class TestMetrics(unittest.TestCase):
    """Test validation metrics and diagnostics."""

    def setUp(self):
        self.v = TaskValidator()

    def test_metrics_initial_state(self):
        m = self.v.metrics()
        self.assertEqual(m["total_validated"], 0)
        self.assertEqual(m["total_passed"], 0)
        self.assertEqual(m["total_rejected"], 0)

    def test_metrics_after_validation(self):
        self.v.validate(_valid_task())
        self.v.validate(
            _valid_task(
                title="Another unique task",
                description="Unique description for another test",
                bounty=-1,
            )
        )
        m = self.v.metrics()
        self.assertEqual(m["total_validated"], 2)
        self.assertEqual(m["total_passed"], 1)
        self.assertEqual(m["total_rejected"], 1)

    def test_pass_rate(self):
        for i in range(3):
            self.v.validate(
                _valid_task(
                    id=f"pr-{i}",
                    title=f"Pass rate task {i}",
                    description=f"Desc pr {i}",
                )
            )
        self.v.validate(_valid_task(id="pr-bad", title="Bad task", bounty=-1))
        m = self.v.metrics()
        self.assertEqual(m["pass_rate"], 0.75)

    def test_top_rejection_reasons(self):
        for i in range(5):
            self.v.validate(
                _valid_task(
                    id=f"tr-{i}",
                    title=f"Top rejection {i}",
                    description=f"Desc tr {i}",
                    bounty=-1,
                )
            )
        top = self.v.top_rejection_reasons(limit=3)
        self.assertTrue(len(top) > 0)
        # bounty_minimum should be top
        self.assertEqual(top[0][0], ValidationRuleId.BOUNTY_MINIMUM.value)

    def test_status_complete(self):
        self.v.validate(_valid_task())
        s = self.v.status()
        self.assertEqual(s["module"], "#58")
        self.assertEqual(s["component"], "TaskValidator")
        self.assertIn("config", s)
        self.assertIn("rules", s)
        self.assertIn("metrics", s)

    def test_health_check(self):
        h = self.v.health_check()
        self.assertTrue(h["healthy"])
        self.assertEqual(h["component"], "TaskValidator")

    def test_reset_metrics(self):
        self.v.validate(_valid_task())
        self.v.reset_metrics()
        m = self.v.metrics()
        self.assertEqual(m["total_validated"], 0)

    def test_validation_timing(self):
        self.v.validate(_valid_task())
        result = self.v.validate(
            _valid_task(id="t2", title="Timing test", description="Desc timing")
        )
        self.assertTrue(result.duration_ms >= 0)

    def test_result_to_dict(self):
        result = self.v.validate(_valid_task())
        d = result.to_dict()
        self.assertIn("passed", d)
        self.assertIn("findings", d)
        self.assertIn("duration_ms", d)

    def test_finding_to_dict(self):
        f = ValidationFinding(
            rule_id="test",
            severity=ValidationSeverity.WARNING,
            message="Test finding",
            field="test_field",
            value="test_value",
        )
        d = f.to_dict()
        self.assertEqual(d["rule_id"], "test")
        self.assertEqual(d["severity"], "warning")
        self.assertIn("field", d)


class TestPersistence(unittest.TestCase):
    """Test save/load round-trip."""

    def setUp(self):
        self.v = TaskValidator(
            min_bounty=0.50,
            max_bounty=1000.0,
            max_description_length=5000,
            fail_fast=True,
        )

    def test_save_returns_dict(self):
        data = self.v.save()
        self.assertIn("version", data)
        self.assertIn("config", data)
        self.assertIn("metrics", data)
        self.assertEqual(data["version"], 1)

    def test_load_restores_config(self):
        data = self.v.save()
        v2 = TaskValidator.load(data)
        self.assertEqual(v2.min_bounty, 0.50)
        self.assertEqual(v2.max_bounty, 1000.0)
        self.assertEqual(v2.max_description_length, 5000)
        self.assertTrue(v2.fail_fast)

    def test_load_restores_disabled_rules(self):
        self.v.disable_rule(ValidationRuleId.DUPLICATE_DETECTION.value)
        self.v.disable_rule(ValidationRuleId.SKILL_PARSEABLE.value)
        data = self.v.save()
        v2 = TaskValidator.load(data)
        self.assertEqual(len(v2.enabled_rules), 8)

    def test_load_restores_metrics(self):
        self.v.validate(_valid_task())
        self.v.validate(
            _valid_task(
                id="p2", title="Persist test 2", description="Desc p2", bounty=-1
            )
        )
        data = self.v.save()
        v2 = TaskValidator.load(data)
        self.assertEqual(v2._total_validated, 2)
        self.assertEqual(v2._total_passed, 1)
        self.assertEqual(v2._total_rejected, 1)

    def test_round_trip_networks(self):
        data = self.v.save()
        v2 = TaskValidator.load(data)
        self.assertEqual(v2.enabled_networks, self.v.enabled_networks)

    def test_load_empty_data(self):
        """Load with empty dict uses defaults."""
        v2 = TaskValidator.load({})
        self.assertEqual(len(v2.enabled_rules), 10)


class TestFailFast(unittest.TestCase):
    """Test fail-fast mode."""

    def test_fail_fast_stops_on_first_rejection(self):
        v = TaskValidator(fail_fast=True)
        # Task missing everything — but fail_fast should stop after first rule
        result = v.validate({})
        # Should have rejections from first failing rule only
        self.assertFalse(result.passed)
        # In fail-fast mode, we get findings from first rule that rejects
        rule_ids = {f.rule_id for f in result.findings}
        # required_fields (order=10) runs first and rejects
        self.assertIn(ValidationRuleId.REQUIRED_FIELDS.value, rule_ids)
        # bounty_minimum (order=20) should NOT have been reached
        # (though required_fields may produce multiple findings for the same rule)
        self.assertNotIn(ValidationRuleId.BOUNTY_MINIMUM.value, rule_ids)

    def test_non_fail_fast_runs_all_rules(self):
        v = TaskValidator(fail_fast=False)
        result = v.validate({})
        # Should have findings from multiple rules
        rule_ids = {f.rule_id for f in result.findings}
        self.assertIn(ValidationRuleId.REQUIRED_FIELDS.value, rule_ids)
        # Other rules may also produce findings


class TestCustomRules(unittest.TestCase):
    """Test custom validation rules integration."""

    def setUp(self):
        self.v = TaskValidator()

    def test_custom_rule_called(self):
        call_count = {"n": 0}

        def counter_check(validator, task):
            call_count["n"] += 1
            return []

        rule = ValidationRule(
            rule_id="counter",
            name="Counter",
            description="Counts calls",
            check=counter_check,
        )
        self.v.add_rule(rule)
        self.v.validate(_valid_task())
        self.assertEqual(call_count["n"], 1)

    def test_custom_rule_can_reject(self):
        def always_reject(validator, task):
            return [
                ValidationFinding(
                    rule_id="always_reject",
                    severity=ValidationSeverity.REJECT,
                    message="Custom rejection",
                )
            ]

        rule = ValidationRule(
            rule_id="always_reject",
            name="Always Reject",
            description="Rejects everything",
            check=always_reject,
        )
        self.v.add_rule(rule)
        result = self.v.validate(_valid_task())
        self.assertFalse(result.passed)

    def test_custom_rule_exception_handled(self):
        def broken_check(validator, task):
            raise RuntimeError("Something broke")

        rule = ValidationRule(
            rule_id="broken",
            name="Broken",
            description="Raises exceptions",
            check=broken_check,
        )
        self.v.add_rule(rule)
        # Should not raise — exception is caught and becomes a warning
        result = self.v.validate(_valid_task())
        self.assertTrue(result.passed)  # Exception = warning, not rejection
        broken_warnings = [f for f in result.warnings if f.rule_id == "broken"]
        self.assertTrue(len(broken_warnings) > 0)

    def test_custom_rule_with_validator_access(self):
        """Custom rules can access validator config."""

        def config_check(validator, task):
            if float(task.get("bounty", 0)) > validator.max_bounty / 2:
                return [
                    ValidationFinding(
                        rule_id="half_max",
                        severity=ValidationSeverity.WARNING,
                        message=f"Bounty over half of max ({validator.max_bounty})",
                    )
                ]
            return []

        rule = ValidationRule(
            rule_id="half_max",
            name="Half Max Check",
            description="Warns when bounty over half of max",
            check=config_check,
        )
        self.v.add_rule(rule)
        result = self.v.validate(_valid_task(bounty=6000))
        half_warnings = [f for f in result.warnings if f.rule_id == "half_max"]
        self.assertTrue(len(half_warnings) > 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        self.v = TaskValidator()

    def test_none_task_handled(self):
        """Passing None-like values shouldn't crash."""
        result = self.v.validate({})
        self.assertFalse(result.passed)

    def test_extra_fields_ignored(self):
        task = _valid_task(extra_field="extra", another=123)
        result = self.v.validate(task)
        self.assertTrue(result.passed)

    def test_result_reasons_property(self):
        result = self.v.validate(_valid_task(bounty=-1))
        self.assertTrue(len(result.reasons) > 0)
        self.assertIsInstance(result.reasons[0], str)

    def test_result_warning_messages_property(self):
        result = self.v.validate(_valid_task(description="Hi"))
        self.assertTrue(len(result.warning_messages) > 0)

    def test_is_valid_shortcut(self):
        self.assertTrue(self.v.is_valid(_valid_task()))
        self.assertFalse(self.v.is_valid({}))

    def test_repr(self):
        r = repr(self.v)
        self.assertIn("TaskValidator", r)
        self.assertIn("rules=", r)

    def test_concurrent_validations_safe(self):
        """Validate many tasks sequentially — state stays consistent."""
        for i in range(50):
            self.v.validate(
                _valid_task(
                    id=f"conc-{i}",
                    title=f"Concurrent task {i}",
                    description=f"Description for concurrent task {i}",
                )
            )
        m = self.v.metrics()
        self.assertEqual(m["total_validated"], 50)

    def test_none_bounty_with_required_fields_disabled(self):
        """If required_fields is disabled, bounty=None shouldn't crash bounty_minimum."""
        self.v.disable_rule(ValidationRuleId.REQUIRED_FIELDS.value)
        result = self.v.validate({"title": "t", "description": "d"})
        # bounty_minimum should handle None bounty gracefully
        self.assertTrue(True)  # No crash is success

    def test_enable_nonexistent_rule_is_safe(self):
        self.v.enable_rule("nonexistent")  # Should not crash

    def test_disable_nonexistent_rule_is_safe(self):
        self.v.disable_rule("nonexistent")  # Should not crash

    def test_remove_nonexistent_rule_is_safe(self):
        before = len(self.v.rules)
        self.v.remove_rule("nonexistent")
        self.assertEqual(len(self.v.rules), before)


# ──────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
