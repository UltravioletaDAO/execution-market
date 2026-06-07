"""Internal/admin Property Ops blocked-claim quarantine vocabulary.

This slice consumes the AAS concept-gap implementation roadmap and expands only
its rank-8 Property Ops planning action. It is deliberately not an operator
answer, approval record, answer receipt, customer/worker/public copy, property
access authorization, appraisal/code/legal/insurance/remediation opinion,
route/queue/dispatch surface, or runtime movement.
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

AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SCHEMA = (
    "city_ops.aas_property_ops_blocked_claim_quarantine_vocabulary.v1"
)
AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_FILENAME = (
    "aas_property_ops_blocked_claim_quarantine_vocabulary.json"
)
AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SAFE_CLAIM = (
    "internal_admin_aas_property_ops_blocked_claim_quarantine_vocabulary_landed"
)
AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_ID = (
    "execution_market.aas.property_ops.blocked_claim_quarantine_vocabulary.2026_06_07_0000"
)
AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_STATUS = (
    "internal_admin_planning_only_no_answer_no_approval_no_property_access_or_authority"
)

FALSE_FLAGS = {
    "vocabulary_records_operator_answer": False,
    "vocabulary_records_operator_approval": False,
    "vocabulary_creates_answer_receipt": False,
    "vocabulary_selects_future_answer": False,
    "vocabulary_approves_product_exposure": False,
    "vocabulary_creates_customer_public_or_worker_copy": False,
    "vocabulary_authorizes_property_access_site_entry_or_recipient": False,
    "vocabulary_authorizes_inspection_appraisal_code_review_or_legal_review": False,
    "vocabulary_certifies_property_condition_value_compliance_or_safety": False,
    "vocabulary_commits_to_repair_remediation_maintenance_or_insurance_outcome": False,
    "vocabulary_creates_public_catalog_pricing_quote_or_route": False,
    "vocabulary_launches_queue_dispatch_or_worker_instruction": False,
    "vocabulary_emits_reputation_or_worker_skill_dna": False,
    "vocabulary_reverifies_payment_or_production": False,
    "vocabulary_mutates_runtime_acontext_or_irc": False,
    "vocabulary_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "vocabulary_grants_property_legal_code_appraisal_insurance_or_remediation_authority": False,
    "vocabulary_publishes_worker_copyable_doctrine": False,
    "vocabulary_integrates_or_expands_stopped_projects": False,
}

QUARANTINE_VOCABULARY_FIELDS = [
    "property_identifier_placeholder_without_private_location_or_parties",
    "visible_condition_placeholder_without_access_or_entry_authorization",
    "apparent_occupancy_or_use_signal_without_tenancy_or_legal_claim",
    "visible_maintenance_signal_without_repair_or_remediation_commitment",
    "apparent_access_or_obstruction_signal_without_right_of_entry_claim",
    "photo_screenshot_or_text_reference_placeholder_after_redaction_review",
    "code_compliance_appraisal_insurance_and_legal_claims_quarantined",
    "unknowns_and_unresolved_property_ops_questions",
]

VOCABULARY_BOUNDARIES = [
    "record_only_blocked_claim_vocabulary_not_property_ops_authorization",
    "separate_visible_condition_language_from appraisal_code_legal_insurance_or_safety_authority",
    "do_not_infer_right_of_entry_occupancy_status_value_compliance_repair_or_remediation",
    "do_not_publish_address_exact_location_raw_metadata_private_context_or_pii",
    "customer_or_worker_copy_requires_separate_explicit_answer_receipt",
]

SAFE_LANGUAGE = [
    "property ops blocked-claim quarantine vocabulary only",
    "property access and authority claims blocked",
    "visible condition language must not become appraisal, code, legal, insurance, safety, or remediation claims",
    "exact location, private context, and raw metadata remain redacted or absent",
    "future answer receipt required before property ops delivery, customer use, or dispatch",
]

FORBIDDEN_LANGUAGE = [
    "property access authorized",
    "inspection complete",
    "appraisal ready",
    "code compliant",
    "legal sufficient",
    "insurance ready",
    "repair approved",
    "remediation complete",
    "dispatch ready",
]

PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "property_ops_blocked_claim_quarantine_vocabulary_records_operator_answer",
    "property_ops_blocked_claim_quarantine_vocabulary_records_operator_approval",
    "property_ops_blocked_claim_quarantine_vocabulary_creates_answer_receipt",
    "property_ops_blocked_claim_quarantine_vocabulary_selects_future_answer",
    "property_ops_blocked_claim_quarantine_vocabulary_treats_planning_as_approval",
    "property_ops_blocked_claim_quarantine_vocabulary_approves_product_exposure",
    "property_ops_blocked_claim_quarantine_vocabulary_creates_customer_public_or_worker_copy",
    "property_ops_blocked_claim_quarantine_vocabulary_authorizes_property_access_site_entry_recipient_or_customer_use",
    "property_ops_blocked_claim_quarantine_vocabulary_authorizes_inspection_appraisal_code_review_legal_review_or_worker_visit",
    "property_ops_blocked_claim_quarantine_vocabulary_certifies_property_condition_value_compliance_or_safety",
    "property_ops_blocked_claim_quarantine_vocabulary_commits_to_repair_remediation_maintenance_or_insurance_outcome",
    "property_ops_blocked_claim_quarantine_vocabulary_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "property_ops_blocked_claim_quarantine_vocabulary_creates_worker_instruction",
    "property_ops_blocked_claim_quarantine_vocabulary_emits_erc8004_reputation_or_worker_skill_dna",
    "property_ops_blocked_claim_quarantine_vocabulary_reverifies_payment_or_production",
    "property_ops_blocked_claim_quarantine_vocabulary_mutates_runtime_acontext_or_irc_session_manager",
    "property_ops_blocked_claim_quarantine_vocabulary_releases_exact_gps_raw_metadata_private_context_or_pii",
    "property_ops_blocked_claim_quarantine_vocabulary_grants_property_legal_code_appraisal_insurance_or_remediation_authority",
    "property_ops_blocked_claim_quarantine_vocabulary_publishes_worker_copyable_doctrine",
    "property_ops_blocked_claim_quarantine_vocabulary_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "property_ops_approved",
    "property_ops_customer_ready",
    "property_access_authorized",
    "inspection_complete",
    "appraisal_ready",
    "code_compliant",
    "legal_sufficient",
    "insurance_ready",
    "repair_approved",
    "remediation_complete",
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


def _property_ops_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in roadmap.get("roadmap_rows", [])
        if row.get("aas_family") == "property_ops"
    ]
    if len(rows) != 1:
        raise CityOpsContractError("AAS property ops vocabulary source row missing")
    row = rows[0]
    if row.get("planning_sequence_rank") != 8:
        raise CityOpsContractError("AAS property ops vocabulary source rank drift")
    if row.get("roadmap_next_planning_slice") != "blocked_claim_quarantine_vocabulary_only":
        raise CityOpsContractError("AAS property ops vocabulary source action drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("AAS property ops vocabulary source row unblocked")
    if row.get("next_allowed_without_human_answer") != "blocked_claim_quarantine_only":
        raise CityOpsContractError("AAS property ops vocabulary source planning mode drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS property ops vocabulary source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS property ops vocabulary source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS property ops vocabulary source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS property ops vocabulary source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS property ops vocabulary source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS property ops vocabulary source selected decision")
    _property_ops_row(roadmap)
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS property ops vocabulary source allowed {key}")


def build_aas_property_ops_blocked_claim_quarantine_vocabulary(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build conservative Property Ops blocked-claim quarantine vocabulary."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    row = _property_ops_row(roadmap)

    vocabulary = {
        "schema": AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SCHEMA,
        "vocabulary_id": AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_ID,
        "vocabulary_status": AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_row_family": "property_ops",
            "consumed_row_rank": row["planning_sequence_rank"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Property Ops planning",
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
            "recommended_no_human_posture": "blocked_claim_quarantine_only",
        },
        "readiness": dict(FALSE_FLAGS),
        "property_ops_blocked_claim_quarantine_vocabulary": {
            "aas_family": "property_ops",
            "allowed_use": "internal_admin_blocked_claim_quarantine_vocabulary_only",
            "source_backed_current_state": row["source_backed_current_state"],
            "implementation_concept_expansion": row["implementation_concept_expansion"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "planning_mode": row["next_allowed_without_human_answer"],
            "quarantine_vocabulary_fields": list(QUARANTINE_VOCABULARY_FIELDS),
            "vocabulary_boundaries": list(VOCABULARY_BOUNDARIES),
            "safe_internal_language": list(SAFE_LANGUAGE),
            "forbidden_language": list(FORBIDDEN_LANGUAGE),
            "next_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_property_ops_customer_or_dispatch_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat this vocabulary as internal/admin planning only, never as approval, property access, inspection, appraisal, code, legal, insurance, repair, remediation, customer copy, or dispatch authority.",
            "Do not authorize site entry, right of access, worker visits, inspections, appraisals, code reviews, legal reviews, maintenance, repair, or remediation from this vocabulary.",
            "Do not convert visible-condition wording into value, compliance, safety, insurance, habitability, or remediation claims.",
            "Create a separate explicit answer receipt before any Property Ops customer, worker, catalog, route, queue, or dispatch gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_BLOCKED_CLAIMS),
        },
        "vocabulary_digest_sha256": "",
    }
    vocabulary["vocabulary_digest_sha256"] = _stable_digest(
        {k: v for k, v in vocabulary.items() if k != "vocabulary_digest_sha256"}
    )
    _assert_property_ops_vocabulary_conservative(vocabulary, source_roadmap=roadmap)
    return vocabulary


def write_aas_property_ops_blocked_claim_quarantine_vocabulary(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Property Ops blocked-claim quarantine vocabulary."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    vocabulary = build_aas_property_ops_blocked_claim_quarantine_vocabulary(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_FILENAME
    path.write_text(json.dumps(vocabulary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_property_ops_blocked_claim_quarantine_vocabulary(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate persisted Property Ops blocked-claim quarantine vocabulary."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    vocabulary = json.loads(
        (base_dir / AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_property_ops_vocabulary_conservative(vocabulary, source_roadmap=source_roadmap)
    return vocabulary


def _assert_property_ops_vocabulary_conservative(
    vocabulary: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if vocabulary.get("schema") != AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SCHEMA:
        raise CityOpsContractError("AAS property ops vocabulary schema drift")
    if vocabulary.get("vocabulary_id") != AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_ID:
        raise CityOpsContractError("AAS property ops vocabulary id drift")
    if vocabulary.get("vocabulary_status") != AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_STATUS:
        raise CityOpsContractError("AAS property ops vocabulary status drift")
    source = vocabulary.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS property ops vocabulary source digest drift")
    if source.get("consumed_row_family") != "property_ops" or source.get(
        "consumed_row_rank"
    ) != 8:
        raise CityOpsContractError("AAS property ops vocabulary consumed wrong row")

    state = vocabulary.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(
                f"AAS property ops vocabulary operator state promoted {key}"
            )
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS property ops vocabulary selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if vocabulary.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS property ops vocabulary readiness promoted {key}")

    fixture = vocabulary.get("property_ops_blocked_claim_quarantine_vocabulary", {})
    if fixture.get("aas_family") != "property_ops":
        raise CityOpsContractError("AAS property ops vocabulary family drift")
    if fixture.get("allowed_use") != "internal_admin_blocked_claim_quarantine_vocabulary_only":
        raise CityOpsContractError("AAS property ops vocabulary use drift")
    if fixture.get("planning_mode") != "blocked_claim_quarantine_only":
        raise CityOpsContractError("AAS property ops vocabulary planning mode drift")
    if fixture.get("still_blocked") is not True:
        raise CityOpsContractError("AAS property ops vocabulary unblocked")
    if fixture.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_explicit_operator_answer_receipt_then_property_ops_customer_or_dispatch_gate"
    ):
        raise CityOpsContractError("AAS property ops vocabulary next gate drift")
    if set(QUARANTINE_VOCABULARY_FIELDS) - set(fixture.get("quarantine_vocabulary_fields", [])):
        raise CityOpsContractError("AAS property ops vocabulary missing quarantine fields")
    if set(VOCABULARY_BOUNDARIES) - set(fixture.get("vocabulary_boundaries", [])):
        raise CityOpsContractError("AAS property ops vocabulary missing boundaries")
    if set(FORBIDDEN_LANGUAGE) - set(fixture.get("forbidden_language", [])):
        raise CityOpsContractError("AAS property ops vocabulary missing forbidden language")
    for forbidden in [
        "property access authorized",
        "inspection complete",
        "appraisal ready",
        "code compliant",
        "dispatch ready",
    ]:
        if forbidden in set(fixture.get("safe_internal_language", [])):
            raise CityOpsContractError("AAS property ops vocabulary safe language promoted")

    safe = set(vocabulary.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(vocabulary.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS property ops vocabulary safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS property ops vocabulary forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS property ops vocabulary missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS property ops vocabulary claim overlap: {sorted(overlap)}"
        )

    firewall = vocabulary.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS property ops vocabulary allowed {key}")
