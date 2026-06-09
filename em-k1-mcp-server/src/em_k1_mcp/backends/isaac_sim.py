"""Isaac Sim backend stub.

The plan is to drive the K1 inside NVIDIA Isaac Sim before the real
hardware arrives. Isaac requires a heavy install (Omniverse + Python
extension) and a workstation with a recent NVIDIA GPU, so this module is
intentionally a thin stub. Every method raises :class:`NotImplementedError`
with a TODO pointing at the corresponding implementation work item.

When you start filling this in:

* Use ``omni.isaac.kit.SimulationApp`` to launch a headless instance.
* Bind to the K1 URDF / USD asset and wire actions through the
  ``omni.isaac.core.controllers`` API.
* Map :meth:`stand`, :meth:`sit`, :meth:`walk_to` onto Booster Robotics'
  ROS-style action interface (same one HardwareK1Backend wraps).
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import BaseK1Backend, ManipulationOutcome, ObservationOutcome, WalkOutcome

logger = logging.getLogger(__name__)


class IsaacSimK1Backend(BaseK1Backend):
    """Stub for the NVIDIA Isaac Sim backend."""

    name = "isaac_sim"

    def __init__(self, config) -> None:
        super().__init__(config)
        # TODO: instantiate omni.isaac.kit.SimulationApp here when ready.
        logger.warning(
            "[isaac_sim] backend is a stub — every call will raise "
            "NotImplementedError. Switch K1_BACKEND=mock for now."
        )

    async def connect(self) -> None:
        raise NotImplementedError(
            "TODO: spin up Isaac Sim SimulationApp and load the K1 USD scene."
        )

    async def disconnect(self) -> None:
        raise NotImplementedError("TODO: tear down Isaac Sim SimulationApp.")

    async def stand(self) -> ManipulationOutcome:
        raise NotImplementedError("TODO: drive joints to standing pose in Isaac Sim.")

    async def sit(self) -> ManipulationOutcome:
        raise NotImplementedError("TODO: drive joints to sitting pose in Isaac Sim.")

    async def walk_to(
        self,
        target: str,
        x_m: float,
        y_m: float,
        heading_deg: float,
        max_speed_mps: float,
    ) -> WalkOutcome:
        raise NotImplementedError(
            "TODO: dispatch a navigate-to-pose action through the Isaac Sim Nav stack."
        )

    async def emergency_stop(self) -> ManipulationOutcome:
        raise NotImplementedError("TODO: pause Isaac Sim and zero out all motor commands.")

    async def pick(self, object_id: str, grip_force: float) -> ManipulationOutcome:
        raise NotImplementedError("TODO: pick via Isaac Sim manipulation pipeline.")

    async def place(self, x_m: float, y_m: float, z_m: float) -> ManipulationOutcome:
        raise NotImplementedError("TODO: place via Isaac Sim manipulation pipeline.")

    async def grip(self, force: float, duration_s: float) -> ManipulationOutcome:
        raise NotImplementedError("TODO: control gripper effort in Isaac Sim.")

    async def observe(
        self,
        save_frame: bool,
        caption_prompt: Optional[str],
    ) -> ObservationOutcome:
        raise NotImplementedError(
            "TODO: render an Isaac Sim camera frame and caption it with the configured VLM."
        )
