"""Internal/admin Document Handoff redaction and delivery-path gap note.

This slice consumes the AAS concept-gap implementation roadmap and expands only
its rank-2 Document Handoff maintenance action. It is deliberately not an
operator answer, approval record, answer receipt, customer/worker/public copy,
delivery authorization, legal/notarial/custody claim, or runtime movement.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS,
    ROADMAP_BLOCKED_CLAIMS,
    load_aas_concept_gap_implementation_roadmap,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SCHEMA = (
    "city_ops.aas_document_handoff_redaction_delivery_gap_note.v1"
)
AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_FILENAME = (
    "aas_document_handoff_redaction_delivery_gap_note.json"
)
AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SAFE_CLAIM = (
    "internal_admin_aas_document_handoff_redaction_delivery_gap_note_landed"
)
AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_ID = (
    "execution_market.aas.document_handoff_redaction_delivery_gap_note.2026_06_06_0000"
)
AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_STATUS = (
    "internal_admin_gap_note_no_answer_no_approval_no_delivery_or_authority_promotion"
)

FALSE_FLAGS = {
    "gap_note_records_operator_answer": False,
    "gap_note_records_operator_approval": False,
    "gap_note_creates_answer_receipt": False,
    "gap_note_selects_future_answer": False,
    "gap_note_approves_product_exposure": False,
    "gap_note_creates_customer_public_or_worker_copy": False,
    "gap_note_authorizes_delivery_path_or_recipient": False,
    "gap_note_creates_public_catalog_pricing_quote_or_route": False,
    "gap_note_launches_queue_dispatch_or_worker_instruction": False,
    "gap_note_emits_reputation_or_worker_skill_dna": False,
    "gap_note_reverifies_payment_or_production": False,
    "gap_note_mutates_runtime_acontext_or_irc": False,
    "gap_note_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "gap_note_grants_legal_notarial_custody_or_acceptance_authority": False,
    "gap_note_publishes_worker_copyable_doctrine": False,
    "gap_note_integrates_or_expands_stopped_projects": False,
}

REDACTION_CHECKS = [
    "remove_or_mask_private_person_identifiers_before_any_operator_review_packet",
    "exclude_exact_locations_coordinates_raw_metadata_and_private_context_from_gap_note",
    "exclude_signatures_payment_details_account_numbers_tokens_keys_and_credentials",
    "reference_source_documents_by_non_secret_digest_or_label_not_raw_sensitive_content",
    "keep excerpts bounded_to_visible_document_facts_only_if_a_future_answer_authorizes_them",
]

DELIVERY_PATH_UNKNOWNS = [
    "authorized_recipient_or_review_role_not_selected",
    "authorized_delivery_channel_not_selected",
    "acceptance_criteria_not_recorded",
    "custody_chain_not_authorized",
    "legal_notarial_or_regulatory_sufficiency_not_authorized",
    "customer_facing_format_not_approved",
]

SAFE_LANGUAGE = [
    "observed visible document fields only",
    "redaction pending operator review",
    "delivery path not authorized",
    "custody and legal effect not claimed",
    "future receipt required before customer or worker use",
]

FORBIDDEN_LANGUAGE = [
    "legally accepted",
    "notarized",
    "chain of custody proven",
    "customer ready",
    "deliver to recipient",
    "dispatch worker",
    "public catalog ready",
]

DOCUMENT_HANDOFF_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "document_handoff_gap_note_records_operator_answer",
    "document_handoff_gap_note_records_operator_approval",
    "document_handoff_gap_note_creates_answer_receipt",
    "document_handoff_gap_note_selects_future_answer",
    "document_handoff_gap_note_treats_maintenance_as_approval",
    "document_handoff_gap_note_approves_product_exposure",
    "document_handoff_gap_note_creates_customer_public_or_worker_copy",
    "document_handoff_gap_note_authorizes_recipient_channel_delivery_or_acceptance",
    "document_handoff_gap_note_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "document_handoff_gap_note_creates_worker_instruction",
    "document_handoff_gap_note_emits_erc8004_reputation_or_worker_skill_dna",
    "document_handoff_gap_note_reverifies_payment_or_production",
    "document_handoff_gap_note_mutates_runtime_acontext_or_irc_session_manager",
    "document_handoff_gap_note_releases_exact_gps_raw_metadata_private_context_or_pii",
    "document_handoff_gap_note_grants_legal_notarial_custody_regulatory_or_acceptance_authority",
    "document_handoff_gap_note_publishes_worker_copyable_doctrine",
    "document_handoff_gap_note_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(DOCUMENT_HANDOFF_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "document_handoff_approved",
    "document_handoff_customer_ready",
    "document_handoff_delivery_authorized",
    "document_handoff_legal_ready",
    "document_handoff_notarial_ready",
    "document_handoff_custody_ready",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "runtime_parity_proven",
    "live_acontext_ready",
    "gps_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _document_handoff_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in roadmap.get("roadmap_rows", [])
        if row.get("aas_family") == "document_handoff"
    ]
    if len(rows) != 1:
        raise CityOpsContractError("AAS document handoff gap note source row missing")
    row = rows[0]
    if row.get("planning_sequence_rank") != 2:
        raise CityOpsContractError("AAS document handoff gap note source rank drift")
    if row.get("roadmap_next_planning_slice") != (
        "redaction_and_delivery_path_gap_note_maintenance_only"
    ):
        raise CityOpsContractError("AAS document handoff gap note source action drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("AAS document handoff gap note source row unblocked")
    if row.get("next_allowed_without_human_answer") != "maintenance_only_no_new_approval_artifact":
        raise CityOpsContractError("AAS document handoff gap note source maintenance drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS document handoff gap note source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS document handoff gap note source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS document handoff gap note source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS document handoff gap note source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS document handoff gap note source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS document handoff gap note source selected decision")
    _document_handoff_row(roadmap)
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS document handoff gap note source allowed {key}")


def build_aas_document_handoff_redaction_delivery_gap_note(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative Document Handoff redaction/delivery gap note."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    row = _document_handoff_row(roadmap)

    note = {
        "schema": AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SCHEMA,
        "gap_note_id": AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_ID,
        "gap_note_status": AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_row_family": "document_handoff",
            "consumed_row_rank": row["planning_sequence_rank"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Document Handoff planning",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_decision": None,
            "recommended_no_human_posture": "maintenance_only_no_new_approval_artifact",
        },
        "readiness": dict(FALSE_FLAGS),
        "document_handoff_gap_note": {
            "aas_family": "document_handoff",
            "allowed_use": "internal_admin_redaction_delivery_path_gap_note_maintenance_only",
            "source_backed_current_state": row["source_backed_current_state"],
            "implementation_concept_expansion": row["implementation_concept_expansion"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "maintenance_mode": row["next_allowed_without_human_answer"],
            "redaction_gap_checks": list(REDACTION_CHECKS),
            "delivery_path_unknowns": list(DELIVERY_PATH_UNKNOWNS),
            "safe_internal_language": list(SAFE_LANGUAGE),
            "forbidden_language": list(FORBIDDEN_LANGUAGE),
            "next_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_document_handoff_delivery_publication_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat this note as maintenance only, never as approval or customer copy.",
            "Do not include raw PII, exact GPS, raw metadata, private context, signatures, payment data, or secrets.",
            "Do not authorize recipient, delivery channel, acceptance, custody, legal effect, notarial effect, or customer format from this note.",
            "Create a separate explicit answer receipt before any Document Handoff delivery/publication gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(DOCUMENT_HANDOFF_BLOCKED_CLAIMS),
        },
        "gap_note_digest_sha256": "",
    }
    note["gap_note_digest_sha256"] = _stable_digest(
        {k: v for k, v in note.items() if k != "gap_note_digest_sha256"}
    )
    _assert_gap_note_conservative(note, source_roadmap=roadmap)
    return note


def write_aas_document_handoff_redaction_delivery_gap_note(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Document Handoff redaction/delivery gap note."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    note = build_aas_document_handoff_redaction_delivery_gap_note(artifact_dir=base_dir)
    path = base_dir / AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_FILENAME
    path.write_text(json.dumps(note, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_document_handoff_redaction_delivery_gap_note(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Document Handoff gap note."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    note = json.loads(
        (base_dir / AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_gap_note_conservative(note, source_roadmap=source_roadmap)
    return note


def _assert_gap_note_conservative(
    note: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if note.get("schema") != AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SCHEMA:
        raise CityOpsContractError("AAS document handoff gap note schema drift")
    if note.get("gap_note_id") != AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_ID:
        raise CityOpsContractError("AAS document handoff gap note id drift")
    if note.get("gap_note_status") != AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_STATUS:
        raise CityOpsContractError("AAS document handoff gap note status drift")
    source = note.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS document handoff gap note source digest drift")
    if source.get("consumed_row_family") != "document_handoff" or source.get("consumed_row_rank") != 2:
        raise CityOpsContractError("AAS document handoff gap note consumed wrong row")

    state = note.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS document handoff gap note operator state promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS document handoff gap note selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if note.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS document handoff gap note readiness promoted {key}")

    gap = note.get("document_handoff_gap_note", {})
    if gap.get("aas_family") != "document_handoff":
        raise CityOpsContractError("AAS document handoff gap note family drift")
    if gap.get("allowed_use") != "internal_admin_redaction_delivery_path_gap_note_maintenance_only":
        raise CityOpsContractError("AAS document handoff gap note use drift")
    if gap.get("maintenance_mode") != "maintenance_only_no_new_approval_artifact":
        raise CityOpsContractError("AAS document handoff gap note maintenance mode drift")
    if gap.get("still_blocked") is not True:
        raise CityOpsContractError("AAS document handoff gap note unblocked")
    if gap.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_explicit_operator_answer_receipt_then_document_handoff_delivery_publication_gate"
    ):
        raise CityOpsContractError("AAS document handoff gap note next gate drift")
    if set(REDACTION_CHECKS) - set(gap.get("redaction_gap_checks", [])):
        raise CityOpsContractError("AAS document handoff gap note missing redaction checks")
    if set(DELIVERY_PATH_UNKNOWNS) - set(gap.get("delivery_path_unknowns", [])):
        raise CityOpsContractError("AAS document handoff gap note missing delivery unknowns")
    if set(FORBIDDEN_LANGUAGE) - set(gap.get("forbidden_language", [])):
        raise CityOpsContractError("AAS document handoff gap note missing forbidden language")
    for forbidden in ["customer ready", "deliver to recipient", "legally accepted"]:
        if forbidden in set(gap.get("safe_internal_language", [])):
            raise CityOpsContractError("AAS document handoff gap note safe language promoted")

    safe = set(note.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(note.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS document handoff gap note safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS document handoff gap note forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(DOCUMENT_HANDOFF_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS document handoff gap note missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS document handoff gap note claim overlap: {sorted(overlap)}"
        )

    firewall = note.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS document handoff gap note allowed {key}")
