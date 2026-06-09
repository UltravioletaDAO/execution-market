"""Configuration loader for em-k1-mcp-server.

Reads from environment variables (and optionally a local ``.env`` file via
``python-dotenv``). NO secret value should ever be hardcoded — anything
sensitive lives in the user's local ``.env`` or AWS Secrets Manager.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:  # pragma: no cover — declared in deps, but keep safe
    _DOTENV_AVAILABLE = False

logger = logging.getLogger(__name__)

BackendName = Literal["mock", "isaac_sim", "hardware"]


@dataclass(frozen=True)
class K1Config:
    """Immutable runtime configuration for em-k1-mcp-server."""

    # Robot connection
    k1_host: str = "127.0.0.1"
    backend: BackendName = "mock"

    # Motion safety caps (clamped server-side regardless of tool input)
    max_linear_velocity_mps: float = 0.6
    max_angular_velocity_rps: float = 0.8
    max_grip_force_n: float = 40.0

    # Perception
    vision_model: str = "claude-opus-4-7"
    capture_dir: Path = field(default_factory=lambda: Path("./captures"))

    # Execution Market integration
    em_api_url: str = "https://api.execution.market"
    em_wallet_key_path: str = ""
    em_agent_id: str = ""
    em_worker_name: str = "k1-executor"

    # Logging
    log_level: str = "INFO"


def _load_dotenv_if_present() -> None:
    """Load ``.env`` from CWD (or its parents) when available."""
    if not _DOTENV_AVAILABLE:
        return
    try:
        load_dotenv(override=False)
    except Exception as exc:  # pragma: no cover
        logger.debug("dotenv load failed: %s", exc)


def _coerce_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Env %s=%r is not a float — using default %s", name, raw, default)
        return default


def _coerce_backend(raw: str | None) -> BackendName:
    candidate = (raw or "mock").strip().lower()
    if candidate not in {"mock", "isaac_sim", "hardware"}:
        logger.warning("K1_BACKEND=%r is not a valid backend, falling back to 'mock'", candidate)
        return "mock"
    return candidate  # type: ignore[return-value]


def load_config() -> K1Config:
    """Read configuration from environment (and ``.env`` if present)."""
    _load_dotenv_if_present()

    capture_dir = Path(os.environ.get("K1_CAPTURE_DIR", "./captures"))

    cfg = K1Config(
        k1_host=os.environ.get("K1_HOST", "127.0.0.1"),
        backend=_coerce_backend(os.environ.get("K1_BACKEND")),
        max_linear_velocity_mps=_coerce_float("K1_MAX_LINEAR_VELOCITY_MPS", 0.6),
        max_angular_velocity_rps=_coerce_float("K1_MAX_ANGULAR_VELOCITY_RPS", 0.8),
        max_grip_force_n=_coerce_float("K1_MAX_GRIP_FORCE_N", 40.0),
        vision_model=os.environ.get("K1_VISION_MODEL", "claude-opus-4-7"),
        capture_dir=capture_dir,
        em_api_url=os.environ.get("EM_API_URL", "https://api.execution.market"),
        em_wallet_key_path=os.environ.get("EM_WALLET_KEY_PATH", ""),
        em_agent_id=os.environ.get("EM_AGENT_ID", ""),
        em_worker_name=os.environ.get("EM_WORKER_NAME", "k1-executor"),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )
    return cfg
