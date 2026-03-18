"""
Tests for AcontextAdapter V2 — Enhanced IRC Coordination
"""

import time
import asyncio
import pytest
from mcp_server.swarm.acontext_adapter import (
    AcontextAdapter,
    WorkerLock,
    TaskBid,
    TaskAuction,
    AgentPresence,
    CoordinationStats,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def adapter():
    return AcontextAdapter(
        irc_host="localhost", port=6667,
        channel="#test-channel", nickname="TestAgent",
        lock_ttl=60.0, auction_timeout=5.0,
    )


@pytest.fixture
def two_adapters():
    """Two adapters simulating different agents."""
    a1 = AcontextAdapter(
        irc_host="localhost", port=6667,
        channel="#test", nickname="Agent-01",
        lock_ttl=60.0, auction_timeout=5.0,
    )
    a2 = AcontextAdapter(
        irc_host="localhost", port=6667,
        channel="#test", nickname="Agent-02",
        lock_ttl=60.0, auction_timeout=5.0,
    )
    return a1, a2


# ──────────────────────────────────────────────────────────────
# WorkerLock
# ──────────────────────────────────────────────────────────────


class TestWorkerLock:
    def test_lock_creation(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1",
            task_type="research", acquired_at=time.time(),
            ttl_seconds=60.0,
        )
        assert lock.worker_id == "w1"
        assert lock.agent_id == "a1"
        assert not lock.is_expired

    def test_lock_expiry(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1",
            task_type="research",
            acquired_at=time.time() - 120,
            ttl_seconds=60.0,
        )
        assert lock.is_expired

    def test_lock_not_expired(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1",
            task_type="research", acquired_at=time.time(),
            ttl_seconds=60.0,
        )
        assert not lock.is_expired

    def test_lock_remaining_seconds(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1",
            task_type="research", acquired_at=time.time(),
            ttl_seconds=60.0,
        )
        assert 55 < lock.remaining_seconds <= 60

    def test_lock_expired_remaining_zero(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1",
            task_type="research",
            acquired_at=time.time() - 120,
            ttl_seconds=60.0,
        )
        assert lock.remaining_seconds == 0

    def test_lock_renewal(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1",
            task_type="research",
            acquired_at=time.time() - 50,
            ttl_seconds=60.0,
        )
        # Almost expired
        assert lock.remaining_seconds < 15
        lock.renew()
        # After renewal, full TTL from now
        assert lock.remaining_seconds > 55

    def test_lock_renewal_updates_timestamp(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1",
            task_type="research", acquired_at=time.time() - 30,
            ttl_seconds=60.0,
        )
        old_renewed = lock.last_renewed
        lock.renew()
        assert lock.last_renewed > old_renewed


# ──────────────────────────────────────────────────────────────
# TaskBid & TaskAuction
# ──────────────────────────────────────────────────────────────


class TestTaskAuction:
    def test_auction_creation(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        assert auction.task_id == "t1"
        assert not auction.closed
        assert len(auction.bids) == 0

    def test_add_bid(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.85)
        assert auction.add_bid(bid)
        assert len(auction.bids) == 1

    def test_add_bid_to_closed_auction(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        auction.closed = True
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.85)
        assert not auction.add_bid(bid)

    def test_resolve_single_bid(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=0.85))
        winner = auction.resolve()
        assert winner == "a1"
        assert auction.closed

    def test_resolve_highest_score_wins(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=0.70))
        auction.add_bid(TaskBid(agent_id="a2", task_id="t1", score=0.95))
        auction.add_bid(TaskBid(agent_id="a3", task_id="t1", score=0.80))
        winner = auction.resolve()
        assert winner == "a2"

    def test_resolve_tie_by_timestamp(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        now = time.time()
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=0.85, timestamp=now + 1))
        auction.add_bid(TaskBid(agent_id="a2", task_id="t1", score=0.85, timestamp=now))
        winner = auction.resolve()
        assert winner == "a2"  # Earlier timestamp wins

    def test_resolve_tie_by_agent_id(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        now = time.time()
        auction.add_bid(TaskBid(agent_id="a2", task_id="t1", score=0.85, timestamp=now))
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=0.85, timestamp=now))
        winner = auction.resolve()
        assert winner == "a1"  # Lower agent_id wins (deterministic)

    def test_resolve_empty_auction(self):
        auction = TaskAuction(task_id="t1", category="research", bounty_usd=2.0)
        winner = auction.resolve()
        assert winner is None
        assert auction.closed

    def test_auction_timeout(self):
        auction = TaskAuction(
            task_id="t1", category="research", bounty_usd=2.0,
            started_at=time.time() - 60, timeout_seconds=30.0,
        )
        assert auction.is_timed_out

    def test_auction_not_timed_out(self):
        auction = TaskAuction(
            task_id="t1", category="research", bounty_usd=2.0,
            timeout_seconds=30.0,
        )
        assert not auction.is_timed_out

    def test_bid_rejected_after_timeout(self):
        auction = TaskAuction(
            task_id="t1", category="research", bounty_usd=2.0,
            started_at=time.time() - 60, timeout_seconds=30.0,
        )
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.85)
        assert not auction.add_bid(bid)


# ──────────────────────────────────────────────────────────────
# AgentPresence
# ──────────────────────────────────────────────────────────────


class TestAgentPresence:
    def test_presence_alive(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time())
        assert p.is_alive

    def test_presence_dead(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time() - 600)
        assert not p.is_alive

    def test_presence_never_heartbeated(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=0)
        assert not p.is_alive

    def test_seconds_since_heartbeat(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time() - 30)
        assert 25 < p.seconds_since_heartbeat < 35


# ──────────────────────────────────────────────────────────────
# Intent Broadcasting (TTL Locks)
# ──────────────────────────────────────────────────────────────


class TestIntentBroadcasting:
    @pytest.mark.asyncio
    async def test_broadcast_intent_creates_lock(self, adapter):
        result = await adapter.broadcast_intent("a1", "worker-1", "research")
        assert result is True
        assert not adapter.is_worker_available("worker-1")
        assert adapter.get_lock_owner("worker-1") == "a1"

    @pytest.mark.asyncio
    async def test_broadcast_intent_contention_blocked(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        result = await adapter.broadcast_intent("a2", "worker-1", "data_entry")
        assert result is False
        assert adapter.get_lock_owner("worker-1") == "a1"  # a1 still owns it

    @pytest.mark.asyncio
    async def test_broadcast_intent_same_agent_allowed(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        result = await adapter.broadcast_intent("a1", "worker-1", "research")
        assert result is True  # Same agent can re-lock

    @pytest.mark.asyncio
    async def test_broadcast_intent_expired_lock_overridden(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        # Manually expire the lock
        adapter.hiring_locks["worker-1"].acquired_at = time.time() - 120
        adapter.hiring_locks["worker-1"].ttl_seconds = 60
        result = await adapter.broadcast_intent("a2", "worker-1", "data_entry")
        assert result is True
        assert adapter.get_lock_owner("worker-1") == "a2"

    @pytest.mark.asyncio
    async def test_broadcast_release(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        assert not adapter.is_worker_available("worker-1")
        result = await adapter.broadcast_release("worker-1")
        assert result is True
        assert adapter.is_worker_available("worker-1")

    @pytest.mark.asyncio
    async def test_release_nonexistent_lock(self, adapter):
        result = await adapter.broadcast_release("worker-999")
        assert result is False

    @pytest.mark.asyncio
    async def test_lock_renewal(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        lock = adapter.hiring_locks["worker-1"]
        old_renewed = lock.last_renewed

        result = await adapter.renew_lock("worker-1", "a1")
        assert result is True
        assert lock.last_renewed > old_renewed

    @pytest.mark.asyncio
    async def test_lock_renewal_wrong_agent(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        result = await adapter.renew_lock("worker-1", "a2")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_agent_locks(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        await adapter.broadcast_intent("a1", "worker-2", "data_entry")
        await adapter.broadcast_intent("a2", "worker-3", "research")
        locks = adapter.get_agent_locks("a1")
        assert len(locks) == 2

    @pytest.mark.asyncio
    async def test_contention_stats_tracked(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        await adapter.broadcast_intent("a2", "worker-1", "data_entry")  # Blocked
        assert adapter.stats.total_contentions == 1

    @pytest.mark.asyncio
    async def test_worker_available_expired_auto_cleanup(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        adapter.hiring_locks["worker-1"].acquired_at = time.time() - 120
        adapter.hiring_locks["worker-1"].ttl_seconds = 60
        assert adapter.is_worker_available("worker-1")  # Auto-cleaned


# ──────────────────────────────────────────────────────────────
# Task Auctions
# ──────────────────────────────────────────────────────────────


class TestTaskAuctions:
    @pytest.mark.asyncio
    async def test_start_auction(self, adapter):
        auction = await adapter.start_auction("t1", "research", 2.0)
        assert auction.task_id == "t1"
        assert not auction.closed

    @pytest.mark.asyncio
    async def test_submit_bid(self, adapter):
        await adapter.start_auction("t1", "research", 2.0)
        result = await adapter.submit_bid("a1", "t1", 0.85)
        assert result is True
        assert len(adapter.auctions["t1"].bids) == 1

    @pytest.mark.asyncio
    async def test_bid_nonexistent_auction(self, adapter):
        result = await adapter.submit_bid("a1", "nonexistent", 0.85)
        assert result is False

    @pytest.mark.asyncio
    async def test_resolve_auction(self, adapter):
        await adapter.start_auction("t1", "research", 2.0)
        await adapter.submit_bid("a1", "t1", 0.70)
        await adapter.submit_bid("a2", "t1", 0.95)
        winner = await adapter.resolve_auction("t1")
        assert winner == "a2"

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_auction(self, adapter):
        result = await adapter.resolve_auction("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_auctions(self, adapter):
        await adapter.start_auction("t1", "research", 2.0)
        await adapter.start_auction("t2", "data_entry", 1.0)
        active = adapter.get_active_auctions()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_resolved_auction_not_active(self, adapter):
        await adapter.start_auction("t1", "research", 2.0)
        await adapter.submit_bid("a1", "t1", 0.85)
        await adapter.resolve_auction("t1")
        active = adapter.get_active_auctions()
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_auction_stats_tracked(self, adapter):
        await adapter.start_auction("t1", "research", 2.0)
        await adapter.submit_bid("a1", "t1", 0.85)
        assert adapter.stats.total_auctions == 1
        assert adapter.stats.total_bids == 1


# ──────────────────────────────────────────────────────────────
# Heartbeat Protocol
# ──────────────────────────────────────────────────────────────


class TestHeartbeat:
    @pytest.mark.asyncio
    async def test_send_heartbeat(self, adapter):
        await adapter.send_heartbeat(status="idle", task_count=0)
        assert adapter.nickname in adapter.agent_presence
        p = adapter.agent_presence[adapter.nickname]
        assert p.status == "idle"
        assert p.is_alive

    @pytest.mark.asyncio
    async def test_heartbeat_updates_presence(self, adapter):
        await adapter.send_heartbeat(status="idle", task_count=0)
        await adapter.send_heartbeat(status="working", task_count=2)
        p = adapter.agent_presence[adapter.nickname]
        assert p.status == "working"
        assert p.task_count == 2

    def test_get_online_agents_empty(self, adapter):
        assert len(adapter.get_online_agents()) == 0

    @pytest.mark.asyncio
    async def test_get_online_agents(self, adapter):
        await adapter.send_heartbeat(status="idle")
        assert len(adapter.get_online_agents()) == 1

    def test_is_agent_alive_false(self, adapter):
        assert not adapter.is_agent_alive("unknown-agent")

    @pytest.mark.asyncio
    async def test_heartbeat_stats(self, adapter):
        await adapter.send_heartbeat()
        assert adapter.stats.total_heartbeats == 1


# ──────────────────────────────────────────────────────────────
# Message Parsing
# ──────────────────────────────────────────────────────────────


class TestMessageParsing:
    def test_parse_intent(self, adapter):
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!intent Agent2 worker_xyz moderation"
        adapter._parse_message(msg)
        assert not adapter.is_worker_available("worker_xyz")
        assert adapter.get_lock_owner("worker_xyz") == "Agent2"

    def test_parse_release(self, adapter):
        adapter.hiring_locks["worker_xyz"] = WorkerLock(
            worker_id="worker_xyz", agent_id="Agent2",
            task_type="moderation", acquired_at=time.time(),
        )
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!release worker_xyz"
        adapter._parse_message(msg)
        assert adapter.is_worker_available("worker_xyz")

    def test_parse_heartbeat(self, adapter):
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!heartbeat Agent2 working 3"
        adapter._parse_message(msg)
        assert "Agent2" in adapter.agent_presence
        p = adapter.agent_presence["Agent2"]
        assert p.status == "working"
        assert p.task_count == 3

    def test_parse_bid(self, adapter):
        adapter.auctions["t1"] = TaskAuction(task_id="t1", category="research")
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!bid Agent2 t1 0.8500"
        adapter._parse_message(msg)
        assert len(adapter.auctions["t1"].bids) == 1

    def test_parse_award(self, adapter):
        adapter.auctions["t1"] = TaskAuction(task_id="t1", category="research")
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!award t1 Agent2"
        adapter._parse_message(msg)
        assert adapter.auctions["t1"].winner == "Agent2"
        assert adapter.auctions["t1"].closed

    def test_parse_renew(self, adapter):
        adapter.hiring_locks["worker-1"] = WorkerLock(
            worker_id="worker-1", agent_id="Agent2",
            task_type="research", acquired_at=time.time() - 50,
            ttl_seconds=60.0,
        )
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!renew Agent2 worker-1"
        adapter._parse_message(msg)
        assert adapter.hiring_locks["worker-1"].last_renewed > 0

    def test_parse_status(self, adapter):
        adapter.agent_presence["Agent2"] = AgentPresence(agent_id="Agent2")
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!status Agent2 degraded"
        adapter._parse_message(msg)
        assert adapter.agent_presence["Agent2"].status == "degraded"

    def test_ignore_non_channel_messages(self, adapter):
        msg = ":Agent2!user@host PRIVMSG #other-channel :!intent Agent2 worker_xyz moderation"
        adapter._parse_message(msg)
        assert adapter.is_worker_available("worker_xyz")

    def test_ignore_non_privmsg(self, adapter):
        msg = ":Agent2!user@host NOTICE #test-channel :!intent Agent2 worker_xyz moderation"
        adapter._parse_message(msg)
        assert adapter.is_worker_available("worker_xyz")

    def test_parse_intent_contention_remote(self, adapter):
        """Remote intent on already-locked worker should be rejected."""
        adapter.hiring_locks["worker-1"] = WorkerLock(
            worker_id="worker-1", agent_id="Agent1",
            task_type="research", acquired_at=time.time(),
        )
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!intent Agent2 worker-1 data_entry"
        adapter._parse_message(msg)
        # Agent1 should still own the lock
        assert adapter.get_lock_owner("worker-1") == "Agent1"
        assert adapter.stats.total_contentions >= 1


# ──────────────────────────────────────────────────────────────
# State Sync
# ──────────────────────────────────────────────────────────────


class TestStateSync:
    @pytest.mark.asyncio
    async def test_build_sync_payload(self, adapter):
        await adapter.broadcast_intent("a1", "worker-1", "research")
        await adapter.send_heartbeat(status="idle")
        payload = adapter._build_sync_payload()
        data = __import__("json").loads(payload)
        assert "locks" in data
        assert "presence" in data
        assert "worker-1" in data["locks"]

    def test_apply_sync_state(self, adapter):
        payload = __import__("json").dumps({
            "locks": {
                "worker-1": {"agent": "remote-a1", "task": "research", "remaining": 200}
            },
            "presence": {
                "remote-a1": {"status": "working", "tasks": 2}
            }
        })
        adapter._apply_sync_state(payload)
        assert not adapter.is_worker_available("worker-1")
        assert "remote-a1" in adapter.agent_presence

    def test_sync_doesnt_overwrite_own_locks(self, adapter):
        adapter.hiring_locks["worker-1"] = WorkerLock(
            worker_id="worker-1", agent_id="local-agent",
            task_type="research", acquired_at=time.time(),
        )
        payload = __import__("json").dumps({
            "locks": {
                "worker-1": {"agent": "remote-agent", "task": "data_entry"}
            }
        })
        adapter._apply_sync_state(payload)
        assert adapter.get_lock_owner("worker-1") == "local-agent"

    def test_sync_invalid_json(self, adapter):
        adapter._apply_sync_state("not valid json")
        # Should not crash


# ──────────────────────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────────────────────


class TestCleanup:
    def test_cleanup_expired_locks(self, adapter):
        adapter.hiring_locks["worker-1"] = WorkerLock(
            worker_id="worker-1", agent_id="a1",
            task_type="research",
            acquired_at=time.time() - 120,
            ttl_seconds=60.0,
        )
        adapter.hiring_locks["worker-2"] = WorkerLock(
            worker_id="worker-2", agent_id="a2",
            task_type="data_entry",
            acquired_at=time.time(),
            ttl_seconds=60.0,
        )
        adapter._cleanup_expired_locks()
        assert "worker-1" not in adapter.hiring_locks
        assert "worker-2" in adapter.hiring_locks
        assert adapter.stats.expired_locks_cleaned >= 1

    def test_cleanup_timed_out_auctions(self, adapter):
        adapter.auctions["t1"] = TaskAuction(
            task_id="t1", category="research",
            started_at=time.time() - 60, timeout_seconds=30.0,
        )
        adapter.auctions["t1"].add_bid(TaskBid(agent_id="a1", task_id="t1", score=0.8))
        adapter._cleanup_timed_out_auctions()
        assert adapter.auctions["t1"].closed


# ──────────────────────────────────────────────────────────────
# Diagnostics
# ──────────────────────────────────────────────────────────────


class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_get_stats(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "research")
        await adapter.broadcast_release("w1")
        stats = adapter.get_stats()
        assert stats["total_intents"] == 1
        assert stats["total_releases"] == 1
        assert stats["connected"] is False

    @pytest.mark.asyncio
    async def test_get_health(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "research")
        health = adapter.get_health()
        assert health["active_locks"] == 1
        assert health["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_contention_rate(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "research")
        await adapter.broadcast_intent("a2", "w1", "data_entry")  # Contention
        await adapter.broadcast_intent("a2", "w2", "research")
        health = adapter.get_health()
        assert health["contention_rate"] > 0


# ──────────────────────────────────────────────────────────────
# Callbacks
# ──────────────────────────────────────────────────────────────


class TestCallbacks:
    @pytest.mark.asyncio
    async def test_intent_callback(self, adapter):
        events = []
        adapter.on_intent(lambda event_type, data: events.append((event_type, data)))
        await adapter.broadcast_intent("a1", "w1", "research")
        assert len(events) == 1
        assert events[0][0] == "intent"

    @pytest.mark.asyncio
    async def test_release_callback(self, adapter):
        events = []
        adapter.on_release(lambda event_type, data: events.append((event_type, data)))
        await adapter.broadcast_intent("a1", "w1", "research")
        await adapter.broadcast_release("w1")
        assert len(events) == 1
        assert events[0][0] == "release"

    @pytest.mark.asyncio
    async def test_heartbeat_callback(self, adapter):
        events = []
        adapter.on_heartbeat(lambda event_type, data: events.append((event_type, data)))
        # Simulate receiving a heartbeat message
        msg = f":Agent2!user@host PRIVMSG {adapter.channel} :!heartbeat Agent2 idle 0"
        adapter._parse_message(msg)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_legacy_callback(self, adapter):
        events = []
        adapter.register_callback(lambda event_type, data: events.append(event_type))
        await adapter.broadcast_intent("a1", "w1", "research")
        assert "intent" in events

    @pytest.mark.asyncio
    async def test_callback_error_doesnt_crash(self, adapter):
        def bad_callback(event_type, data):
            raise ValueError("Callback error!")

        adapter.on_intent(bad_callback)
        # Should not raise
        result = await adapter.broadcast_intent("a1", "w1", "research")
        assert result is True


# ──────────────────────────────────────────────────────────────
# Connection Properties
# ──────────────────────────────────────────────────────────────


class TestConnection:
    def test_not_connected_by_default(self, adapter):
        assert not adapter.is_connected

    def test_default_properties(self, adapter):
        assert adapter.irc_host == "localhost"
        assert adapter.port == 6667
        assert adapter.channel == "#test-channel"
        assert adapter.nickname == "TestAgent"
