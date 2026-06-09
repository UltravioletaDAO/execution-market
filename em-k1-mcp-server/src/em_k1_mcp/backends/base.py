"""Abstract backend interface for the Booster K1.

Every backend (mock, Isaac Sim, real hardware) implements this contract.
Tools only depend on :class:`BaseK1Backend` so swapping backends is a
config-only change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ..config import K1Config


@dataclass(frozen=True)
class WalkOutcome:
    """Result of a :meth:`BaseK1Backend.walk_to` call."""

    reached: bool
    final_x_m: float
    final_y_m: float
    final_heading_deg: float
    distance_traveled_m: float
    detail: Dict[str, Any]


@dataclass(frozen=True)
class ManipulationOutcome:
    """Result of a pick/place/grip call."""

    success: bool
    detail: Dict[str, Any]


@dataclass(frozen=True)
class ObservationOutcome:
    """Result of an :meth:`BaseK1Backend.observe` call."""

    frame_path: Optional[str]
    caption: str
    width: int
    height: int
    captured_at_iso: str
    raw_bytes: Optional[bytes] = None


class BaseK1Backend(ABC):
    """Abstract base for all K1 backends.

    Implementations should be safe to instantiate without the robot being
    online — actual connection setup belongs in :meth:`connect`.
    """

    name: str = "base"

    def __init__(self, config: "K1Config") -> None:
        self.config = config
        self._connected = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """Open the connection to the robot/sim. Idempotent."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection. Safe to call multiple times."""

    # ------------------------------------------------------------------ #
    # Locomotion
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def stand(self) -> ManipulationOutcome:
        """Bring the robot to the standing pose."""

    @abstractmethod
    async def sit(self) -> ManipulationOutcome:
        """Bring the robot to the sitting pose."""

    @abstractmethod
    async def walk_to(
        self,
        target: str,
        x_m: float,
        y_m: float,
        heading_deg: float,
        max_speed_mps: float,
    ) -> WalkOutcome:
        """Walk to (x_m, y_m, heading_deg) at the requested speed."""

    @abstractmethod
    async def emergency_stop(self) -> ManipulationOutcome:
        """Cut motion immediately. Always safe to call."""

    # ------------------------------------------------------------------ #
    # Manipulation
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def pick(self, object_id: str, grip_force: float) -> ManipulationOutcome:
        """Pick up ``object_id`` using the requested grip force."""

    @abstractmethod
    async def place(self, x_m: float, y_m: float, z_m: float) -> ManipulationOutcome:
        """Place the held object at the given coordinates."""

    @abstractmethod
    async def grip(self, force: float, duration_s: float) -> ManipulationOutcome:
        """Close grippers at ``force`` for ``duration_s`` seconds."""

    # ------------------------------------------------------------------ #
    # Perception
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def observe(
        self,
        save_frame: bool,
        caption_prompt: Optional[str],
    ) -> ObservationOutcome:
        """Capture a camera frame and produce an AI caption."""
