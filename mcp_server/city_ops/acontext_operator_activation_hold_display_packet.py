"""Internal/admin Acontext operator activation hold display packet.

This proof block consumes the no-answer activation work queue and materializes
only the first allowed no-answer activity: display the current internal/admin
hold posture and the allowed future answer values.

It records no operator answer, records no approval, does not validate or accept
a future answer, does not register or enable a runtime adapter, does not mutate
IRC/session-manager behavior, does not start services, does not create/write/
retrieve Acontext sessions or messages, exposes no customer/public/worker
surface, launches no dispatch, emits no reputation, verifies no payment/
production claim, and persists no exact GPS/raw metadata, private context,
secrets, session IDs, or message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_operator_activation_answer_schema_gate import ALLOWED_OPERATOR_ANSWER_VALUES
from .acontext_operator_activation_no_answer_work_queue import (
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCHEMA,
    NO_ANSWER_WORK_QUEUE_BLOCKED_CLAIMS,
    load_acontext_operator_activation_no_answer_work_queue,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCHEMA = (
    "city_ops.acontext_operator_activation_hold_display_packet.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME = (
    "acontext_operator_activation_hold_display_packet.json"
)
ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM = (
    "admin_acontext_operator_activation_hold_display_packet_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_ID = (
    "execution_market.aas.acontext_operator_activation_hold_display_packet.2026_06_01_0200"
)
ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCOPE = (
    "internal_admin_acontext_activation_hold_display_no_answer_no_approval"
)
ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_VERDICT = (
    "hold_display_packet_landed_no_answer_no_approval_default_hold_preserved"
)
ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_STOP_LINE = (
    "This packet is only an internal/admin display of the existing no-answer hold posture. "
    "It records no answer, records no approval, does not validate a future answer, and "
    "does not authorize runtime adapter registration or enablement, IRC/session-manager "
    "mutation, bounded activation tests, customer/public delivery, dispatch, reputation, "
    "payment/production claims, exact GPS/raw metadata release, private-context release, "
    "authority claims, worker-copyable doctrine, or stopped-project integration."
)

HOLD_DISPLAY_PACKET_BLOCKED_CLAIMS = [
    *NO_ANSWER_WORK_QUEUE_BLOCKED_CLAIMS,
    "hold_display_packet_records_operator_answer",
    "hold_display_packet_records_operator_approval",
    "hold_display_packet_validates_future_answer",
    "hold_display_packet_accepts_future_answer_as_approval",
    "hold_display_packet_authorizes_runtime_adapter_registration",
    "hold_display_packet_authorizes_runtime_adapter_enablement",
    "hold_display_packet_authorizes_irc_session_manager_mutation",
    "hold_display_packet_authorizes_bounded_activation_test_execution",
    "hold_display_packet_authorizes_cross_project_autorouting",
    "hold_display_packet_authorizes_customer_copy_delivery_or_publication",
    "hold_display_packet_authorizes_public_or_catalog_route",
    "hold_display_packet_authorizes_pricing_or_customer_quote",
    "hold_display_packet_authorizes_queue_launch_or_dispatch",
    "hold_display_packet_authorizes_erc8004_reputation",
    "hold_display_packet_authorizes_worker_skill_dna",
    "hold_display_packet_reverifies_payment_or_production",
    "hold_display_packet_allows_exact_gps_or_raw_metadata",
    "hold_display_packet_releases_private_operator_context",
    "hold_display_packet_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "hold_display_packet_creates_worker_copyable_doctrine",
    "hold_display_packet_declares_general_acontext_sink_ready",
    "hold_display_packet_declares_runtime_parity_proven",
    "hold_display_packet_authorizes_stopped_project_integration",
]

_FALSE_ACCESS_FLAGS = {
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "cross_project_autorouting_enabled": False,
    "network_route_registered": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "pricing_enabled": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "starts_live_services": False,
    "creates_sessions": False,
    "writes_messages": False,
    "retrieves_messages": False,
    "emits_reputation_receipts": False,
    "reverifies_payment_or_production": False,
    "exposes_gps_or_metadata": False,
    "releases_private_operator_context": False,
    "grants_domain_or_emergency_authority": False,
    "publishes_worker_doctrine": False,
    "integrates_stopped_projects": False,
}

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-ac-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret" r"_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b\S+@\S+\.\S+\b"),
    re.compile(r"\+?\d[\d\s().-]{2,}[\s().-]\d[\d\s().-]{4,}\d"),
]


def build_acontext_operator_activation_hold_display_packet(
    *,
    artifact_dir: str | Path | None = None,
    no_answer_work_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic hold display packet while no operator answer exists."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = no_answer_work_queue or load_acontext_operator_activation_no_answer_work_queue(
        artifact_dir=base_dir
    )
    _assert_no_answer_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *HOLD_DISPLAY_PACKET_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME
    packet: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCHEMA,
        "packet_id": ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_VERDICT,
        "source_artifacts": {
            "operator_activation_no_answer_work_queue": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME,
                "schema": source["schema"],
                "id": source["queue_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "hold_display_packet": {
            "display_id": "acontext_activation_hold_no_answer_internal_admin_display",
            "intended_audience": "internal_admin_operator_only",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "current_decision": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "answer_schema_validated": False,
            "records_customer_or_public_approval": False,
            "runtime_mutation_authorized": False,
            "bounded_activation_test_authorized": False,
            "safe_status_lines": [
                "Candidate: irc_session_manager_memory_sink",
                "Current decision: hold_no_runtime_mutation",
                "Operator answer present: false",
                "Approval record present: false",
                "Runtime mutation authorized: false",
                "Customer/public/worker exposure: none",
            ],
            "allowed_future_answer_values": ALLOWED_OPERATOR_ANSWER_VALUES,
        },
        "displayed_allowed_no_answer_work": [
            {
                "work_id": item["work_id"],
                "requires_operator_answer": item["requires_operator_answer"],
                "records_approval": item["records_approval"],
                "runtime_mutation": item["runtime_mutation"],
                "customer_or_worker_exposure": item["customer_or_worker_exposure"],
            }
            for item in source["allowed_internal_work_queue"]
        ],
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "readiness": {
            "hold_display_packet_landed": True,
            "source_no_answer_work_queue_validated": True,
            "operator_answer_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_internal_admin_hold_display": True,
            "safe_for_future_answer_validation": False,
            "safe_for_operator_answer_recording": False,
            "safe_for_operator_approval_recording": False,
            "safe_for_runtime_adapter_registration": False,
            "safe_for_runtime_adapter_enablement": False,
            "safe_for_runtime_session_manager_mutation": False,
            "safe_for_bounded_activation_test_execution": False,
            "safe_for_cross_project_autorouting": False,
            "safe_for_customer_or_public_delivery": False,
            "safe_for_queue_launch_or_dispatch": False,
            "safe_for_reputation_or_worker_skill_dna": False,
            "safe_for_payment_or_production_claim": False,
            "safe_for_gps_or_raw_metadata_release": False,
            "safe_for_private_context_release": False,
            "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority": False,
            "safe_for_worker_copyable_doctrine": False,
            "safe_for_stopped_project_integration": False,
            "general_acontext_sink_ready": False,
            "runtime_parity_proven": False,
            "operator_activation_approved": False,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_guidance": {
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_runtime_mutation_or_activation_test",
            "if_no_human_answer": "display_this_packet_or_continue_read_only_internal_admin_review_only",
        },
    }
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    return packet


def write_acontext_operator_activation_hold_display_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext hold display packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_acontext_operator_activation_hold_display_packet(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_operator_activation_hold_display_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext hold display packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_no_answer_work_queue(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    if packet != build_acontext_operator_activation_hold_display_packet(
        artifact_dir=base_dir,
        no_answer_work_queue=source,
    ):
        raise CityOpsContractError("Acontext operator activation hold display packet fixture drift")
    return packet


def _assert_no_answer_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCHEMA:
        raise CityOpsContractError("unexpected Acontext no-answer work queue source schema")
    if ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext no-answer work queue source safe claim missing")
    posture = source.get("no_answer_runtime_posture", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "answer_schema_validated",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if posture.get(key) is not False:
            raise CityOpsContractError(f"source no-answer posture promoted: {key}")
    if posture.get("effective_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source no-answer decision promoted")
    if posture.get("this_queue_is_not_an_approval_record") is not True:
        raise CityOpsContractError("source no-answer approval boundary drift")

    if source.get("readiness", {}).get("safe_for_internal_admin_no_answer_work_queue_display") is not True:
        raise CityOpsContractError("source no-answer display readiness missing")
    for key in [
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_adapter_enablement",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_bounded_activation_test_execution",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_worker_copyable_doctrine",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        if source.get("readiness", {}).get(key) is not False:
            raise CityOpsContractError(f"source no-answer readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source no-answer access flag promoted: {key}")
    for item in source.get("allowed_internal_work_queue", []):
        if item.get("records_approval") is not False:
            raise CityOpsContractError("source no-answer work item records approval")
        if item.get("runtime_mutation") is not False:
            raise CityOpsContractError("source no-answer work item mutates runtime")
        if item.get("customer_or_worker_exposure") != "none":
            raise CityOpsContractError("source no-answer work item exposes customer/worker surface")
    missing_blocked = set(NO_ANSWER_WORK_QUEUE_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source no-answer work queue missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_packet_conservative(
    packet: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_no_answer_source_conservative(source)
    if packet.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext hold display packet schema")
    if packet.get("packet_id") != ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_ID:
        raise CityOpsContractError("Acontext hold display packet id drift")
    if packet.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_VERDICT:
        raise CityOpsContractError("Acontext hold display packet verdict drift")

    source_ref = packet.get("source_artifacts", {}).get("operator_activation_no_answer_work_queue", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext hold display source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext hold display source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM:
        raise CityOpsContractError("Acontext hold display source safe claim drift")

    display = packet.get("hold_display_packet", {})
    if display.get("intended_audience") != "internal_admin_operator_only":
        raise CityOpsContractError("Acontext hold display audience drift")
    for key in ["not_customer_copy", "not_worker_instruction"]:
        if display.get(key) is not True:
            raise CityOpsContractError(f"Acontext hold display boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "answer_schema_validated",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if display.get(key) is not False:
            raise CityOpsContractError(f"Acontext hold display promoted: {key}")
    if display.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext hold display decision drift")
    if display.get("allowed_future_answer_values") != ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("Acontext hold display allowed answer values drift")

    for item in packet.get("displayed_allowed_no_answer_work", []):
        if item.get("records_approval") is not False:
            raise CityOpsContractError("Acontext hold display work item records approval")
        if item.get("runtime_mutation") is not False:
            raise CityOpsContractError("Acontext hold display work item mutates runtime")
        if item.get("customer_or_worker_exposure") != "none":
            raise CityOpsContractError("Acontext hold display work item exposes customer/worker surface")
    if not packet.get("displayed_allowed_no_answer_work"):
        raise CityOpsContractError("Acontext hold display missing displayed work items")

    for key, value in packet.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"Acontext hold display stopped project firewall promoted: {key}")

    readiness = packet.get("readiness", {})
    for key in [
        "hold_display_packet_landed",
        "source_no_answer_work_queue_validated",
        "operator_answer_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_hold_display",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"Acontext hold display readiness missing: {key}")
    for key in [
        "safe_for_future_answer_validation",
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_adapter_enablement",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_bounded_activation_test_execution",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority",
        "safe_for_worker_copyable_doctrine",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"Acontext hold display readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if packet.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext hold display access flag promoted: {key}")

    _assert_claim_boundaries(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext hold display missing safe claim")

    serialized = json.dumps(packet, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("Acontext hold display persisted secret, identifier, or PII pattern")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    if not safe_to_claim or not do_not_claim_yet:
        raise CityOpsContractError("claim boundaries must be explicit")
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
