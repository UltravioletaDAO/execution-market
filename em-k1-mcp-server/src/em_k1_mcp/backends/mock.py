"""Mock backend — works without any robot, simulator, or network.

This backend is the default in CI/CD and on developer laptops while the
physical K1 is in shipping. It returns deterministic, plausible-looking
results so MCP tool wiring, unit tests, and Claude Code integration can be
exercised end to end.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .base import BaseK1Backend, ManipulationOutcome, ObservationOutcome, WalkOutcome

logger = logging.getLogger(__name__)


class MockK1Backend(BaseK1Backend):
    """In-memory K1 stand-in."""

    name = "mock"

    def __init__(self, config) -> None:
        super().__init__(config)
        # Robot pose in the map frame.
        self._x_m: float = 0.0
        self._y_m: float = 0.0
        self._heading_deg: float = 0.0
        self._posture: str = "sitting"
        self._holding: Optional[str] = None
        self._frame_counter: int = 0

    async def connect(self) -> None:
        self._connected = True
        logger.info("[mock] connect() — virtual K1 at host=%s", self.config.k1_host)

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("[mock] disconnect()")

    # ------------------------------------------------------------------ #
    # Locomotion
    # ------------------------------------------------------------------ #

    async def stand(self) -> ManipulationOutcome:
        await self.connect()
        self._posture = "standing"
        return ManipulationOutcome(success=True, detail={"posture": "standing"})

    async def sit(self) -> ManipulationOutcome:
        await self.connect()
        self._posture = "sitting"
        return ManipulationOutcome(success=True, detail={"posture": "sitting"})

    async def walk_to(
        self,
        target: str,
        x_m: float,
        y_m: float,
        heading_deg: float,
        max_speed_mps: float,
    ) -> WalkOutcome:
        await self.connect()
        # If we're sitting, stand up first (matches real K1 firmware behavior).
        if self._posture != "standing":
            self._posture = "standing"

        dx = x_m - self._x_m
        dy = y_m - self._y_m
        distance = math.hypot(dx, dy)

        self._x_m = float(x_m)
        self._y_m = float(y_m)
        self._heading_deg = float(heading_deg)

        return WalkOutcome(
            reached=True,
            final_x_m=self._x_m,
            final_y_m=self._y_m,
            final_heading_deg=self._heading_deg,
            distance_traveled_m=distance,
            detail={
                "target": target,
                "max_speed_mps": max_speed_mps,
                "posture": self._posture,
            },
        )

    async def emergency_stop(self) -> ManipulationOutcome:
        # E-stop is the one call that's valid even when not connected.
        self._posture = "estopped"
        self._holding = None
        return ManipulationOutcome(success=True, detail={"posture": "estopped"})

    # ------------------------------------------------------------------ #
    # Manipulation
    # ------------------------------------------------------------------ #

    async def pick(self, object_id: str, grip_force: float) -> ManipulationOutcome:
        await self.connect()
        self._holding = object_id
        return ManipulationOutcome(
            success=True,
            detail={"object_id": object_id, "grip_force": grip_force},
        )

    async def place(self, x_m: float, y_m: float, z_m: float) -> ManipulationOutcome:
        await self.connect()
        placed = self._holding
        self._holding = None
        return ManipulationOutcome(
            success=True,
            detail={
                "placed_object": placed,
                "x_m": x_m,
                "y_m": y_m,
                "z_m": z_m,
            },
        )

    async def grip(self, force: float, duration_s: float) -> ManipulationOutcome:
        await self.connect()
        return ManipulationOutcome(
            success=True,
            detail={"force": force, "duration_s": duration_s},
        )

    # ------------------------------------------------------------------ #
    # Perception
    # ------------------------------------------------------------------ #

    async def observe(
        self,
        save_frame: bool,
        caption_prompt: Optional[str],
    ) -> ObservationOutcome:
        await self.connect()
        self._frame_counter += 1
        captured_at = datetime.now(timezone.utc).isoformat()

        frame_path: Optional[str] = None
        if save_frame:
            capture_dir = Path(self.config.capture_dir)
            try:
                capture_dir.mkdir(parents=True, exist_ok=True)
                # Write a small placeholder file — the real backend would
                # dump JPEG bytes here.
                path = capture_dir / f"mock_frame_{self._frame_counter:04d}.txt"
                path.write_text(
                    f"mock K1 frame #{self._frame_counter} @ {captured_at}\n",
                    encoding="utf-8",
                )
                frame_path = str(path)
            except OSError as exc:
                logger.warning("[mock] failed to write capture file: %s", exc)
                frame_path = None

        caption = self._build_caption(caption_prompt)

        return ObservationOutcome(
            frame_path=frame_path,
            caption=caption,
            width=640,
            height=480,
            captured_at_iso=captured_at,
            raw_bytes=None,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _build_caption(self, prompt: Optional[str]) -> str:
        base = (
            f"[mock] Standing in a plain indoor room. Robot is {self._posture}, "
            f"holding={self._holding or 'nothing'}, "
            f"pose=({self._x_m:.2f}, {self._y_m:.2f}, {self._heading_deg:.0f}deg)."
        )
        if prompt:
            base += f" (Prompt hint: {prompt})"
        return base
