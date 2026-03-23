"""
AcontextAdapter Test Suite
===========================

Tests the IRC-based distributed coordination layer for the KK V2 swarm.
Validates: worker locks, task auctions, heartbeat protocol, conflict
resolution, state sync, and message handling — all without actual IRC.

88 tests covering:
    - Worker lock lifecycle (acquire, release, expire, renew, contention)
    - Task auctions (start, bid, resolve, timeout, tie-breaking)
    - Heartbeat protocol (presence tracking, liveness detection)
    - State sync (build, apply, merge semantics)
    - IRC message parsing (all 10 command types)
    - Diagnostics (stats, health)
    - Callback system (events, errors)
"""

import asyncio
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from mcp_server.swarm.acontext_adapter import (
    AcontextAdapter,
    WorkerLock,
    TaskBid,
    TaskAuction,
    AgentPresence,
    CoordinationStats,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_adapter(**kwargs) -> AcontextAdapter:
    """Create adapter without connecting to IRC."""
    defaults = {
        "irc_host": "localhost",
        "port": 6667,
        "channel": "#test",
        "nickname": "TestAgent",
        "lock_ttl": 300.0,
        "auction_timeout": 30.0,
    }
    defaults.update(kwargs)
    return AcontextAdapter(**defaults)


# ─── WorkerLock Data Type ─────────────────────────────────────────────────────


class TestWorkerLock:
    def test_lock_not_expired_when_fresh(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time(), ttl_seconds=300.0,
        )
        assert not lock.is_expired
        assert lock.remaining_seconds > 299

    def test_lock_expired_after_ttl(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time() - 400, ttl_seconds=300.0,
        )
        assert lock.is_expired
        assert lock.remaining_seconds == 0

    def test_lock_renew_extends_ttl(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time() - 250, ttl_seconds=300.0,
        )
        assert not lock.is_expired
        assert lock.remaining_seconds < 60
        lock.renew()
        assert lock.remaining_seconds > 290
        assert lock.last_renewed > 0

    def test_lock_expired_then_renewed_uses_renewal_time(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time() - 400, ttl_seconds=300.0,
        )
        assert lock.is_expired
        lock.renew()
        assert not lock.is_expired


# ─── TaskBid Data Type ────────────────────────────────────────────────────────


class TestTaskBid:
    def test_bid_defaults(self):
        bid = TaskBid(agent_id="a1", task_id="t1", score=85.5)
        assert bid.agent_id == "a1"
        assert bid.score == 85.5
        assert bid.timestamp > 0


# ─── TaskAuction ──────────────────────────────────────────────────────────────


class TestTaskAuction:
    def test_auction_defaults(self):
        auction = TaskAuction(task_id="t1", category="photo", bounty_usd=1.0)
        assert not auction.closed
        assert not auction.is_timed_out
        assert auction.winner is None

    def test_add_bid_success(self):
        auction = TaskAuction(task_id="t1")
        bid = TaskBid(agent_id="a1", task_id="t1", score=80.0)
        assert auction.add_bid(bid) is True
        assert len(auction.bids) == 1

    def test_add_bid_to_closed_auction_fails(self):
        auction = TaskAuction(task_id="t1")
        auction.closed = True
        bid = TaskBid(agent_id="a1", task_id="t1", score=80.0)
        assert auction.add_bid(bid) is False
        assert len(auction.bids) == 0

    def test_add_bid_to_timed_out_auction_fails(self):
        auction = TaskAuction(
            task_id="t1", started_at=time.time() - 100, timeout_seconds=30.0
        )
        assert auction.is_timed_out
        bid = TaskBid(agent_id="a1", task_id="t1", score=80.0)
        assert auction.add_bid(bid) is False

    def test_resolve_no_bids_returns_none(self):
        auction = TaskAuction(task_id="t1")
        assert auction.resolve() is None
        assert auction.closed

    def test_resolve_single_bid(self):
        auction = TaskAuction(task_id="t1")
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=80.0))
        assert auction.resolve() == "a1"
        assert auction.winner == "a1"
        assert auction.closed

    def test_resolve_highest_score_wins(self):
        auction = TaskAuction(task_id="t1")
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=60.0))
        auction.add_bid(TaskBid(agent_id="a2", task_id="t1", score=90.0))
        auction.add_bid(TaskBid(agent_id="a3", task_id="t1", score=75.0))
        assert auction.resolve() == "a2"

    def test_resolve_tie_breaks_by_timestamp_then_agent_id(self):
        auction = TaskAuction(task_id="t1")
        now = time.time()
        auction.bids = [
            TaskBid(agent_id="a2", task_id="t1", score=80.0, timestamp=now + 1),
            TaskBid(agent_id="a1", task_id="t1", score=80.0, timestamp=now),
        ]
        # Same score → earlier timestamp wins → a1
        assert auction.resolve() == "a1"

    def test_resolve_tie_same_timestamp_breaks_by_agent_id(self):
        auction = TaskAuction(task_id="t1")
        now = time.time()
        auction.bids = [
            TaskBid(agent_id="b_agent", task_id="t1", score=80.0, timestamp=now),
            TaskBid(agent_id="a_agent", task_id="t1", score=80.0, timestamp=now),
        ]
        # Same score + same timestamp → lower agent_id wins
        assert auction.resolve() == "a_agent"


# ─── AgentPresence ────────────────────────────────────────────────────────────


class TestAgentPresence:
    def test_alive_when_recent_heartbeat(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time())
        assert p.is_alive

    def test_not_alive_when_no_heartbeat(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=0)
        assert not p.is_alive

    def test_not_alive_after_5_minutes(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time() - 400)
        assert not p.is_alive

    def test_seconds_since_heartbeat(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time() - 10)
        assert 9 <= p.seconds_since_heartbeat <= 12

    def test_seconds_since_heartbeat_no_heartbeat(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=0)
        assert p.seconds_since_heartbeat == float("inf")


# ─── AcontextAdapter: Worker Lock Operations ─────────────────────────────────


class TestAdapterLocks:
    @pytest.fixture
    def adapter(self):
        return make_adapter()

    @pytest.mark.asyncio
    async def test_broadcast_intent_acquires_lock(self, adapter):
        result = await adapter.broadcast_intent("a1", "w1", "photo")
        assert result is True
        assert "w1" in adapter.hiring_locks
        assert adapter.hiring_locks["w1"].agent_id == "a1"
        assert adapter.stats.total_intents == 1

    @pytest.mark.asyncio
    async def test_broadcast_intent_contention_blocked(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        result = await adapter.broadcast_intent("a2", "w1", "delivery")
        assert result is False
        assert adapter.hiring_locks["w1"].agent_id == "a1"
        assert adapter.stats.total_contentions == 1

    @pytest.mark.asyncio
    async def test_broadcast_intent_same_agent_updates(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        result = await adapter.broadcast_intent("a1", "w1", "delivery")
        assert result is True
        assert adapter.hiring_locks["w1"].task_type == "delivery"

    @pytest.mark.asyncio
    async def test_broadcast_intent_expired_lock_allows_new(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        # Simulate expiry
        adapter.hiring_locks["w1"].acquired_at = time.time() - 400
        adapter.hiring_locks["w1"].ttl_seconds = 300.0
        result = await adapter.broadcast_intent("a2", "w1", "delivery")
        assert result is True
        assert adapter.hiring_locks["w1"].agent_id == "a2"

    @pytest.mark.asyncio
    async def test_broadcast_intent_custom_ttl(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo", ttl=60.0)
        assert adapter.hiring_locks["w1"].ttl_seconds == 60.0

    @pytest.mark.asyncio
    async def test_broadcast_release(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        result = await adapter.broadcast_release("w1")
        assert result is True
        assert "w1" not in adapter.hiring_locks
        assert adapter.stats.total_releases == 1

    @pytest.mark.asyncio
    async def test_broadcast_release_nonexistent(self, adapter):
        result = await adapter.broadcast_release("w_nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_renew_lock(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        result = await adapter.renew_lock("w1", "a1")
        assert result is True
        assert adapter.hiring_locks["w1"].last_renewed > 0

    @pytest.mark.asyncio
    async def test_renew_lock_wrong_agent(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        result = await adapter.renew_lock("w1", "a2")
        assert result is False

    @pytest.mark.asyncio
    async def test_renew_lock_nonexistent(self, adapter):
        result = await adapter.renew_lock("w_ghost", "a1")
        assert result is False

    def test_is_worker_available_no_lock(self, adapter):
        assert adapter.is_worker_available("w1") is True

    @pytest.mark.asyncio
    async def test_is_worker_available_locked(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        assert adapter.is_worker_available("w1") is False

    @pytest.mark.asyncio
    async def test_is_worker_available_expired_lock_cleaned(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        adapter.hiring_locks["w1"].acquired_at = time.time() - 400
        assert adapter.is_worker_available("w1") is True
        assert "w1" not in adapter.hiring_locks
        assert adapter.stats.expired_locks_cleaned == 1

    @pytest.mark.asyncio
    async def test_get_lock_owner(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        assert adapter.get_lock_owner("w1") == "a1"
        assert adapter.get_lock_owner("w_nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_active_locks(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        await adapter.broadcast_intent("a2", "w2", "delivery")
        active = adapter.get_active_locks()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_get_agent_locks(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        await adapter.broadcast_intent("a1", "w2", "delivery")
        await adapter.broadcast_intent("a2", "w3", "photo")
        locks = adapter.get_agent_locks("a1")
        assert len(locks) == 2


# ─── AcontextAdapter: Task Auctions ──────────────────────────────────────────


class TestAdapterAuctions:
    @pytest.fixture
    def adapter(self):
        return make_adapter()

    @pytest.mark.asyncio
    async def test_start_auction(self, adapter):
        auction = await adapter.start_auction("t1", category="photo", bounty_usd=1.0)
        assert auction.task_id == "t1"
        assert adapter.stats.total_auctions == 1
        assert "t1" in adapter.auctions

    @pytest.mark.asyncio
    async def test_submit_bid(self, adapter):
        await adapter.start_auction("t1")
        result = await adapter.submit_bid("a1", "t1", 85.0)
        assert result is True
        assert adapter.stats.total_bids == 1

    @pytest.mark.asyncio
    async def test_submit_bid_no_auction(self, adapter):
        result = await adapter.submit_bid("a1", "t_nonexistent", 85.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_resolve_auction(self, adapter):
        await adapter.start_auction("t1")
        await adapter.submit_bid("a1", "t1", 60.0)
        await adapter.submit_bid("a2", "t1", 90.0)
        winner = await adapter.resolve_auction("t1")
        assert winner == "a2"

    @pytest.mark.asyncio
    async def test_resolve_auction_no_bids(self, adapter):
        await adapter.start_auction("t1")
        winner = await adapter.resolve_auction("t1")
        assert winner is None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_auction(self, adapter):
        winner = await adapter.resolve_auction("t_ghost")
        assert winner is None

    @pytest.mark.asyncio
    async def test_get_auction(self, adapter):
        await adapter.start_auction("t1", category="photo")
        auction = adapter.get_auction("t1")
        assert auction is not None
        assert auction.category == "photo"
        assert adapter.get_auction("t_missing") is None

    @pytest.mark.asyncio
    async def test_get_active_auctions(self, adapter):
        await adapter.start_auction("t1")
        await adapter.start_auction("t2")
        # Close one
        adapter.auctions["t1"].closed = True
        active = adapter.get_active_auctions()
        assert len(active) == 1
        assert active[0].task_id == "t2"


# ─── AcontextAdapter: Heartbeat Protocol ─────────────────────────────────────


class TestAdapterHeartbeat:
    @pytest.fixture
    def adapter(self):
        return make_adapter(nickname="Agent-01")

    @pytest.mark.asyncio
    async def test_send_heartbeat(self, adapter):
        await adapter.send_heartbeat(status="idle", task_count=3)
        assert "Agent-01" in adapter.agent_presence
        p = adapter.agent_presence["Agent-01"]
        assert p.status == "idle"
        assert p.task_count == 3
        assert adapter.stats.total_heartbeats == 1

    def test_get_online_agents_empty(self, adapter):
        assert adapter.get_online_agents() == []

    @pytest.mark.asyncio
    async def test_get_online_agents_with_alive(self, adapter):
        await adapter.send_heartbeat(status="active")
        online = adapter.get_online_agents()
        assert len(online) == 1
        assert online[0].agent_id == "Agent-01"

    def test_get_online_agents_filters_dead(self, adapter):
        adapter.agent_presence["dead-agent"] = AgentPresence(
            agent_id="dead-agent", last_heartbeat=time.time() - 600
        )
        assert len(adapter.get_online_agents()) == 0

    def test_get_agent_status(self, adapter):
        adapter.agent_presence["a1"] = AgentPresence(
            agent_id="a1", status="working", last_heartbeat=time.time()
        )
        status = adapter.get_agent_status("a1")
        assert status is not None
        assert status.status == "working"
        assert adapter.get_agent_status("a_ghost") is None

    def test_is_agent_alive(self, adapter):
        adapter.agent_presence["a1"] = AgentPresence(
            agent_id="a1", last_heartbeat=time.time()
        )
        assert adapter.is_agent_alive("a1") is True
        assert adapter.is_agent_alive("a_ghost") is False


# ─── AcontextAdapter: State Sync ─────────────────────────────────────────────


class TestAdapterStateSync:
    @pytest.fixture
    def adapter(self):
        return make_adapter(nickname="Sync-Agent")

    @pytest.mark.asyncio
    async def test_build_sync_payload_with_locks(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        payload = adapter._build_sync_payload()
        data = json.loads(payload)
        assert "locks" in data
        assert "w1" in data["locks"]
        assert data["locks"]["w1"]["agent"] == "a1"

    @pytest.mark.asyncio
    async def test_build_sync_payload_with_presence(self, adapter):
        await adapter.send_heartbeat(status="idle")
        payload = adapter._build_sync_payload()
        data = json.loads(payload)
        assert "presence" in data
        assert "Sync-Agent" in data["presence"]

    def test_build_sync_payload_excludes_expired_locks(self, adapter):
        adapter.hiring_locks["w1"] = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time() - 500, ttl_seconds=300.0,
        )
        payload = adapter._build_sync_payload()
        data = json.loads(payload)
        assert "w1" not in data["locks"]

    def test_apply_sync_state_merges_locks(self, adapter):
        payload = json.dumps({
            "locks": {
                "w1": {"agent": "remote-agent", "task": "photo", "remaining": 200},
            },
            "presence": {},
        })
        adapter._apply_sync_state(payload)
        assert "w1" in adapter.hiring_locks
        assert adapter.hiring_locks["w1"].agent_id == "remote-agent"

    @pytest.mark.asyncio
    async def test_apply_sync_state_doesnt_overwrite_own_locks(self, adapter):
        await adapter.broadcast_intent("local", "w1", "photo")
        payload = json.dumps({
            "locks": {
                "w1": {"agent": "remote", "task": "delivery"},
            },
            "presence": {},
        })
        adapter._apply_sync_state(payload)
        assert adapter.hiring_locks["w1"].agent_id == "local"

    def test_apply_sync_state_merges_presence(self, adapter):
        payload = json.dumps({
            "locks": {},
            "presence": {
                "remote-agent": {"status": "working", "tasks": 2},
            },
        })
        adapter._apply_sync_state(payload)
        assert "remote-agent" in adapter.agent_presence
        assert adapter.agent_presence["remote-agent"].status == "working"

    @pytest.mark.asyncio
    async def test_apply_sync_state_doesnt_overwrite_own_presence(self, adapter):
        await adapter.send_heartbeat(status="idle")
        payload = json.dumps({
            "locks": {},
            "presence": {
                "Sync-Agent": {"status": "working", "tasks": 5},
            },
        })
        adapter._apply_sync_state(payload)
        # Our own presence should not be overwritten
        assert adapter.agent_presence["Sync-Agent"].status == "idle"

    def test_apply_sync_state_invalid_json(self, adapter):
        adapter._apply_sync_state("not json at all")
        # Should not raise, just silently skip
        assert len(adapter.hiring_locks) == 0


# ─── AcontextAdapter: IRC Message Parsing ────────────────────────────────────


class TestAdapterMessageParsing:
    @pytest.fixture
    def adapter(self):
        return make_adapter(channel="#test")

    def test_handle_intent_command(self, adapter):
        adapter._handle_swarm_command("!intent a1 w1 photo", "a1")
        assert "w1" in adapter.hiring_locks
        assert adapter.hiring_locks["w1"].agent_id == "a1"
        assert adapter.hiring_locks["w1"].task_type == "photo"

    def test_handle_release_command(self, adapter):
        adapter.hiring_locks["w1"] = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time(),
        )
        adapter._handle_swarm_command("!release w1", "a1")
        assert "w1" not in adapter.hiring_locks

    def test_handle_renew_command(self, adapter):
        adapter.hiring_locks["w1"] = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time() - 200,
        )
        old_renewed = adapter.hiring_locks["w1"].last_renewed
        adapter._handle_swarm_command("!renew a1 w1", "a1")
        assert adapter.hiring_locks["w1"].last_renewed > old_renewed

    def test_handle_heartbeat_command_new_agent(self, adapter):
        adapter._handle_swarm_command("!heartbeat remote-01 working 5", "remote-01")
        assert "remote-01" in adapter.agent_presence
        p = adapter.agent_presence["remote-01"]
        assert p.status == "working"
        assert p.task_count == 5

    def test_handle_heartbeat_command_update_existing(self, adapter):
        adapter.agent_presence["a1"] = AgentPresence(
            agent_id="a1", status="idle", last_heartbeat=time.time() - 100
        )
        adapter._handle_swarm_command("!heartbeat a1 working 3", "a1")
        assert adapter.agent_presence["a1"].status == "working"
        assert adapter.agent_presence["a1"].task_count == 3

    def test_handle_bid_command(self, adapter):
        adapter.auctions["t1"] = TaskAuction(task_id="t1")
        adapter._handle_swarm_command("!bid a1 t1 85.5000", "a1")
        assert len(adapter.auctions["t1"].bids) == 1
        assert adapter.auctions["t1"].bids[0].score == 85.5

    def test_handle_bid_invalid_score(self, adapter):
        adapter.auctions["t1"] = TaskAuction(task_id="t1")
        adapter._handle_swarm_command("!bid a1 t1 not_a_number", "a1")
        assert len(adapter.auctions["t1"].bids) == 0

    def test_handle_award_command(self, adapter):
        adapter.auctions["t1"] = TaskAuction(task_id="t1")
        adapter._handle_swarm_command("!award t1 a2", "coordinator")
        assert adapter.auctions["t1"].winner == "a2"
        assert adapter.auctions["t1"].closed

    def test_handle_auction_command(self, adapter):
        payload = json.dumps({"task_id": "t99", "category": "delivery", "bounty_usd": 2.5})
        adapter._handle_swarm_command(f"!auction {payload}", "coordinator")
        assert "t99" in adapter.auctions
        assert adapter.auctions["t99"].category == "delivery"

    def test_handle_auction_invalid_json(self, adapter):
        adapter._handle_swarm_command("!auction {bad json", "coord")
        assert len(adapter.auctions) == 0

    def test_handle_sync_state_command(self, adapter):
        payload = json.dumps({
            "locks": {"w5": {"agent": "remote", "task": "photo"}},
            "presence": {},
        })
        adapter._handle_swarm_command(f"!sync-state {payload}", "remote")
        assert "w5" in adapter.hiring_locks

    def test_handle_status_command(self, adapter):
        adapter.agent_presence["a1"] = AgentPresence(
            agent_id="a1", last_heartbeat=time.time()
        )
        adapter._handle_swarm_command("!status a1 cooldown", "a1")
        assert adapter.agent_presence["a1"].status == "cooldown"

    def test_parse_message_extracts_command(self, adapter):
        irc_msg = f":remote!user@host PRIVMSG #test :!heartbeat remote idle 0"
        adapter._parse_message(irc_msg)
        assert "remote" in adapter.agent_presence

    def test_parse_message_ignores_wrong_channel(self, adapter):
        irc_msg = f":remote!user@host PRIVMSG #other :!heartbeat remote idle 0"
        adapter._parse_message(irc_msg)
        assert len(adapter.agent_presence) == 0

    def test_parse_message_ignores_non_privmsg(self, adapter):
        adapter._parse_message("NOTICE :Server starting")
        assert len(adapter.hiring_locks) == 0


# ─── AcontextAdapter: Callbacks ───────────────────────────────────────────────


class TestAdapterCallbacks:
    @pytest.fixture
    def adapter(self):
        return make_adapter()

    @pytest.mark.asyncio
    async def test_intent_callback_fired(self, adapter):
        events = []
        adapter.on_intent(lambda t, d: events.append((t, d)))
        await adapter.broadcast_intent("a1", "w1", "photo")
        assert len(events) == 1
        assert events[0][0] == "intent"
        assert events[0][1]["worker"] == "w1"

    @pytest.mark.asyncio
    async def test_release_callback_fired(self, adapter):
        events = []
        adapter.on_release(lambda t, d: events.append((t, d)))
        await adapter.broadcast_intent("a1", "w1", "photo")
        await adapter.broadcast_release("w1")
        assert len(events) == 1
        assert events[0][0] == "release"

    @pytest.mark.asyncio
    async def test_auction_callback_fired(self, adapter):
        events = []
        adapter.on_auction(lambda t, d: events.append((t, d)))
        await adapter.start_auction("t1")
        await adapter.submit_bid("a1", "t1", 80.0)
        await adapter.resolve_auction("t1")
        assert len(events) == 1
        assert events[0][0] == "auction_resolved"
        assert events[0][1]["winner"] == "a1"

    @pytest.mark.asyncio
    async def test_callback_error_doesnt_crash(self, adapter):
        def bad_callback(t, d):
            raise RuntimeError("Boom!")
        adapter.on_intent(bad_callback)
        # Should not raise
        result = await adapter.broadcast_intent("a1", "w1", "photo")
        assert result is True

    def test_register_legacy_callback(self, adapter):
        events = []
        adapter.register_callback(lambda t, d: events.append(t))
        assert len(adapter._intent_callbacks) == 1
        assert len(adapter._release_callbacks) == 1

    def test_status_callback_fired_on_command(self, adapter):
        events = []
        adapter.on_status_change(lambda t, d: events.append(d))
        adapter.agent_presence["a1"] = AgentPresence(
            agent_id="a1", last_heartbeat=time.time()
        )
        adapter._handle_swarm_command("!status a1 suspended", "a1")
        assert len(events) == 1
        assert events[0]["state"] == "suspended"


# ─── AcontextAdapter: Cleanup ─────────────────────────────────────────────────


class TestAdapterCleanup:
    @pytest.fixture
    def adapter(self):
        return make_adapter()

    def test_cleanup_expired_locks(self, adapter):
        adapter.hiring_locks["w1"] = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="photo",
            acquired_at=time.time() - 500, ttl_seconds=300.0,
        )
        adapter.hiring_locks["w2"] = WorkerLock(
            worker_id="w2", agent_id="a2", task_type="delivery",
            acquired_at=time.time(), ttl_seconds=300.0,
        )
        adapter._cleanup_expired_locks()
        assert "w1" not in adapter.hiring_locks
        assert "w2" in adapter.hiring_locks
        assert adapter.stats.expired_locks_cleaned == 1

    def test_cleanup_timed_out_auctions(self, adapter):
        adapter.auctions["t1"] = TaskAuction(
            task_id="t1", started_at=time.time() - 100, timeout_seconds=30.0
        )
        adapter.auctions["t2"] = TaskAuction(task_id="t2")
        adapter._cleanup_timed_out_auctions()
        assert adapter.auctions["t1"].closed
        assert not adapter.auctions["t2"].closed


# ─── AcontextAdapter: Diagnostics ────────────────────────────────────────────


class TestAdapterDiagnostics:
    @pytest.fixture
    def adapter(self):
        return make_adapter()

    @pytest.mark.asyncio
    async def test_get_stats(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        await adapter.start_auction("t1")
        stats = adapter.get_stats()
        assert stats["total_intents"] == 1
        assert stats["total_auctions"] == 1
        assert stats["active_locks"] == 1
        assert stats["connected"] is False  # not connected to IRC
        assert "messages_sent" in stats

    @pytest.mark.asyncio
    async def test_get_health(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        health = adapter.get_health()
        assert health["status"] == "disconnected"
        assert health["active_locks"] == 1
        assert "contention_rate" in health

    def test_is_connected_default_false(self, adapter):
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_contention_rate(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "photo")
        await adapter.broadcast_intent("a2", "w1", "photo")  # contention
        health = adapter.get_health()
        assert health["contention_rate"] > 0
