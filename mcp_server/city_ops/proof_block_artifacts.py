"""Deterministic proof-block artifact generation for City-as-a-Service.

This module is intentionally tiny: it regenerates the current first CaaS proof
block from reviewed fixtures and compact decision contracts.  The goal is to let
session-rebuild, Acontext-preview, and telemetry consumers read persisted JSON
artifacts without reopening raw transcripts or re-deriving municipal truth.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .closure import build_acontext_export_preview, build_session_rebuild_preview
from .coordination import build_coordination_ledger_events, build_morning_pickup_brief
from .decision_projection import load_json_artifact, project_compact_decision
from .dispatch_guidance import build_dispatch_guidance_block
from .observability import build_proof_block_telemetry_gate
from .parity_scoreboard import build_shared_decision_parity_scoreboard
from .reuse import (
    build_reuse_behavior_scoreboard,
    build_reuse_event,
    build_reuse_observability_row,
    build_worker_instruction_block,
)

PACKAGE_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = PACKAGE_DIR / "fixtures"
DEFAULT_PROOF_ANCHOR_ID = "redirect_outdated_packet_001"
PROOF_BLOCK_FILENAMES = {
    "shared_decision_parity_scoreboard": "city_shared_decision_parity_scoreboard.json",
    "telemetry_gate": "proof_block_telemetry_gate.json",
    "session_rebuild_preview": "session_rebuild_preview.json",
    "acontext_export_preview": "acontext_export_preview.json",
}


def build_redirect_outdated_packet_001_proof_block() -> dict[str, Any]:
    """Build the full persisted proof-block artifact set for the first anchor."""

    review_packet = load_json_artifact(
        FIXTURES_DIR
        / "city_ops_review_cases"
        / f"{DEFAULT_PROOF_ANCHOR_ID}.json"
    )
    freeze_note = load_json_artifact(
        FIXTURES_DIR
        / "proof_anchors"
        / DEFAULT_PROOF_ANCHOR_ID
        / "proof_anchor_freeze_note.json"
    )
    decision = project_compact_decision(review_packet, freeze_note)
    ledger = build_coordination_ledger_events(
        decision,
        occurred_at="2026-05-06T08:20:00Z",
    )
    pickup = build_morning_pickup_brief(decision, ledger)
    dispatch_guidance_block = build_dispatch_guidance_block(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
    )
    reuse_event = build_reuse_event(
        decision,
        task_id="city_task_next_dispatch_001",
        reuse_mode="dispatch",
        behavior_change_class="routing_changed",
        reused_guidance_ids=["guidance_redirect_outdated_packet_001"],
        notes=["prior reviewed redirect learning changed operator-visible routing prep"],
        occurred_at="2026-05-06T08:21:00Z",
    )
    worker_block = build_worker_instruction_block(decision, reuse_event=reuse_event)
    reuse_row = build_reuse_observability_row(decision, reuse_event=reuse_event)
    reuse_scoreboard = build_reuse_behavior_scoreboard(
        decision,
        reuse_event=reuse_event,
        worker_instruction_block=worker_block,
        observability_row=reuse_row,
        supporting_evidence=[
            "prior reviewed redirect episode reused",
            "dispatch routing guidance changed while staying operator-visible",
            "worker-copyable block excluded cautious municipal doctrine",
        ],
        next_review_need=[
            "one repeated redirect case needed before confident worker-copyable promotion"
        ],
    )
    telemetry_gate = build_proof_block_telemetry_gate(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        reuse_observability_row=reuse_row,
        reuse_behavior_scoreboard=reuse_scoreboard,
    )
    session_rebuild_preview = build_session_rebuild_preview(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
    )
    acontext_export_preview = build_acontext_export_preview(
        decision,
        morning_pickup_brief=pickup,
        telemetry_gate=telemetry_gate,
    )
    shared_decision_parity_scoreboard = build_shared_decision_parity_scoreboard(
        decision,
        ledger_events=ledger,
        morning_pickup_brief=pickup,
        dispatch_guidance_block=dispatch_guidance_block,
        reuse_event=reuse_event,
        worker_instruction_block=worker_block,
        reuse_observability_row=reuse_row,
        reuse_behavior_scoreboard=reuse_scoreboard,
        telemetry_gate=telemetry_gate,
        session_rebuild_preview=session_rebuild_preview,
        acontext_export_preview=acontext_export_preview,
    )
    return {
        "decision": decision,
        "ledger_events": ledger,
        "morning_pickup_brief": pickup,
        "dispatch_guidance_block": dispatch_guidance_block,
        "reuse_event": reuse_event,
        "worker_instruction_block": worker_block,
        "reuse_observability_row": reuse_row,
        "reuse_behavior_scoreboard": reuse_scoreboard,
        "shared_decision_parity_scoreboard": shared_decision_parity_scoreboard,
        "telemetry_gate": telemetry_gate,
        "session_rebuild_preview": session_rebuild_preview,
        "acontext_export_preview": acontext_export_preview,
    }


def write_redirect_outdated_packet_001_proof_block(
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Regenerate and write persisted JSON artifacts for the first proof block."""

    proof_block = build_redirect_outdated_packet_001_proof_block()
    artifact_dir = Path(output_dir) if output_dir else _default_proof_block_dir()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}
    for key, filename in PROOF_BLOCK_FILENAMES.items():
        path = artifact_dir / filename
        _write_json(path, proof_block[key])
        written[key] = path
    return written


def _default_proof_block_dir() -> Path:
    return FIXTURES_DIR / "proof_blocks" / DEFAULT_PROOF_ANCHOR_ID


def _write_json(path: Path, artifact: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate deterministic CaaS proof-block JSON artifacts."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write artifacts to the proof_blocks fixture directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="optional output directory for --write",
    )
    args = parser.parse_args(argv)

    if args.write:
        written = write_redirect_outdated_packet_001_proof_block(args.output_dir)
        for key, path in written.items():
            print(f"{key}: {path}")
    else:
        proof_block = build_redirect_outdated_packet_001_proof_block()
        printable = {key: proof_block[key] for key in PROOF_BLOCK_FILENAMES}
        print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
