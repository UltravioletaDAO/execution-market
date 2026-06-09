"""Manipulation tools: pick, place, grip.

All grip-force inputs are clamped to ``K1_MAX_GRIP_FORCE_N`` before
reaching the backend — this prevents an LLM caller from accidentally
crushing a fragile object even if the tool argument is unbounded by the
MCP schema.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ..backends.base import BaseK1Backend
from ..config import K1Config
from ..models import GripInput, ManipulationResult, PickInput, PlaceInput

logger = logging.getLogger(__name__)


def register_manipulation_tools(
    mcp: FastMCP,
    backend: BaseK1Backend,
    config: K1Config,
) -> None:
    """Attach pick/place/grip tools to ``mcp``."""

    def _clamp_force(name: str, value: float) -> float:
        cap = config.max_grip_force_n
        if value > cap:
            logger.info("Clamped %s force %.2f → %.2f N (safety cap)", name, value, cap)
            return cap
        return value

    @mcp.tool(
        name="k1_pick",
        annotations={
            "title": "Pick Up an Object",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def k1_pick(params: PickInput) -> ManipulationResult:
        """Pick up ``object_id`` (must already be detected by perception)."""
        force = _clamp_force("pick", params.grip_force)
        outcome = await backend.pick(object_id=params.object_id, grip_force=force)
        return ManipulationResult(
            ok=outcome.success,
            backend=backend.name,
            action="pick",
            message=(
                f"Picked up '{params.object_id}' at {force:.1f} N."
                if outcome.success
                else f"Failed to pick '{params.object_id}'."
            ),
            detail=outcome.detail,
        )

    @mcp.tool(
        name="k1_place",
        annotations={
            "title": "Place Held Object at Coordinates",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def k1_place(params: PlaceInput) -> ManipulationResult:
        """Place the currently held object at ``(x_m, y_m, z_m)``."""
        outcome = await backend.place(x_m=params.x_m, y_m=params.y_m, z_m=params.z_m)
        return ManipulationResult(
            ok=outcome.success,
            backend=backend.name,
            action="place",
            message=(
                f"Placed object at ({params.x_m:.2f}, {params.y_m:.2f}, {params.z_m:.2f})."
                if outcome.success
                else "Failed to place object."
            ),
            detail=outcome.detail,
        )

    @mcp.tool(
        name="k1_grip",
        annotations={
            "title": "Close Grippers (force + duration)",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def k1_grip(params: GripInput) -> ManipulationResult:
        """Close the grippers at ``force`` N for ``duration_s`` seconds."""
        force = _clamp_force("grip", params.force)
        outcome = await backend.grip(force=force, duration_s=params.duration_s)
        return ManipulationResult(
            ok=outcome.success,
            backend=backend.name,
            action="grip",
            message=(
                f"Gripped at {force:.1f} N for {params.duration_s:.1f} s."
                if outcome.success
                else "Failed to close grippers."
            ),
            detail=outcome.detail,
        )
