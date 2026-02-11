"""
Tests for timestamp verification module.
"""

import pytest
from datetime import datetime, timedelta, UTC

pytestmark = pytest.mark.infrastructure
from verification.checks.timestamp import (
    check_timestamp,
)


class TestCheckTimestamp:
    """Tests for timestamp verification."""

    def test_valid_recent_timestamp(self):
        """Photo taken just now should pass."""
        now = datetime.now(UTC)
        photo_time = now - timedelta(seconds=30)

        result = check_timestamp(
            photo_timestamp=photo_time, submission_timestamp=now, max_age_minutes=5
        )

        assert result.is_valid
        assert result.age_seconds is not None
        assert result.age_seconds < 60
        assert result.reason is None

    def test_photo_too_old(self):
        """Photo older than max_age should fail."""
        now = datetime.now(UTC)
        photo_time = now - timedelta(minutes=10)

        result = check_timestamp(
            photo_timestamp=photo_time, submission_timestamp=now, max_age_minutes=5
        )

        assert not result.is_valid
        assert "too old" in result.reason

    def test_missing_timestamp(self):
        """Missing photo timestamp should fail."""
        result = check_timestamp(photo_timestamp=None, max_age_minutes=5)

        assert not result.is_valid
        assert result.photo_timestamp is None
        assert "timestamp metadata" in result.reason

    def test_future_timestamp_rejected(self):
        """Photo from the future should fail."""
        now = datetime.now(UTC)
        photo_time = now + timedelta(minutes=10)

        result = check_timestamp(
            photo_timestamp=photo_time,
            submission_timestamp=now,
            max_age_minutes=5,
            allow_future=False,
        )

        assert not result.is_valid
        assert "future" in result.reason

    def test_small_future_offset_allowed(self):
        """Small future offset (timezone) should pass when allowed."""
        now = datetime.now(UTC)
        photo_time = now + timedelta(minutes=2)  # 2 minutes in future

        result = check_timestamp(
            photo_timestamp=photo_time,
            submission_timestamp=now,
            max_age_minutes=5,
            allow_future=True,
        )

        # 2 minutes is within 5-minute tolerance
        assert result.is_valid

    def test_large_future_offset_rejected(self):
        """Large future offset should fail even when allow_future=True."""
        now = datetime.now(UTC)
        photo_time = now + timedelta(minutes=10)  # 10 minutes in future

        result = check_timestamp(
            photo_timestamp=photo_time,
            submission_timestamp=now,
            max_age_minutes=5,
            allow_future=True,  # Still should fail
        )

        assert not result.is_valid
        assert "future" in result.reason

    def test_photo_before_task_start(self):
        """Photo taken before task assigned should fail."""
        now = datetime.now(UTC)
        task_start = now - timedelta(minutes=10)
        photo_time = now - timedelta(minutes=15)  # Before task started

        result = check_timestamp(
            photo_timestamp=photo_time,
            submission_timestamp=now,
            task_start=task_start,
            max_age_minutes=20,
        )

        assert not result.is_valid
        assert "before task" in result.reason

    def test_photo_after_deadline(self):
        """Photo taken after deadline should fail."""
        now = datetime.now(UTC)
        deadline = now - timedelta(minutes=5)
        photo_time = now - timedelta(minutes=2)  # After deadline

        result = check_timestamp(
            photo_timestamp=photo_time,
            submission_timestamp=now,
            task_deadline=deadline,
            max_age_minutes=10,
        )

        assert not result.is_valid
        assert "after task deadline" in result.reason

    def test_valid_within_task_window(self):
        """Photo within valid task window should pass."""
        now = datetime.now(UTC)
        task_start = now - timedelta(minutes=30)
        deadline = now + timedelta(minutes=30)
        photo_time = now - timedelta(minutes=2)

        result = check_timestamp(
            photo_timestamp=photo_time,
            submission_timestamp=now,
            task_start=task_start,
            task_deadline=deadline,
            max_age_minutes=5,
        )

        assert result.is_valid

    def test_timezone_naive_timestamps(self):
        """Timezone-naive timestamps should be handled."""
        now = datetime.now()  # Naive
        photo_time = now - timedelta(minutes=2)

        result = check_timestamp(
            photo_timestamp=photo_time, submission_timestamp=now, max_age_minutes=5
        )

        # Should work, timestamps get UTC attached
        assert result.is_valid

    def test_custom_max_age(self):
        """Custom max_age should be respected."""
        now = datetime.now(UTC)
        photo_time = now - timedelta(minutes=3)

        # With 2 minute max, should fail
        result = check_timestamp(
            photo_timestamp=photo_time, submission_timestamp=now, max_age_minutes=2
        )
        assert not result.is_valid

        # With 5 minute max, should pass
        result = check_timestamp(
            photo_timestamp=photo_time, submission_timestamp=now, max_age_minutes=5
        )
        assert result.is_valid

    def test_result_contains_all_timestamps(self):
        """Result should contain all timestamp information."""
        now = datetime.now(UTC)
        task_start = now - timedelta(hours=1)
        deadline = now + timedelta(hours=1)
        photo_time = now - timedelta(minutes=2)

        result = check_timestamp(
            photo_timestamp=photo_time,
            submission_timestamp=now,
            task_start=task_start,
            task_deadline=deadline,
            max_age_minutes=5,
        )

        assert result.photo_timestamp == photo_time.replace(tzinfo=UTC)
        assert result.submission_timestamp is not None
        assert result.task_start is not None
        assert result.task_deadline is not None
