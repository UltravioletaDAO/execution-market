"""Locomotion tools: stand, sit, walk_to, emergency_stop.

All four tools clamp incoming requests against the configured safety caps
before handing off to the backend, so a misbehaving caller can't drive the
K1 above the velocity / force the operator approved at startup.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ..backends.base import BaseK1Backend
from ..config import K1Config
from ..models import (
    EmergencyStopInput,
    K1ToolResult,
    SitInput,
    StandInput,
    WalkToInput,
    WalkToResult,
)

logger = logging.getLogger(__name__)


def register_locomotion_tools(
    mcp: FastMCP,
    backend: BaseK1Backend,
    config: K1Config,
) -> None:
    """Attach locomotion tools to ``mcp``."""

    @mcp.tool(
        name="k1_stand",
        annotations={
            "title": "Stand Up the K1",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def k1_stand(params: StandInput) -> K1ToolResult:
        """Bring the K1 from any pose to a stable standing pose.

        Idempotent: calling stand while already standing is a no-op.
        """
        del params  # no parameters
        outcome = await backend.stand()
        return K1ToolResult(
            ok=outcome.success,
            backend=backend.name,
            message="K1 standing." if outcome.success else "Failed to stand.",
            detail=outcome.detail,
        )

    @mcp.tool(
        name="k1_sit",
        annotations={
            "title": "Sit Down the K1",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def k1_sit(params: SitInput) -> K1ToolResult:
        """Bring the K1 to a stable sitting pose (resting position)."""
        del params
        outcome = await backend.sit()
        return K1ToolResult(
            ok=outcome.success,
            backend=backend.name,
            message="K1 sitting." if outcome.success else "Failed to sit.",
            detail=outcome.detail,
        )

    @mcp.tool(
        name="k1_walk_to",
        annotations={
            "title": "Walk to Target Pose",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def k1_walk_to(params: WalkToInput) -> WalkToResult:
        """Drive the K1 to ``(x_m, y_m, heading_deg)`` at ``max_speed_mps``.

        The requested speed is silently clamped to the server-side
        ``K1_MAX_LINEAR_VELOCITY_MPS`` safety cap.
        """
        speed = min(params.max_speed_mps, config.max_linear_velocity_mps)
        if speed < params.max_speed_mps:
            logger.info(
                "Clamped walk speed %.2f → %.2f m/s (safety cap)",
                params.max_speed_mps,
                speed,
            )
        outcome = await backend.walk_to(
            target=params.target,
            x_m=params.x_m,
            y_m=params.y_m,
            heading_deg=params.heading_deg,
            max_speed_mps=speed,
        )
        return WalkToResult(
            ok=outcome.reached,
            backend=backend.name,
            message=(
                f"Reached '{params.target}' ({outcome.distance_traveled_m:.2f} m traveled)."
                if outcome.reached
                else f"Failed to reach '{params.target}'."
            ),
            target=params.target,
            reached=outcome.reached,
            final_pose={
                "x_m": outcome.final_x_m,
                "y_m": outcome.final_y_m,
                "heading_deg": outcome.final_heading_deg,
            },
            detail=outcome.detail,
        )

    @mcp.tool(
        name="k1_emergency_stop",
        annotations={
            "title": "Emergency Stop (halt all motion)",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def k1_emergency_stop(params: EmergencyStopInput) -> K1ToolResult:
        """Halt every actuator immediately.

        ALWAYS safe to call — even if the K1 is not currently connected this
        tool returns ``ok=True`` so callers can use it as a guaranteed safety
        action.
        """
        del params
        outcome = await backend.emergency_stop()
        return K1ToolResult(
            ok=outcome.success,
            backend=backend.name,
            message="Emergency stop engaged.",
            detail=outcome.detail,
        )
