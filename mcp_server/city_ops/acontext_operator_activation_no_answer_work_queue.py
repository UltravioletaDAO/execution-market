"""Internal/admin Acontext no-answer activation work queue.

This proof block consumes the Acontext operator activation answer schema gate and
turns the current absence of a human/operator answer into an explicit safe work
queue.  It is deliberately boring: display the no-answer posture, validate only
the shape of a future answer, or continue read-only fixture/doc review.

It records no operator answer, records no approval, does not register or enable
a runtime adapter, does not mutate IRC/session-manager behavior, does not start
services, does not create/write/retrieve Acontext sessions or messages, exposes
no customer/public/worker surface, launches no dispatch, emits no reputation,
verifies no payment/production claim, and persists no exact GPS/raw metadata,
private context, secrets, session IDs, or message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_operator_activation_answer_schema_gate import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCHEMA,
    ALLOWED_OPERATOR_ANSWER_VALUES,
    ANSWER_SCHEMA_BLOCKED_CLAIMS,
    load_acontext_operator_activation_answer_schema_gate,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCHEMA = (
    "city_ops.acontext_operator_activation_no_answer_work_queue.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME = (
    "acontext_operator_activation_no_answer_work_queue.json"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM = (
    "admin_acontext_operator_activation_no_answer_work_queue_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_ID = (
    "execution_market.aas.acontext_operator_activation_no_answer_work_queue.2026_06_01_0100"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCOPE = (
    "internal_admin_acontext_activation_no_answer_safe_work_queue_no_approval_recorded"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_VERDICT = (
    "no_answer_work_queue_landed_default_hold_preserved_no_runtime_mutation"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_STOP_LINE = (
    "No explicit operator answer exists, so the only allowed work is internal/admin "
    "display of the hold posture, shape-only validation of a future answer, or "
    "read-only docs/fixture review. This queue records no answer, records no "
    "approval, and does not authorize runtime adapter registration or enablement, "
    "IRC/session-manager mutation, bounded activation tests, customer/public "
    "delivery, dispatch, reputation, payment/production claims, exact GPS/raw "
    "metadata release, private-context release, authority claims, worker-copyable "
    "doctrine, or stopped-project integration."
)

NO_ANSWER_WORK_QUEUE_BLOCKED_CLAIMS = [
    *ANSWER_SCHEMA_BLOCKED_CLAIMS,
    "no_answer_work_queue_records_operator_answer",
    "no_answer_work_queue_records_operator_approval",
    "no_answer_work_queue_selects_design_only_wiring",
    "no_answer_work_queue_selects_bounded_local_activation_test",
    "no_answer_work_queue_authorizes_runtime_adapter_registration",
    "no_answer_work_queue_authorizes_runtime_adapter_enablement",
    "no_answer_work_queue_authorizes_irc_session_manager_mutation",
    "no_answer_work_queue_authorizes_cross_project_autorouting",
    "no_answer_work_queue_authorizes_customer_copy_delivery_or_publication",
    "no_answer_work_queue_authorizes_public_or_catalog_route",
    "no_answer_work_queue_authorizes_pricing_or_customer_quote",
    "no_answer_work_queue_authorizes_queue_launch_or_dispatch",
    "no_answer_work_queue_authorizes_erc8004_reputation",
    "no_answer_work_queue_authorizes_worker_skill_dna",
    "no_answer_work_queue_reverifies_payment_or_production",
    "no_answer_work_queue_allows_exact_gps_or_raw_metadata",
    "no_answer_work_queue_releases_private_operator_context",
    "no_answer_work_queue_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "no_answer_work_queue_creates_worker_copyable_doctrine",
    "no_answer_work_queue_declares_general_acontext_sink_ready",
    "no_answer_work_queue_declares_runtime_parity_proven",
    "no_answer_work_queue_authorizes_stopped_project_integration",
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
    re.compile(r"\+?\d[\d\s().-]{7,}\d"),
]


def build_acontext_operator_activation_no_answer_work_queue(
    *,
    artifact_dir: str | Path | None = None,
    answer_schema_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic safe work queue while no operator answer exists."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = answer_schema_gate or load_acontext_operator_activation_answer_schema_gate(
        artifact_dir=base_dir
    )
    _assert_answer_schema_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *NO_ANSWER_WORK_QUEUE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME
    queue: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCHEMA,
        "queue_id": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_VERDICT,
        "source_artifacts": {
            "operator_activation_answer_schema_gate": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME,
                "schema": source["schema"],
                "id": source["gate_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": {
            "candidate_id": source["activation_candidate"]["candidate_id"],
            "source_current_decision": source["activation_candidate"]["source_current_decision"],
            "default_decision": "hold_no_runtime_mutation",
            "customer_or_worker_exposure": "none",
        },
        "no_answer_runtime_posture": {
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "answer_schema_validated": False,
            "effective_decision": "hold_no_runtime_mutation",
            "records_customer_or_public_approval": False,
            "runtime_mutation_authorized": False,
            "bounded_activation_test_authorized": False,
            "this_queue_is_not_an_approval_record": True,
        },
        "allowed_internal_work_queue": [
            {
                "work_id": "display_internal_admin_hold_and_answer_schema",
                "description": "Show the current no-answer/default-hold posture and allowed future answer values.",
                "requires_operator_answer": False,
                "records_approval": False,
                "runtime_mutation": False,
                "customer_or_worker_exposure": "none",
            },
            {
                "work_id": "validate_future_answer_shape_only",
                "description": "Run the answer-shape validator if a future explicit answer is supplied, without treating shape validity as approval.",
                "requires_operator_answer": True,
                "records_approval": False,
                "runtime_mutation": False,
                "customer_or_worker_exposure": "none",
            },
            {
                "work_id": "continue_read_only_docs_or_fixture_review",
                "description": "Review docs or deterministic fixtures while preserving all blocked claims and stopped-project firewalls.",
                "requires_operator_answer": False,
                "records_approval": False,
                "runtime_mutation": False,
                "customer_or_worker_exposure": "none",
            },
        ],
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "future_answer_values_still_require_separate_artifact": ALLOWED_OPERATOR_ANSWER_VALUES,
        "readiness": {
            "no_answer_work_queue_landed": True,
            "source_answer_schema_gate_validated": True,
            "operator_answer_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_internal_admin_no_answer_work_queue_display": True,
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
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_runtime_mutation_or_activation_test",
            "if_no_human_answer": "stay_on_hold_or_do_read_only_internal_admin_review_only",
        },
    }
    _assert_queue_conservative(queue, source=source, source_file=source_file)
    return queue


def write_acontext_operator_activation_no_answer_work_queue(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext no-answer activation work queue."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    queue = build_acontext_operator_activation_no_answer_work_queue(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME
    path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_operator_activation_no_answer_work_queue(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted no-answer activation work queue."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME
    queue = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_answer_schema_gate(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME
    _assert_queue_conservative(queue, source=source, source_file=source_file)
    if queue != build_acontext_operator_activation_no_answer_work_queue(
        artifact_dir=base_dir,
        answer_schema_gate=source,
    ):
        raise CityOpsContractError("Acontext no-answer activation work queue fixture drift")
    return queue


def _assert_answer_schema_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("unexpected Acontext answer schema source schema")
    if ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext answer schema source safe claim missing")
    state = source.get("current_answer_state", {})
    if state.get("explicit_operator_answer_present") is not False:
        raise CityOpsContractError("Acontext answer schema source records answer")
    if state.get("operator_approval_record_present") is not False:
        raise CityOpsContractError("Acontext answer schema source records approval")
    if state.get("effective_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext answer schema source decision promoted")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source answer schema access flag promoted: {key}")
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
            raise CityOpsContractError(f"source answer schema readiness promoted: {key}")
    missing_blocked = set(ANSWER_SCHEMA_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source answer schema missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_queue_conservative(
    queue: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_answer_schema_source_conservative(source)
    if queue.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCHEMA:
        raise CityOpsContractError("unexpected Acontext no-answer work queue schema")
    if queue.get("queue_id") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_ID:
        raise CityOpsContractError("Acontext no-answer work queue id drift")
    if queue.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_VERDICT:
        raise CityOpsContractError("Acontext no-answer work queue verdict drift")

    source_ref = queue.get("source_artifacts", {}).get("operator_activation_answer_schema_gate", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext no-answer work queue source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext no-answer work queue source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM:
        raise CityOpsContractError("Acontext no-answer work queue source safe claim drift")

    posture = queue.get("no_answer_runtime_posture", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "answer_schema_validated",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if posture.get(key) is not False:
            raise CityOpsContractError(f"Acontext no-answer posture promoted: {key}")
    if posture.get("effective_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext no-answer work queue decision drift")
    if posture.get("this_queue_is_not_an_approval_record") is not True:
        raise CityOpsContractError("Acontext no-answer approval boundary drift")

    for item in queue.get("allowed_internal_work_queue", []):
        if item.get("records_approval") is not False:
            raise CityOpsContractError("Acontext no-answer work item records approval")
        if item.get("runtime_mutation") is not False:
            raise CityOpsContractError("Acontext no-answer work item mutates runtime")
        if item.get("customer_or_worker_exposure") != "none":
            raise CityOpsContractError("Acontext no-answer work item exposes customer or worker surface")
    if not queue.get("allowed_internal_work_queue"):
        raise CityOpsContractError("Acontext no-answer work queue missing internal work items")

    for key, value in queue.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"Acontext no-answer stopped project firewall promoted: {key}")

    readiness = queue.get("readiness", {})
    if readiness.get("safe_for_internal_admin_no_answer_work_queue_display") is not True:
        raise CityOpsContractError("Acontext no-answer display readiness missing")
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
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority",
        "safe_for_worker_copyable_doctrine",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"Acontext no-answer readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if queue.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext no-answer access flag promoted: {key}")

    _assert_claim_boundaries(
        queue.get("claim_boundaries", {}).get("safe_to_claim", []),
        queue.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM not in queue.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext no-answer work queue missing safe claim")

    serialized = json.dumps(queue, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("Acontext no-answer work queue persisted secret, identifier, or PII pattern")


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
