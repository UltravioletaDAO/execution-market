"""Operator review brief for the single-boundary AAS approval gate.

This module consumes the schema gate for a future single-boundary human
approval record and creates a human-readable internal/admin review brief. The
brief is deliberately not a human approval record, does not satisfy redactions,
does not authorize customer delivery, does not publish, does not create public
routes/catalog/pilots, does not approve pricing or queue launch, does not
dispatch, does not attach reputation, does not prove live Acontext/runtime
parity, and does not expose exact GPS/raw metadata or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_single_boundary_approval_record_schema_gate import (
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA,
    AUTHORIZED_DELIVERY_PATH,
    FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS,
    FUTURE_RECORD_MUST_KEEP_FALSE,
    GATE_ID,
    GATE_STATUS,
    RECORD_GATE_READINESS_FALSE_FLAGS,
    REQUIRED_BLOCKED_CLAIMS as GATE_REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_REDACTION_CHECKS,
    SELECTED_BOUNDARY_KEY,
    build_aas_single_boundary_approval_record_schema_gate,
    load_aas_single_boundary_approval_record_schema_gate,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA = (
    "city_ops.aas_single_boundary_operator_review_brief.v1"
)
AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME = (
    "aas_single_boundary_operator_review_brief.json"
)
AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM = (
    "aas_single_boundary_operator_review_brief_landed"
)

BRIEF_ID = "execution_market.aas.single_boundary_operator_review_brief.001"
SCOPE = "internal_admin_operator_review_brief_for_pending_single_boundary_only"
SOURCE_POLICY = "consume_only_single_boundary_approval_record_schema_gate_json"
BRIEF_STATUS = "operator_review_brief_only_no_human_approval_recorded"

BRIEF_READINESS_FALSE_FLAGS = [
    *RECORD_GATE_READINESS_FALSE_FLAGS,
    "operator_review_brief_is_approval",
    "operator_review_brief_satisfied_redactions",
    "operator_review_brief_authorized_delivery",
    "operator_review_brief_authorized_publication",
    "operator_review_brief_authorized_pricing",
    "operator_review_brief_authorized_queue_launch",
]

REQUIRED_BLOCKED_CLAIMS = [
    *GATE_REQUIRED_BLOCKED_CLAIMS,
    "operator_review_brief_is_approval",
    "operator_review_brief_satisfied_redactions",
    "operator_review_brief_authorized_delivery",
    "operator_review_brief_authorized_publication",
    "operator_review_brief_authorized_pricing",
    "operator_review_brief_authorized_queue_launch",
    "review_brief_publishable",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "approval_record_ready",
    "human_approved",
    "operator_approved",
    "selected_boundary_ready",
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_ready",
    "public_route_ready",
    "catalog_ready",
    "pilot_ready",
    "public_price_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
}

HUMAN_REVIEW_CHECKLIST = [
    "confirm_source_request_digest_matches_schema_gate",
    "confirm_exact_boundary_text_is_the_only_text_under_review",
    "attach_non_secret_human_operator_reference",
    "record_approval_timestamp_utc_if_and_only_if_approved",
    "verify_exact_gps_raw_metadata_and_private_source_identifiers_removed",
    "verify_domain_authority_and_guarantee_language_absent",
    "verify_dispatch_reputation_price_quote_and_queue_language_absent",
    "keep_authorized_delivery_path_none_unless_separate_delivery_gate_exists",
    "copy_still_blocked_claims_into_any_future_record",
    "keep_future_record_must_keep_false_flags_false",
]

SOURCE_GATE_CURRENT_VALUES = {
    "human_operator_approval_recorded": False,
    "selected_boundary_approved": False,
    "approved_text_boundary_recorded": False,
    "redaction_checks_passed": False,
    "authorized_delivery_path": AUTHORIZED_DELIVERY_PATH,
    "customer_delivery_path_authorized": False,
    "operator_publish_approval_recorded": False,
    "publication_approved": False,
}

CURRENT_BRIEF_VALUES = {
    **SOURCE_GATE_CURRENT_VALUES,
    "public_price_approved": False,
    "customer_quote_ready": False,
    "operator_queue_launch_ready": False,
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


def _load_source_gate(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_single_boundary_approval_record_schema_gate(artifact_dir=artifact_dir)


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("operator review brief source gate schema drift")
    if gate.get("gate_id") != GATE_ID:
        raise CityOpsContractError("operator review brief source gate id drift")
    if gate.get("gate_status") != GATE_STATUS:
        raise CityOpsContractError("operator review brief source gate status drift")
    if AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM not in gate.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("operator review brief source gate safe claim missing")
    forbidden_safe = set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"operator review brief source gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(GATE_REQUIRED_BLOCKED_CLAIMS) - set(gate.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"operator review brief source gate missing blocked claims: {sorted(missing_blocked)}"
        )
    fields = gate.get("future_approval_record_required_fields", [])
    if [field.get("field") for field in fields] != FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS:
        raise CityOpsContractError("operator review brief source required fields drift")
    for field in fields:
        if field.get("satisfied_by_this_gate") is not False:
            raise CityOpsContractError("operator review brief source satisfied future approval field")
    boundary = gate.get("selected_boundary", {})
    if boundary.get("key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("operator review brief source selected boundary drift")
    if boundary.get("selected_boundary_approved_here") is not False:
        raise CityOpsContractError("operator review brief source approved selected boundary")
    if boundary.get("human_operator_approval_recorded_here") is not False:
        raise CityOpsContractError("operator review brief source recorded human approval")
    if [item.get("check") for item in gate.get("redaction_contract", [])] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("operator review brief source redaction contract drift")
    for item in gate.get("redaction_contract", []):
        if item.get("passed_by_this_gate") is not False:
            raise CityOpsContractError("operator review brief source passed redactions")
    current = gate.get("current_gate_values", {})
    for flag, expected in SOURCE_GATE_CURRENT_VALUES.items():
        if current.get(flag) != expected:
            raise CityOpsContractError(f"operator review brief source promoted current value {flag}")
    if gate.get("future_record_must_keep_false") != FUTURE_RECORD_MUST_KEEP_FALSE:
        raise CityOpsContractError("operator review brief source false-flag contract drift")
    for flag in RECORD_GATE_READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"operator review brief source promoted readiness {flag}")


def _human_review_checklist(gate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "check": check,
            "required_for_future_human_record": True,
            "satisfied_by_this_brief": False,
            "operator_action_required": True,
            "source_gate_id": gate["gate_id"],
        }
        for check in HUMAN_REVIEW_CHECKLIST
    ]


def _redaction_review_items(gate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "check": item["check"],
            "required_for_future_human_record": True,
            "passed_by_this_brief": False,
            "evidence_reference_required_later": item["future_record_must_include_evidence_reference"],
        }
        for item in gate["redaction_contract"]
    ]


def build_aas_single_boundary_operator_review_brief(
    *,
    artifact_dir: Path | None = None,
    source_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an internal/admin brief for a human operator's later review."""

    gate = source_gate or _load_source_gate(artifact_dir=artifact_dir)
    _assert_source_gate(gate)
    boundary = gate["selected_boundary"]

    safe_to_claim = _dedupe(
        [
            *gate.get("safe_to_claim", []),
            AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*REQUIRED_BLOCKED_CLAIMS, *gate.get("do_not_claim_yet", [])])

    brief = {
        "schema": AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA,
        "brief_id": BRIEF_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "source_gate_file": AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME,
        "source_gate_schema": gate["schema"],
        "source_gate_id": gate["gate_id"],
        "source_gate_digest_sha256": _canonical_digest(gate),
        "source_safe_claim": AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "brief_status": BRIEF_STATUS,
        "selected_boundary": {
            "key": boundary["key"],
            "family_id": boundary["family_id"],
            "family_label": boundary["family_label"],
            "offer_id": boundary["offer_id"],
            "text_boundary_under_review": boundary["candidate_text_boundary"],
            "exact_text_under_review": boundary["candidate_text_value"],
            "candidate_text_fields": boundary["candidate_text_fields"],
            "selected_boundary_approved_by_this_brief": False,
            "human_operator_approval_recorded_by_this_brief": False,
        },
        "human_review_checklist": _human_review_checklist(gate),
        "redaction_review_items": _redaction_review_items(gate),
        "future_record_required_fields": gate["future_approval_record_required_fields"],
        "future_record_must_keep_false": FUTURE_RECORD_MUST_KEEP_FALSE,
        "current_brief_values": dict(CURRENT_BRIEF_VALUES),
        "readiness": {flag: False for flag in BRIEF_READINESS_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this brief only as a daytime checklist for a human operator. If the operator "
            "approves the exact boundary later, create a separate approval record with a "
            "non-secret reference, timestamp, redaction evidence, exact approved text, and the "
            "same blocked-claims list. Do not infer delivery, publication, routes, pricing, "
            "queue launch, dispatch, reputation, live runtime, GPS/raw metadata release, domain "
            "authority, or worker-copyable doctrine from this brief."
        ),
        "next_smallest_proof": (
            "Either keep the boundary held, or have a human operator create one separate "
            "approval record for this exact Compliance Desk package-label boundary while all "
            "delivery/publication/pricing/route/queue/dispatch/reputation/runtime/GPS/domain-authority/worker-doctrine "
            "flags remain false unless future gates prove them."
        ),
    }
    _assert_brief(brief)
    return brief


def _assert_brief(brief: dict[str, Any]) -> None:
    if brief.get("schema") != AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SCHEMA:
        raise CityOpsContractError("operator review brief schema drift")
    if brief.get("brief_id") != BRIEF_ID:
        raise CityOpsContractError("operator review brief id drift")
    if brief.get("scope") != SCOPE:
        raise CityOpsContractError("operator review brief scope drift")
    if brief.get("source_gate_file") != AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_FILENAME:
        raise CityOpsContractError("operator review brief source file drift")
    if brief.get("source_gate_schema") != AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("operator review brief source schema drift")
    if brief.get("source_gate_id") != GATE_ID:
        raise CityOpsContractError("operator review brief source id drift")
    if brief.get("source_safe_claim") != AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_SCHEMA_GATE_SAFE_CLAIM:
        raise CityOpsContractError("operator review brief source safe claim drift")
    if AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_SAFE_CLAIM not in brief.get("safe_to_claim", []):
        raise CityOpsContractError("operator review brief safe claim missing")
    forbidden_safe = set(brief.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"operator review brief forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(brief.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"operator review brief missing blocked claims: {sorted(missing_blocked)}"
        )
    if brief.get("brief_status") != BRIEF_STATUS:
        raise CityOpsContractError("operator review brief status drift")
    boundary = brief.get("selected_boundary", {})
    if boundary.get("key") != SELECTED_BOUNDARY_KEY:
        raise CityOpsContractError("operator review brief selected boundary drift")
    if boundary.get("exact_text_under_review") != "Visible posting / notice compliance snapshot":
        raise CityOpsContractError("operator review brief exact text drift")
    if boundary.get("selected_boundary_approved_by_this_brief") is not False:
        raise CityOpsContractError("operator review brief approved selected boundary")
    if boundary.get("human_operator_approval_recorded_by_this_brief") is not False:
        raise CityOpsContractError("operator review brief recorded human approval")
    checklist = brief.get("human_review_checklist", [])
    if [item.get("check") for item in checklist] != HUMAN_REVIEW_CHECKLIST:
        raise CityOpsContractError("operator review brief checklist drift")
    for item in checklist:
        if item.get("required_for_future_human_record") is not True:
            raise CityOpsContractError("operator review brief checklist item not required")
        if item.get("satisfied_by_this_brief") is not False:
            raise CityOpsContractError("operator review brief satisfied checklist item")
        if item.get("operator_action_required") is not True:
            raise CityOpsContractError("operator review brief checklist does not require action")
    if [item.get("check") for item in brief.get("redaction_review_items", [])] != REQUIRED_REDACTION_CHECKS:
        raise CityOpsContractError("operator review brief redaction items drift")
    for item in brief.get("redaction_review_items", []):
        if item.get("passed_by_this_brief") is not False:
            raise CityOpsContractError("operator review brief passed redactions")
    fields = brief.get("future_record_required_fields", [])
    if [field.get("field") for field in fields] != FUTURE_APPROVAL_RECORD_REQUIRED_FIELDS:
        raise CityOpsContractError("operator review brief future required fields drift")
    for field in fields:
        if field.get("satisfied_by_this_gate") is not False:
            raise CityOpsContractError("operator review brief carries satisfied future field")
    if brief.get("future_record_must_keep_false") != FUTURE_RECORD_MUST_KEEP_FALSE:
        raise CityOpsContractError("operator review brief false-flag contract drift")
    current = brief.get("current_brief_values", {})
    for flag, expected in CURRENT_BRIEF_VALUES.items():
        if current.get(flag) != expected:
            raise CityOpsContractError(f"operator review brief promoted current value {flag}")
    for flag in BRIEF_READINESS_FALSE_FLAGS:
        if brief.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"operator review brief promoted readiness {flag}")
    if brief.get("still_blocked_claims") != brief.get("do_not_claim_yet"):
        raise CityOpsContractError("operator review brief blocked claims drift")


def write_aas_single_boundary_operator_review_brief(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    brief = build_aas_single_boundary_operator_review_brief(artifact_dir=target_dir)
    path = target_dir / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME
    path.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_single_boundary_operator_review_brief(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        brief = json.load(fh)
    _assert_brief(brief)
    return brief
