"""Internal/admin Acontext operator activation read-only review packet.

This proof block consumes the answer-shape validation packet and materializes
only the third allowed no-answer activity: continue read-only docs/fixture
review.  It turns late-night pattern recognition into a bounded review packet
without recording an operator answer or approval.

It does not register or enable a runtime adapter, does not mutate IRC/session-
manager behavior, does not start services, does not create/write/retrieve
Acontext sessions or messages, exposes no customer/public/worker surface,
launches no dispatch, emits no reputation, verifies no payment/production claim,
and persists no exact GPS/raw metadata, private context, secrets, session IDs,
or message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_operator_activation_answer_shape_validation_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCHEMA,
    ANSWER_SHAPE_VALIDATION_PACKET_BLOCKED_CLAIMS,
    load_acontext_operator_activation_answer_shape_validation_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCHEMA = (
    "city_ops.acontext_operator_activation_read_only_review_packet.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME = (
    "acontext_operator_activation_read_only_review_packet.json"
)
ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM = (
    "admin_acontext_operator_activation_read_only_review_packet_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_ID = (
    "execution_market.aas.acontext_operator_activation_read_only_review_packet.2026_06_01_0400"
)
ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCOPE = (
    "internal_admin_acontext_activation_read_only_docs_fixture_review_no_answer_no_approval"
)
ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_VERDICT = (
    "read_only_review_packet_landed_no_answer_no_approval_default_hold_preserved"
)
ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_STOP_LINE = (
    "This packet is read-only docs/fixture review only. It records no answer, "
    "records no approval, keeps the active decision at hold_no_runtime_mutation, "
    "and does not authorize runtime adapter registration or enablement, IRC/"
    "session-manager mutation, bounded activation tests, customer/public delivery, "
    "dispatch, reputation, payment/production claims, exact GPS/raw metadata "
    "release, private-context release, authority claims, worker-copyable doctrine, "
    "or stopped-project integration."
)

READ_ONLY_REVIEW_PACKET_BLOCKED_CLAIMS = [
    *ANSWER_SHAPE_VALIDATION_PACKET_BLOCKED_CLAIMS,
    "read_only_review_packet_records_operator_answer",
    "read_only_review_packet_records_operator_approval",
    "read_only_review_packet_treats_review_as_approval",
    "read_only_review_packet_changes_effective_decision",
    "read_only_review_packet_selects_design_only_wiring",
    "read_only_review_packet_selects_bounded_local_activation_test",
    "read_only_review_packet_authorizes_runtime_adapter_registration",
    "read_only_review_packet_authorizes_runtime_adapter_enablement",
    "read_only_review_packet_authorizes_irc_session_manager_mutation",
    "read_only_review_packet_authorizes_bounded_activation_test_execution",
    "read_only_review_packet_authorizes_cross_project_autorouting",
    "read_only_review_packet_authorizes_customer_copy_delivery_or_publication",
    "read_only_review_packet_authorizes_public_or_catalog_route",
    "read_only_review_packet_authorizes_pricing_or_customer_quote",
    "read_only_review_packet_authorizes_queue_launch_or_dispatch",
    "read_only_review_packet_authorizes_erc8004_reputation",
    "read_only_review_packet_authorizes_worker_skill_dna",
    "read_only_review_packet_reverifies_payment_or_production",
    "read_only_review_packet_allows_exact_gps_or_raw_metadata",
    "read_only_review_packet_releases_private_operator_context",
    "read_only_review_packet_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "read_only_review_packet_creates_worker_copyable_doctrine",
    "read_only_review_packet_declares_general_acontext_sink_ready",
    "read_only_review_packet_declares_runtime_parity_proven",
    "read_only_review_packet_authorizes_stopped_project_integration",
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

_REVIEW_INVARIANTS = [
    "source_digests_before_payloads",
    "operator_answers_before_runtime_mutation",
    "approval_records_before_activation_tests",
    "sanitized_fixtures_before_customer_surfaces",
    "blocked_claims_before_product_copy",
    "stopped_project_firewall_before_cross_project_reuse",
]



def build_acontext_operator_activation_read_only_review_packet(
    *,
    artifact_dir: str | Path | None = None,
    answer_shape_validation_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic read-only docs/fixture review packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = answer_shape_validation_packet or load_acontext_operator_activation_answer_shape_validation_packet(
        artifact_dir=base_dir
    )
    _assert_answer_shape_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *READ_ONLY_REVIEW_PACKET_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME
    packet: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCHEMA,
        "packet_id": ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_VERDICT,
        "source_artifacts": {
            "operator_activation_answer_shape_validation_packet": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME,
                "schema": source["schema"],
                "id": source["packet_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "read_only_review_packet": {
            "review_packet_id": "acontext_activation_read_only_docs_fixture_review_internal_admin_only",
            "intended_audience": "internal_admin_operator_only",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "current_decision": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "records_customer_or_public_approval": False,
            "review_only_landed": True,
            "review_is_not_approval": True,
            "effective_decision_after_review": "hold_no_runtime_mutation",
            "runtime_mutation_authorized": False,
            "bounded_activation_test_authorized": False,
            "review_inputs": [
                {
                    "input_id": "answer_shape_validation_fixture_digest_review",
                    "source_file": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME,
                    "mode": "digest_and_boundary_review_only",
                    "payload_persisted": False,
                    "raw_context_persisted": False,
                },
                {
                    "input_id": "activation_ladder_docs_boundary_review",
                    "source_file": "CITY_AS_A_SERVICE_ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_IMPLEMENTATION.md",
                    "mode": "docs_boundary_review_only",
                    "payload_persisted": False,
                    "raw_context_persisted": False,
                },
            ],
            "review_invariants": _REVIEW_INVARIANTS,
            "pattern_recognition_findings": [
                {
                    "finding_id": "memory_promotion_requires_explicit_answer_chain",
                    "safe_observation": "Durable agent memory should move from sanitized candidate to digest-backed fixture to explicit operator answer before any runtime mutation.",
                    "action_authorized": "read_only_review_only",
                },
                {
                    "finding_id": "coordination_value_comes_from_claim_boundaries",
                    "safe_observation": "IRC and session insights scale when every packet carries safe-to-claim and do-not-claim-yet boundaries instead of raw transcript authority.",
                    "action_authorized": "read_only_review_only",
                },
                {
                    "finding_id": "aas_multiplier_is_repeatable_low_authority_packaging",
                    "safe_observation": "The reusable AAS pattern is a low-authority package ladder: fixture, review packet, operator display, explicit decision, then bounded activation only if separately approved.",
                    "action_authorized": "read_only_review_only",
                },
            ],
        },
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "readiness": {
            "read_only_review_packet_landed": True,
            "source_answer_shape_validation_packet_validated": True,
            "operator_answer_absent": True,
            "operator_approval_record_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_read_only_docs_fixture_review": True,
            "safe_for_operator_answer_recording": False,
            "safe_for_operator_approval_recording": False,
            "safe_for_design_only_wiring_selection": False,
            "safe_for_bounded_local_activation_test_selection": False,
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
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_runtime_mutation_or_activation_test",
            "if_no_human_answer": "keep_default_hold_or_continue_read_only_internal_admin_docs_fixture_review_only",
        },
    }
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    return packet



def write_acontext_operator_activation_read_only_review_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext read-only review packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_acontext_operator_activation_read_only_review_packet(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path



def load_acontext_operator_activation_read_only_review_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext read-only review packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_answer_shape_validation_packet(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    if packet != build_acontext_operator_activation_read_only_review_packet(
        artifact_dir=base_dir,
        answer_shape_validation_packet=source,
    ):
        raise CityOpsContractError("Acontext operator activation read-only review packet fixture drift")
    return packet



def _assert_answer_shape_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext answer shape source schema")
    if ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext answer shape source safe claim missing")

    validation = source.get("answer_shape_validation_packet", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if validation.get(key) is not False:
            raise CityOpsContractError(f"source answer shape promoted: {key}")
    if validation.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source answer shape current decision promoted")
    if validation.get("effective_decision_after_shape_validation") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source answer shape effective decision promoted")
    if validation.get("shape_validity_is_not_approval") is not True:
        raise CityOpsContractError("source answer shape approval boundary missing")

    readiness = source.get("readiness", {})
    for key in [
        "answer_shape_validation_packet_landed",
        "source_hold_display_packet_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_future_answer_shape_validation",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"source answer shape readiness missing: {key}")
    for key in [
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
        "safe_for_design_only_wiring_selection",
        "safe_for_bounded_local_activation_test_selection",
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
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"source answer shape readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source answer shape access flag promoted: {key}")
    for key, value in source.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"source answer shape stopped project firewall promoted: {key}")
    missing_blocked = set(ANSWER_SHAPE_VALIDATION_PACKET_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source answer shape missing blocked claims: {sorted(missing_blocked)}"
        )



def _assert_packet_conservative(
    packet: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_answer_shape_source_conservative(source)
    if packet.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext read-only review packet schema")
    if packet.get("packet_id") != ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_ID:
        raise CityOpsContractError("Acontext read-only review packet id drift")
    if packet.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_VERDICT:
        raise CityOpsContractError("Acontext read-only review packet verdict drift")

    source_ref = packet.get("source_artifacts", {}).get("operator_activation_answer_shape_validation_packet", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext read-only review source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext read-only review source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM:
        raise CityOpsContractError("Acontext read-only review source safe claim drift")

    review = packet.get("read_only_review_packet", {})
    if review.get("intended_audience") != "internal_admin_operator_only":
        raise CityOpsContractError("Acontext read-only review audience drift")
    for key in ["not_customer_copy", "not_worker_instruction", "review_only_landed", "review_is_not_approval"]:
        if review.get(key) is not True:
            raise CityOpsContractError(f"Acontext read-only review boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if review.get(key) is not False:
            raise CityOpsContractError(f"Acontext read-only review promoted: {key}")
    if review.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext read-only review current decision drift")
    if review.get("effective_decision_after_review") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext read-only review effective decision drift")
    if review.get("review_invariants") != _REVIEW_INVARIANTS:
        raise CityOpsContractError("Acontext read-only review invariants drift")
    if not review.get("pattern_recognition_findings"):
        raise CityOpsContractError("Acontext read-only review missing pattern findings")
    for item in review.get("review_inputs", []):
        if item.get("payload_persisted") is not False:
            raise CityOpsContractError("Acontext read-only review persisted payload")
        if item.get("raw_context_persisted") is not False:
            raise CityOpsContractError("Acontext read-only review persisted raw context")
    for item in review.get("pattern_recognition_findings", []):
        if item.get("action_authorized") != "read_only_review_only":
            raise CityOpsContractError("Acontext read-only review finding authorized action")

    for key, value in packet.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"Acontext read-only review stopped project firewall promoted: {key}")

    readiness = packet.get("readiness", {})
    for key in [
        "read_only_review_packet_landed",
        "source_answer_shape_validation_packet_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_read_only_docs_fixture_review",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"Acontext read-only review readiness missing: {key}")
    for key in [
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
        "safe_for_design_only_wiring_selection",
        "safe_for_bounded_local_activation_test_selection",
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
            raise CityOpsContractError(f"Acontext read-only review readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if packet.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext read-only review access flag promoted: {key}")

    _assert_claim_boundaries(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext read-only review missing safe claim")

    serialized = json.dumps(packet, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("Acontext read-only review persisted secret, identifier, or PII pattern")



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
