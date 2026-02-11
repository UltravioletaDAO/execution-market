"""
Test script for recon.py module.

Tests for NOW-131 (Task type tiers) and NOW-132 (Execution Market Recon observation tasks).
"""

import pytest
import sys
from pathlib import Path

pytestmark = pytest.mark.dormant

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_types.recon import (
    TaskTier,
    ReconTaskType,
    ReconTaskFactory,
    Location,
)
from decimal import Decimal


def test_task_tier():
    """Test TaskTier enum."""
    print("TaskTier Tests:")
    print(f"  SIMPLE: ${TaskTier.SIMPLE.min_bounty}-${TaskTier.SIMPLE.max_bounty}")
    print(
        f"  STANDARD: ${TaskTier.STANDARD.min_bounty}-${TaskTier.STANDARD.max_bounty}"
    )
    print(f"  PREMIUM: ${TaskTier.PREMIUM.min_bounty}-${TaskTier.PREMIUM.max_bounty}")

    assert TaskTier.SIMPLE.min_bounty == Decimal("1.00")
    assert TaskTier.SIMPLE.max_bounty == Decimal("5.00")
    assert TaskTier.STANDARD.min_bounty == Decimal("10.00")
    assert TaskTier.STANDARD.max_bounty == Decimal("30.00")
    assert TaskTier.PREMIUM.min_bounty == Decimal("50.00")
    assert TaskTier.PREMIUM.max_bounty == Decimal("500.00")
    print("  All tier assertions passed!")


def test_recon_task_type():
    """Test ReconTaskType enum."""
    print("\nReconTaskType Tests:")
    for rt in ReconTaskType:
        print(f"  {rt.value}: {rt.description} (default: {rt.default_tier.value})")

    assert ReconTaskType.STORE_CHECK.default_tier == TaskTier.SIMPLE
    assert ReconTaskType.CROWD_COUNT.default_tier == TaskTier.SIMPLE
    assert ReconTaskType.CONDITION_REPORT.default_tier == TaskTier.STANDARD
    print("  All task type assertions passed!")


def test_bounty_suggestion():
    """Test bounty suggestion calculation."""
    print("\nBounty Suggestions:")
    for rt in ReconTaskType:
        suggestion = ReconTaskFactory.suggest_bounty(rt, "urban")
        print(f"  {rt.value}: ${suggestion.amount} ({suggestion.tier.value})")
        assert suggestion.amount >= suggestion.tier.min_bounty
        assert suggestion.amount <= suggestion.tier.max_bounty
    print("  All bounty suggestions within tier bounds!")


def test_store_check():
    """Test store check task creation."""
    print("\nStore Check Test:")
    loc = Location(40.7128, -74.0060, "Times Square, NYC", 200, "Walmart")
    task = ReconTaskFactory.create_store_check(loc, "Walmart")

    print(f"  Title: {task.title}")
    print(f"  Bounty: ${task.bounty_usd}")
    print(f"  Tier: {task.tier.value}")
    print(f"  Questions: {len(task.questions)}")
    print(f"  Evidence requirements: {len(task.evidence_requirements)}")

    assert task.task_type == ReconTaskType.STORE_CHECK
    assert task.tier == TaskTier.SIMPLE
    assert len(task.questions) == 3
    assert len(task.evidence_requirements) >= 2
    print("  Store check assertions passed!")


def test_crowd_count():
    """Test crowd count task creation."""
    print("\nCrowd Count Test:")
    loc = Location(38.9072, -77.0369, "DMV Office", 100)
    task = ReconTaskFactory.create_crowd_count(loc, "people", "in the main line")

    print(f"  Title: {task.title}")
    print(f"  Bounty: ${task.bounty_usd}")
    print(f"  Count what: {task.metadata['count_what']}")

    assert task.task_type == ReconTaskType.CROWD_COUNT
    assert "people" in task.metadata["count_what"]
    print("  Crowd count assertions passed!")


def test_price_check():
    """Test price check task creation."""
    print("\nPrice Check Test:")
    loc = Location(40.7128, -74.0060, "Times Square, NYC", 200, "Walmart")
    items = ["milk", "bread", "eggs"]
    task = ReconTaskFactory.create_price_check(loc, items, "Walmart")

    print(f"  Title: {task.title}")
    print(f"  Bounty: ${task.bounty_usd}")
    print(f"  Items: {task.metadata['items']}")

    assert task.task_type == ReconTaskType.PRICE_CHECK
    assert len(task.metadata["items"]) == 3
    # Should have more evidence requirements (one per item plus base)
    assert len(task.evidence_requirements) >= 4
    print("  Price check assertions passed!")


def test_availability_check():
    """Test availability check task creation."""
    print("\nAvailability Check Test:")
    loc = Location(40.7128, -74.0060, "Best Buy", 200, "Best Buy")
    task = ReconTaskFactory.create_availability_check(
        loc, "PlayStation 5", "Digital Edition"
    )

    print(f"  Title: {task.title}")
    print(f"  Bounty: ${task.bounty_usd}")
    print(f"  Product: {task.metadata['product']}")

    assert task.task_type == ReconTaskType.AVAILABILITY
    assert "PlayStation 5" in task.metadata["product"]
    print("  Availability check assertions passed!")


def test_condition_report():
    """Test condition report task creation."""
    print("\nCondition Report Test:")
    loc = Location(40.7829, -73.9654, "Central Park", 500, "Playground")
    task = ReconTaskFactory.create_condition_report(loc, "playground equipment")

    print(f"  Title: {task.title}")
    print(f"  Bounty: ${task.bounty_usd}")
    print(f"  Tier: {task.tier.value}")
    print(f"  Aspects: {task.metadata['aspects_to_check']}")

    assert task.task_type == ReconTaskType.CONDITION_REPORT
    assert task.tier == TaskTier.STANDARD  # Condition reports are standard tier
    print("  Condition report assertions passed!")


def test_task_validation():
    """Test task validation."""
    print("\nTask Validation Test:")
    loc = Location(40.7128, -74.0060, "Times Square, NYC", 200, "Walmart")
    task = ReconTaskFactory.create_store_check(loc, "Walmart")

    is_valid, errors = task.validate()
    print(f"  Valid: {is_valid}")
    if errors:
        print(f"  Errors: {errors}")

    assert is_valid, f"Task should be valid, but got errors: {errors}"
    print("  Validation assertions passed!")


def test_location_factors():
    """Test location-based bounty adjustment."""
    print("\nLocation Factor Tests:")
    for loc_type in ["urban_core", "urban", "suburban", "rural", "remote"]:
        suggestion = ReconTaskFactory.suggest_bounty(
            ReconTaskType.STORE_CHECK, location_type=loc_type
        )
        print(f"  {loc_type}: ${suggestion.amount}")

    # Rural and remote should have higher bounties
    urban = ReconTaskFactory.suggest_bounty(ReconTaskType.STORE_CHECK, "urban")
    rural = ReconTaskFactory.suggest_bounty(ReconTaskType.STORE_CHECK, "rural")
    assert rural.amount >= urban.amount
    print("  Location factor assertions passed!")


def test_to_dict():
    """Test serialization to dictionary."""
    print("\nSerialization Test:")
    loc = Location(40.7128, -74.0060, "Times Square, NYC", 200, "Walmart")
    task = ReconTaskFactory.create_store_check(loc, "Walmart")

    task_dict = task.to_dict()
    print(f"  Keys: {list(task_dict.keys())}")

    assert "id" in task_dict
    assert "task_type" in task_dict
    assert "bounty_usd" in task_dict
    assert task_dict["task_type"] == "store_check"
    print("  Serialization assertions passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("EM RECON MODULE TESTS")
    print("=" * 60)

    test_task_tier()
    test_recon_task_type()
    test_bounty_suggestion()
    test_store_check()
    test_crowd_count()
    test_price_check()
    test_availability_check()
    test_condition_report()
    test_task_validation()
    test_location_factors()
    test_to_dict()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
