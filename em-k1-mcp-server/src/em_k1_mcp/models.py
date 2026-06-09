"""Pydantic input/output models for the em-k1-mcp tools.

Every MCP tool takes a single ``params`` model (matches the pattern used in
``mcp_server/`` for the main Execution Market server) and returns a typed
output model. Outputs always carry ``ok: bool``, ``backend: str``, and a
human-readable ``message`` so MCP clients (and humans reading logs) can
quickly tell what happened.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

BackendName = Literal["mock", "isaac_sim", "hardware"]


# ---------------------------------------------------------------------------
# Shared output base
# ---------------------------------------------------------------------------


class K1ToolResult(BaseModel):
    """Base shape returned by every K1 tool."""

    model_config = ConfigDict(extra="allow")

    ok: bool = Field(..., description="True if the action completed without error.")
    backend: BackendName = Field(..., description="Backend that executed the call.")
    message: str = Field(..., description="Human-readable status line.")


# ---------------------------------------------------------------------------
# Locomotion
# ---------------------------------------------------------------------------


class StandInput(BaseModel):
    """Inputs for ``k1_stand`` — no parameters required."""

    model_config = ConfigDict(extra="forbid")


class SitInput(BaseModel):
    """Inputs for ``k1_sit`` — no parameters required."""

    model_config = ConfigDict(extra="forbid")


class WalkToInput(BaseModel):
    """Inputs for ``k1_walk_to`` — drive to a target pose."""

    model_config = ConfigDict(extra="forbid")

    target: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Human-readable label for the destination (e.g. 'kitchen').",
    )
    x_m: float = Field(..., description="Target X coordinate in meters (map frame).")
    y_m: float = Field(..., description="Target Y coordinate in meters (map frame).")
    heading_deg: float = Field(
        0.0,
        ge=-360.0,
        le=360.0,
        description="Final heading in degrees (0 = +X axis).",
    )
    max_speed_mps: float = Field(
        0.4,
        gt=0.0,
        le=1.5,
        description="Requested speed cap (clamped by server-side safety limit).",
    )


class WalkToResult(K1ToolResult):
    """Output for ``k1_walk_to``."""

    target: str
    reached: bool
    final_pose: Dict[str, float]


class EmergencyStopInput(BaseModel):
    """Inputs for ``k1_emergency_stop`` — no parameters."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Manipulation
# ---------------------------------------------------------------------------


class PickInput(BaseModel):
    """Inputs for ``k1_pick``."""

    model_config = ConfigDict(extra="forbid")

    object_id: str = Field(..., min_length=1, max_length=120)
    grip_force: float = Field(
        15.0,
        gt=0.0,
        le=100.0,
        description="Grip force in Newtons (clamped by server-side cap).",
    )


class PlaceInput(BaseModel):
    """Inputs for ``k1_place``."""

    model_config = ConfigDict(extra="forbid")

    x_m: float
    y_m: float
    z_m: float = Field(..., ge=0.0, le=2.0)


class GripInput(BaseModel):
    """Inputs for ``k1_grip``."""

    model_config = ConfigDict(extra="forbid")

    force: float = Field(..., gt=0.0, le=100.0)
    duration_s: float = Field(..., gt=0.0, le=60.0)


class ManipulationResult(K1ToolResult):
    """Output for pick / place / grip tools."""

    action: Literal["pick", "place", "grip"]
    detail: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Perception
# ---------------------------------------------------------------------------


class ObserveInput(BaseModel):
    """Inputs for ``k1_observe``."""

    model_config = ConfigDict(extra="forbid")

    save_frame: bool = Field(
        True,
        description="If true, persist the captured frame under capture_dir.",
    )
    caption_prompt: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional prompt steering the AI caption.",
    )


class ObserveResult(K1ToolResult):
    """Output for ``k1_observe``."""

    frame_path: Optional[str]
    caption: str
    width: int
    height: int
    captured_at_iso: str


# ---------------------------------------------------------------------------
# Execution Market integration
# ---------------------------------------------------------------------------


class ClaimTaskInput(BaseModel):
    """Inputs for ``em_claim_task``."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=1)
    evidence_url: str = Field(
        ...,
        min_length=1,
        description="Pre-uploaded evidence URL (S3/CloudFront/IPFS) included with the claim.",
    )


class ClaimTaskResult(BaseModel):
    """Output for ``em_claim_task``."""

    model_config = ConfigDict(extra="allow")

    ok: bool
    task_id: str
    application_id: Optional[str] = None
    status: Optional[str] = None
    message: str


class SubmitEvidenceInput(BaseModel):
    """Inputs for ``em_submit_evidence``."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=1)
    photo_path: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form metadata: GPS, sensor readings, captions, timestamps, etc.",
    )


class SubmitEvidenceResult(BaseModel):
    """Output for ``em_submit_evidence``."""

    model_config = ConfigDict(extra="allow")

    ok: bool
    task_id: str
    submission_id: Optional[str] = None
    status: Optional[str] = None
    message: str
