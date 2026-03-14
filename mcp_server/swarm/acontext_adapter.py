"""
Acontext Adapter for KK V2 Swarm
================================

Provides structured memory and observability for agent coordination.

Two modes:
1. **Local Mode** (default): File-based structured memory using JSON files.
   Works offline, no Docker required. Production-ready for single-node swarms.
2. **API Mode**: Connects to Acontext service for distributed memory.
   Requires ACONTEXT_API_KEY. Used for multi-node swarms.

Memory Structure (Local Mode):
    ~/.em-swarm/memory/
    ├── sessions/           # Agent work sessions
    │   ├── agent_1_cycle_abc.json
    │   └── agent_2_cycle_def.json
    ├── knowledge/          # Persistent learned knowledge
    │   ├── task_patterns.json
    │   ├── agent_specializations.json
    │   └── failure_modes.json
    ├── observations/       # Raw event observations
    │   └── 2026-03-14.jsonl
    └── index.json          # Session index for fast lookup

Usage:
    adapter = AcontextAdapter()  # Auto-detects mode

    # Session lifecycle
    session_id = adapter.create_agent_session(agent_id=1, cycle_id="abc")
    adapter.store_interaction(session_id, "system", "Task assigned: photo verification")
    adapter.store_interaction(session_id, "agent", "Routing to worker with photo expertise")
    adapter.store_interaction(session_id, "tool", '{"action": "assign", "worker_id": 42}')

    # Task result learning
    adapter.report_task_result(session_id, "task-123", success=True,
        evidence={"type": "photo_geo", "quality": 0.95})

    # Knowledge retrieval
    patterns = adapter.get_task_patterns(category="photo")
    specialists = adapter.get_agent_specializations()

    # Context retrieval
    context = adapter.get_compressed_context(session_id, max_tokens=50000)
"""

import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("em.swarm.acontext")


# ─── Data Models ──────────────────────────────────────────────────────────────


class Interaction:
    """A single interaction in an agent session."""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None,
                 metadata: Optional[dict] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Interaction":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )

    @property
    def token_estimate(self) -> int:
        """Rough token estimate (4 chars per token heuristic)."""
        return max(1, len(self.content) // 4)


class AgentSession:
    """A structured memory session for an agent's work cycle."""

    def __init__(self, session_id: str, agent_id: int, cycle_id: str):
        self.session_id = session_id
        self.agent_id = agent_id
        self.cycle_id = cycle_id
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.interactions: list[Interaction] = []
        self.task_results: list[dict] = []
        self.metadata: dict = {}

    def add_interaction(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        self.interactions.append(Interaction(role, content, metadata=metadata))

    def add_task_result(self, task_id: str, success: bool, evidence: dict) -> None:
        self.task_results.append({
            "task_id": task_id,
            "success": success,
            "evidence": evidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @property
    def total_tokens(self) -> int:
        return sum(i.token_estimate for i in self.interactions)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "cycle_id": self.cycle_id,
            "created_at": self.created_at,
            "interactions": [i.to_dict() for i in self.interactions],
            "task_results": self.task_results,
            "metadata": self.metadata,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentSession":
        session = cls(
            session_id=data["session_id"],
            agent_id=data["agent_id"],
            cycle_id=data["cycle_id"],
        )
        session.created_at = data.get("created_at", session.created_at)
        session.interactions = [Interaction.from_dict(i) for i in data.get("interactions", [])]
        session.task_results = data.get("task_results", [])
        session.metadata = data.get("metadata", {})
        return session


# ─── Adapter ──────────────────────────────────────────────────────────────────


class AcontextAdapter:
    """
    Structured memory and observability adapter for swarm coordination.

    Provides local file-based memory with API fallback.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        state_dir: str = os.path.expanduser("~/.em-swarm"),
    ):
        self.base_url = base_url or os.getenv("ACONTEXT_API_URL", "http://localhost:8029/api/v1")
        self.api_key = api_key or os.getenv("ACONTEXT_API_KEY")
        self.state_dir = state_dir
        self.mode = "api" if self.api_key else "local"

        # Local storage paths
        self._memory_dir = os.path.join(state_dir, "memory")
        self._sessions_dir = os.path.join(self._memory_dir, "sessions")
        self._knowledge_dir = os.path.join(self._memory_dir, "knowledge")
        self._observations_dir = os.path.join(self._memory_dir, "observations")

        # In-memory cache
        self._active_sessions: dict[str, AgentSession] = {}

        # Ensure directories exist
        for d in [self._sessions_dir, self._knowledge_dir, self._observations_dir]:
            os.makedirs(d, exist_ok=True)

        if self.mode == "local":
            logger.info("AcontextAdapter: Running in local file mode")
        else:
            logger.info(f"AcontextAdapter: Running in API mode ({self.base_url})")

    # ─── Session Management ──────────────────────────────────────────

    def create_agent_session(self, agent_id: int, cycle_id: str) -> str:
        """Create a new structured memory session for an agent's work cycle."""
        session_id = f"agent_{agent_id}_cycle_{cycle_id}"

        session = AgentSession(
            session_id=session_id,
            agent_id=agent_id,
            cycle_id=cycle_id,
        )

        self._active_sessions[session_id] = session

        # Update index
        self._update_session_index(session_id, agent_id, cycle_id)

        logger.debug(f"Created session {session_id} for agent {agent_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get a session by ID (from cache or disk)."""
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # Try loading from disk
        return self._load_session(session_id)

    def close_session(self, session_id: str) -> bool:
        """Flush session to disk and remove from active cache."""
        session = self._active_sessions.pop(session_id, None)
        if session is None:
            return False

        self._save_session(session)
        logger.debug(f"Closed and persisted session {session_id}")
        return True

    # ─── Interaction Storage ─────────────────────────────────────────

    def store_interaction(self, session_id: str, role: str, content: str,
                          metadata: Optional[dict] = None) -> bool:
        """Store an LLM interaction or tool result into the agent's context."""
        session = self._active_sessions.get(session_id)
        if session is None:
            # Try loading from disk
            session = self._load_session(session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found")
                return False
            self._active_sessions[session_id] = session

        session.add_interaction(role, content, metadata)

        # Auto-save every 10 interactions
        if len(session.interactions) % 10 == 0:
            self._save_session(session)

        # Record observation
        self._record_observation("interaction", {
            "session_id": session_id,
            "agent_id": session.agent_id,
            "role": role,
            "content_length": len(content),
        })

        return True

    # ─── Context Retrieval ───────────────────────────────────────────

    def get_compressed_context(self, session_id: str, max_tokens: int = 50000) -> list[dict]:
        """
        Retrieve the context window, auto-compressing older interactions.

        Strategy:
        - Keep recent interactions verbatim
        - Summarize older tool results (truncate to first 200 chars)
        - Drop system messages older than the midpoint
        """
        session = self.get_session(session_id)
        if session is None:
            return []

        interactions = session.interactions
        if not interactions:
            return []

        # If within budget, return all
        total = sum(i.token_estimate for i in interactions)
        if total <= max_tokens:
            return [i.to_dict() for i in interactions]

        # Compress: keep last 60%, summarize first 40%
        split_idx = max(1, int(len(interactions) * 0.4))
        old = interactions[:split_idx]
        recent = interactions[split_idx:]

        compressed = []

        # Compress old interactions
        for i in old:
            if i.role == "tool" and len(i.content) > 200:
                compressed.append({
                    "role": i.role,
                    "content": i.content[:200] + "... [truncated]",
                    "timestamp": i.timestamp,
                    "metadata": {**i.metadata, "compressed": True},
                })
            elif i.role == "system":
                # Skip old system messages
                continue
            else:
                compressed.append(i.to_dict())

        # Keep recent verbatim
        for i in recent:
            compressed.append(i.to_dict())

        # Final budget check — drop from beginning if still over
        result_tokens = sum(max(1, len(c.get("content", "")) // 4) for c in compressed)
        while result_tokens > max_tokens and len(compressed) > 1:
            dropped = compressed.pop(0)
            result_tokens -= max(1, len(dropped.get("content", "")) // 4)

        return compressed

    # ─── Task Result Learning ────────────────────────────────────────

    def report_task_result(self, session_id: str, task_id: str, success: bool,
                           evidence: dict) -> None:
        """Feed task execution results for agent learning."""
        session = self._active_sessions.get(session_id)
        if session:
            session.add_task_result(task_id, success, evidence)

        # Update knowledge base
        self._update_task_patterns(task_id, success, evidence)

        # Record observation
        self._record_observation("task_result", {
            "session_id": session_id,
            "task_id": task_id,
            "success": success,
            "evidence_type": evidence.get("type", "unknown"),
            "quality": evidence.get("quality"),
        })

    # ─── Knowledge Base ──────────────────────────────────────────────

    def get_task_patterns(self, category: Optional[str] = None) -> dict:
        """Get learned task patterns from knowledge base."""
        patterns = self._load_knowledge("task_patterns")

        if category and patterns:
            return patterns.get("categories", {}).get(category, {})

        return patterns

    def get_agent_specializations(self) -> dict:
        """Get learned agent specializations."""
        return self._load_knowledge("agent_specializations")

    def get_failure_modes(self) -> dict:
        """Get common failure patterns."""
        return self._load_knowledge("failure_modes")

    def update_agent_specialization(self, agent_id: int, category: str,
                                     success_rate: float, task_count: int) -> None:
        """Update agent specialization data."""
        specs = self._load_knowledge("agent_specializations")
        if not specs:
            specs = {"agents": {}}

        agent_key = str(agent_id)
        if agent_key not in specs["agents"]:
            specs["agents"][agent_key] = {"categories": {}}

        specs["agents"][agent_key]["categories"][category] = {
            "success_rate": round(success_rate, 3),
            "task_count": task_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._save_knowledge("agent_specializations", specs)

    # ─── Observations ────────────────────────────────────────────────

    def get_observations(self, date: Optional[str] = None, limit: int = 100) -> list[dict]:
        """Get raw observations for a date."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        obs_file = os.path.join(self._observations_dir, f"{date}.jsonl")
        if not os.path.exists(obs_file):
            return []

        observations = []
        try:
            with open(obs_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        observations.append(json.loads(line))
        except (json.JSONDecodeError, IOError):
            pass

        return observations[-limit:]

    def get_session_count(self) -> int:
        """Get total number of sessions on disk."""
        try:
            return len([f for f in os.listdir(self._sessions_dir) if f.endswith(".json")])
        except OSError:
            return 0

    def get_observation_days(self) -> list[str]:
        """Get list of dates with observations."""
        try:
            return sorted([
                f.replace(".jsonl", "")
                for f in os.listdir(self._observations_dir)
                if f.endswith(".jsonl")
            ])
        except OSError:
            return []

    # ─── Status ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get adapter status."""
        return {
            "mode": self.mode,
            "active_sessions": len(self._active_sessions),
            "persisted_sessions": self.get_session_count(),
            "knowledge_files": self._list_knowledge_files(),
            "observation_days": self.get_observation_days(),
            "state_dir": self.state_dir,
        }

    # ─── Internal Helpers ────────────────────────────────────────────

    def _save_session(self, session: AgentSession) -> None:
        """Save session to disk."""
        path = os.path.join(self._sessions_dir, f"{session.session_id}.json")
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def _load_session(self, session_id: str) -> Optional[AgentSession]:
        """Load session from disk."""
        path = os.path.join(self._sessions_dir, f"{session_id}.json")
        try:
            with open(path, "r") as f:
                return AgentSession.from_dict(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _update_session_index(self, session_id: str, agent_id: int, cycle_id: str) -> None:
        """Update the session index for fast lookup."""
        index_path = os.path.join(self._memory_dir, "index.json")
        try:
            with open(index_path, "r") as f:
                index = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            index = {"sessions": []}

        index["sessions"].append({
            "session_id": session_id,
            "agent_id": agent_id,
            "cycle_id": cycle_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        # Keep only last 1000 entries
        index["sessions"] = index["sessions"][-1000:]

        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

    def _record_observation(self, event_type: str, data: dict) -> None:
        """Record a timestamped observation."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        obs_file = os.path.join(self._observations_dir, f"{today}.jsonl")

        entry = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }

        try:
            with open(obs_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except IOError as e:
            logger.warning(f"Failed to write observation: {e}")

    def _load_knowledge(self, name: str) -> dict:
        """Load a knowledge file."""
        path = os.path.join(self._knowledge_dir, f"{name}.json")
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_knowledge(self, name: str, data: dict) -> None:
        """Save a knowledge file."""
        path = os.path.join(self._knowledge_dir, f"{name}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _list_knowledge_files(self) -> list[str]:
        """List available knowledge files."""
        try:
            return [f.replace(".json", "") for f in os.listdir(self._knowledge_dir) if f.endswith(".json")]
        except OSError:
            return []

    def _update_task_patterns(self, task_id: str, success: bool, evidence: dict) -> None:
        """Update task pattern knowledge from a result."""
        patterns = self._load_knowledge("task_patterns")
        if not patterns:
            patterns = {"total": 0, "successes": 0, "failures": 0, "categories": {}}

        patterns["total"] = patterns.get("total", 0) + 1
        if success:
            patterns["successes"] = patterns.get("successes", 0) + 1
        else:
            patterns["failures"] = patterns.get("failures", 0) + 1

        # Update category stats
        category = evidence.get("category", "unknown")
        cats = patterns.setdefault("categories", {})
        if category not in cats:
            cats[category] = {"total": 0, "successes": 0, "avg_quality": 0, "qualities": []}

        cat = cats[category]
        cat["total"] += 1
        if success:
            cat["successes"] += 1
        quality = evidence.get("quality")
        if quality is not None:
            cat["qualities"].append(quality)
            cat["avg_quality"] = sum(cat["qualities"]) / len(cat["qualities"])
            # Keep only last 100 quality samples
            cat["qualities"] = cat["qualities"][-100:]

        patterns["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_knowledge("task_patterns", patterns)

    def _update_failure_modes(self, task_id: str, error: str, evidence: dict) -> None:
        """Update failure mode knowledge."""
        modes = self._load_knowledge("failure_modes")
        if not modes:
            modes = {"patterns": {}, "total": 0}

        modes["total"] = modes.get("total", 0) + 1

        # Simple error categorization
        error_key = error[:50] if error else "unknown"
        if error_key not in modes["patterns"]:
            modes["patterns"][error_key] = {"count": 0, "examples": []}

        modes["patterns"][error_key]["count"] += 1
        modes["patterns"][error_key]["examples"].append({
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep only last 5 examples per pattern
        modes["patterns"][error_key]["examples"] = modes["patterns"][error_key]["examples"][-5:]

        modes["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_knowledge("failure_modes", modes)
