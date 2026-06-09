"""Perception tools: ``k1_observe``.

Captures a frame from the K1's head camera and returns an AI caption. The
caption model is determined by ``K1_VISION_MODEL`` (default Claude Opus
4.7) — the mock backend returns a deterministic synthetic caption so this
tool can be tested without any model credentials.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ..backends.base import BaseK1Backend
from ..config import K1Config
from ..models import ObserveInput, ObserveResult

logger = logging.getLogger(__name__)


def register_perception_tools(
    mcp: FastMCP,
    backend: BaseK1Backend,
    config: K1Config,
) -> None:
    """Attach perception tools to ``mcp``."""

    @mcp.tool(
        name="k1_observe",
        annotations={
            "title": "Observe Surroundings (camera + AI caption)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def k1_observe(params: ObserveInput) -> ObserveResult:
        """Capture a head-camera frame and produce an AI caption.

        Args:
            params: ``save_frame`` writes the frame to ``K1_CAPTURE_DIR``;
                ``caption_prompt`` is an optional steering prompt for the
                vision model (defaults to a generic "describe the scene"
                prompt).

        Returns:
            :class:`ObserveResult` with ``frame_path`` (or ``None`` if the
            frame couldn't be persisted) and the caption text.
        """
        outcome = await backend.observe(
            save_frame=params.save_frame,
            caption_prompt=params.caption_prompt,
        )
        message = f"Observed {outcome.width}x{outcome.height} frame via {config.vision_model}."
        return ObserveResult(
            ok=True,
            backend=backend.name,
            message=message,
            frame_path=outcome.frame_path,
            caption=outcome.caption,
            width=outcome.width,
            height=outcome.height,
            captured_at_iso=outcome.captured_at_iso,
        )
