"""Delivery/publication gate for the single-boundary AAS approval record.

This module consumes the one human-operator approval record and creates the
next internal/admin gate before any customer exposure. It deliberately does not
authorize delivery or publication, does not create a customer/public route, does
not launch a catalog, pilot, queue, dispatch, reputation attachment, live
Acontext/runtime parity, exact GPS/raw metadata release, domain-authority claim,
legal/regulator claim, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_single_boundary_approval_record_validator import (
    APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
    APPROVAL_RECORD_ALLOWED_SCOPE,
    APPROVAL_RECORD_ALLOWED_STATUS,
)
from .aas_single_boundary_human_operator_approval_record import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA,
    APPROVED_BOUNDARY_KEY,
    APPROVED_TEXT_BOUNDARY,
    APPROVED_TEXT_FIELDS,
    DELIVERY_FLAGS_FALSE,
    EXACT_APPROVED_TEXT,
    RECORD_STILL_BLOCKED_CLAIMS as SOURCE_RECORD_REQUIRED_BLOCKED_CLAIMS,
    load_aas_single_boundary_human_operator_approval_record,
)
from .aas_single_boundary_approval_record_schema_gate import REQUIRED_REDACTION_CHECKS
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SCHEMA = (
    "city_ops.aas_single_boundary_delivery_publication_gate.v1"
)
AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME = (
    "aas_single_boundary_delivery_publication_gate.json"
)
AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM = (
    "delivery_publication_gate_landed"
)

GATE_ID = (
    "execution_market.aas.single_boundary_delivery_publication_gate."
    "compliance_desk.visible_posting_notice_compliance_snapshot.2026_05_18"
)
GATE_SCOPE = "internal_admin_delivery_publication_gate_only_no_customer_exposure"
GATE_STATUS = "blocked_not_approved_internal_admin_gate_only"
DELIVERY_PUBLICATION_VERDICT = "hold_no_authorized_delivery_path"

REQUIRED_DELIVERY_PUBLICATION_CHECKS = [
    "source_human_operator_approval_record_valid",
    "approved_text_boundary_snapshot_preserved",
    "safe_and_blocked_claims_remain_adjacent",
    "fresh_redaction_reverification_required_at_delivery_time",
    "domain_authority_reverification_required_at_delivery_time",
    "authorized_delivery_path_required_but_absent",
    "operator_publish_approval_required_but_absent",
    "customer_delivery_approval_required_but_absent",
    "no_public_route_catalog_pilot_queue_or_dispatch",
    "no_reputation_runtime_gps_legal_or_worker_doctrine_promotion",
]

DELIVERY_PUBLICATION_BLOCKED_CLAIMS = [
    *SOURCE_RECORD_REQUIRED_BLOCKED_CLAIMS,
    "delivery_publication_gate_authorizes_customer_delivery",
    "delivery_publication_gate_authorizes_publication",
    "delivery_publication_gate_authorizes_authorized_delivery_path",
    "delivery_publication_gate_authorizes_public_route_or_catalog",
    "delivery_publication_gate_authorizes_controlled_pilot_or_front_door_sku",
    "delivery_publication_gate_authorizes_public_price_or_customer_quote",
    "delivery_publication_gate_authorizes_operator_queue_launch",
    "delivery_publication_gate_authorizes_dispatch",
    "delivery_publication_gate_authorizes_erc8004_reputation_receipts",
    "delivery_publication_gate_authorizes_live_acontext_or_runtime_parity",
    "delivery_publication_gate_authorizes_exact_gps_or_raw_metadata_exposure",
    "delivery_publication_gate_authorizes_domain_authority_claims",
    "delivery_publication_gate_authorizes_legal_regulator_notarial_custody_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_claims",
    "delivery_publication_gate_authorizes_worker_skill_dna_or_copyable_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(DELIVERY_PUBLICATION_BLOCKED_CLAIMS) | {
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "authorized_delivery_path_ready",
    "authorized_delivery_path_approved",
    "publishable",
    "publication_ready",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "controlled_pilot_ready",
    "front_door_sku_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "domain_authority_ready",
    "legal_or_regulator_authority_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
}

DELIVERY_PUBLICATION_FALSE_FLAGS = {
    "authorized_delivery_path_authorized": False,
    "operator_publish_approval": False,
    "customer_delivery_approval": False,
    "customer_delivery_approved": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "publication_approved": False,
    "publish_route_ready": False,
    "public_route_ready": False,
    "catalog_route_ready": False,
    "controlled_pilot_ready": False,
    "front_door_sku_ready": False,
    "public_price_approved": False,
    "customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_enabled": False,
    "autonomous_dispatch_ready": False,
    "reputation_ready": False,
    "erc8004_reputation_ready": False,
    "live_acontext_ready": False,
    "runtime_parity_proven": False,
    "exact_gps_or_raw_metadata_exposure_allowed": False,
    "domain_authority_claims_allowed": False,
    "legal_regulator_or_official_authority_claims_allowed": False,
    "worker_skill_dna_ready": False,
    "worker_copyable_doctrine_ready": False,
}


def _canonical_digest(payload: dict[str, Any]) -> str:
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


def _load_source_record(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_single_boundary_human_operator_approval_record(
        artifact_dir=artifact_dir
    )


def build_aas_single_boundary_delivery_publication_gate(
    *,
    artifact_dir: Path | None = None,
    source_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the no-delivery/no-publication gate over the approval record."""

    record = source_record or _load_source_record(artifact_dir=artifact_dir)
    _assert_source_record_is_conservative(record)

    safe_to_claim = _dedupe(
        [
            *record.get("safe_to_claim", []),
            AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *DELIVERY_PUBLICATION_BLOCKED_CLAIMS,
            *record.get("do_not_claim_yet", []),
        ]
    )

    gate: dict[str, Any] = {
        "schema": AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SCHEMA,
        "gate_id": GATE_ID,
        "scope": GATE_SCOPE,
        "gate_status": GATE_STATUS,
        "source_record_file": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
        "source_record_id": record["record_id"],
        "source_record_schema": record["schema"],
        "source_record_digest_sha256": _canonical_digest(record),
        "source_record_safe_claim": AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "delivery_publication_verdict": DELIVERY_PUBLICATION_VERDICT,
        "authorized_delivery_path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
        "authorized_delivery_path_authorized": False,
        "authorized_delivery_path_detail": {
            "path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
            "path_authorized_for_customer_delivery": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "public_route_allowed": False,
            "catalog_route_allowed": False,
            "controlled_pilot_allowed": False,
            "operator_queue_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "exact_gps_or_raw_metadata_allowed": False,
            "domain_authority_claims_allowed": False,
        },
        "approved_text_boundary_snapshot": {
            "selected_boundary_key": record["selected_boundary_key"],
            "family_id": record["family_id"],
            "family_label": record["family_label"],
            "offer_id": record["offer_id"],
            "approved_text_boundary": record["approved_text_boundary"],
            "exact_approved_text": record["exact_approved_text"],
            "approved_text_fields": list(record["approved_text_fields"]),
            "human_operator_approval_recorded": True,
            "selected_boundary_approved": True,
            "customer_delivery_authorized_by_snapshot": False,
            "publication_authorized_by_snapshot": False,
        },
        "delivery_publication_checks": _build_delivery_publication_checks(record),
        "delivery_time_reverification": _build_delivery_time_reverification(record),
        "delivery_channel_gate": {
            "internal_admin_only": True,
            "customer_email_allowed": False,
            "customer_dashboard_allowed": False,
            "public_catalog_allowed": False,
            "api_route_allowed": False,
            "worker_visible_instruction_allowed": False,
        },
        "route_catalog_pilot_queue_dispatch_gate": {
            "public_route_ready": False,
            "catalog_route_ready": False,
            "controlled_pilot_ready": False,
            "front_door_sku_ready": False,
            "operator_queue_launch_ready": False,
            "dispatch_enabled": False,
            "autonomous_dispatch_ready": False,
        },
        "reputation_runtime_gps_legal_worker_gate": {
            "erc8004_reputation_ready": False,
            "live_acontext_ready": False,
            "runtime_parity_proven": False,
            "exact_gps_or_raw_metadata_exposure_allowed": False,
            "domain_authority_claims_allowed": False,
            "legal_regulator_or_official_authority_claims_allowed": False,
            "worker_skill_dna_ready": False,
            "worker_copyable_doctrine_ready": False,
        },
        **DELIVERY_PUBLICATION_FALSE_FLAGS,
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "This gate is an internal/admin hold over the approved text boundary. "
            "Do not deliver or publish it. Any future customer exposure requires a "
            "separate explicit authorized delivery path, operator publish approval, "
            "customer-delivery approval, and fresh redaction/domain-authority checks "
            "at delivery time."
        ),
        "next_smallest_proof": (
            "Record an explicit human operator decision for a named delivery path, "
            "or keep authorized_delivery_path_authorized=false and all route/catalog/"
            "pilot/queue/dispatch/reputation/runtime/GPS/legal/worker-doctrine flags false."
        ),
    }
    _assert_gate_is_conservative(gate, source_record=record)
    return gate


def write_aas_single_boundary_delivery_publication_gate(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_aas_single_boundary_delivery_publication_gate(artifact_dir=target_dir)
    path = target_dir / AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_single_boundary_delivery_publication_gate(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    if not isinstance(gate, dict):
        raise CityOpsContractError("delivery publication gate must be a JSON object")
    source_record = _load_source_record(artifact_dir=source_dir)
    _assert_gate_is_conservative(gate, source_record=source_record)
    return gate


def _build_delivery_publication_checks(record: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for check in REQUIRED_DELIVERY_PUBLICATION_CHECKS:
        structural_passed = check in {
            "source_human_operator_approval_record_valid",
            "approved_text_boundary_snapshot_preserved",
            "safe_and_blocked_claims_remain_adjacent",
        }
        checks.append(
            {
                "check": check,
                "structural_check_passed": structural_passed,
                "approval_granted": False,
                "customer_delivery_allowed": False,
                "publication_allowed": False,
                "evidence_reference": f"source_record:{record['record_id']}:{check}",
            }
        )
    return checks


def _build_delivery_time_reverification(record: dict[str, Any]) -> list[dict[str, Any]]:
    source_checks = {
        item.get("check"): item for item in record.get("redaction_checks_passed", [])
    }
    reverification = [
        {
            "check": check,
            "source_record_passed": source_checks.get(check, {}).get("passed") is True,
            "rerun_required_at_delivery_time": True,
            "passed_for_delivery": False,
            "authorizes_delivery_or_publication": False,
        }
        for check in REQUIRED_REDACTION_CHECKS
    ]
    reverification.append(
        {
            "check": "domain_authority_claims_reverified_at_delivery_time",
            "source_record_passed": False,
            "rerun_required_at_delivery_time": True,
            "passed_for_delivery": False,
            "authorizes_delivery_or_publication": False,
        }
    )
    return reverification


def _assert_source_record_is_conservative(record: dict[str, Any]) -> None:
    if record.get("schema") != AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA:
        raise CityOpsContractError("delivery publication gate source record schema drift")
    if AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM not in record.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("delivery publication gate source safe claim missing")
    forbidden_safe = set(record.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"delivery publication gate source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SOURCE_RECORD_REQUIRED_BLOCKED_CLAIMS) - set(
        record.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"delivery publication gate source missing blocked claims: {sorted(missing_blocked)}"
        )
    if record.get("record_status") != APPROVAL_RECORD_ALLOWED_STATUS:
        raise CityOpsContractError("delivery publication gate source record status drift")
    if record.get("approval_scope") != APPROVAL_RECORD_ALLOWED_SCOPE:
        raise CityOpsContractError("delivery publication gate source approval scope drift")
    if record.get("authorized_delivery_path") != APPROVAL_RECORD_ALLOWED_DELIVERY_PATH:
        raise CityOpsContractError("delivery publication gate source delivery path drift")
    if record.get("selected_boundary_key") != APPROVED_BOUNDARY_KEY:
        raise CityOpsContractError("delivery publication gate source boundary drift")
    if record.get("approved_text_boundary") != APPROVED_TEXT_BOUNDARY:
        raise CityOpsContractError("delivery publication gate source text boundary drift")
    if record.get("exact_approved_text") != EXACT_APPROVED_TEXT:
        raise CityOpsContractError("delivery publication gate source exact text drift")
    if record.get("approved_text_fields") != APPROVED_TEXT_FIELDS:
        raise CityOpsContractError("delivery publication gate source approved fields drift")
    if record.get("human_operator_approval_recorded") is not True:
        raise CityOpsContractError("delivery publication gate source missing human approval")
    if record.get("selected_boundary_approved") is not True:
        raise CityOpsContractError("delivery publication gate source missing boundary approval")
    if [item.get("check") for item in record.get("redaction_checks_passed", [])] != (
        REQUIRED_REDACTION_CHECKS
    ):
        raise CityOpsContractError("delivery publication gate source redaction checks drift")
    for flag in set(DELIVERY_FLAGS_FALSE) | set(DELIVERY_PUBLICATION_FALSE_FLAGS):
        if record.get(flag) is True:
            raise CityOpsContractError(
                f"delivery publication gate source promoted false flag {flag}"
            )


def _assert_gate_is_conservative(
    gate: dict[str, Any], *, source_record: dict[str, Any] | None = None
) -> None:
    if source_record is not None:
        _assert_source_record_is_conservative(source_record)
        if gate.get("source_record_digest_sha256") != _canonical_digest(source_record):
            raise CityOpsContractError("delivery publication gate source digest drift")
        if gate.get("source_record_id") != source_record.get("record_id"):
            raise CityOpsContractError("delivery publication gate source record id drift")
    if gate.get("schema") != AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SCHEMA:
        raise CityOpsContractError("delivery publication gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("delivery publication gate id drift")
    if gate.get("scope") != GATE_SCOPE:
        raise CityOpsContractError("delivery publication gate scope drift")
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("delivery publication gate status drift")
    if gate.get("delivery_publication_verdict") != DELIVERY_PUBLICATION_VERDICT:
        raise CityOpsContractError("delivery publication gate verdict drift")
    if AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM not in gate.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("delivery publication gate safe claim missing")
    forbidden_safe = set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"delivery publication gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    if set(gate.get("safe_to_claim", [])) & set(gate.get("do_not_claim_yet", [])):
        raise CityOpsContractError("delivery publication gate safe/blocked overlap")
    missing_blocked = set(DELIVERY_PUBLICATION_BLOCKED_CLAIMS) - set(
        gate.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"delivery publication gate missing blocked claims: {sorted(missing_blocked)}"
        )
    if gate.get("still_blocked_claims") != gate.get("do_not_claim_yet"):
        raise CityOpsContractError("delivery publication gate blocked claims drift")
    if gate.get("authorized_delivery_path") != APPROVAL_RECORD_ALLOWED_DELIVERY_PATH:
        raise CityOpsContractError("delivery publication gate delivery path drift")
    detail = gate.get("authorized_delivery_path_detail", {})
    for field in [
        "path_authorized_for_customer_delivery",
        "customer_delivery_allowed",
        "publication_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "controlled_pilot_allowed",
        "operator_queue_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
        "domain_authority_claims_allowed",
    ]:
        if detail.get(field) is not False:
            raise CityOpsContractError(
                f"delivery publication gate promoted delivery detail {field}"
            )
    if [item.get("check") for item in gate.get("delivery_publication_checks", [])] != (
        REQUIRED_DELIVERY_PUBLICATION_CHECKS
    ):
        raise CityOpsContractError("delivery publication gate check order drift")
    for item in gate.get("delivery_publication_checks", []):
        if item.get("approval_granted") is not False:
            raise CityOpsContractError("delivery publication gate granted approval")
        if item.get("customer_delivery_allowed") is not False:
            raise CityOpsContractError("delivery publication gate allowed customer delivery")
        if item.get("publication_allowed") is not False:
            raise CityOpsContractError("delivery publication gate allowed publication")
    if [item.get("check") for item in gate.get("delivery_time_reverification", [])] != [
        *REQUIRED_REDACTION_CHECKS,
        "domain_authority_claims_reverified_at_delivery_time",
    ]:
        raise CityOpsContractError("delivery publication gate reverification order drift")
    for item in gate.get("delivery_time_reverification", []):
        if item.get("rerun_required_at_delivery_time") is not True:
            raise CityOpsContractError("delivery publication gate missing delivery-time rerun")
        if item.get("passed_for_delivery") is not False:
            raise CityOpsContractError("delivery publication gate passed delivery check")
        if item.get("authorizes_delivery_or_publication") is not False:
            raise CityOpsContractError("delivery publication gate authorized delivery/publication")
    snapshot = gate.get("approved_text_boundary_snapshot", {})
    if snapshot.get("selected_boundary_key") != APPROVED_BOUNDARY_KEY:
        raise CityOpsContractError("delivery publication gate snapshot boundary drift")
    if snapshot.get("approved_text_boundary") != APPROVED_TEXT_BOUNDARY:
        raise CityOpsContractError("delivery publication gate snapshot text boundary drift")
    if snapshot.get("exact_approved_text") != EXACT_APPROVED_TEXT:
        raise CityOpsContractError("delivery publication gate snapshot exact text drift")
    if snapshot.get("approved_text_fields") != APPROVED_TEXT_FIELDS:
        raise CityOpsContractError("delivery publication gate snapshot fields drift")
    if snapshot.get("customer_delivery_authorized_by_snapshot") is not False:
        raise CityOpsContractError("delivery publication gate snapshot authorized delivery")
    if snapshot.get("publication_authorized_by_snapshot") is not False:
        raise CityOpsContractError("delivery publication gate snapshot authorized publication")
    for container_name in [
        "delivery_channel_gate",
        "route_catalog_pilot_queue_dispatch_gate",
        "reputation_runtime_gps_legal_worker_gate",
    ]:
        for flag, value in gate.get(container_name, {}).items():
            if flag == "internal_admin_only":
                if value is not True:
                    raise CityOpsContractError("delivery publication gate internal-only drift")
            elif value is not False:
                raise CityOpsContractError(
                    f"delivery publication gate promoted nested flag {flag}"
                )
    for flag in DELIVERY_PUBLICATION_FALSE_FLAGS:
        if gate.get(flag) is not False:
            raise CityOpsContractError(f"delivery publication gate promoted false flag {flag}")
