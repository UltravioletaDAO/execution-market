"""Internal packaging/pricing/operator-workflow packet for the three held AAS families.

This module intentionally follows the no-customer-exposure fork after the May 14
three-family AAS readiness matrix. It packages the three explicit internal/admin
hold decisions for review by humans, but it does not approve customer copy,
publication, delivery, public catalog routes, pilot exposure, dispatch, live
Acontext/runtime parity, ERC-8004 reputation, exact GPS/raw metadata release, or
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .compliance_desk_sample_output_review_decision import (
    COMPLIANCE_DESK_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    COMPLIANCE_DESK_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    build_compliance_desk_sample_output_review_decision,
)
from .contracts import CityOpsContractError
from .document_handoff_sample_output_review_decision import (
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    build_document_handoff_sample_output_review_decision,
)
from .incident_verification_sample_output_review_decision import (
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    build_incident_verification_sample_output_review_decision,
)

AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA = (
    "city_ops.aas_three_family_packaging_review_packet.v1"
)
AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME = (
    "aas_three_family_packaging_review_packet.json"
)
AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM = (
    "aas_three_family_packaging_review_packet_landed"
)

PACKET_ID = "execution_market.aas.three_family_packaging_review_packet.001"
SCOPE = "internal_admin_packaging_pricing_operator_workflow_review_only"
REVIEW_MODE = "no_customer_exposure_all_families_remain_held"

SOURCE_DECISION_SPECS = [
    {
        "key": "compliance_desk",
        "family_id": "compliance_desk_as_a_service",
        "family_label": "Compliance Desk as a Service",
        "offer_id": "visible_posting_notice_compliance_snapshot",
        "source_file": COMPLIANCE_DESK_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
        "latest_safe_claim": COMPLIANCE_DESK_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        "blocked_authority_class": "legal/regulator/inspection/compliance guarantees",
        "package_label": "Visible posting / notice compliance snapshot",
        "pricing_review_unit": "one reviewed visible-state evidence packet plus operator limitation review",
        "operator_queue": "posting-or-notice reality check queue",
    },
    {
        "key": "document_handoff",
        "family_id": "document_handoff_logistics_as_a_service",
        "family_label": "Document / Handoff Logistics as a Service",
        "offer_id": "document_handoff_proof_run",
        "source_file": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
        "latest_safe_claim": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        "blocked_authority_class": (
            "legal service/notarial/private-identity/acceptance/filing/custody guarantees"
        ),
        "package_label": "Document handoff proof run",
        "pricing_review_unit": "one bounded chain-of-custody attempt plus receipt/failure classification review",
        "operator_queue": "document movement proof queue",
    },
    {
        "key": "incident_verification",
        "family_id": "incident_verification_as_a_service",
        "family_label": "Incident Verification as a Service",
        "offer_id": "one_location_incident_state_snapshot",
        "source_file": INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
        "latest_safe_claim": INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        "blocked_authority_class": (
            "emergency/safety/repair/insurance/SLA/official-report/fault-liability claims"
        ),
        "package_label": "One-location incident state snapshot",
        "pricing_review_unit": "one time-bound visible-state evidence packet plus uncertainty/next-step review",
        "operator_queue": "incident-state verification queue",
    },
]

READINESS_FALSE_FLAGS = [
    "customer_copy_ready",
    "customer_delivery_approved",
    "customer_delivery_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "public_route_ready",
    "controlled_pilot_ready",
    "controlled_pilot_authorized",
    "front_door_sku_ready",
    "operator_publish_approval",
    "publication_approved",
    "dispatch_enabled",
    "dispatch_instruction_ready",
    "autonomous_dispatch_ready",
    "emits_reputation_receipts",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "raw_metadata_release_ready",
    "legal_or_regulator_authority_ready",
    "emergency_or_safety_authority_ready",
    "notarial_or_custody_authority_ready",
    "customer_public_launch_ready",
]

PACKET_BLOCKED_CLAIMS = [
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "public_route_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "operator_publish_approval",
    "publication_approved",
    "dispatch_enabled",
    "dispatch_instruction_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "reputation_receipt_attachable",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "raw_metadata_release_ready",
    "legal_or_regulator_authority_ready",
    "legal_sufficiency",
    "regulator_acceptance",
    "official_inspection",
    "legal_service",
    "notarial_act_without_separate_credential_scope",
    "private_identity_verification_ready",
    "custody_guarantee_ready",
    "emergency_response_ready",
    "safety_certification_ready",
    "repair_or_insurance_or_sla_ready",
    "official_incident_report_ready",
    "fault_or_liability_assignment_ready",
    "public_price_approved",
    "customer_price_quote_ready",
    "operator_workflow_launch_ready",
    "customer_public_launch_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(PACKET_BLOCKED_CLAIMS) | {
    "customer_copy",
    "customer_output_ready",
    "publishable",
    "publication_ready",
    "catalog_ready",
    "pilot_ready",
    "route_ready",
    "dispatch_ready",
    "reputation_ready",
    "gps_release_ready",
    "public_price_ready",
    "customer_delivery_approval",
}

REQUIRED_HOLD_FIELDS = [
    "operator_approval_granted",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "sample_output_publishable",
    "customer_copy_ready",
    "public_service_catalog_ready",
]


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _default_source_decisions() -> dict[str, dict[str, Any]]:
    return {
        "compliance_desk": build_compliance_desk_sample_output_review_decision(),
        "document_handoff": build_document_handoff_sample_output_review_decision(),
        "incident_verification": build_incident_verification_sample_output_review_decision(),
    }


def _validate_source_decision(spec: dict[str, str], decision: dict[str, Any]) -> None:
    if decision.get("package_family_id") != spec["family_id"]:
        raise CityOpsContractError(f"source family drift for {spec['key']}")
    if decision.get("offer_id") != spec["offer_id"]:
        raise CityOpsContractError(f"source offer drift for {spec['key']}")
    if decision.get("review_decision") != "hold_not_approved_not_publishable":
        raise CityOpsContractError(f"source decision not held for {spec['key']}")
    if decision.get("explicit_hold_decision_recorded") is not True:
        raise CityOpsContractError(f"source hold missing for {spec['key']}")
    if decision.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError(f"source promoted ladder boundary for {spec['key']}")
    for field in REQUIRED_HOLD_FIELDS:
        if decision.get(field) is not False:
            raise CityOpsContractError(f"source promoted readiness {field} for {spec['key']}")
    if spec["latest_safe_claim"] not in decision.get("safe_to_claim", []):
        raise CityOpsContractError(f"source safe claim missing for {spec['key']}")
    forbidden = set(decision.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden:
        raise CityOpsContractError(f"source forbidden safe claims for {spec['key']}: {sorted(forbidden)}")


def _source_summary(spec: dict[str, str], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": spec["key"],
        "family_id": spec["family_id"],
        "offer_id": spec["offer_id"],
        "source_file": spec["source_file"],
        "source_schema": decision.get("schema"),
        "source_decision_id": decision.get("decision_id"),
        "source_digest_sha256": _canonical_digest(decision),
        "review_decision": decision.get("review_decision"),
        "latest_safe_claim": spec["latest_safe_claim"],
        "customer_delivery_approval": False,
        "publication_approved": False,
        "promotion_allowed": False,
    }


def _review_row(spec: dict[str, str], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": spec["key"],
        "family_id": spec["family_id"],
        "family_label": spec["family_label"],
        "offer_id": spec["offer_id"],
        "current_ladder_step": "explicit_internal_admin_sample_output_hold_decision",
        "source_decision_file": spec["source_file"],
        "latest_safe_claim": spec["latest_safe_claim"],
        "blocked_authority_class": spec["blocked_authority_class"],
        "package_label_for_review": spec["package_label"],
        "pricing_review_unit": spec["pricing_review_unit"],
        "operator_queue_for_review": spec["operator_queue"],
        "packaging_state": "internal_admin_package_candidate_only",
        "pricing_state": "pricing_inputs_reviewable_but_no_public_price_or_quote_approved",
        "operator_workflow_state": "queue_and_review_steps_discussable_but_not_launch_ready",
        "operator_workflow_steps_for_review": [
            "intake_question_capture",
            "evidence_contract_selection",
            "reviewed_fixture_or_package_record_lookup",
            "operator_limitation_and_redaction_review",
            "explicit_hold_or_separate_human_approval_decision",
        ],
        "next_smallest_gate": (
            "separate human-operator approval artifact for exactly one held text boundary, "
            "only if customer exposure is explicitly desired"
        ),
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "do_not_promote_from_source": decision.get("do_not_claim_yet", []),
    }


def build_aas_three_family_packaging_review_packet(
    source_decisions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the internal three-family packaging/pricing/workflow review packet."""

    sources = source_decisions or _default_source_decisions()
    missing = {spec["key"] for spec in SOURCE_DECISION_SPECS} - set(sources)
    if missing:
        raise CityOpsContractError(f"missing source decisions: {sorted(missing)}")

    safe_to_claim: list[str] = []
    blocked_claims: list[str] = list(PACKET_BLOCKED_CLAIMS)
    source_summaries: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []

    for spec in SOURCE_DECISION_SPECS:
        decision = sources[spec["key"]]
        _validate_source_decision(spec, decision)
        safe_to_claim.extend(decision.get("safe_to_claim", []))
        blocked_claims.extend(decision.get("do_not_claim_yet", []))
        source_summaries.append(_source_summary(spec, decision))
        review_rows.append(_review_row(spec, decision))

    safe_to_claim = _unique(safe_to_claim + [AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM])
    do_not_claim_yet = _unique(blocked_claims)

    packet = {
        "schema": AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA,
        "packet_id": PACKET_ID,
        "scope": SCOPE,
        "review_mode": REVIEW_MODE,
        "source_decision_files": [spec["source_file"] for spec in SOURCE_DECISION_SPECS],
        "source_decisions": source_summaries,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "summary": {
            "families_reviewed": 3,
            "all_families_at_explicit_hold_decision": True,
            "all_customer_delivery_blocked": True,
            "all_publication_blocked": True,
            "all_dispatch_and_reputation_blocked": True,
            "recommended_use": (
                "Use as an internal packaging, pricing-input, and operator-queue review packet; "
                "not as approval for customer exposure."
            ),
        },
        "review_rows": review_rows,
        "packaging_review_boundaries": {
            "allowed": [
                "compare package labels across held AAS families",
                "compare operator queue names and artifact reading order",
                "estimate internal review complexity from evidence packet shape",
                "identify exactly one held text boundary for possible future human approval",
            ],
            "forbidden": [
                "publish customer copy",
                "quote a customer/public price",
                "mount catalog or public routes",
                "authorize controlled pilot exposure",
                "dispatch workers from this packet",
                "attach ERC-8004 reputation receipts",
                "claim live Acontext/runtime parity",
                "release exact GPS/raw metadata",
                "create worker-copyable doctrine",
            ],
        },
        "pricing_review_inputs": {
            "reviewable_inputs": [
                "operator_minutes_estimate",
                "evidence_count_and_media_complexity",
                "redaction_complexity",
                "domain_authority_risk_class",
                "need_for_follow_on_task_trigger",
            ],
            "outputs_not_approved": [
                "public_price",
                "customer_quote",
                "front_door_sku",
                "sla_or_guaranteed_outcome_price",
            ],
        },
        "operator_workflow_review": {
            "reviewable_workflow": [
                "intake_question_capture",
                "evidence_contract_selection",
                "artifact_lookup",
                "operator_limitation_review",
                "redaction_review",
                "explicit_hold_or_separate_approval_record",
            ],
            "launch_not_authorized": True,
            "customer_delivery_path_authorized": False,
            "worker_dispatch_path_authorized": False,
        },
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "next_steps": [
            (
                "If customer exposure is explicitly desired, create one separate human-operator "
                "approval artifact for exactly one held text boundary."
            ),
            (
                "Otherwise keep all three families held and use this packet for package labels, "
                "pricing-input discussion, and operator workflow review only."
            ),
        ],
    }
    _validate_packet(packet)
    return packet


def _validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA:
        raise CityOpsContractError("packaging review packet schema drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("packaging review packet scope drift")
    if packet.get("review_mode") != REVIEW_MODE:
        raise CityOpsContractError("packaging review packet mode drift")
    if len(packet.get("review_rows", [])) != 3:
        raise CityOpsContractError("packaging review packet must contain exactly three rows")
    if set(packet.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("packaging review packet contains forbidden safe claims")
    if not isinstance(packet.get("do_not_claim_yet"), list) or not packet["do_not_claim_yet"]:
        raise CityOpsContractError("packaging review packet blocked claims missing")
    for flag in READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"packaging review packet promoted readiness {flag}")
    summary = packet.get("summary", {})
    for flag in [
        "all_families_at_explicit_hold_decision",
        "all_customer_delivery_blocked",
        "all_publication_blocked",
        "all_dispatch_and_reputation_blocked",
    ]:
        if summary.get(flag) is not True:
            raise CityOpsContractError(f"packaging review packet summary drift {flag}")
    for row in packet.get("review_rows", []):
        if row.get("current_ladder_step") != "explicit_internal_admin_sample_output_hold_decision":
            raise CityOpsContractError("packaging review row ladder drift")
        if row.get("packaging_state") != "internal_admin_package_candidate_only":
            raise CityOpsContractError("packaging review row state drift")
        if any(value is not False for value in row.get("readiness", {}).values()):
            raise CityOpsContractError("packaging review row promoted readiness")
    boundaries = packet.get("packaging_review_boundaries", {})
    forbidden = set(boundaries.get("forbidden", []))
    required_forbidden = {
        "publish customer copy",
        "mount catalog or public routes",
        "dispatch workers from this packet",
        "attach ERC-8004 reputation receipts",
        "release exact GPS/raw metadata",
    }
    if not required_forbidden <= forbidden:
        raise CityOpsContractError("packaging review packet forbidden boundary drift")


def write_aas_three_family_packaging_review_packet(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_three_family_packaging_review_packet()
    path = target_dir / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_three_family_packaging_review_packet(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    _validate_packet(packet)
    return packet
