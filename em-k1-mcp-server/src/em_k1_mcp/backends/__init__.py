"""K1 backend abstraction.

The MCP tools always go through :class:`BaseK1Backend` so they don't care
whether the robot is real, simulated, or mocked. :func:`get_backend` picks
an implementation based on configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import BaseK1Backend
from .mock import MockK1Backend

if TYPE_CHECKING:
    from ..config import K1Config

logger = logging.getLogger(__name__)

__all__ = ["BaseK1Backend", "MockK1Backend", "get_backend"]


def get_backend(config: "K1Config") -> BaseK1Backend:
    """Return the backend instance matching ``config.backend``.

    Falls back to :class:`MockK1Backend` if the requested backend cannot be
    instantiated (e.g. ``booster_robotics_sdk`` not installed).
    """
    name = config.backend
    if name == "mock":
        return MockK1Backend(config)
    if name == "isaac_sim":
        # Local import — Isaac Sim deps are optional and heavy.
        from .isaac_sim import IsaacSimK1Backend

        try:
            return IsaacSimK1Backend(config)
        except NotImplementedError as exc:
            logger.warning("Isaac Sim backend not implemented yet (%s) — using mock instead.", exc)
            return MockK1Backend(config)
    if name == "hardware":
        from .hardware import HardwareK1Backend

        try:
            return HardwareK1Backend(config)
        except (ImportError, NotImplementedError) as exc:
            logger.warning(
                "Hardware backend unavailable (%s) — using mock instead. "
                "Install booster-robotics-sdk and connect the K1 to switch backends.",
                exc,
            )
            return MockK1Backend(config)
    # Shouldn't happen — config loader already validates this — but be defensive.
    logger.error("Unknown backend %r, defaulting to mock.", name)
    return MockK1Backend(config)
