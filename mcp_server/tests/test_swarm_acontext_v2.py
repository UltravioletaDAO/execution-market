"""
Comprehensive test suite for AcontextAdapter V2 — IRC-based swarm coordination.

Tests cover:
  - Worker locks (acquire, release, TTL expiry, contention, renewal)
  - Task auctions (create, bid, resolve, timeout, tie-breaking)
  - Heartbeat protocol (send, parse, liveness tracking)
  - State sync (build payload, apply payload, merge rules)
  - Message parsing (all IRC command types)
  - Callbacks (intent, release, auction, heartbeat, status)
  - Diagnostics (stats, health)
  - Edge cases (expired locks, duplicate bids, empty auctions)
"""

import asyncio
import json
import time

import pytest

from mcp_server.swarm.acontext_adapter import (
    AcontextAdapter,
    AgentPresence,
    TaskAuction,
    TaskBid,
    WorkerLock,
)


# ──────── Fixtures ────────


@pytest.fixture
def adapter():
    """Create a disconnected adapter for unit testing."""
    return AcontextAdapter(
        irc_host="localhost",
        port=6667,
        channel="#test-swarm",
        nickname="TestAgent-00",
        lock_ttl=300.0,
        auction_timeout=30.0,
    )


@pytest.fixture
def adapter_short_ttl():
    """Adapter with very short TTL for expiry testing."""
    return AcontextAdapter(
        irc_host="localhost",
        port=6667,
        channel="#test-swarm",
        nickname="TestAgent-00",
        lock_ttl=0.01,  # 10ms TTL
        auction_timeout=0.01,
    )


# ──────── WorkerLock Data Class ────────


class TestWorkerLock:
    def test_lock_creation(self):
        lock = WorkerLock(
            worker_id="w1",
            agent_id="a1",
            task_type="data_entry",
            acquired_at=time.time(),
        )
        assert lock.worker_id == "w1"
        assert lock.agent_id == "a1"
        assert lock.task_type == "data_entry"
        assert lock.ttl_seconds == 300.0
        assert lock.renewable is True

    def test_lock_not_expired_when_fresh(self):
        lock = WorkerLock(
            worker_id="w1", agent_id="a1", task_type="t", acquired_at=time.time()
        )
        assert not lock.is_expired
        assert lock.remaining_seconds > 299

    def test_lock_expired_after_ttl(self):
        lock = WorkerLock(
            worker_id="w1",
            agent_id="a1",
            task_type="t",
            acquired_at=time.time() - 301,
            ttl_seconds=300.0,
        )
        assert lock.is_expired
        assert lock.remaining_seconds == 0

    def test_lock_renewal_extends_ttl(self):
        lock = WorkerLock(
            worker_id="w1",
            agent_id="a1",
            task_type="t",
            acquired_at=time.time() - 280,
            ttl_seconds=300.0,
        )
        # Almost expired — 20 seconds left
        assert lock.remaining_seconds < 25
        lock.renew()
        # Now full TTL from renewal
        assert lock.remaining_seconds > 299
        assert not lock.is_expired

    def test_lock_custom_ttl(self):
        lock = WorkerLock(
            worker_id="w1",
            agent_id="a1",
            task_type="t",
            acquired_at=time.time(),
            ttl_seconds=60.0,
        )
        assert lock.ttl_seconds == 60.0
        assert lock.remaining_seconds <= 60.0


# ──────── TaskBid Data Class ────────


class TestTaskBid:
    def test_bid_creation(self):
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.85)
        assert bid.agent_id == "a1"
        assert bid.task_id == "t1"
        assert bid.score == 0.85
        assert bid.timestamp > 0

    def test_bid_timestamp_auto_set(self):
        before = time.time()
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.5)
        after = time.time()
        assert before <= bid.timestamp <= after


# ──────── TaskAuction Data Class ────────


class TestTaskAuction:
    def test_auction_creation(self):
        auction = TaskAuction(task_id="t1", category="simple_action", bounty_usd=0.25)
        assert auction.task_id == "t1"
        assert not auction.closed
        assert auction.winner is None
        assert len(auction.bids) == 0

    def test_add_bid(self):
        auction = TaskAuction(task_id="t1")
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.9)
        assert auction.add_bid(bid) is True
        assert len(auction.bids) == 1

    def test_add_bid_to_closed_auction(self):
        auction = TaskAuction(task_id="t1")
        auction.closed = True
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.9)
        assert auction.add_bid(bid) is False

    def test_add_bid_to_timed_out_auction(self):
        auction = TaskAuction(
            task_id="t1",
            started_at=time.time() - 100,
            timeout_seconds=30,
        )
        bid = TaskBid(agent_id="a1", task_id="t1", score=0.9)
        assert auction.add_bid(bid) is False

    def test_resolve_picks_highest_score(self):
        auction = TaskAuction(task_id="t1")
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=0.5))
        auction.add_bid(TaskBid(agent_id="a2", task_id="t1", score=0.9))
        auction.add_bid(TaskBid(agent_id="a3", task_id="t1", score=0.7))
        winner = auction.resolve()
        assert winner == "a2"
        assert auction.closed is True
        assert auction.winner == "a2"

    def test_resolve_tiebreak_by_timestamp(self):
        """When scores are equal, earlier bid wins."""
        auction = TaskAuction(task_id="t1")
        now = time.time()
        auction.add_bid(
            TaskBid(agent_id="a1", task_id="t1", score=0.8, timestamp=now + 1)
        )
        auction.add_bid(TaskBid(agent_id="a2", task_id="t1", score=0.8, timestamp=now))
        winner = auction.resolve()
        assert winner == "a2"  # Earlier timestamp wins

    def test_resolve_tiebreak_by_agent_id(self):
        """When score and timestamp are equal, alphabetical agent_id wins."""
        auction = TaskAuction(task_id="t1")
        ts = time.time()
        auction.add_bid(
            TaskBid(agent_id="agent_c", task_id="t1", score=0.8, timestamp=ts)
        )
        auction.add_bid(
            TaskBid(agent_id="agent_a", task_id="t1", score=0.8, timestamp=ts)
        )
        auction.add_bid(
            TaskBid(agent_id="agent_b", task_id="t1", score=0.8, timestamp=ts)
        )
        winner = auction.resolve()
        assert winner == "agent_a"  # Alphabetically first

    def test_resolve_empty_auction(self):
        auction = TaskAuction(task_id="t1")
        winner = auction.resolve()
        assert winner is None
        assert auction.closed is True

    def test_is_timed_out(self):
        auction = TaskAuction(
            task_id="t1",
            started_at=time.time() - 31,
            timeout_seconds=30,
        )
        assert auction.is_timed_out

    def test_not_timed_out(self):
        auction = TaskAuction(task_id="t1", timeout_seconds=30)
        assert not auction.is_timed_out


# ──────── AgentPresence Data Class ────────


class TestAgentPresence:
    def test_presence_creation(self):
        p = AgentPresence(agent_id="a1", status="idle", task_count=0)
        assert p.agent_id == "a1"
        assert p.status == "idle"

    def test_is_alive_when_recent(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time())
        assert p.is_alive

    def test_not_alive_when_stale(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time() - 301)
        assert not p.is_alive

    def test_seconds_since_heartbeat(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=time.time() - 60)
        assert 59 <= p.seconds_since_heartbeat <= 61

    def test_seconds_since_heartbeat_never_seen(self):
        p = AgentPresence(agent_id="a1", last_heartbeat=0)
        assert p.seconds_since_heartbeat == float("inf")


# ──────── Worker Lock Operations (Adapter) ────────


class TestWorkerLockOperations:
    @pytest.mark.asyncio
    async def test_acquire_lock(self, adapter):
        result = await adapter.broadcast_intent("a1", "w1", "data_entry")
        assert result is True
        assert not adapter.is_worker_available("w1")
        assert adapter.get_lock_owner("w1") == "a1"

    @pytest.mark.asyncio
    async def test_release_lock(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "data_entry")
        result = await adapter.broadcast_release("w1")
        assert result is True
        assert adapter.is_worker_available("w1")

    @pytest.mark.asyncio
    async def test_release_nonexistent_lock(self, adapter):
        result = await adapter.broadcast_release("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_contention_blocked(self, adapter):
        """Second agent can't lock already-locked worker."""
        await adapter.broadcast_intent("a1", "w1", "data_entry")
        result = await adapter.broadcast_intent("a2", "w1", "moderation")
        assert result is False
        assert adapter.get_lock_owner("w1") == "a1"
        assert adapter.stats.total_contentions == 1

    @pytest.mark.asyncio
    async def test_same_agent_can_relock(self, adapter):
        """Same agent can re-acquire its own lock."""
        await adapter.broadcast_intent("a1", "w1", "data_entry")
        result = await adapter.broadcast_intent("a1", "w1", "moderation")
        assert result is True

    @pytest.mark.asyncio
    async def test_expired_lock_allows_relock(self, adapter_short_ttl):
        """Expired lock can be overtaken by another agent."""
        await adapter_short_ttl.broadcast_intent("a1", "w1", "data_entry")
        # Wait for TTL to expire
        await asyncio.sleep(0.02)
        result = await adapter_short_ttl.broadcast_intent("a2", "w1", "moderation")
        assert result is True
        assert adapter_short_ttl.get_lock_owner("w1") == "a2"

    @pytest.mark.asyncio
    async def test_custom_ttl_per_intent(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "data_entry", ttl=60.0)
        lock = adapter.hiring_locks["w1"]
        assert lock.ttl_seconds == 60.0

    @pytest.mark.asyncio
    async def test_renew_lock_success(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "data_entry")
        result = await adapter.renew_lock("w1", "a1")
        assert result is True

    @pytest.mark.asyncio
    async def test_renew_lock_wrong_agent(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "data_entry")
        result = await adapter.renew_lock("w1", "a2")
        assert result is False

    @pytest.mark.asyncio
    async def test_renew_lock_nonexistent(self, adapter):
        result = await adapter.renew_lock("nonexistent", "a1")
        assert result is False

    def test_is_worker_available_no_lock(self, adapter):
        assert adapter.is_worker_available("w1")

    def test_get_lock_owner_no_lock(self, adapter):
        assert adapter.get_lock_owner("w1") is None

    @pytest.mark.asyncio
    async def test_get_active_locks(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "t1")
        await adapter.broadcast_intent("a2", "w2", "t2")
        locks = adapter.get_active_locks()
        assert len(locks) == 2
        assert "w1" in locks
        assert "w2" in locks

    @pytest.mark.asyncio
    async def test_get_agent_locks(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "t1")
        await adapter.broadcast_intent("a1", "w2", "t2")
        await adapter.broadcast_intent("a2", "w3", "t3")
        locks = adapter.get_agent_locks("a1")
        assert len(locks) == 2
        worker_ids = {l.worker_id for l in locks}
        assert worker_ids == {"w1", "w2"}

    @pytest.mark.asyncio
    async def test_expired_lock_cleaned_on_availability_check(self, adapter_short_ttl):
        await adapter_short_ttl.broadcast_intent("a1", "w1", "t1")
        await asyncio.sleep(0.02)
        assert adapter_short_ttl.is_worker_available("w1")
        assert adapter_short_ttl.stats.expired_locks_cleaned >= 1

    @pytest.mark.asyncio
    async def test_intent_stats_tracking(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "t1")
        await adapter.broadcast_intent("a2", "w2", "t2")
        assert adapter.stats.total_intents == 2

    @pytest.mark.asyncio
    async def test_release_stats_tracking(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "t1")
        await adapter.broadcast_release("w1")
        assert adapter.stats.total_releases == 1


# ──────── Task Auction Operations (Adapter) ────────


class TestTaskAuctionOperations:
    @pytest.mark.asyncio
    async def test_start_auction(self, adapter):
        auction = await adapter.start_auction("t1", "simple_action", 0.25)
        assert auction.task_id == "t1"
        assert auction.category == "simple_action"
        assert auction.bounty_usd == 0.25
        assert adapter.stats.total_auctions == 1

    @pytest.mark.asyncio
    async def test_submit_bid_success(self, adapter):
        await adapter.start_auction("t1")
        result = await adapter.submit_bid("a1", "t1", 0.85)
        assert result is True
        assert adapter.stats.total_bids == 1

    @pytest.mark.asyncio
    async def test_submit_bid_no_auction(self, adapter):
        result = await adapter.submit_bid("a1", "nonexistent", 0.85)
        assert result is False

    @pytest.mark.asyncio
    async def test_resolve_auction_winner(self, adapter):
        await adapter.start_auction("t1")
        await adapter.submit_bid("a1", "t1", 0.5)
        await adapter.submit_bid("a2", "t1", 0.9)
        winner = await adapter.resolve_auction("t1")
        assert winner == "a2"

    @pytest.mark.asyncio
    async def test_resolve_auction_no_bids(self, adapter):
        await adapter.start_auction("t1")
        winner = await adapter.resolve_auction("t1")
        assert winner is None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_auction(self, adapter):
        winner = await adapter.resolve_auction("nonexistent")
        assert winner is None

    @pytest.mark.asyncio
    async def test_get_auction(self, adapter):
        await adapter.start_auction("t1", "data_entry")
        auction = adapter.get_auction("t1")
        assert auction is not None
        assert auction.category == "data_entry"

    @pytest.mark.asyncio
    async def test_get_active_auctions(self, adapter):
        await adapter.start_auction("t1")
        await adapter.start_auction("t2")
        await adapter.start_auction("t3")
        # Resolve one
        await adapter.resolve_auction("t2")
        active = adapter.get_active_auctions()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_auction_custom_timeout(self, adapter):
        auction = await adapter.start_auction("t1", timeout=120.0)
        assert auction.timeout_seconds == 120.0


# ──────── Heartbeat Protocol (Adapter) ────────


class TestHeartbeatProtocol:
    @pytest.mark.asyncio
    async def test_send_heartbeat(self, adapter):
        await adapter.send_heartbeat(status="working", task_count=3)
        assert adapter.stats.total_heartbeats == 1
        presence = adapter.get_agent_status("TestAgent-00")
        assert presence is not None
        assert presence.status == "working"
        assert presence.task_count == 3

    def test_get_online_agents_empty(self, adapter):
        assert len(adapter.get_online_agents()) == 0

    @pytest.mark.asyncio
    async def test_get_online_agents_with_heartbeats(self, adapter):
        await adapter.send_heartbeat(status="idle")
        # Simulate remote agent presence
        adapter.agent_presence["Remote-01"] = AgentPresence(
            agent_id="Remote-01",
            status="working",
            task_count=1,
            last_heartbeat=time.time(),
        )
        online = adapter.get_online_agents()
        assert len(online) == 2

    def test_is_agent_alive_not_present(self, adapter):
        assert not adapter.is_agent_alive("nonexistent")

    @pytest.mark.asyncio
    async def test_is_agent_alive_after_heartbeat(self, adapter):
        await adapter.send_heartbeat()
        assert adapter.is_agent_alive("TestAgent-00")


# ──────── Message Parsing ────────


class TestMessageParsing:
    def test_parse_intent(self, adapter):
        msg = ":Agent2!user@host PRIVMSG #test-swarm :!intent Agent2 worker_xyz moderation"
        adapter._parse_message(msg)
        assert not adapter.is_worker_available("worker_xyz")
        assert adapter.get_lock_owner("worker_xyz") == "Agent2"
        assert adapter.stats.total_intents == 1

    def test_parse_release(self, adapter):
        # First lock, then release
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!intent A1 w1 task1")
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!release w1")
        assert adapter.is_worker_available("w1")
        assert adapter.stats.total_releases == 1

    def test_parse_renew(self, adapter):
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!intent A1 w1 task1")
        old_renewed = adapter.hiring_locks["w1"].last_renewed
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!renew A1 w1")
        assert adapter.hiring_locks["w1"].last_renewed > old_renewed

    def test_parse_heartbeat(self, adapter):
        adapter._parse_message(
            ":Remote-05!u@h PRIVMSG #test-swarm :!heartbeat Remote-05 working 2"
        )
        p = adapter.get_agent_status("Remote-05")
        assert p is not None
        assert p.status == "working"
        assert p.task_count == 2

    def test_parse_heartbeat_updates_existing(self, adapter):
        adapter._parse_message(":R1!u@h PRIVMSG #test-swarm :!heartbeat R1 idle 0")
        adapter._parse_message(":R1!u@h PRIVMSG #test-swarm :!heartbeat R1 working 3")
        p = adapter.get_agent_status("R1")
        assert p.status == "working"
        assert p.task_count == 3

    def test_parse_bid(self, adapter):
        # Need an open auction first
        adapter.auctions["t1"] = TaskAuction(task_id="t1")
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!bid A1 t1 0.9500")
        assert len(adapter.auctions["t1"].bids) == 1
        assert adapter.auctions["t1"].bids[0].score == 0.95
        assert adapter.stats.total_bids == 1

    def test_parse_award(self, adapter):
        adapter.auctions["t1"] = TaskAuction(task_id="t1")
        adapter._parse_message(":Coord!u@h PRIVMSG #test-swarm :!award t1 WinnerAgent")
        assert adapter.auctions["t1"].winner == "WinnerAgent"
        assert adapter.auctions["t1"].closed is True

    def test_parse_auction(self, adapter):
        payload = json.dumps(
            {
                "task_id": "t99",
                "category": "research",
                "bounty_usd": 0.50,
                "timeout": 60,
            }
        )
        adapter._parse_message(f":Coord!u@h PRIVMSG #test-swarm :!auction {payload}")
        assert "t99" in adapter.auctions
        assert adapter.auctions["t99"].category == "research"
        assert adapter.auctions["t99"].bounty_usd == 0.50

    def test_parse_status(self, adapter):
        adapter.agent_presence["A1"] = AgentPresence(agent_id="A1", status="idle")
        adapter._parse_message(":Coord!u@h PRIVMSG #test-swarm :!status A1 cooldown")
        assert adapter.agent_presence["A1"].status == "cooldown"

    def test_parse_sync_state(self, adapter):
        state = json.dumps(
            {
                "locks": {
                    "w1": {
                        "agent": "Remote-01",
                        "task": "data_entry",
                        "remaining": 200,
                    },
                    "w2": {
                        "agent": "Remote-02",
                        "task": "moderation",
                        "remaining": 100,
                    },
                },
                "presence": {
                    "Remote-01": {"status": "working", "tasks": 1},
                },
            }
        )
        adapter._parse_message(f":Peer!u@h PRIVMSG #test-swarm :!sync-state {state}")
        assert "w1" in adapter.hiring_locks
        assert "w2" in adapter.hiring_locks
        assert adapter.hiring_locks["w1"].agent_id == "Remote-01"
        assert "Remote-01" in adapter.agent_presence

    def test_parse_intent_contention(self, adapter):
        """Remote intent on already-locked worker is blocked."""
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!intent A1 w1 task1")
        adapter._parse_message(":A2!u@h PRIVMSG #test-swarm :!intent A2 w1 task2")
        # A1 should still own the lock
        assert adapter.get_lock_owner("w1") == "A1"
        assert adapter.stats.total_contentions == 1

    def test_parse_ignores_non_privmsg(self, adapter):
        adapter._parse_message(":server NOTICE * :Looking up your hostname...")
        assert len(adapter.hiring_locks) == 0

    def test_parse_ignores_wrong_channel(self, adapter):
        adapter._parse_message(":A1!u@h PRIVMSG #other-channel :!intent A1 w1 task1")
        assert adapter.is_worker_available("w1")

    def test_parse_heartbeat_invalid_task_count(self, adapter):
        adapter._parse_message(
            ":R1!u@h PRIVMSG #test-swarm :!heartbeat R1 idle notanumber"
        )
        p = adapter.get_agent_status("R1")
        assert p is not None
        assert p.task_count == 0  # Falls back to 0

    def test_parse_bid_invalid_score(self, adapter):
        adapter.auctions["t1"] = TaskAuction(task_id="t1")
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!bid A1 t1 notanumber")
        # Bid should be rejected (no crash)
        assert len(adapter.auctions["t1"].bids) == 0

    def test_parse_auction_invalid_json(self, adapter):
        adapter._parse_message(":C!u@h PRIVMSG #test-swarm :!auction {invalid-json}")
        # No crash, no auction created
        assert len(adapter.auctions) == 0


# ──────── State Sync ────────


class TestStateSync:
    @pytest.mark.asyncio
    async def test_build_sync_payload(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "data_entry")
        await adapter.send_heartbeat(status="idle")
        payload = adapter._build_sync_payload()
        data = json.loads(payload)
        assert "locks" in data
        assert "presence" in data
        assert "w1" in data["locks"]
        assert "TestAgent-00" in data["presence"]

    def test_apply_sync_doesnt_overwrite_own_locks(self, adapter):
        adapter.hiring_locks["w1"] = WorkerLock(
            worker_id="w1", agent_id="local", task_type="t", acquired_at=time.time()
        )
        state = json.dumps(
            {
                "locks": {"w1": {"agent": "remote", "task": "other"}},
                "presence": {},
            }
        )
        adapter._apply_sync_state(state)
        # Own lock should NOT be overwritten
        assert adapter.hiring_locks["w1"].agent_id == "local"

    def test_apply_sync_adds_new_locks(self, adapter):
        state = json.dumps(
            {
                "locks": {"w_new": {"agent": "remote", "task": "data"}},
                "presence": {},
            }
        )
        adapter._apply_sync_state(state)
        assert "w_new" in adapter.hiring_locks
        assert adapter.hiring_locks["w_new"].agent_id == "remote"

    def test_apply_sync_doesnt_overwrite_own_presence(self, adapter):
        adapter.agent_presence["TestAgent-00"] = AgentPresence(
            agent_id="TestAgent-00", status="working"
        )
        state = json.dumps(
            {
                "locks": {},
                "presence": {"TestAgent-00": {"status": "idle", "tasks": 0}},
            }
        )
        adapter._apply_sync_state(state)
        # Own presence should NOT be overwritten
        assert adapter.agent_presence["TestAgent-00"].status == "working"

    def test_apply_sync_adds_remote_presence(self, adapter):
        state = json.dumps(
            {
                "locks": {},
                "presence": {"Remote-01": {"status": "working", "tasks": 2}},
            }
        )
        adapter._apply_sync_state(state)
        assert "Remote-01" in adapter.agent_presence
        assert adapter.agent_presence["Remote-01"].status == "working"

    def test_apply_sync_invalid_json(self, adapter):
        # Should not crash
        adapter._apply_sync_state("not valid json")
        assert len(adapter.hiring_locks) == 0

    @pytest.mark.asyncio
    async def test_build_sync_excludes_expired_locks(self, adapter_short_ttl):
        await adapter_short_ttl.broadcast_intent("a1", "w1", "t1")
        await asyncio.sleep(0.02)
        payload = adapter_short_ttl._build_sync_payload()
        data = json.loads(payload)
        assert "w1" not in data["locks"]


# ──────── Callback System ────────


class TestCallbacks:
    @pytest.mark.asyncio
    async def test_intent_callback_fires(self, adapter):
        events = []
        adapter.on_intent(lambda evt, data: events.append((evt, data)))
        await adapter.broadcast_intent("a1", "w1", "t1")
        assert len(events) == 1
        assert events[0][0] == "intent"
        assert events[0][1]["agent"] == "a1"

    @pytest.mark.asyncio
    async def test_release_callback_fires(self, adapter):
        events = []
        adapter.on_release(lambda evt, data: events.append((evt, data)))
        await adapter.broadcast_intent("a1", "w1", "t1")
        await adapter.broadcast_release("w1")
        assert len(events) == 1
        assert events[0][0] == "release"

    @pytest.mark.asyncio
    async def test_auction_callback_fires(self, adapter):
        events = []
        adapter.on_auction(lambda evt, data: events.append((evt, data)))
        await adapter.start_auction("t1")
        await adapter.submit_bid("a1", "t1", 0.9)
        await adapter.resolve_auction("t1")
        assert len(events) == 1
        assert events[0][1]["winner"] == "a1"

    @pytest.mark.asyncio
    async def test_heartbeat_callback_fires(self, adapter):
        events = []
        adapter.on_heartbeat(lambda evt, data: events.append((evt, data)))
        adapter._parse_message(":R1!u@h PRIVMSG #test-swarm :!heartbeat R1 idle 0")
        assert len(events) == 1
        assert events[0][1]["agent"] == "R1"

    @pytest.mark.asyncio
    async def test_status_callback_fires(self, adapter):
        events = []
        adapter.on_status_change(lambda evt, data: events.append((evt, data)))
        adapter.agent_presence["A1"] = AgentPresence(agent_id="A1")
        adapter._parse_message(":C!u@h PRIVMSG #test-swarm :!status A1 cooldown")
        assert len(events) == 1
        assert events[0][1]["state"] == "cooldown"

    def test_legacy_register_callback(self, adapter):
        events = []
        adapter.register_callback(lambda evt, data: events.append((evt, data)))
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!intent A1 w1 task1")
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_callback_error_doesnt_crash(self, adapter):
        def bad_callback(evt, data):
            raise ValueError("boom")

        adapter.on_intent(bad_callback)
        # Should not raise
        await adapter.broadcast_intent("a1", "w1", "t1")
        assert adapter.get_lock_owner("w1") == "a1"

    @pytest.mark.asyncio
    async def test_multiple_callbacks(self, adapter):
        events_a = []
        events_b = []
        adapter.on_intent(lambda evt, data: events_a.append(data))
        adapter.on_intent(lambda evt, data: events_b.append(data))
        await adapter.broadcast_intent("a1", "w1", "t1")
        assert len(events_a) == 1
        assert len(events_b) == 1


# ──────── Cleanup and Expiry ────────


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_expired_locks(self, adapter_short_ttl):
        await adapter_short_ttl.broadcast_intent("a1", "w1", "t1")
        await adapter_short_ttl.broadcast_intent("a2", "w2", "t2")
        await asyncio.sleep(0.02)
        adapter_short_ttl._cleanup_expired_locks()
        assert len(adapter_short_ttl.hiring_locks) == 0
        assert adapter_short_ttl.stats.expired_locks_cleaned >= 2

    def test_cleanup_timed_out_auctions(self, adapter):
        # Create auction that started recently, add bid, then make it time out
        auction = TaskAuction(task_id="t1", started_at=time.time(), timeout_seconds=30)
        auction.add_bid(TaskBid(agent_id="a1", task_id="t1", score=0.9))
        assert len(auction.bids) == 1
        # Now make it timed out by adjusting start time
        auction.started_at = time.time() - 100
        adapter.auctions["t1"] = auction
        adapter._cleanup_timed_out_auctions()
        assert adapter.auctions["t1"].closed is True
        assert adapter.auctions["t1"].winner == "a1"


# ──────── Diagnostics ────────


class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_get_stats(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "t1")
        await adapter.broadcast_release("w1")
        stats = adapter.get_stats()
        assert stats["total_intents"] == 1
        assert stats["total_releases"] == 1
        assert stats["active_locks"] == 0
        assert stats["connected"] is False  # Not connected in test

    @pytest.mark.asyncio
    async def test_get_health(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "t1")
        health = adapter.get_health()
        assert health["status"] == "disconnected"
        assert health["active_locks"] == 1
        assert health["contention_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_health_contention_rate(self, adapter):
        await adapter.broadcast_intent("a1", "w1", "t1")
        await adapter.broadcast_intent(
            "a1", "w2", "t2"
        )  # No contention — different worker
        await adapter.broadcast_intent("a2", "w1", "t3")  # Contention on w1
        health = adapter.get_health()
        # 1 contention / 2 successful intents = 0.5
        assert health["contention_rate"] == 0.5

    def test_is_connected_false_by_default(self, adapter):
        assert not adapter.is_connected


# ──────── Connection Properties ────────


class TestConnectionProperties:
    def test_adapter_defaults(self, adapter):
        assert adapter.irc_host == "localhost"
        assert adapter.port == 6667
        assert adapter.channel == "#test-swarm"
        assert adapter.nickname == "TestAgent-00"
        assert adapter.lock_ttl == 300.0
        assert adapter.auction_timeout == 30.0
        assert adapter._running is False

    def test_adapter_custom_params(self):
        a = AcontextAdapter(
            irc_host="irc.example.com",
            port=6697,
            channel="#production",
            nickname="KK-Agent-12",
            lock_ttl=600.0,
            auction_timeout=60.0,
        )
        assert a.irc_host == "irc.example.com"
        assert a.port == 6697
        assert a.channel == "#production"
        assert a.nickname == "KK-Agent-12"
        assert a.lock_ttl == 600.0


# ──────── Integration Scenarios ────────


class TestIntegrationScenarios:
    @pytest.mark.asyncio
    async def test_full_auction_lifecycle(self, adapter):
        """Full auction: create, multi-bid, resolve, verify winner."""
        await adapter.start_auction("task-100", "research", 0.50)
        await adapter.submit_bid("agent-a", "task-100", 0.7)
        await adapter.submit_bid("agent-b", "task-100", 0.95)
        await adapter.submit_bid("agent-c", "task-100", 0.8)
        winner = await adapter.resolve_auction("task-100")
        assert winner == "agent-b"
        assert adapter.stats.total_auctions == 1
        assert adapter.stats.total_bids == 3

    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, adapter):
        """Multiple agents acquire different workers without contention."""
        results = []
        for i in range(5):
            r = await adapter.broadcast_intent(f"agent-{i}", f"worker-{i}", "t")
            results.append(r)
        assert all(results)
        assert len(adapter.get_active_locks()) == 5
        assert adapter.stats.total_contentions == 0

    @pytest.mark.asyncio
    async def test_lock_then_auction(self, adapter):
        """Agent locks a worker, then an auction runs for a task."""
        await adapter.broadcast_intent("a1", "w1", "data_entry")
        await adapter.start_auction("t1", "simple_action", 0.25)
        await adapter.submit_bid("a1", "t1", 0.9)
        await adapter.submit_bid("a2", "t1", 0.5)
        winner = await adapter.resolve_auction("t1")
        assert winner == "a1"
        assert not adapter.is_worker_available("w1")

    @pytest.mark.asyncio
    async def test_sync_then_local_operations(self, adapter):
        """Apply remote state, then perform local operations without conflict."""
        state = json.dumps(
            {
                "locks": {"w_remote": {"agent": "Remote", "task": "t"}},
                "presence": {"Remote": {"status": "working", "tasks": 1}},
            }
        )
        adapter._apply_sync_state(state)
        # Local agent takes a different worker
        result = await adapter.broadcast_intent("TestAgent-00", "w_local", "t")
        assert result is True
        assert len(adapter.hiring_locks) == 2

    @pytest.mark.asyncio
    async def test_sync_contention_with_remote(self, adapter):
        """Can't lock a worker that was synced from remote."""
        state = json.dumps(
            {
                "locks": {"w1": {"agent": "Remote", "task": "t"}},
                "presence": {},
            }
        )
        adapter._apply_sync_state(state)
        result = await adapter.broadcast_intent("Local", "w1", "t2")
        assert result is False
        assert adapter.stats.total_contentions == 1

    def test_full_message_flow_via_parsing(self, adapter):
        """Simulate a complete flow through message parsing only."""
        # Agent 1 joins and sends heartbeat
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!heartbeat A1 idle 0")
        # Agent 1 locks a worker
        adapter._parse_message(
            ":A1!u@h PRIVMSG #test-swarm :!intent A1 worker1 data_entry"
        )
        # Agent 2 tries same worker — contention
        adapter._parse_message(
            ":A2!u@h PRIVMSG #test-swarm :!intent A2 worker1 moderation"
        )
        # Agent 2 takes a different worker
        adapter._parse_message(
            ":A2!u@h PRIVMSG #test-swarm :!intent A2 worker2 moderation"
        )
        # Agent 1 releases
        adapter._parse_message(":A1!u@h PRIVMSG #test-swarm :!release worker1")

        assert adapter.is_worker_available("worker1")
        assert not adapter.is_worker_available("worker2")
        assert adapter.get_lock_owner("worker2") == "A2"
        assert adapter.stats.total_contentions == 1
        assert adapter.is_agent_alive("A1")
