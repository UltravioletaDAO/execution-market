"""Tests for em-k1-mcp tools against the mock backend.

These tests exercise the MockK1Backend directly *and* the FastMCP server
that wires it up. They must pass without any robot, simulator, or
network connectivity — that's the whole point of the mock backend.
"""

from __future__ import annotations

import pytest

from em_k1_mcp.backends.mock import MockK1Backend
from em_k1_mcp.config import K1Config, load_config
from em_k1_mcp.server import build_server


# ---------------------------------------------------------------------------
# Backend-level tests (no FastMCP)
# ---------------------------------------------------------------------------


async def test_mock_backend_stand(mock_backend: MockK1Backend):
    outcome = await mock_backend.stand()
    assert outcome.success is True
    assert outcome.detail["posture"] == "standing"


async def test_mock_backend_sit(mock_backend: MockK1Backend):
    outcome = await mock_backend.sit()
    assert outcome.success is True
    assert outcome.detail["posture"] == "sitting"


async def test_mock_backend_walk_to_records_distance(mock_backend: MockK1Backend):
    outcome = await mock_backend.walk_to(
        target="kitchen", x_m=3.0, y_m=4.0, heading_deg=90.0, max_speed_mps=0.4
    )
    assert outcome.reached is True
    assert outcome.final_x_m == 3.0
    assert outcome.final_y_m == 4.0
    assert outcome.final_heading_deg == 90.0
    # Distance from (0, 0) to (3, 4) is exactly 5.
    assert outcome.distance_traveled_m == pytest.approx(5.0)


async def test_mock_backend_emergency_stop_always_succeeds(mock_backend: MockK1Backend):
    outcome = await mock_backend.emergency_stop()
    assert outcome.success is True
    assert outcome.detail["posture"] == "estopped"


async def test_mock_backend_pick_place_round_trip(mock_backend: MockK1Backend):
    pick_outcome = await mock_backend.pick(object_id="apple", grip_force=12.0)
    assert pick_outcome.success is True
    assert pick_outcome.detail["object_id"] == "apple"

    place_outcome = await mock_backend.place(x_m=1.0, y_m=2.0, z_m=0.5)
    assert place_outcome.success is True
    assert place_outcome.detail["placed_object"] == "apple"


async def test_mock_backend_grip(mock_backend: MockK1Backend):
    outcome = await mock_backend.grip(force=10.0, duration_s=1.5)
    assert outcome.success is True
    assert outcome.detail["force"] == 10.0
    assert outcome.detail["duration_s"] == 1.5


async def test_mock_backend_observe_writes_frame(mock_backend: MockK1Backend, config: K1Config):
    outcome = await mock_backend.observe(save_frame=True, caption_prompt=None)
    assert outcome.frame_path is not None
    assert config.capture_dir.exists()
    assert outcome.width == 640
    assert outcome.height == 480
    assert "[mock]" in outcome.caption


async def test_mock_backend_observe_skips_save(mock_backend: MockK1Backend):
    outcome = await mock_backend.observe(save_frame=False, caption_prompt="describe colors")
    assert outcome.frame_path is None
    assert "describe colors" in outcome.caption


# ---------------------------------------------------------------------------
# FastMCP server-level tests — registers tools and asserts they are present
# ---------------------------------------------------------------------------


async def test_build_server_registers_all_tools(config: K1Config, mock_backend: MockK1Backend):
    mcp = build_server(config=config, backend=mock_backend)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "k1_stand",
        "k1_sit",
        "k1_walk_to",
        "k1_emergency_stop",
        "k1_pick",
        "k1_place",
        "k1_grip",
        "k1_observe",
        "em_claim_task",
        "em_submit_evidence",
    }
    assert expected.issubset(names), f"missing tools: {expected - names}"


async def test_walk_to_clamps_speed_at_safety_cap(config: K1Config, mock_backend: MockK1Backend):
    # config caps linear speed at 0.6 m/s; request 1.5 (the Pydantic upper
    # bound) to verify the server-side clamping kicks in.
    mcp = build_server(config=config, backend=mock_backend)
    result = await mcp.call_tool(
        "k1_walk_to",
        {
            "params": {
                "target": "far_room",
                "x_m": 1.0,
                "y_m": 0.0,
                "heading_deg": 0.0,
                "max_speed_mps": 1.5,
            }
        },
    )
    # FastMCP.call_tool returns a (content_list, structured) tuple in 1.20+.
    # Be tolerant about which shape we got.
    structured = _extract_structured(result)
    assert structured["ok"] is True
    assert structured["reached"] is True
    # The backend echoes back the clamped speed in its detail dict.
    assert structured["detail"]["max_speed_mps"] == pytest.approx(0.6)


async def test_grip_clamps_force_at_safety_cap(config: K1Config, mock_backend: MockK1Backend):
    mcp = build_server(config=config, backend=mock_backend)
    result = await mcp.call_tool(
        "k1_grip",
        {"params": {"force": 99.0, "duration_s": 1.0}},
    )
    structured = _extract_structured(result)
    assert structured["ok"] is True
    assert structured["detail"]["force"] == pytest.approx(40.0)


async def test_stand_tool_via_mcp(config: K1Config, mock_backend: MockK1Backend):
    mcp = build_server(config=config, backend=mock_backend)
    result = await mcp.call_tool("k1_stand", {"params": {}})
    structured = _extract_structured(result)
    assert structured["ok"] is True
    assert structured["backend"] == "mock"


async def test_observe_tool_via_mcp(config: K1Config, mock_backend: MockK1Backend):
    mcp = build_server(config=config, backend=mock_backend)
    result = await mcp.call_tool(
        "k1_observe",
        {"params": {"save_frame": False, "caption_prompt": None}},
    )
    structured = _extract_structured(result)
    assert structured["ok"] is True
    assert structured["width"] == 640
    assert structured["height"] == 480
    assert "[mock]" in structured["caption"]


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


def test_load_config_defaults_to_mock(monkeypatch: pytest.MonkeyPatch):
    # Clear every K1_* / EM_* env var that might be sitting in the shell.
    for key in list(monkeypatch._setenv if hasattr(monkeypatch, "_setenv") else []):
        monkeypatch.delenv(key, raising=False)
    for key in [
        "K1_HOST",
        "K1_BACKEND",
        "K1_MAX_LINEAR_VELOCITY_MPS",
        "K1_MAX_ANGULAR_VELOCITY_RPS",
        "K1_MAX_GRIP_FORCE_N",
        "K1_VISION_MODEL",
        "K1_CAPTURE_DIR",
        "EM_API_URL",
        "EM_WALLET_KEY_PATH",
        "EM_AGENT_ID",
        "EM_WORKER_NAME",
        "LOG_LEVEL",
    ]:
        monkeypatch.delenv(key, raising=False)

    cfg = load_config()
    # Backend always falls back to mock when unset / invalid.
    assert cfg.backend == "mock"
    # Critical: wallet path defaults to empty — NEVER a real key.
    assert cfg.em_wallet_key_path == ""


def test_load_config_invalid_backend_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("K1_BACKEND", "not-a-real-backend")
    cfg = load_config()
    assert cfg.backend == "mock"


def test_load_config_reads_env_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("K1_HOST", "10.0.0.5")
    monkeypatch.setenv("K1_BACKEND", "mock")
    monkeypatch.setenv("K1_MAX_GRIP_FORCE_N", "25.5")
    monkeypatch.setenv("EM_API_URL", "https://staging.execution.market")
    cfg = load_config()
    assert cfg.k1_host == "10.0.0.5"
    assert cfg.max_grip_force_n == 25.5
    assert cfg.em_api_url == "https://staging.execution.market"


# ---------------------------------------------------------------------------
# Hardware backend safety — must not import the SDK at import time
# ---------------------------------------------------------------------------


def test_hardware_backend_raises_clean_import_error_without_sdk(config: K1Config):
    from em_k1_mcp.backends import hardware as hw_mod

    # Test environment has no booster_robotics_sdk installed; the module
    # should still import cleanly, with the import error captured.
    assert hw_mod._booster_sdk is None
    with pytest.raises(ImportError) as excinfo:
        hw_mod.HardwareK1Backend(config)
    assert "booster_robotics_sdk" in str(excinfo.value)


def test_get_backend_falls_back_to_mock_when_hardware_missing(config: K1Config):
    from em_k1_mcp.backends import get_backend

    hardware_cfg = K1Config(**{**config.__dict__, "backend": "hardware"})
    backend = get_backend(hardware_cfg)
    # SDK not installed → fallback to mock with a warning log.
    assert backend.name == "mock"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_structured(result):
    """FastMCP.call_tool returns ``(content_list, structured_content)`` in 1.20+.

    Older / alternate shapes return a single value or a list. Normalize to
    a plain dict for assertion convenience.
    """
    # FastMCP >=1.20 returns CallToolResult-like with .structuredContent
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    # Tuple shape
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        if isinstance(structured, dict):
            return structured
    # Last resort — pull from the content blocks
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, list):
        for block in result:
            data = getattr(block, "data", None)
            if isinstance(data, dict):
                return data
            text = getattr(block, "text", None)
            if isinstance(text, str):
                import json

                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
    raise AssertionError(f"Could not extract structured content from {result!r}")
