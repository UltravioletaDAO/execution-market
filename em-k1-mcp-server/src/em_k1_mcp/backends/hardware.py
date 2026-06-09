"""Real Booster K1 hardware backend.

This module wraps the official ``booster_robotics_sdk`` (provided by
Booster Robotics on K1 delivery). All methods are stubs today — they raise
``NotImplementedError`` with a TODO comment so the wiring is clear when the
robot arrives. Importing ``booster_robotics_sdk`` is guarded so the package
remains installable on machines that don't have the SDK.

Construction order (TODO when robot arrives):

1. ``client = BoosterClient(host=self.config.k1_host)`` — open a connection.
2. ``client.enable_motors()`` — wake actuators.
3. Wire each method below onto the matching SDK call.
4. Wire :meth:`observe` onto ``client.cameras.head.read_frame()`` + an
   external caption call (Anthropic Vision or local VLM).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import BaseK1Backend, ManipulationOutcome, ObservationOutcome, WalkOutcome

logger = logging.getLogger(__name__)

# Soft import — the SDK isn't on PyPI yet, and we don't want this module to
# break installation on developer machines that don't have hardware.
_SDK_IMPORT_ERROR: Optional[Exception] = None
try:  # pragma: no cover — depends on hardware SDK
    import booster_robotics_sdk as _booster_sdk  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    _booster_sdk = None  # type: ignore[assignment]
    _SDK_IMPORT_ERROR = exc


class HardwareK1Backend(BaseK1Backend):
    """Booster K1 SDK wrapper. NOT YET IMPLEMENTED — robot in shipping."""

    name = "hardware"

    def __init__(self, config) -> None:
        super().__init__(config)
        if _booster_sdk is None:
            raise ImportError(
                "booster_robotics_sdk is not installed. Install it manually once the "
                "Booster K1 ships (it is not on PyPI as of 2026-05). Until then, set "
                "K1_BACKEND=mock or K1_BACKEND=isaac_sim. "
                f"Original ImportError: {_SDK_IMPORT_ERROR!r}"
            )
        # TODO: ``self._client = _booster_sdk.BoosterClient(host=config.k1_host)``
        self._client: Any = None
        logger.info("[hardware] HardwareK1Backend constructed (host=%s)", config.k1_host)

    async def connect(self) -> None:
        # TODO: open TCP/UDP connection, run handshake, enable motors.
        raise NotImplementedError(
            "TODO: call self._client.connect() and enable motors via the Booster SDK."
        )

    async def disconnect(self) -> None:
        # TODO: disable motors and close the SDK connection cleanly.
        raise NotImplementedError("TODO: disable motors + self._client.close().")

    # ------------------------------------------------------------------ #
    # Locomotion
    # ------------------------------------------------------------------ #

    async def stand(self) -> ManipulationOutcome:
        # TODO: self._client.locomotion.stand_up()
        raise NotImplementedError("TODO: bind to Booster SDK stand_up().")

    async def sit(self) -> ManipulationOutcome:
        # TODO: self._client.locomotion.sit_down()
        raise NotImplementedError("TODO: bind to Booster SDK sit_down().")

    async def walk_to(
        self,
        target: str,
        x_m: float,
        y_m: float,
        heading_deg: float,
        max_speed_mps: float,
    ) -> WalkOutcome:
        # TODO: self._client.navigation.go_to_pose(x=x_m, y=y_m, theta=heading_deg, ...)
        raise NotImplementedError("TODO: bind to Booster SDK navigation.go_to_pose().")

    async def emergency_stop(self) -> ManipulationOutcome:
        # TODO: self._client.safety.estop() — must work even without a prior connect().
        raise NotImplementedError("TODO: bind to Booster SDK safety.estop().")

    # ------------------------------------------------------------------ #
    # Manipulation
    # ------------------------------------------------------------------ #

    async def pick(self, object_id: str, grip_force: float) -> ManipulationOutcome:
        # TODO: combine SDK perception + grasp planner + execute.
        raise NotImplementedError(
            "TODO: implement pick via Booster SDK manipulation.pick(object_id, force=...)."
        )

    async def place(self, x_m: float, y_m: float, z_m: float) -> ManipulationOutcome:
        # TODO: self._client.manipulation.place(target_pose=...)
        raise NotImplementedError("TODO: bind to Booster SDK manipulation.place().")

    async def grip(self, force: float, duration_s: float) -> ManipulationOutcome:
        # TODO: self._client.manipulation.close_gripper(force=force, duration=duration_s)
        raise NotImplementedError("TODO: bind to Booster SDK manipulation.close_gripper().")

    # ------------------------------------------------------------------ #
    # Perception
    # ------------------------------------------------------------------ #

    async def observe(
        self,
        save_frame: bool,
        caption_prompt: Optional[str],
    ) -> ObservationOutcome:
        # TODO: read frame from head camera, persist if save_frame, caption via configured VLM.
        raise NotImplementedError(
            "TODO: read frame from self._client.cameras.head + caption via "
            "configured K1_VISION_MODEL."
        )
