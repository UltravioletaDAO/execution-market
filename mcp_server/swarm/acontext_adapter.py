"""
Acontext Adapter for MeshRelay (IRC) Coordination — V2
========================================================

Provides distributed coordination for the KarmaCadabra V2 swarm via IRC.
Allows 24 agents to synchronize hiring intents, avoid collisions, and
coordinate task assignment without a central lock server.

V2 capabilities:
1. **TTL-based locks** — Locks auto-expire to prevent deadlocks from crashed agents
2. **Lock renewal** — Active agents renew locks to maintain ownership
3. **Task auctions** — Agents bid on tasks, best scorer wins
4. **Heartbeat protocol** — Agents broadcast presence for liveness detection
5. **Conflict resolution** — Deterministic tie-breaking when agents collide
6. **State sync** — New agents catch up via state snapshots on join
7. **Message batching** — Reduce IRC traffic via batched updates

Protocol commands (sent as PRIVMSG to channel):
    !intent <agent_id> <worker_id> <task_type>  — Lock a worker
    !release <worker_id>                         — Release a lock
    !heartbeat <agent_id> <status> <task_count>  — Presence ping
    !bid <agent_id> <task_id> <score>           — Submit task bid
    !award <task_id> <winner_agent_id>          — Announce auction winner
    !sync-request <agent_id>                    — Request state snapshot
    !sync-state <json_payload>                  — Respond with state
    !status <agent_id> <state>                  — Agent state change

No external dependencies beyond asyncio.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class WorkerLock:
    """A worker hiring lock with TTL."""
    worker_id: str
    agent_id: str
    task_type: str
    acquired_at: float
    ttl_seconds: float = 300.0     # Default 5-minute TTL
    last_renewed: float = 0.0
    renewable: bool = True

    @property
    def is_expired(self) -> bool:
        effective_time = max(self.acquired_at, self.last_renewed)
        return (time.time() - effective_time) > self.ttl_seconds

    @property
    def remaining_seconds(self) -> float:
        effective_time = max(self.acquired_at, self.last_renewed)
        return max(0, self.ttl_seconds - (time.time() - effective_time))

    def renew(self):
        self.last_renewed = time.time()


@dataclass
class TaskBid:
    """A bid on a task auction."""
    agent_id: str
    task_id: str
    score: float            # Higher = better match
    timestamp: float = field(default_factory=time.time)


@dataclass
class TaskAuction:
    """An active task auction."""
    task_id: str
    category: str = ""
    bounty_usd: float = 0.0
    started_at: float = field(default_factory=time.time)
    timeout_seconds: float = 30.0
    bids: list[TaskBid] = field(default_factory=list)
    winner: Optional[str] = None
    closed: bool = False

    @property
    def is_timed_out(self) -> bool:
        return (time.time() - self.started_at) > self.timeout_seconds

    def add_bid(self, bid: TaskBid) -> bool:
        """Add a bid. Returns False if auction is closed."""
        if self.closed or self.is_timed_out:
            return False
        self.bids.append(bid)
        return True

    def resolve(self) -> Optional[str]:
        """Resolve auction. Returns winner agent_id or None."""
        if not self.bids:
            self.closed = True
            return None

        # Sort by score (desc), then by timestamp (asc) for tie-breaking,
        # then by agent_id (asc) for deterministic resolution
        sorted_bids = sorted(
            self.bids,
            key=lambda b: (-b.score, b.timestamp, b.agent_id)
        )
        self.winner = sorted_bids[0].agent_id
        self.closed = True
        return self.winner


@dataclass
class AgentPresence:
    """Tracked agent presence from heartbeats."""
    agent_id: str
    status: str = "unknown"      # idle, working, cooldown, etc.
    task_count: int = 0
    last_heartbeat: float = 0.0
    first_seen: float = field(default_factory=time.time)

    @property
    def is_alive(self) -> bool:
        """Agent seen in last 5 minutes."""
        return (time.time() - self.last_heartbeat) < 300

    @property
    def seconds_since_heartbeat(self) -> float:
        return time.time() - self.last_heartbeat if self.last_heartbeat > 0 else float("inf")


@dataclass
class CoordinationStats:
    """Statistics for monitoring coordination health."""
    total_intents: int = 0
    total_releases: int = 0
    total_contentions: int = 0     # Lock collisions
    total_auctions: int = 0
    total_bids: int = 0
    total_heartbeats: int = 0
    total_sync_requests: int = 0
    expired_locks_cleaned: int = 0
    messages_sent: int = 0
    messages_received: int = 0


# ──────────────────────────────────────────────────────────────
# Acontext Adapter V2
# ──────────────────────────────────────────────────────────────


class AcontextAdapter:
    """
    Synchronizes agent hiring intents and swarm state via MeshRelay IRC.

    V2: TTL-based locks, task auctions, heartbeat protocol, conflict resolution.
    """

    DEFAULT_LOCK_TTL = 300.0         # 5 minutes
    DEFAULT_AUCTION_TIMEOUT = 30.0   # 30 seconds
    HEARTBEAT_INTERVAL = 60.0        # 60 seconds
    CLEANUP_INTERVAL = 30.0          # Check for expired locks every 30s
    RECONNECT_DELAY = 10.0           # Seconds between reconnect attempts
    MAX_RECONNECT_ATTEMPTS = 5

    def __init__(self, irc_host: str = "meshrelay.local", port: int = 6667,
                 channel: str = "#em-swarm", nickname: str = "EM-Agent-00",
                 lock_ttl: float = DEFAULT_LOCK_TTL,
                 auction_timeout: float = DEFAULT_AUCTION_TIMEOUT):
        self.irc_host = irc_host
        self.port = port
        self.channel = channel
        self.nickname = nickname
        self.lock_ttl = lock_ttl
        self.auction_timeout = auction_timeout

        # State
        self.hiring_locks: Dict[str, WorkerLock] = {}       # worker_id -> lock
        self.auctions: Dict[str, TaskAuction] = {}           # task_id -> auction
        self.agent_presence: Dict[str, AgentPresence] = {}   # agent_id -> presence
        self.stats = CoordinationStats()

        # Callbacks
        self._intent_callbacks: List[Callable] = []
        self._release_callbacks: List[Callable] = []
        self._auction_callbacks: List[Callable] = []
        self._heartbeat_callbacks: List[Callable] = []
        self._status_callbacks: List[Callable] = []

        # Connection
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0

    # ──────── Connection ────────

    async def connect(self):
        """Connect to MeshRelay IRC network."""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.irc_host, self.port
            )
            self._send(f"NICK {self.nickname}")
            self._send(f"USER {self.nickname} 0 * :EM Swarm Agent V2")
            self._send(f"JOIN {self.channel}")
            self._running = True
            self._reconnect_attempts = 0
            logger.info(f"[Acontext] Connected to {self.irc_host}:{self.port} as {self.nickname}")

            # Start background tasks
            asyncio.create_task(self._listen())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Request state sync from peers
            await self._request_sync()

        except Exception as e:
            logger.error(f"[Acontext] Failed to connect: {e}")
            self._running = False

    async def disconnect(self):
        """Gracefully disconnect."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._writer:
            self._send(f"QUIT :Shutting down")
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    async def _reconnect(self):
        """Attempt reconnection with backoff."""
        while self._reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            self._reconnect_attempts += 1
            delay = self.RECONNECT_DELAY * self._reconnect_attempts
            logger.info(f"[Acontext] Reconnecting in {delay}s (attempt {self._reconnect_attempts})")
            await asyncio.sleep(delay)
            try:
                await self.connect()
                return
            except Exception as e:
                logger.error(f"[Acontext] Reconnect failed: {e}")
        logger.error("[Acontext] Max reconnect attempts reached")

    def _send(self, message: str):
        """Send raw IRC message."""
        if self._writer:
            self._writer.write(f"{message}\r\n".encode())
            self.stats.messages_sent += 1

    def _send_channel(self, message: str):
        """Send a PRIVMSG to the coordination channel."""
        self._send(f"PRIVMSG {self.channel} :{message}")

    @property
    def is_connected(self) -> bool:
        return self._running and self._writer is not None

    # ──────── Worker Locks (TTL-based) ────────

    async def broadcast_intent(self, agent_id: str, worker_id: str,
                                task_type: str, ttl: Optional[float] = None) -> bool:
        """
        Announce intention to hire a worker.
        Returns False if worker is already locked by another agent.
        """
        # Check if already locked by someone else
        if worker_id in self.hiring_locks:
            existing = self.hiring_locks[worker_id]
            if not existing.is_expired and existing.agent_id != agent_id:
                self.stats.total_contentions += 1
                logger.warning(
                    f"[Acontext] Contention: {agent_id} wants {worker_id} "
                    f"but locked by {existing.agent_id}"
                )
                return False
            # Expired lock — clean it up
            if existing.is_expired:
                self.stats.expired_locks_cleaned += 1

        lock = WorkerLock(
            worker_id=worker_id,
            agent_id=agent_id,
            task_type=task_type,
            acquired_at=time.time(),
            ttl_seconds=ttl or self.lock_ttl,
        )
        self.hiring_locks[worker_id] = lock
        self.stats.total_intents += 1

        if self._running:
            self._send_channel(f"!intent {agent_id} {worker_id} {task_type}")

        for cb in self._intent_callbacks:
            try:
                cb("intent", {"agent": agent_id, "worker": worker_id, "task": task_type})
            except Exception:
                pass

        return True

    async def broadcast_release(self, worker_id: str) -> bool:
        """Release a hiring lock."""
        if worker_id not in self.hiring_locks:
            return False

        del self.hiring_locks[worker_id]
        self.stats.total_releases += 1

        if self._running:
            self._send_channel(f"!release {worker_id}")

        for cb in self._release_callbacks:
            try:
                cb("release", {"worker": worker_id})
            except Exception:
                pass

        return True

    async def renew_lock(self, worker_id: str, agent_id: str) -> bool:
        """Renew an existing lock (extend TTL)."""
        lock = self.hiring_locks.get(worker_id)
        if lock and lock.agent_id == agent_id and lock.renewable:
            lock.renew()
            if self._running:
                self._send_channel(f"!renew {agent_id} {worker_id}")
            return True
        return False

    def is_worker_available(self, worker_id: str) -> bool:
        """Check if worker is currently available (not locked or lock expired)."""
        if worker_id not in self.hiring_locks:
            return True
        lock = self.hiring_locks[worker_id]
        if lock.is_expired:
            del self.hiring_locks[worker_id]
            self.stats.expired_locks_cleaned += 1
            return True
        return False

    def get_lock_owner(self, worker_id: str) -> Optional[str]:
        """Get the agent that holds the lock, or None."""
        lock = self.hiring_locks.get(worker_id)
        if lock and not lock.is_expired:
            return lock.agent_id
        return None

    def get_active_locks(self) -> Dict[str, WorkerLock]:
        """Get all non-expired locks."""
        self._cleanup_expired_locks()
        return dict(self.hiring_locks)

    def get_agent_locks(self, agent_id: str) -> list[WorkerLock]:
        """Get all locks held by a specific agent."""
        return [l for l in self.hiring_locks.values()
                if l.agent_id == agent_id and not l.is_expired]

    # ──────── Task Auctions ────────

    async def start_auction(self, task_id: str, category: str = "",
                            bounty_usd: float = 0.0,
                            timeout: Optional[float] = None) -> TaskAuction:
        """Start a task auction. Agents can bid within the timeout."""
        auction = TaskAuction(
            task_id=task_id,
            category=category,
            bounty_usd=bounty_usd,
            timeout_seconds=timeout or self.auction_timeout,
        )
        self.auctions[task_id] = auction
        self.stats.total_auctions += 1

        if self._running:
            payload = json.dumps({
                "task_id": task_id, "category": category,
                "bounty_usd": bounty_usd, "timeout": auction.timeout_seconds,
            })
            self._send_channel(f"!auction {payload}")

        return auction

    async def submit_bid(self, agent_id: str, task_id: str,
                          score: float) -> bool:
        """Submit a bid on an active auction."""
        auction = self.auctions.get(task_id)
        if not auction:
            return False

        bid = TaskBid(agent_id=agent_id, task_id=task_id, score=score)
        success = auction.add_bid(bid)

        if success:
            self.stats.total_bids += 1
            if self._running:
                self._send_channel(f"!bid {agent_id} {task_id} {score:.4f}")

        return success

    async def resolve_auction(self, task_id: str) -> Optional[str]:
        """Resolve an auction and return the winner."""
        auction = self.auctions.get(task_id)
        if not auction:
            return None

        winner = auction.resolve()

        if winner and self._running:
            self._send_channel(f"!award {task_id} {winner}")

        for cb in self._auction_callbacks:
            try:
                cb("auction_resolved", {"task_id": task_id, "winner": winner,
                                         "bid_count": len(auction.bids)})
            except Exception:
                pass

        return winner

    def get_auction(self, task_id: str) -> Optional[TaskAuction]:
        """Get an auction by task ID."""
        return self.auctions.get(task_id)

    def get_active_auctions(self) -> list[TaskAuction]:
        """Get all open (non-closed, non-timed-out) auctions."""
        return [a for a in self.auctions.values()
                if not a.closed and not a.is_timed_out]

    # ──────── Heartbeat Protocol ────────

    async def send_heartbeat(self, status: str = "idle", task_count: int = 0):
        """Broadcast presence heartbeat."""
        now = time.time()
        # Update own presence
        self.agent_presence[self.nickname] = AgentPresence(
            agent_id=self.nickname,
            status=status,
            task_count=task_count,
            last_heartbeat=now,
        )
        self.stats.total_heartbeats += 1

        if self._running:
            self._send_channel(f"!heartbeat {self.nickname} {status} {task_count}")

    def get_online_agents(self) -> list[AgentPresence]:
        """Get agents that have heartbeated in the last 5 minutes."""
        return [p for p in self.agent_presence.values() if p.is_alive]

    def get_agent_status(self, agent_id: str) -> Optional[AgentPresence]:
        """Get presence info for a specific agent."""
        return self.agent_presence.get(agent_id)

    def is_agent_alive(self, agent_id: str) -> bool:
        """Check if an agent has heartbeated recently."""
        presence = self.agent_presence.get(agent_id)
        return presence.is_alive if presence else False

    # ──────── Callback Registration ────────

    def on_intent(self, callback: Callable):
        """Register callback for intent events."""
        self._intent_callbacks.append(callback)

    def on_release(self, callback: Callable):
        """Register callback for release events."""
        self._release_callbacks.append(callback)

    def on_auction(self, callback: Callable):
        """Register callback for auction events."""
        self._auction_callbacks.append(callback)

    def on_heartbeat(self, callback: Callable):
        """Register callback for heartbeat events."""
        self._heartbeat_callbacks.append(callback)

    def on_status_change(self, callback: Callable):
        """Register callback for agent status changes."""
        self._status_callbacks.append(callback)

    # Legacy compatibility
    def register_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register a callback for all swarm events (legacy API)."""
        self._intent_callbacks.append(callback)
        self._release_callbacks.append(callback)

    # ──────── State Sync ────────

    async def _request_sync(self):
        """Request state sync from peers when joining."""
        if self._running:
            self._send_channel(f"!sync-request {self.nickname}")
            self.stats.total_sync_requests += 1

    def _build_sync_payload(self) -> str:
        """Build current state as JSON for sync responses."""
        locks = {}
        for wid, lock in self.hiring_locks.items():
            if not lock.is_expired:
                locks[wid] = {
                    "agent": lock.agent_id,
                    "task": lock.task_type,
                    "remaining": lock.remaining_seconds,
                }

        presence = {}
        for aid, p in self.agent_presence.items():
            if p.is_alive:
                presence[aid] = {"status": p.status, "tasks": p.task_count}

        return json.dumps({"locks": locks, "presence": presence})

    def _apply_sync_state(self, payload: str):
        """Apply a state sync payload from a peer."""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return

        # Merge locks (don't overwrite our own)
        for wid, lock_data in data.get("locks", {}).items():
            if wid not in self.hiring_locks:
                self.hiring_locks[wid] = WorkerLock(
                    worker_id=wid,
                    agent_id=lock_data["agent"],
                    task_type=lock_data.get("task", "unknown"),
                    acquired_at=time.time(),
                    ttl_seconds=lock_data.get("remaining", self.lock_ttl),
                )

        # Merge presence (don't overwrite our own)
        for aid, pres_data in data.get("presence", {}).items():
            if aid != self.nickname and aid not in self.agent_presence:
                self.agent_presence[aid] = AgentPresence(
                    agent_id=aid,
                    status=pres_data.get("status", "unknown"),
                    task_count=pres_data.get("tasks", 0),
                    last_heartbeat=time.time(),
                )

    # ──────── Message Handling ────────

    async def _listen(self):
        """Listen for incoming IRC messages."""
        while self._running and self._reader:
            try:
                line = await self._reader.readline()
                if not line:
                    break
                decoded = line.decode().strip()
                if decoded.startswith("PING"):
                    self._send(f"PONG {decoded.split()[1]}")
                else:
                    self._parse_message(decoded)
                    self.stats.messages_received += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Acontext] Error reading from IRC: {e}")
                break

        # Connection lost — attempt reconnect
        if self._running:
            self._running = False
            await self._reconnect()

    def _parse_message(self, message: str):
        """Parse incoming IRC messages for swarm coordination commands."""
        if "PRIVMSG" not in message or self.channel not in message:
            return

        parts = message.split(f"PRIVMSG {self.channel} :")
        if len(parts) < 2:
            return

        content = parts[1].strip()
        # Extract sender from IRC prefix
        sender = ""
        if message.startswith(":"):
            sender = message[1:].split("!")[0]

        self._handle_swarm_command(content, sender)

    def _handle_swarm_command(self, command: str, sender: str = ""):
        """Route incoming swarm commands to handlers."""
        if command.startswith("!intent "):
            self._handle_intent(command, sender)
        elif command.startswith("!release "):
            self._handle_release(command)
        elif command.startswith("!renew "):
            self._handle_renew(command)
        elif command.startswith("!heartbeat "):
            self._handle_heartbeat(command)
        elif command.startswith("!bid "):
            self._handle_bid(command)
        elif command.startswith("!award "):
            self._handle_award(command)
        elif command.startswith("!auction "):
            self._handle_auction(command)
        elif command.startswith("!sync-request "):
            self._handle_sync_request(command)
        elif command.startswith("!sync-state "):
            self._handle_sync_state(command)
        elif command.startswith("!status "):
            self._handle_status(command)

    def _handle_intent(self, command: str, sender: str):
        tokens = command.split(" ")
        if len(tokens) >= 4:
            _, agent, worker, task = tokens[:4]
            # Check for contention
            if worker in self.hiring_locks:
                existing = self.hiring_locks[worker]
                if not existing.is_expired and existing.agent_id != agent:
                    self.stats.total_contentions += 1
                    logger.warning(f"[Acontext] Remote contention on {worker}: {agent} vs {existing.agent_id}")
                    return

            self.hiring_locks[worker] = WorkerLock(
                worker_id=worker, agent_id=agent,
                task_type=task, acquired_at=time.time(),
                ttl_seconds=self.lock_ttl,
            )
            self.stats.total_intents += 1
            logger.info(f"[Acontext] Synced lock: {agent} → {worker} for {task}")

            for cb in self._intent_callbacks:
                try:
                    cb("intent", {"agent": agent, "worker": worker, "task": task})
                except Exception:
                    pass

    def _handle_release(self, command: str):
        tokens = command.split(" ")
        if len(tokens) >= 2:
            worker = tokens[1]
            if worker in self.hiring_locks:
                del self.hiring_locks[worker]
                self.stats.total_releases += 1
                logger.info(f"[Acontext] Released lock on {worker}")

    def _handle_renew(self, command: str):
        tokens = command.split(" ")
        if len(tokens) >= 3:
            _, agent, worker = tokens[:3]
            lock = self.hiring_locks.get(worker)
            if lock and lock.agent_id == agent:
                lock.renew()

    def _handle_heartbeat(self, command: str):
        tokens = command.split(" ")
        if len(tokens) >= 4:
            _, agent, status, task_count_str = tokens[:4]
            try:
                task_count = int(task_count_str)
            except ValueError:
                task_count = 0

            now = time.time()
            if agent in self.agent_presence:
                p = self.agent_presence[agent]
                p.status = status
                p.task_count = task_count
                p.last_heartbeat = now
            else:
                self.agent_presence[agent] = AgentPresence(
                    agent_id=agent, status=status,
                    task_count=task_count, last_heartbeat=now,
                )

            self.stats.total_heartbeats += 1

            for cb in self._heartbeat_callbacks:
                try:
                    cb("heartbeat", {"agent": agent, "status": status, "tasks": task_count})
                except Exception:
                    pass

    def _handle_bid(self, command: str):
        tokens = command.split(" ")
        if len(tokens) >= 4:
            _, agent, task_id, score_str = tokens[:4]
            try:
                score = float(score_str)
            except ValueError:
                return

            auction = self.auctions.get(task_id)
            if auction and not auction.closed:
                bid = TaskBid(agent_id=agent, task_id=task_id, score=score)
                auction.add_bid(bid)
                self.stats.total_bids += 1

    def _handle_award(self, command: str):
        tokens = command.split(" ")
        if len(tokens) >= 3:
            _, task_id, winner = tokens[:3]
            auction = self.auctions.get(task_id)
            if auction:
                auction.winner = winner
                auction.closed = True

    def _handle_auction(self, command: str):
        try:
            payload_str = command[len("!auction "):]
            payload = json.loads(payload_str)
            task_id = payload.get("task_id")
            if task_id and task_id not in self.auctions:
                self.auctions[task_id] = TaskAuction(
                    task_id=task_id,
                    category=payload.get("category", ""),
                    bounty_usd=payload.get("bounty_usd", 0.0),
                    timeout_seconds=payload.get("timeout", self.auction_timeout),
                )
        except (json.JSONDecodeError, KeyError):
            pass

    def _handle_sync_request(self, command: str):
        tokens = command.split(" ")
        if len(tokens) >= 2:
            requester = tokens[1]
            if requester != self.nickname and self._running:
                payload = self._build_sync_payload()
                self._send_channel(f"!sync-state {payload}")

    def _handle_sync_state(self, command: str):
        payload = command[len("!sync-state "):]
        self._apply_sync_state(payload)

    def _handle_status(self, command: str):
        tokens = command.split(" ")
        if len(tokens) >= 3:
            _, agent, state = tokens[:3]
            if agent in self.agent_presence:
                self.agent_presence[agent].status = state
            for cb in self._status_callbacks:
                try:
                    cb("status", {"agent": agent, "state": state})
                except Exception:
                    pass

    # ──────── Background Tasks ────────

    async def _cleanup_loop(self):
        """Periodically clean up expired locks."""
        while self._running:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                self._cleanup_expired_locks()
                self._cleanup_timed_out_auctions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Acontext] Cleanup error: {e}")

    async def _heartbeat_loop(self):
        """Periodically send heartbeats."""
        while self._running:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Acontext] Heartbeat error: {e}")

    def _cleanup_expired_locks(self):
        """Remove expired locks."""
        expired = [wid for wid, lock in self.hiring_locks.items() if lock.is_expired]
        for wid in expired:
            del self.hiring_locks[wid]
            self.stats.expired_locks_cleaned += 1
        if expired:
            logger.info(f"[Acontext] Cleaned {len(expired)} expired lock(s)")

    def _cleanup_timed_out_auctions(self):
        """Auto-resolve timed-out auctions."""
        timed_out = [tid for tid, a in self.auctions.items()
                     if a.is_timed_out and not a.closed]
        for tid in timed_out:
            self.auctions[tid].resolve()
            logger.info(f"[Acontext] Auto-resolved timed-out auction {tid}")

    # ──────── Diagnostics ────────

    def get_stats(self) -> dict:
        """Get coordination statistics."""
        return {
            "total_intents": self.stats.total_intents,
            "total_releases": self.stats.total_releases,
            "total_contentions": self.stats.total_contentions,
            "total_auctions": self.stats.total_auctions,
            "total_bids": self.stats.total_bids,
            "total_heartbeats": self.stats.total_heartbeats,
            "active_locks": len(self.hiring_locks),
            "expired_locks_cleaned": self.stats.expired_locks_cleaned,
            "agents_online": len(self.get_online_agents()),
            "active_auctions": len(self.get_active_auctions()),
            "connected": self.is_connected,
            "messages_sent": self.stats.messages_sent,
            "messages_received": self.stats.messages_received,
        }

    def get_health(self) -> dict:
        """Get coordination health summary."""
        active = self.get_active_locks()
        stale = sum(1 for l in active.values() if l.remaining_seconds < 60)
        return {
            "status": "connected" if self.is_connected else "disconnected",
            "active_locks": len(active),
            "stale_locks": stale,
            "agents_online": len(self.get_online_agents()),
            "contention_rate": (
                self.stats.total_contentions / self.stats.total_intents
                if self.stats.total_intents > 0 else 0.0
            ),
        }
