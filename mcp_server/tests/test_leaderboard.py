"""
Tests for the GET /api/v1/reputation/leaderboard endpoint.

Validates:
- Successful response with mock data
- Empty leaderboard
- limit/offset query parameters
- Response model (LeaderboardEntry) validation
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Must set TESTING before importing api modules (supabase_client needs it)
os.environ.setdefault("TESTING", "1")

import pytest

pytestmark = pytest.mark.core

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.reputation import LeaderboardEntry, get_leaderboard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ENTRIES = [
    {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeee01",
        "display_name": "Alice",
        "reputation_score": 95.2,
        "tier": "expert",
        "tasks_completed": 42,
        "avg_rating": 4.8,
        "rank": 1,
        "badges_count": 5,
    },
    {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeee02",
        "display_name": "Bob",
        "reputation_score": 72.0,
        "tier": "intermediate",
        "tasks_completed": 10,
        "avg_rating": 3.9,
        "rank": 2,
        "badges_count": 1,
    },
    {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeee03",
        "display_name": None,
        "reputation_score": 50.0,
        "tier": None,
        "tasks_completed": 2,
        "avg_rating": None,
        "rank": 3,
        "badges_count": 0,
    },
]


def _mock_supabase_response(data):
    """Build a fake Supabase execute() result."""
    resp = MagicMock()
    resp.data = data
    return resp


def _make_chain(data):
    """Return a mock that supports .table().select().eq().gt().order().order().limit().offset().execute().

    The leaderboard endpoint queries the executors table directly:
        client.table("executors")
            .select(...)
            .eq("status", "active")
            .gt("tasks_completed", 0)
            .order("reputation_score", desc=True)
            .order("tasks_completed", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
    """
    execute = MagicMock(return_value=_mock_supabase_response(data))
    offset_mock = MagicMock()
    offset_mock.execute = execute
    limit_mock = MagicMock()
    limit_mock.offset = MagicMock(return_value=offset_mock)
    order2 = MagicMock()
    order2.limit = MagicMock(return_value=limit_mock)
    order1 = MagicMock()
    order1.order = MagicMock(return_value=order2)
    gt_mock = MagicMock()
    gt_mock.order = MagicMock(return_value=order1)
    eq_mock = MagicMock()
    eq_mock.gt = MagicMock(return_value=gt_mock)
    select = MagicMock()
    select.eq = MagicMock(return_value=eq_mock)
    table = MagicMock()
    table.select = MagicMock(return_value=select)
    client = MagicMock()
    client.table = MagicMock(return_value=table)
    return client, {
        "table": table,
        "select": select,
        "eq": eq_mock,
        "gt": gt_mock,
        "order1": order1,
        "order2": order2,
        "limit": limit_mock,
        "offset": offset_mock,
        "execute": execute,
    }


# ---------------------------------------------------------------------------
# LeaderboardEntry model tests
# ---------------------------------------------------------------------------


class TestLeaderboardEntryModel:
    """Validate Pydantic model for individual entries."""

    def test_full_entry(self):
        entry = LeaderboardEntry(**SAMPLE_ENTRIES[0])
        assert entry.id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeee01"
        assert entry.display_name == "Alice"
        assert entry.reputation_score == 95.2
        assert entry.tier == "expert"
        assert entry.tasks_completed == 42
        assert entry.avg_rating == 4.8
        assert entry.rank == 1
        assert entry.badges_count == 5

    def test_nullable_fields(self):
        entry = LeaderboardEntry(**SAMPLE_ENTRIES[2])
        assert entry.display_name is None
        assert entry.tier is None
        assert entry.avg_rating is None
        assert entry.badges_count == 0

    def test_defaults(self):
        minimal = {
            "id": "00000000-0000-0000-0000-000000000000",
            "reputation_score": 0.0,
            "tasks_completed": 0,
            "rank": 1,
        }
        entry = LeaderboardEntry(**minimal)
        assert entry.display_name is None
        assert entry.tier is None
        assert entry.avg_rating is None
        assert entry.badges_count == 0


# ---------------------------------------------------------------------------
# get_leaderboard endpoint tests
# ---------------------------------------------------------------------------


class TestGetLeaderboard:
    """Tests for the get_leaderboard async endpoint."""

    @pytest.mark.asyncio
    async def test_returns_workers_with_data(self):
        """Successful response with mock entries."""
        client, chain = _make_chain(SAMPLE_ENTRIES)

        with patch("api.reputation.db") as mock_db:
            mock_db.get_client.return_value = client

            result = await get_leaderboard(limit=20, offset=0)

        assert "workers" in result
        assert "count" in result
        assert result["count"] == 3
        assert len(result["workers"]) == 3
        assert result["workers"][0]["display_name"] == "Alice"
        assert result["workers"][1]["rank"] == 2

    @pytest.mark.asyncio
    async def test_empty_leaderboard(self):
        """Empty leaderboard returns zero workers."""
        client, chain = _make_chain([])

        with patch("api.reputation.db") as mock_db:
            mock_db.get_client.return_value = client

            result = await get_leaderboard(limit=20, offset=0)

        assert result["workers"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_none_data_treated_as_empty(self):
        """If Supabase returns None data, treat as empty list."""
        client, _ = _make_chain(None)

        with patch("api.reputation.db") as mock_db:
            mock_db.get_client.return_value = client

            result = await get_leaderboard(limit=10, offset=0)

        assert result["workers"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_limit_parameter_forwarded(self):
        """limit param is forwarded to Supabase .limit() call."""
        client, chain = _make_chain([])

        with patch("api.reputation.db") as mock_db:
            mock_db.get_client.return_value = client

            await get_leaderboard(limit=5, offset=0)

        chain["order2"].limit.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_offset_parameter_forwarded(self):
        """offset param is forwarded to Supabase .offset() call."""
        client, chain = _make_chain([])

        with patch("api.reputation.db") as mock_db:
            mock_db.get_client.return_value = client

            await get_leaderboard(limit=20, offset=10)

        chain["limit"].offset.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_response_entries_are_dicts(self):
        """Each worker in the response must be a plain dict (serializable)."""
        client, _ = _make_chain(SAMPLE_ENTRIES[:1])

        with patch("api.reputation.db") as mock_db:
            mock_db.get_client.return_value = client

            result = await get_leaderboard(limit=20, offset=0)

        worker = result["workers"][0]
        assert isinstance(worker, dict)
        assert set(worker.keys()) == {
            "id",
            "display_name",
            "reputation_score",
            "tier",
            "tasks_completed",
            "avg_rating",
            "rank",
            "badges_count",
        }

    @pytest.mark.asyncio
    async def test_count_matches_workers_length(self):
        """count field must equal the number of returned workers."""
        client, _ = _make_chain(SAMPLE_ENTRIES[:2])

        with patch("api.reputation.db") as mock_db:
            mock_db.get_client.return_value = client

            result = await get_leaderboard(limit=20, offset=0)

        assert result["count"] == len(result["workers"])
