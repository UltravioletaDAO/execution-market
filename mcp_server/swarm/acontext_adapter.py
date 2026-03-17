"""
Acontext Adapter for MeshRelay (IRC) Coordination
Provides a shared memory space across distinct agent sessions by synchronizing state via IRC.
"""
import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class AcontextAdapter:
    """
    Synchronizes agent hiring intents and swarm state via MeshRelay IRC.
    Allows distributed agents to avoid colliding on the same human worker.
    """
    def __init__(self, irc_host="meshrelay.local", port=6667, channel="#em-swarm", nickname="EM-Agent-00"):
        self.irc_host = irc_host
        self.port = port
        self.channel = channel
        self.nickname = nickname
        self.active_intents: Dict[str, Dict[str, Any]] = {}  # task_id -> {agent_id, worker_id, timestamp}
        self.hiring_locks: Dict[str, str] = {}               # worker_id -> agent_id
        self.callbacks = []
        self._reader = None
        self._writer = None
        self._running = False

    async def connect(self):
        """Connect to MeshRelay IRC network."""
        try:
            self._reader, self._writer = await asyncio.open_connection(self.irc_host, self.port)
            self._send(f"NICK {self.nickname}")
            self._send(f"USER {self.nickname} 0 * :EM Swarm Agent")
            self._send(f"JOIN {self.channel}")
            self._running = True
            logger.info(f"[Acontext] Connected to {self.irc_host}:{self.port} as {self.nickname}")
            asyncio.create_task(self._listen())
        except Exception as e:
            logger.error(f"[Acontext] Failed to connect: {e}")
            # Stub implementation allows continuing without connection
            self._running = False

    def _send(self, message: str):
        if self._writer:
            self._writer.write(f"{message}\r\n".encode())

    async def _listen(self):
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
            except Exception as e:
                logger.error(f"[Acontext] Error reading from IRC: {e}")
                break

    def _parse_message(self, message: str):
        """Parse incoming IRC messages for swarm coordination commands."""
        # e.g. :AgentA!user@host PRIVMSG #em-swarm :!intent AgentA 0x8F2... DataEntry
        if "PRIVMSG" in message and self.channel in message:
            parts = message.split(f"PRIVMSG {self.channel} :")
            if len(parts) > 1:
                content = parts[1].strip()
                self._handle_swarm_command(content)

    def _handle_swarm_command(self, command: str):
        if command.startswith("!intent "):
            tokens = command.split(" ")
            if len(tokens) >= 4:
                _, agent, worker, task = tokens[:4]
                self.hiring_locks[worker] = agent
                logger.info(f"[Acontext] Synced lock: Agent {agent} locked worker {worker} for {task}")
                for cb in self.callbacks:
                    cb("intent", {"agent": agent, "worker": worker, "task": task})
        elif command.startswith("!release "):
            tokens = command.split(" ")
            if len(tokens) >= 2:
                _, worker = tokens[:2]
                if worker in self.hiring_locks:
                    del self.hiring_locks[worker]
                    logger.info(f"[Acontext] Released lock on worker {worker}")

    def register_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register a callback to react to swarm state changes."""
        self.callbacks.append(callback)

    async def broadcast_intent(self, agent_id: str, worker_id: str, task_type: str):
        """Announce intention to hire a worker to prevent collision."""
        msg = f"!intent {agent_id} {worker_id} {task_type}"
        self.hiring_locks[worker_id] = agent_id  # local optimistic lock
        if self._running:
            self._send(f"PRIVMSG {self.channel} :{msg}")
        return True

    async def broadcast_release(self, worker_id: str):
        """Release a hiring lock."""
        if worker_id in self.hiring_locks:
            del self.hiring_locks[worker_id]
        if self._running:
            self._send(f"PRIVMSG {self.channel} :!release {worker_id}")

    def is_worker_available(self, worker_id: str) -> bool:
        """Check if worker is currently being recruited by another agent."""
        return worker_id not in self.hiring_locks

    def get_lock_owner(self, worker_id: str) -> Optional[str]:
        return self.hiring_locks.get(worker_id)
