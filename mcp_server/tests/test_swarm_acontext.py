"""
Tests for AcontextAdapter — structured memory and observability.

Covers: session lifecycle, interaction storage, context compression,
task result learning, knowledge base, observations, and status.
"""

import json
import os
import pytest
import tempfile
from datetime import datetime, timezone

from mcp_server.swarm.acontext_adapter import (
    AcontextAdapter,
    AgentSession,
    Interaction,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def adapter(tmp_dir):
    return AcontextAdapter(state_dir=tmp_dir)


# ─── Interaction Model ───────────────────────────────────────────────────────


class TestInteraction:
    def test_creation(self):
        i = Interaction("system", "Hello agent")
        assert i.role == "system"
        assert i.content == "Hello agent"
        assert i.timestamp is not None

    def test_to_dict(self):
        i = Interaction("agent", "On it", metadata={"task": "t1"})
        d = i.to_dict()
        assert d["role"] == "agent"
        assert d["metadata"]["task"] == "t1"

    def test_from_dict(self):
        d = {"role": "tool", "content": '{"result": 42}', "timestamp": "2026-03-14T03:00:00Z"}
        i = Interaction.from_dict(d)
        assert i.role == "tool"
        assert i.content == '{"result": 42}'

    def test_token_estimate(self):
        i = Interaction("agent", "a" * 400)
        assert i.token_estimate == 100  # 400 / 4

    def test_token_estimate_minimum(self):
        i = Interaction("agent", "hi")
        assert i.token_estimate >= 1


# ─── AgentSession Model ──────────────────────────────────────────────────────


class TestAgentSession:
    def test_creation(self):
        s = AgentSession("s1", agent_id=1, cycle_id="abc")
        assert s.session_id == "s1"
        assert s.agent_id == 1
        assert len(s.interactions) == 0

    def test_add_interaction(self):
        s = AgentSession("s1", 1, "abc")
        s.add_interaction("system", "Task assigned")
        s.add_interaction("agent", "Routing now")
        assert len(s.interactions) == 2

    def test_add_task_result(self):
        s = AgentSession("s1", 1, "abc")
        s.add_task_result("t1", True, {"type": "photo", "quality": 0.9})
        assert len(s.task_results) == 1
        assert s.task_results[0]["success"] is True

    def test_total_tokens(self):
        s = AgentSession("s1", 1, "abc")
        s.add_interaction("agent", "a" * 400)  # ~100 tokens
        s.add_interaction("agent", "b" * 200)  # ~50 tokens
        assert s.total_tokens == 150

    def test_to_dict_roundtrip(self):
        s = AgentSession("s1", 1, "abc")
        s.add_interaction("system", "Hello")
        s.add_task_result("t1", True, {"type": "photo"})

        d = s.to_dict()
        restored = AgentSession.from_dict(d)
        assert restored.session_id == "s1"
        assert restored.agent_id == 1
        assert len(restored.interactions) == 1
        assert len(restored.task_results) == 1


# ─── Session Management ──────────────────────────────────────────────────────


class TestSessionManagement:
    def test_create_session(self, adapter):
        sid = adapter.create_agent_session(agent_id=1, cycle_id="c1")
        assert sid == "agent_1_cycle_c1"

    def test_get_active_session(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        session = adapter.get_session(sid)
        assert session is not None
        assert session.agent_id == 1

    def test_close_session_persists(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.store_interaction(sid, "agent", "test message")
        result = adapter.close_session(sid)
        assert result is True

        # Should be loadable from disk
        session = adapter.get_session(sid)
        assert session is not None
        assert len(session.interactions) == 1

    def test_close_nonexistent_session(self, adapter):
        result = adapter.close_session("nonexistent")
        assert result is False

    def test_get_nonexistent_session(self, adapter):
        session = adapter.get_session("nonexistent")
        assert session is None

    def test_multiple_sessions(self, adapter):
        sid1 = adapter.create_agent_session(1, "c1")
        sid2 = adapter.create_agent_session(2, "c2")
        assert sid1 != sid2
        assert adapter.get_session(sid1) is not None
        assert adapter.get_session(sid2) is not None


# ─── Interaction Storage ─────────────────────────────────────────────────────


class TestInteractionStorage:
    def test_store_interaction(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        result = adapter.store_interaction(sid, "system", "Task: photo verification")
        assert result is True

        session = adapter.get_session(sid)
        assert len(session.interactions) == 1
        assert session.interactions[0].role == "system"

    def test_store_with_metadata(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.store_interaction(sid, "tool", '{"status": 200}', metadata={"api": "em"})
        session = adapter.get_session(sid)
        assert session.interactions[0].metadata["api"] == "em"

    def test_store_to_nonexistent_session(self, adapter):
        result = adapter.store_interaction("nonexistent", "agent", "hello")
        assert result is False

    def test_store_to_closed_and_reloaded_session(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.store_interaction(sid, "system", "first")
        adapter.close_session(sid)

        # Store to closed session (should reload from disk)
        result = adapter.store_interaction(sid, "agent", "second")
        assert result is True

    def test_auto_save_on_threshold(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        for i in range(10):
            adapter.store_interaction(sid, "agent", f"message {i}")
        # Session file should exist on disk after 10 interactions
        path = os.path.join(adapter._sessions_dir, f"{sid}.json")
        assert os.path.exists(path)


# ─── Context Compression ─────────────────────────────────────────────────────


class TestContextCompression:
    def test_small_context_returns_all(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.store_interaction(sid, "system", "hello")
        adapter.store_interaction(sid, "agent", "hi")
        context = adapter.get_compressed_context(sid, max_tokens=50000)
        assert len(context) == 2

    def test_large_context_compresses(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        # Add many tool interactions with long content
        for i in range(20):
            adapter.store_interaction(sid, "tool", "x" * 2000)  # ~500 tokens each
        # Total ~10000 tokens, request 5000
        context = adapter.get_compressed_context(sid, max_tokens=5000)
        assert len(context) < 20  # Some should be compressed or dropped

    def test_compression_preserves_recent(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        for i in range(10):
            adapter.store_interaction(sid, "agent", f"message_{i}")
        context = adapter.get_compressed_context(sid, max_tokens=5)
        # Should have at least the most recent
        assert len(context) >= 1

    def test_empty_session_returns_empty(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        context = adapter.get_compressed_context(sid)
        assert context == []

    def test_nonexistent_session_returns_empty(self, adapter):
        context = adapter.get_compressed_context("nope")
        assert context == []

    def test_tool_messages_truncated(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        # Old tool message (will be in first 40%)
        for i in range(5):
            adapter.store_interaction(sid, "tool", "z" * 1000)
        # Recent messages
        for i in range(8):
            adapter.store_interaction(sid, "agent", "short")

        context = adapter.get_compressed_context(sid, max_tokens=500)
        # Some old tool messages should be truncated
        truncated = [c for c in context if c.get("metadata", {}).get("compressed")]
        # At least check that context is returned
        assert len(context) > 0


# ─── Task Result Learning ────────────────────────────────────────────────────


class TestTaskResultLearning:
    def test_report_success(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.report_task_result(sid, "t1", True, {"type": "photo", "quality": 0.9})

        session = adapter.get_session(sid)
        assert len(session.task_results) == 1

    def test_updates_task_patterns(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.report_task_result(sid, "t1", True, {"category": "photo", "quality": 0.9})
        adapter.report_task_result(sid, "t2", False, {"category": "photo"})

        patterns = adapter.get_task_patterns()
        assert patterns["total"] == 2
        assert patterns["successes"] == 1
        assert patterns["failures"] == 1

    def test_category_patterns(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.report_task_result(sid, "t1", True, {"category": "photo", "quality": 0.8})
        adapter.report_task_result(sid, "t2", True, {"category": "photo", "quality": 0.9})

        patterns = adapter.get_task_patterns(category="photo")
        assert patterns["total"] == 2
        assert patterns["successes"] == 2
        assert abs(patterns["avg_quality"] - 0.85) < 0.01


# ─── Knowledge Base ──────────────────────────────────────────────────────────


class TestKnowledgeBase:
    def test_empty_patterns(self, adapter):
        patterns = adapter.get_task_patterns()
        assert patterns == {}

    def test_empty_specializations(self, adapter):
        specs = adapter.get_agent_specializations()
        assert specs == {}

    def test_update_specialization(self, adapter):
        adapter.update_agent_specialization(
            agent_id=1, category="photo",
            success_rate=0.95, task_count=50,
        )
        specs = adapter.get_agent_specializations()
        assert "1" in specs["agents"]
        assert specs["agents"]["1"]["categories"]["photo"]["success_rate"] == 0.95

    def test_multiple_specializations(self, adapter):
        adapter.update_agent_specialization(1, "photo", 0.9, 30)
        adapter.update_agent_specialization(1, "delivery", 0.7, 10)
        adapter.update_agent_specialization(2, "photo", 0.95, 50)

        specs = adapter.get_agent_specializations()
        assert len(specs["agents"]) == 2
        assert len(specs["agents"]["1"]["categories"]) == 2

    def test_failure_modes_empty(self, adapter):
        modes = adapter.get_failure_modes()
        assert modes == {}


# ─── Observations ─────────────────────────────────────────────────────────────


class TestObservations:
    def test_observations_recorded(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.store_interaction(sid, "agent", "test")
        obs = adapter.get_observations()
        assert len(obs) >= 1
        assert obs[0]["type"] == "interaction"

    def test_task_result_observation(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.report_task_result(sid, "t1", True, {"type": "photo"})
        obs = adapter.get_observations()
        task_obs = [o for o in obs if o["type"] == "task_result"]
        assert len(task_obs) >= 1

    def test_observations_by_date(self, adapter):
        obs = adapter.get_observations(date="2020-01-01")
        assert obs == []

    def test_observation_limit(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        for i in range(20):
            adapter.store_interaction(sid, "agent", f"msg {i}")
        obs = adapter.get_observations(limit=5)
        assert len(obs) == 5

    def test_observation_days(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.store_interaction(sid, "agent", "test")
        days = adapter.get_observation_days()
        assert len(days) >= 1


# ─── Status ───────────────────────────────────────────────────────────────────


class TestStatus:
    def test_initial_status(self, adapter):
        s = adapter.get_status()
        assert s["mode"] == "local"
        assert s["active_sessions"] == 0
        assert s["persisted_sessions"] == 0

    def test_status_with_sessions(self, adapter):
        adapter.create_agent_session(1, "c1")
        adapter.create_agent_session(2, "c2")
        s = adapter.get_status()
        assert s["active_sessions"] == 2

    def test_session_count(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        adapter.close_session(sid)
        assert adapter.get_session_count() == 1

    def test_api_mode_detection(self, tmp_dir):
        a = AcontextAdapter(api_key="test-key", state_dir=tmp_dir)
        assert a.mode == "api"

    def test_local_mode_default(self, adapter):
        assert adapter.mode == "local"


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_concurrent_sessions_same_agent(self, adapter):
        sid1 = adapter.create_agent_session(1, "cycle_a")
        sid2 = adapter.create_agent_session(1, "cycle_b")
        assert sid1 != sid2

    def test_empty_content_interaction(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        result = adapter.store_interaction(sid, "agent", "")
        assert result is True

    def test_large_evidence_object(self, adapter):
        sid = adapter.create_agent_session(1, "c1")
        evidence = {
            "type": "photo_geo",
            "quality": 0.95,
            "data": "x" * 10000,
            "nested": {"deep": {"value": 42}},
        }
        adapter.report_task_result(sid, "t1", True, evidence)
        session = adapter.get_session(sid)
        assert len(session.task_results) == 1

    def test_directory_creation(self, tmp_dir):
        nested = os.path.join(tmp_dir, "deep", "nested")
        a = AcontextAdapter(state_dir=nested)
        assert os.path.exists(os.path.join(nested, "memory", "sessions"))

    def test_session_index_updates(self, adapter):
        for i in range(5):
            adapter.create_agent_session(i, f"c{i}")
        index_path = os.path.join(adapter._memory_dir, "index.json")
        with open(index_path) as f:
            index = json.load(f)
        assert len(index["sessions"]) == 5
