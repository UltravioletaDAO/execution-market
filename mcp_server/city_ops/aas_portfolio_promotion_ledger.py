"""Execution Market AAS portfolio promotion ledger.

This module implements the no-human/no-runtime continuation from the May 26
portfolio promotion map. It consumes the current boundary artifacts for five AAS
families and emits one deterministic internal/admin ledger. The ledger is a
read-only coordination artifact: it does not create customer copy, approve
customer delivery, authorize publication, mount public/catalog routes, create
pricing or queue launch, dispatch workers, attach ERC-8004 reputation, prove
live Acontext/runtime parity, release exact GPS/raw metadata, or publish
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_single_boundary_human_operator_approval_record import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA,
    load_aas_single_boundary_human_operator_approval_record,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError
from .document_handoff_sample_output_review_decision import (
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
    REVIEW_DECISION as DOCUMENT_REVIEW_DECISION,
    load_document_handoff_sample_output_review_decision,
)
from .incident_verification_sample_output_review_decision import (
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
    REVIEW_DECISION as INCIDENT_REVIEW_DECISION,
    load_incident_verification_sample_output_review_decision,
)
from .local_data_collection_sample_output_review_decision import (
    LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
    LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
    REVIEW_DECISION as LOCAL_DATA_COLLECTION_REVIEW_DECISION,
    load_local_data_collection_sample_output_review_decision,
)
from .retail_reality_pending_approval_status_card import (
    APPROVAL_REQUEST_STATUS as RETAIL_APPROVAL_REQUEST_STATUS,
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME,
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA,
    load_retail_reality_pending_approval_status_card,
)

AAS_PORTFOLIO_PROMOTION_LEDGER_SCHEMA = "city_ops.aas_portfolio_promotion_ledger.v1"
AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME = "aas_portfolio_promotion_ledger.json"
AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM = "admin_aas_portfolio_promotion_ledger_landed"

LEDGER_ID = "execution_market.aas.portfolio_promotion_ledger.2026_05_27_0000"
SCOPE = "internal_admin_aas_portfolio_promotion_ledger_only_no_customer_exposure"
LEDGER_STATUS = "read_only_portfolio_promotion_ledger_all_public_delivery_dispatch_runtime_claims_blocked"

FAMILY_ORDER = [
    "compliance_desk_as_a_service",
    "document_handoff_logistics_as_a_service",
    "incident_verification_as_a_service",
    "retail_reality_as_a_service",
    "local_data_collection_as_a_service",
]

SUMMARY_COUNTERS_ZERO = [
    "families_with_customer_delivery_authorization",
    "families_publishable",
    "families_with_public_or_catalog_routes",
    "families_ready_for_pricing_or_customer_quote",
    "families_ready_for_queue_or_dispatch",
    "families_ready_for_reputation_attachment",
    "families_with_live_acontext_runtime_parity",
    "families_allowed_to_release_exact_gps_or_raw_metadata",
    "families_with_worker_copyable_doctrine",
]

LEDGER_FALSE_FLAGS = {
    "ledger_creates_human_operator_approval": False,
    "ledger_approves_any_selected_boundary": False,
    "ledger_authorizes_customer_copy": False,
    "ledger_authorizes_customer_delivery": False,
    "ledger_authorizes_publication": False,
    "ledger_authorizes_public_or_catalog_route": False,
    "ledger_authorizes_public_pricing_or_customer_quote": False,
    "ledger_authorizes_queue_or_dispatch": False,
    "ledger_authorizes_reputation_attachment": False,
    "ledger_proves_live_acontext_runtime_parity": False,
    "ledger_reverifies_payment_or_production_health": False,
    "ledger_allows_exact_gps_or_raw_metadata_release": False,
    "ledger_releases_private_operator_context": False,
    "ledger_creates_worker_skill_dna_or_copyable_doctrine": False,
    "network_route_registered": False,
    "public_route_registered": False,
    "customer_visible": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "worker_visible": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "emits_reputation_receipts": False,
}

LEDGER_BLOCKED_CLAIMS = [
    "portfolio_ledger_customer_copy_ready",
    "portfolio_ledger_customer_delivery_approved",
    "portfolio_ledger_publication_approved",
    "portfolio_ledger_public_catalog_ready",
    "portfolio_ledger_public_route_ready",
    "portfolio_ledger_controlled_pilot_ready",
    "portfolio_ledger_public_pricing_or_customer_quote_ready",
    "portfolio_ledger_operator_queue_launch_ready",
    "portfolio_ledger_autonomous_dispatch_ready",
    "portfolio_ledger_erc8004_reputation_ready",
    "portfolio_ledger_worker_skill_dna_ready",
    "portfolio_ledger_live_acontext_runtime_parity",
    "portfolio_ledger_acontext_sink_ready",
    "portfolio_ledger_payment_or_production_reverified",
    "portfolio_ledger_exact_gps_or_raw_metadata_release_allowed",
    "portfolio_ledger_private_operator_context_release_allowed",
    "portfolio_ledger_raw_transcript_authority",
    "portfolio_ledger_legal_or_regulator_authority",
    "portfolio_ledger_emergency_or_safety_authority",
    "portfolio_ledger_repair_or_insurance_or_sla_authority",
    "portfolio_ledger_dataset_or_analytics_ready",
    "portfolio_ledger_statistical_representativeness_ready",
    "portfolio_ledger_continuous_monitoring_ready",
    "portfolio_ledger_worker_copyable_aas_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(LEDGER_BLOCKED_CLAIMS) | {
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_ready",
    "publication_approved",
    "public_catalog_ready",
    "public_service_catalog_ready",
    "public_route_ready",
    "catalog_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "public_price_ready",
    "pricing_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "acontext_sink_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "legal_or_regulator_authority_ready",
    "emergency_response",
    "safety_certification",
    "repair_diagnosis",
    "insurance_adjustment",
    "dataset_publication_ready",
    "analytics_ready",
    "statistical_representativeness_ready",
    "continuous_monitoring_ready",
    "worker_copyable_doctrine_ready",
}

SOURCE_PUBLIC_FLAGS = [
    "customer_copy_ready",
    "customer_delivery_approved",
    "customer_delivery_authorized",
    "customer_delivery_path_authorized",
    "publication_approved",
    "public_route_ready",
    "public_route_registered",
    "catalog_route_ready",
    "catalog_visible",
    "public_service_catalog_ready",
    "customer_visible_catalog_ready",
    "controlled_pilot_ready",
    "controlled_pilot_authorized",
    "front_door_sku_ready",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_enabled",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "private_context_release_allowed",
    "worker_copyable_doctrine_ready",
]


def _canonical_digest(payload: Any) -> str:
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


def _load_sources(artifact_dir: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        load_aas_single_boundary_human_operator_approval_record(artifact_dir=artifact_dir),
        load_document_handoff_sample_output_review_decision(artifact_dir=artifact_dir),
        load_incident_verification_sample_output_review_decision(artifact_dir=artifact_dir),
        load_retail_reality_pending_approval_status_card(artifact_dir=artifact_dir),
        load_local_data_collection_sample_output_review_decision(artifact_dir=artifact_dir),
    )


def build_aas_portfolio_promotion_ledger(
    *,
    artifact_dir: Path | None = None,
    compliance_record: dict[str, Any] | None = None,
    document_decision: dict[str, Any] | None = None,
    incident_decision: dict[str, Any] | None = None,
    retail_status_card: dict[str, Any] | None = None,
    local_data_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a five-family internal/admin promotion ledger."""

    if any(
        source is None
        for source in [
            compliance_record,
            document_decision,
            incident_decision,
            retail_status_card,
            local_data_decision,
        ]
    ):
        loaded = _load_sources(artifact_dir)
        compliance_record = compliance_record or loaded[0]
        document_decision = document_decision or loaded[1]
        incident_decision = incident_decision or loaded[2]
        retail_status_card = retail_status_card or loaded[3]
        local_data_decision = local_data_decision or loaded[4]

    assert compliance_record is not None
    assert document_decision is not None
    assert incident_decision is not None
    assert retail_status_card is not None
    assert local_data_decision is not None

    _assert_compliance_record(compliance_record)
    _assert_hold_decision(
        document_decision,
        schema=DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
        safe_claim=DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        review_decision=DOCUMENT_REVIEW_DECISION,
        label="document",
    )
    _assert_hold_decision(
        incident_decision,
        schema=INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
        safe_claim=INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        review_decision=INCIDENT_REVIEW_DECISION,
        label="incident",
    )
    _assert_retail_status_card(retail_status_card)
    _assert_hold_decision(
        local_data_decision,
        schema=LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
        safe_claim=LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        review_decision=LOCAL_DATA_COLLECTION_REVIEW_DECISION,
        label="local data",
    )

    source_specs = {
        "compliance_desk": {
            "file": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
            "payload": compliance_record,
            "id_key": "record_id",
            "safe_claim": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
        },
        "document_handoff": {
            "file": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
            "payload": document_decision,
            "id_key": "decision_id",
            "safe_claim": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        },
        "incident_verification": {
            "file": INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
            "payload": incident_decision,
            "id_key": "decision_id",
            "safe_claim": INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        },
        "retail_reality": {
            "file": RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME,
            "payload": retail_status_card,
            "id_key": "status_card_id",
            "safe_claim": RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
        },
        "local_data_collection": {
            "file": LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_FILENAME,
            "payload": local_data_decision,
            "id_key": "decision_id",
            "safe_claim": LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        },
    }

    safe_to_claim = _dedupe(
        [*(spec["safe_claim"] for spec in source_specs.values()), AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM]
    )
    do_not_claim_yet = _dedupe(
        [
            *LEDGER_BLOCKED_CLAIMS,
            *compliance_record.get("do_not_claim_yet", []),
            *document_decision.get("do_not_claim_yet", []),
            *incident_decision.get("do_not_claim_yet", []),
            *retail_status_card.get("do_not_claim_yet", []),
            *local_data_decision.get("do_not_claim_yet", []),
        ]
    )

    ledger: dict[str, Any] = {
        "schema": AAS_PORTFOLIO_PROMOTION_LEDGER_SCHEMA,
        "ledger_id": LEDGER_ID,
        "scope": SCOPE,
        "ledger_status": LEDGER_STATUS,
        "source_artifacts": {
            key: {
                "file": spec["file"],
                "schema": spec["payload"]["schema"],
                "id": spec["payload"][spec["id_key"]],
                "digest_sha256": _canonical_digest(spec["payload"]),
                "safe_claim": spec["safe_claim"],
            }
            for key, spec in source_specs.items()
        },
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "family_rows": [
            {
                "family_id": "compliance_desk_as_a_service",
                "family_label": "Compliance Desk as a Service",
                "current_highest_safe_boundary": "single_boundary_human_operator_approval_record_for_internal_package_label",
                "decision_posture": "approved_internal_label_only_no_delivery_path",
                "safe_meaning_only": "one exact package-label text boundary can be referenced internally as operator-approved",
                "latest_safe_claim": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
                "recommended_next_gate": "delivery_publication_gate_only_if_exact_delivery_path_is_separately_authorized_else_keep_internal",
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "public_or_catalog_route_ready": False,
                "pricing_or_customer_quote_ready": False,
                "queue_or_dispatch_ready": False,
                "reputation_attachment_ready": False,
                "live_acontext_runtime_parity": False,
                "exact_gps_or_raw_metadata_release_allowed": False,
                "worker_copyable_doctrine_ready": False,
                "family_specific_blocked_claims": [
                    "compliance_customer_delivery_ready",
                    "compliance_publication_ready",
                    "compliance_catalog_or_route_ready",
                    "compliance_legal_or_regulator_authority",
                    "compliance_worker_copyable_doctrine_ready",
                ],
            },
            {
                "family_id": "document_handoff_logistics_as_a_service",
                "family_label": "Document / Handoff Logistics as a Service",
                "current_highest_safe_boundary": "internal_sample_output_with_explicit_hold_decision",
                "decision_posture": "held_not_approved_not_publishable",
                "safe_meaning_only": "one internal sample wording shape exists for review and remains held",
                "latest_safe_claim": DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
                "recommended_next_gate": "package_review_decision_or_exact_human_approval_request_prerequisites_not_customer_delivery",
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "public_or_catalog_route_ready": False,
                "pricing_or_customer_quote_ready": False,
                "queue_or_dispatch_ready": False,
                "reputation_attachment_ready": False,
                "live_acontext_runtime_parity": False,
                "exact_gps_or_raw_metadata_release_allowed": False,
                "worker_copyable_doctrine_ready": False,
                "family_specific_blocked_claims": [
                    "document_legal_service_ready",
                    "document_notarial_act_ready",
                    "document_identity_verification_ready",
                    "document_custody_or_filing_success_ready",
                    "document_worker_copyable_doctrine_ready",
                ],
            },
            {
                "family_id": "incident_verification_as_a_service",
                "family_label": "Incident Verification as a Service",
                "current_highest_safe_boundary": "internal_sample_output_with_explicit_hold_decision",
                "decision_posture": "held_not_approved_not_publishable",
                "safe_meaning_only": "one internal incident wording shape exists for review and remains held",
                "latest_safe_claim": INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
                "recommended_next_gate": "package_review_decision_for_triage_language_and_escalation_exclusions",
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "public_or_catalog_route_ready": False,
                "pricing_or_customer_quote_ready": False,
                "queue_or_dispatch_ready": False,
                "reputation_attachment_ready": False,
                "live_acontext_runtime_parity": False,
                "exact_gps_or_raw_metadata_release_allowed": False,
                "worker_copyable_doctrine_ready": False,
                "family_specific_blocked_claims": [
                    "incident_emergency_response_ready",
                    "incident_safety_certification_ready",
                    "incident_repair_or_insurance_or_sla_ready",
                    "incident_official_report_or_fault_liability_ready",
                    "incident_worker_copyable_doctrine_ready",
                ],
            },
            {
                "family_id": "retail_reality_as_a_service",
                "family_label": "Retail Reality as a Service",
                "current_highest_safe_boundary": "pending_human_operator_approval_request_status_card",
                "decision_posture": "pending_human_review_not_approved",
                "safe_meaning_only": "one exact selected boundary is queued for possible review and visible only as pending status",
                "latest_safe_claim": RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
                "recommended_next_gate": "human_operator_approval_record_for_selected_boundary_if_authorized_else_keep_pending",
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "public_or_catalog_route_ready": False,
                "pricing_or_customer_quote_ready": False,
                "queue_or_dispatch_ready": False,
                "reputation_attachment_ready": False,
                "live_acontext_runtime_parity": False,
                "exact_gps_or_raw_metadata_release_allowed": False,
                "worker_copyable_doctrine_ready": False,
                "family_specific_blocked_claims": [
                    "retail_human_operator_approval_recorded",
                    "retail_customer_delivery_ready",
                    "retail_permanent_business_status_ready",
                    "retail_inventory_or_brand_or_safety_certification_ready",
                    "retail_worker_copyable_doctrine_ready",
                ],
            },
            {
                "family_id": "local_data_collection_as_a_service",
                "family_label": "Local Data Collection as a Service",
                "current_highest_safe_boundary": "internal_sample_output_with_explicit_hold_decision",
                "decision_posture": "held_not_approved_not_publishable",
                "safe_meaning_only": "one method-bounded synthetic sample exists for review and remains held",
                "latest_safe_claim": LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
                "recommended_next_gate": "no_customer_exposure_keep_hold_or_exact_human_review_with_method_boundary",
                "customer_delivery_authorized": False,
                "publication_authorized": False,
                "public_or_catalog_route_ready": False,
                "pricing_or_customer_quote_ready": False,
                "queue_or_dispatch_ready": False,
                "reputation_attachment_ready": False,
                "live_acontext_runtime_parity": False,
                "exact_gps_or_raw_metadata_release_allowed": False,
                "worker_copyable_doctrine_ready": False,
                "family_specific_blocked_claims": [
                    "local_data_dataset_publication_ready",
                    "local_data_analytics_ready",
                    "local_data_statistical_representativeness_ready",
                    "local_data_continuous_monitoring_or_certification_ready",
                    "local_data_worker_copyable_doctrine_ready",
                ],
            },
        ],
        "ledger_summary": {
            "families_tracked": 5,
            "families_with_internal_label_approval_only": 1,
            "families_held": 3,
            "families_pending_human_review_not_approved": 1,
            **{key: 0 for key in SUMMARY_COUNTERS_ZERO},
        },
        **LEDGER_FALSE_FLAGS,
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this only as an internal/admin portfolio promotion ledger. Pick exactly one next gate: "
            "a narrow human-review record, a runtime prerequisite repair lane, or another internal proof seam. "
            "Do not infer customer copy, delivery, publication, catalog route, pricing, queue launch, dispatch, "
            "reputation, live runtime parity, raw-location release, domain authority, or worker doctrine from this ledger."
        ),
        "next_smallest_proof": (
            "Default no-human/no-runtime continuation is to keep this ledger as the morning decision surface; "
            "if work continues, choose Retail Reality approval record, Compliance delivery/publication gate, "
            "or isolated Acontext runtime repair as separate slices."
        ),
    }
    _assert_ledger_is_conservative(
        ledger,
        compliance_record=compliance_record,
        document_decision=document_decision,
        incident_decision=incident_decision,
        retail_status_card=retail_status_card,
        local_data_decision=local_data_decision,
    )
    return ledger


def write_aas_portfolio_promotion_ledger(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    ledger = build_aas_portfolio_promotion_ledger(artifact_dir=target_dir)
    path = target_dir / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_portfolio_promotion_ledger(artifact_dir: Path | None = None) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        ledger = json.load(fh)
    if not isinstance(ledger, dict):
        raise CityOpsContractError("AAS portfolio promotion ledger must be a JSON object")
    sources = _load_sources(source_dir)
    _assert_ledger_is_conservative(
        ledger,
        compliance_record=sources[0],
        document_decision=sources[1],
        incident_decision=sources[2],
        retail_status_card=sources[3],
        local_data_decision=sources[4],
    )
    return ledger


def _assert_no_forbidden_safe_claims(payload: dict[str, Any], *, label: str) -> None:
    forbidden_safe = set(payload.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS portfolio promotion ledger {label} source forbidden safe claims: {sorted(forbidden_safe)}"
        )


def _assert_source_public_flags_false(payload: dict[str, Any], *, label: str) -> None:
    for flag in SOURCE_PUBLIC_FLAGS:
        if flag in payload and payload.get(flag) is not False:
            raise CityOpsContractError(
                f"AAS portfolio promotion ledger {label} source promoted {flag}"
            )
    for container_key in ["readiness", "decision_readiness", "access_policy", "derived_output_contract"]:
        nested = payload.get(container_key, {})
        if not isinstance(nested, dict):
            continue
        for flag in SOURCE_PUBLIC_FLAGS:
            if flag in nested and nested.get(flag) is not False:
                raise CityOpsContractError(
                    f"AAS portfolio promotion ledger {label} source promoted {container_key}.{flag}"
                )


def _assert_compliance_record(record: dict[str, Any]) -> None:
    if record.get("schema") != AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA:
        raise CityOpsContractError("AAS portfolio promotion ledger compliance source schema drift")
    if AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM not in record.get("safe_to_claim", []):
        raise CityOpsContractError("AAS portfolio promotion ledger compliance source safe claim missing")
    if record.get("record_status") != "human_operator_approved_selected_boundary_only":
        raise CityOpsContractError("AAS portfolio promotion ledger compliance source status drift")
    if record.get("human_operator_approval_recorded") is not True:
        raise CityOpsContractError("AAS portfolio promotion ledger compliance approval record missing")
    if record.get("selected_boundary_approved") is not True:
        raise CityOpsContractError("AAS portfolio promotion ledger compliance selected boundary missing")
    _assert_no_forbidden_safe_claims(record, label="compliance")
    _assert_source_public_flags_false(record, label="compliance")


def _assert_hold_decision(
    decision: dict[str, Any],
    *,
    schema: str,
    safe_claim: str,
    review_decision: str,
    label: str,
) -> None:
    if decision.get("schema") != schema:
        raise CityOpsContractError(f"AAS portfolio promotion ledger {label} source schema drift")
    if safe_claim not in decision.get("safe_to_claim", []):
        raise CityOpsContractError(f"AAS portfolio promotion ledger {label} source safe claim missing")
    if decision.get("review_decision") != review_decision:
        raise CityOpsContractError(f"AAS portfolio promotion ledger {label} source decision promoted")
    if decision.get("explicit_hold_decision_recorded") is not True:
        raise CityOpsContractError(f"AAS portfolio promotion ledger {label} hold decision missing")
    if decision.get("operator_review_recorded") is not True:
        raise CityOpsContractError(f"AAS portfolio promotion ledger {label} operator review missing")
    _assert_no_forbidden_safe_claims(decision, label=label)
    _assert_source_public_flags_false(decision, label=label)


def _assert_retail_status_card(card: dict[str, Any]) -> None:
    if card.get("schema") != RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA:
        raise CityOpsContractError("AAS portfolio promotion ledger retail source schema drift")
    if RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM not in card.get("safe_to_claim", []):
        raise CityOpsContractError("AAS portfolio promotion ledger retail source safe claim missing")
    if card.get("status_card_status") != "read_only_pending_approval_status_card_not_approval_not_customer_ready":
        raise CityOpsContractError("AAS portfolio promotion ledger retail source status drift")
    if card.get("source_approval_request_status") != RETAIL_APPROVAL_REQUEST_STATUS:
        raise CityOpsContractError("AAS portfolio promotion ledger retail source request status promoted")
    if card.get("human_operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS portfolio promotion ledger retail source approval promoted")
    _assert_no_forbidden_safe_claims(card, label="retail")
    _assert_source_public_flags_false(card, label="retail")


def _assert_ledger_is_conservative(
    ledger: dict[str, Any],
    *,
    compliance_record: dict[str, Any],
    document_decision: dict[str, Any],
    incident_decision: dict[str, Any],
    retail_status_card: dict[str, Any],
    local_data_decision: dict[str, Any],
) -> None:
    _assert_compliance_record(compliance_record)
    _assert_hold_decision(
        document_decision,
        schema=DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
        safe_claim=DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        review_decision=DOCUMENT_REVIEW_DECISION,
        label="document",
    )
    _assert_hold_decision(
        incident_decision,
        schema=INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
        safe_claim=INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        review_decision=INCIDENT_REVIEW_DECISION,
        label="incident",
    )
    _assert_retail_status_card(retail_status_card)
    _assert_hold_decision(
        local_data_decision,
        schema=LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SCHEMA,
        safe_claim=LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
        review_decision=LOCAL_DATA_COLLECTION_REVIEW_DECISION,
        label="local data",
    )
    if ledger.get("schema") != AAS_PORTFOLIO_PROMOTION_LEDGER_SCHEMA:
        raise CityOpsContractError("AAS portfolio promotion ledger schema drift")
    if ledger.get("ledger_id") != LEDGER_ID:
        raise CityOpsContractError("AAS portfolio promotion ledger id drift")
    if ledger.get("scope") != SCOPE:
        raise CityOpsContractError("AAS portfolio promotion ledger scope drift")
    if ledger.get("ledger_status") != LEDGER_STATUS:
        raise CityOpsContractError("AAS portfolio promotion ledger status drift")
    if AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM not in ledger.get("safe_to_claim", []):
        raise CityOpsContractError("AAS portfolio promotion ledger safe claim missing")
    forbidden_safe = set(ledger.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS portfolio promotion ledger forbidden safe claims: {sorted(forbidden_safe)}"
        )
    if set(ledger.get("safe_to_claim", [])) & set(ledger.get("do_not_claim_yet", [])):
        raise CityOpsContractError("AAS portfolio promotion ledger safe/blocked overlap")
    missing_blocked = set(LEDGER_BLOCKED_CLAIMS) - set(ledger.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS portfolio promotion ledger missing blocked claims: {sorted(missing_blocked)}"
        )
    if ledger.get("still_blocked_claims") != ledger.get("do_not_claim_yet"):
        raise CityOpsContractError("AAS portfolio promotion ledger blocked claims drift")
    expected_sources = {
        "compliance_desk": compliance_record,
        "document_handoff": document_decision,
        "incident_verification": incident_decision,
        "retail_reality": retail_status_card,
        "local_data_collection": local_data_decision,
    }
    source_artifacts = ledger.get("source_artifacts", {})
    for key, payload in expected_sources.items():
        if source_artifacts.get(key, {}).get("digest_sha256") != _canonical_digest(payload):
            raise CityOpsContractError(f"AAS portfolio promotion ledger {key} source digest drift")
    rows = ledger.get("family_rows", [])
    if [row.get("family_id") for row in rows] != FAMILY_ORDER:
        raise CityOpsContractError("AAS portfolio promotion ledger family row order drift")
    summary = ledger.get("ledger_summary", {})
    if summary.get("families_tracked") != 5:
        raise CityOpsContractError("AAS portfolio promotion ledger family count drift")
    if summary.get("families_with_internal_label_approval_only") != 1:
        raise CityOpsContractError("AAS portfolio promotion ledger approval-only count drift")
    if summary.get("families_held") != 3:
        raise CityOpsContractError("AAS portfolio promotion ledger held count drift")
    if summary.get("families_pending_human_review_not_approved") != 1:
        raise CityOpsContractError("AAS portfolio promotion ledger pending count drift")
    for count_key in SUMMARY_COUNTERS_ZERO:
        if summary.get(count_key) != 0:
            raise CityOpsContractError(f"AAS portfolio promotion ledger promoted summary {count_key}")
    for row in rows:
        for row_flag in [
            "customer_delivery_authorized",
            "publication_authorized",
            "public_or_catalog_route_ready",
            "pricing_or_customer_quote_ready",
            "queue_or_dispatch_ready",
            "reputation_attachment_ready",
            "live_acontext_runtime_parity",
            "exact_gps_or_raw_metadata_release_allowed",
            "worker_copyable_doctrine_ready",
        ]:
            if row.get(row_flag) is not False:
                raise CityOpsContractError(
                    f"AAS portfolio promotion ledger row promoted {row.get('family_id')} {row_flag}"
                )
    for flag in LEDGER_FALSE_FLAGS:
        if ledger.get(flag) is not False:
            raise CityOpsContractError(f"AAS portfolio promotion ledger promoted false flag {flag}")
