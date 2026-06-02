"""Internal/admin no-answer observability rubric fixture.

This proof block consumes the session-manager no-mutation adapter field map and
turns the June 2 no-answer posture into a small scoring rubric for coordination
quality. The rubric measures only whether safe/blocked claim boundaries survive
handoffs. It records no operator answer or approval, creates no dashboard/public
metric, emits no reputation or Worker Skill DNA, mutates no session manager,
writes or retrieves no Acontext memory, and exposes no private context, raw
transcripts, exact GPS, raw metadata, or stopped-project inputs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .aas_session_manager_no_mutation_adapter_field_map import (
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME,
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM,
    AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SCHEMA,
    SESSION_MANAGER_FIELD_MAP_BLOCKED_CLAIMS,
    load_aas_session_manager_no_mutation_adapter_field_map,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SCHEMA = (
    "city_ops.aas_no_answer_observability_rubric_fixture.v1"
)
AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME = (
    "aas_no_answer_observability_rubric_fixture.json"
)
AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM = (
    "internal_admin_aas_no_answer_observability_rubric_fixture_landed"
)
AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_ID = (
    "execution_market.aas.no_answer_observability_rubric_fixture.2026_06_02_0600"
)
AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_VERDICT = (
    "no_answer_observability_rubric_landed_boundaries_preserved_no_runtime_or_external_promotion"
)

NO_ANSWER_OBSERVABILITY_STOP_LINE = (
    "This rubric is an internal/admin coordination-quality fixture only. It "
    "scores boundary preservation and records no answer or approval. It does "
    "not authorize dashboards, public metrics, customer copy, worker doctrine, "
    "runtime adapter registration or enablement, IRC/session-manager mutation, "
    "Acontext writes or retrievals, cross-project autorouting, pricing, queue, "
    "dispatch, reputation, Worker Skill DNA, payment/production claims, exact "
    "GPS/raw metadata release, private-context release, authority claims, or "
    "stopped-project integration."
)

NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS = [
    *SESSION_MANAGER_FIELD_MAP_BLOCKED_CLAIMS,
    "no_answer_observability_records_operator_answer",
    "no_answer_observability_records_operator_approval",
    "no_answer_observability_treats_score_as_approval",
    "no_answer_observability_selects_design_only_wiring",
    "no_answer_observability_authorizes_bounded_activation_test",
    "no_answer_observability_registers_or_enables_adapter",
    "no_answer_observability_mutates_session_manager",
    "no_answer_observability_writes_or_retrieves_live_acontext",
    "no_answer_observability_proves_runtime_parity",
    "no_answer_observability_creates_dashboard_or_public_metric",
    "no_answer_observability_creates_customer_public_or_worker_surface",
    "no_answer_observability_creates_worker_instruction_or_doctrine",
    "no_answer_observability_authorizes_pricing_queue_or_dispatch",
    "no_answer_observability_emits_erc8004_reputation_or_worker_skill_dna",
    "no_answer_observability_reverifies_payment_or_production",
    "no_answer_observability_exposes_exact_gps_or_raw_metadata",
    "no_answer_observability_releases_private_context_or_raw_transcripts",
    "no_answer_observability_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "no_answer_observability_integrates_stopped_projects",
]

_ACCESS_FLAGS = {
    "rubric_fixture_documented": True,
    "operator_answer_recorded": False,
    "operator_approval_recorded": False,
    "score_treated_as_approval": False,
    "dashboard_created": False,
    "public_metric_created": False,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "session_manager_mutated": False,
    "acontext_write_enabled": False,
    "acontext_retrieval_enabled": False,
    "cross_project_autorouting_enabled": False,
    "customer_visible": False,
    "public_visible": False,
    "worker_visible": False,
    "pricing_enabled": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "reputation_emission_enabled": False,
    "payment_or_production_reverified": False,
    "gps_or_raw_metadata_exposed": False,
    "private_context_released": False,
    "authority_claim_granted": False,
    "worker_doctrine_published": False,
    "stopped_projects_integrated": False,
}

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret" r"_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b\S+@\S+\.\S+\b"),
    re.compile(r"\+?\d[\d\s().-]{2,}[\s().-]\d[\d\s().-]{4,}\d"),
]


def build_aas_no_answer_observability_rubric_fixture(
    *,
    artifact_dir: str | Path | None = None,
    field_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin no-answer observability rubric."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = field_map or load_aas_session_manager_no_mutation_adapter_field_map(
        artifact_dir=base_dir
    )
    _assert_field_map_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM,
            AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME
    dimensions = _rubric_dimensions(source)
    total_score = sum(item["score"] for item in dimensions)
    max_score = sum(item["max_score"] for item in dimensions)

    rubric: dict[str, Any] = {
        "schema": AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SCHEMA,
        "rubric_id": AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_ID,
        "scope": "internal_admin_no_answer_coordination_observability_fixture_only",
        "status_verdict": AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_VERDICT,
        "source_artifacts": {
            "session_manager_no_mutation_adapter_field_map": {
                "file": AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME,
                "schema": source["schema"],
                "id": source["field_map_id"],
                "safe_claim": AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "derived_from": {
            "read_only": True,
            "consumes_only": [AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME],
            "scores_only_boundary_preservation": True,
            "records_operator_answer": False,
            "records_operator_approval": False,
            "treats_score_as_approval": False,
            "creates_dashboard": False,
            "creates_public_metric": False,
            "calls_acontext": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "changes_irc_runtime_session_manager": False,
            "registers_adapter": False,
            "enables_adapter": False,
            "enables_cross_project_autorouting": False,
            "writes_customer_copy": False,
            "writes_worker_instruction": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_or_production": False,
            "exposes_gps_or_metadata": False,
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "no_answer_observability_rubric": {
            "rubric_landed": True,
            "current_decision": "hold_no_runtime_mutation",
            "effective_decision_after_rubric": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "score_treated_as_approval": False,
            "dashboard_or_public_metric_authorized_now": False,
            "runtime_mutation_authorized_now": False,
            "answers_only": "whether no-answer handoffs preserve safe and blocked claim boundaries",
        },
        "scoring_model": {
            "model": "binary_boundary_preservation_v1",
            "score_is_internal_admin_only": True,
            "score_is_not_reputation": True,
            "score_is_not_worker_skill_dna": True,
            "score_is_not_customer_metric": True,
            "pass_threshold": max_score,
            "total_score": total_score,
            "max_score": max_score,
            "passed": total_score == max_score,
        },
        "rubric_dimensions": dimensions,
        "failure_actions": _failure_actions(),
        "future_gate_order": [
            {
                "step": "separate_explicit_operator_answer_record",
                "required_before": "any_approval_wiring_or_adapter_registration",
                "passed_now": False,
            },
            {
                "step": "separate_observability_surface_approval",
                "required_before": "any_dashboard_public_metric_or_reporting_route",
                "passed_now": False,
            },
            {
                "step": "separate_design_only_wiring_approval_record",
                "required_before": "disabled_session_manager_adapter_contract_implementation",
                "passed_now": False,
            },
            {
                "step": "bounded_local_activation_test_approval_record",
                "required_before": "any_live_session_manager_or_acontext_attempt",
                "passed_now": False,
            },
        ],
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "access_flags": dict(_ACCESS_FLAGS),
        "readiness": _readiness_flags(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_guidance": {
            "stop_line": NO_ANSWER_OBSERVABILITY_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_dashboard_spec": True,
            "next_required_gate": "separate_explicit_operator_answer_record_or_safe_pause",
            "if_no_human_answer": "use_this_rubric_only_for_internal_admin_handoff_quality_review",
        },
    }

    _assert_rubric_conservative(rubric, source=source, source_file=source_file)
    return rubric


def write_aas_no_answer_observability_rubric_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic no-answer observability rubric fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    rubric = build_aas_no_answer_observability_rubric_fixture(artifact_dir=base_dir)
    path = base_dir / AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME
    path.write_text(json.dumps(rubric, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_no_answer_observability_rubric_fixture(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted no-answer observability rubric fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_FILENAME
    rubric = json.loads(path.read_text(encoding="utf-8"))
    source = load_aas_session_manager_no_mutation_adapter_field_map(artifact_dir=base_dir)
    source_file = base_dir / AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME
    _assert_rubric_conservative(rubric, source=source, source_file=source_file)
    if rubric != build_aas_no_answer_observability_rubric_fixture(
        artifact_dir=base_dir,
        field_map=source,
    ):
        raise CityOpsContractError("AAS no-answer observability rubric fixture drift")
    return rubric


def _rubric_dimensions(source: dict[str, Any]) -> list[dict[str, Any]]:
    safe = set(source["claim_boundaries"]["safe_to_claim"])
    blocked = set(source["claim_boundaries"]["do_not_claim_yet"])
    readiness = source.get("readiness", {})
    access = source.get("access_flags", {})
    firewall = source.get("stopped_project_firewall", {})
    gates = source.get("future_gate_order", [])

    checks = [
        (
            "safe_and_blocked_claims_carried_together",
            AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM in safe
            and bool(blocked)
            and safe.isdisjoint(blocked),
            "safe_to_claim and do_not_claim_yet remain explicit and disjoint",
        ),
        (
            "no_answer_no_approval_preserved",
            readiness.get("operator_answer_absent") is True
            and readiness.get("operator_approval_record_absent") is True,
            "the no-answer posture is measurable without becoming approval",
        ),
        (
            "runtime_mutation_blocked",
            readiness.get("safe_for_runtime_session_manager_mutation") is False
            and access.get("session_manager_mutated") is False,
            "session-manager runtime changes remain blocked",
        ),
        (
            "acontext_live_access_blocked",
            readiness.get("safe_for_live_acontext_write_or_retrieval") is False
            and access.get("acontext_write_enabled") is False
            and access.get("acontext_retrieval_enabled") is False,
            "live Acontext write/retrieve remains blocked",
        ),
        (
            "external_surfaces_blocked",
            readiness.get("safe_for_customer_or_public_delivery") is False
            and readiness.get("safe_for_worker_instruction_or_doctrine") is False
            and access.get("customer_visible") is False
            and access.get("public_visible") is False
            and access.get("worker_visible") is False,
            "customer/public/worker surfaces remain blocked",
        ),
        (
            "settlement_and_reputation_blocked",
            readiness.get("safe_for_queue_launch_or_dispatch") is False
            and readiness.get("safe_for_reputation_or_worker_skill_dna") is False
            and access.get("dispatch_enabled") is False
            and access.get("reputation_emission_enabled") is False,
            "dispatch, reputation, Worker Skill DNA, and settlement signals remain blocked",
        ),
        (
            "privacy_and_authority_blocked",
            readiness.get("safe_for_gps_or_raw_metadata_release") is False
            and readiness.get("safe_for_private_context_release") is False
            and readiness.get("safe_for_domain_legal_emergency_repair_insurance_or_sla_authority") is False,
            "private context, raw metadata, exact location, and authority claims remain blocked",
        ),
        (
            "stopped_project_firewall_preserved",
            firewall.get("autojob_work_allowed") is False
            and firewall.get("frontier_academy_work_allowed") is False
            and firewall.get("kk_v2_work_allowed") is False
            and firewall.get("karmacadabra_v2_work_allowed") is False,
            "DREAM-PRIORITIES stopped-project firewall remains intact",
        ),
        (
            "future_gates_not_passed_by_observation",
            bool(gates) and all(gate.get("passed_now") is False for gate in gates),
            "future answer, approval, wiring, and activation gates remain separate",
        ),
    ]
    return [
        {
            "dimension": name,
            "max_score": 1,
            "score": 1 if passed else 0,
            "passed": passed,
            "meaning": meaning,
            "promotion_allowed": False,
        }
        for name, passed, meaning in checks
    ]


def _failure_actions() -> list[dict[str, str | bool]]:
    return [
        {
            "if_dimension_fails": "any",
            "action": "hold_no_runtime_mutation_and_reopen_source_boundary_review",
            "external_notification_required": False,
            "customer_or_worker_action_allowed": False,
        },
        {
            "if_dimension_fails": "safe_and_blocked_claims_carried_together",
            "action": "quarantine_handoff_until_safe_and_blocked_claims_are_restored",
            "external_notification_required": False,
            "customer_or_worker_action_allowed": False,
        },
        {
            "if_dimension_fails": "stopped_project_firewall_preserved",
            "action": "stop_dream_work_and_return_to_dream_priorities_file",
            "external_notification_required": False,
            "customer_or_worker_action_allowed": False,
        },
    ]


def _readiness_flags() -> dict[str, bool]:
    return {
        "no_answer_observability_rubric_landed": True,
        "source_session_manager_field_map_validated": True,
        "boundary_preservation_dimensions_named": True,
        "score_is_internal_admin_only": True,
        "operator_answer_absent": True,
        "operator_approval_record_absent": True,
        "default_hold_no_runtime_mutation_applied": True,
        "safe_for_internal_admin_handoff_quality_review": True,
        "safe_for_operator_answer_recording": False,
        "safe_for_operator_approval_recording": False,
        "safe_for_score_as_approval": False,
        "safe_for_observability_dashboard_or_public_metric": False,
        "safe_for_design_only_wiring_selection": False,
        "safe_for_bounded_local_activation_test_selection": False,
        "safe_for_runtime_adapter_registration": False,
        "safe_for_runtime_adapter_enablement": False,
        "safe_for_runtime_session_manager_mutation": False,
        "safe_for_live_acontext_write_or_retrieval": False,
        "safe_for_cross_project_autorouting": False,
        "safe_for_customer_or_public_delivery": False,
        "safe_for_worker_instruction_or_doctrine": False,
        "safe_for_queue_launch_or_dispatch": False,
        "safe_for_reputation_or_worker_skill_dna": False,
        "safe_for_payment_or_production_claim": False,
        "safe_for_gps_or_raw_metadata_release": False,
        "safe_for_private_context_release": False,
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority": False,
        "safe_for_stopped_project_integration": False,
        "general_acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "operator_activation_approved": False,
    }


def _assert_field_map_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SCHEMA:
        raise CityOpsContractError("unexpected session-manager field map source schema")
    if AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("session-manager field map source safe claim missing")

    mapped = source.get("no_mutation_adapter_field_map", {})
    if mapped.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source field map current decision promoted")
    if mapped.get("effective_decision_after_field_map") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source field map effective decision promoted")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "design_only_wiring_authorized_now",
        "bounded_activation_test_authorized_now",
        "adapter_registration_authorized_now",
        "adapter_enablement_authorized_now",
        "session_manager_mutation_authorized_now",
    ]:
        if mapped.get(key) is not False:
            raise CityOpsContractError(f"source field map promoted: {key}")

    readiness = source.get("readiness", {})
    for key in [
        "session_manager_no_mutation_field_map_landed",
        "source_carry_forward_card_validated",
        "allowed_adapter_fields_named",
        "excluded_fields_named",
        "adapter_runtime_defaults_named",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_adapter_shape_reference",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"source field map readiness missing: {key}")
    for key, value in readiness.items():
        if key not in {
            "session_manager_no_mutation_field_map_landed",
            "source_carry_forward_card_validated",
            "allowed_adapter_fields_named",
            "excluded_fields_named",
            "adapter_runtime_defaults_named",
            "operator_answer_absent",
            "operator_approval_record_absent",
            "default_hold_no_runtime_mutation_applied",
            "safe_for_internal_admin_adapter_shape_reference",
        } and value is not False:
            raise CityOpsContractError(f"source field map readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if key != "adapter_shape_documented" and value is not False:
            raise CityOpsContractError(f"source field map access flag promoted: {key}")
    for key, value in source.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"source field map stopped project firewall promoted: {key}")


def _assert_rubric_conservative(
    rubric: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_field_map_source_conservative(source)
    if rubric.get("schema") != AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SCHEMA:
        raise CityOpsContractError("unexpected no-answer observability rubric schema")
    if rubric.get("rubric_id") != AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_ID:
        raise CityOpsContractError("no-answer observability rubric id drift")
    if rubric.get("status_verdict") != AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_VERDICT:
        raise CityOpsContractError("no-answer observability rubric verdict drift")

    source_ref = rubric.get("source_artifacts", {}).get(
        "session_manager_no_mutation_adapter_field_map", {}
    )
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("no-answer observability source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("no-answer observability source file digest drift")
    if source_ref.get("safe_claim") != AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM:
        raise CityOpsContractError("no-answer observability source safe claim drift")

    observed = rubric.get("no_answer_observability_rubric", {})
    if observed.get("rubric_landed") is not True:
        raise CityOpsContractError("no-answer observability landed flag missing")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "score_treated_as_approval",
        "dashboard_or_public_metric_authorized_now",
        "runtime_mutation_authorized_now",
    ]:
        if observed.get(key) is not False:
            raise CityOpsContractError(f"no-answer observability promoted: {key}")
    if observed.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("no-answer observability current decision drift")
    if observed.get("effective_decision_after_rubric") != "hold_no_runtime_mutation":
        raise CityOpsContractError("no-answer observability effective decision drift")

    scoring = rubric.get("scoring_model", {})
    if scoring.get("score_is_internal_admin_only") is not True:
        raise CityOpsContractError("no-answer observability score escaped internal/admin scope")
    for key in ["score_is_not_reputation", "score_is_not_worker_skill_dna", "score_is_not_customer_metric"]:
        if scoring.get(key) is not True:
            raise CityOpsContractError(f"no-answer observability scoring boundary missing: {key}")
    if scoring.get("passed") is not True:
        raise CityOpsContractError("no-answer observability rubric did not pass")
    if scoring.get("total_score") != scoring.get("max_score"):
        raise CityOpsContractError("no-answer observability rubric score mismatch")

    dimensions = rubric.get("rubric_dimensions", [])
    if len(dimensions) != 9:
        raise CityOpsContractError("no-answer observability dimension count drift")
    if any(item.get("passed") is not True for item in dimensions):
        raise CityOpsContractError("no-answer observability dimension failed")
    if any(item.get("promotion_allowed") is not False for item in dimensions):
        raise CityOpsContractError("no-answer observability dimension allowed promotion")

    if any(gate.get("passed_now") is not False for gate in rubric.get("future_gate_order", [])):
        raise CityOpsContractError("no-answer observability future gate already passed")
    for key, value in rubric.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"no-answer observability stopped project firewall promoted: {key}")
    for key, expected in _ACCESS_FLAGS.items():
        if rubric.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"no-answer observability access flag drift: {key}")

    readiness = rubric.get("readiness", {})
    for key in [
        "no_answer_observability_rubric_landed",
        "source_session_manager_field_map_validated",
        "boundary_preservation_dimensions_named",
        "score_is_internal_admin_only",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_handoff_quality_review",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"no-answer observability readiness missing: {key}")
    for key, value in readiness.items():
        if key not in {
            "no_answer_observability_rubric_landed",
            "source_session_manager_field_map_validated",
            "boundary_preservation_dimensions_named",
            "score_is_internal_admin_only",
            "operator_answer_absent",
            "operator_approval_record_absent",
            "default_hold_no_runtime_mutation_applied",
            "safe_for_internal_admin_handoff_quality_review",
        } and value is not False:
            raise CityOpsContractError(f"no-answer observability readiness promoted: {key}")

    _assert_claim_boundaries(
        rubric.get("claim_boundaries", {}).get("safe_to_claim", []),
        rubric.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if AAS_NO_ANSWER_OBSERVABILITY_RUBRIC_FIXTURE_SAFE_CLAIM not in rubric.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("no-answer observability missing safe claim")
    missing_blocked = set(NO_ANSWER_OBSERVABILITY_BLOCKED_CLAIMS) - set(
        rubric.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"no-answer observability missing blocked claims: {sorted(missing_blocked)}"
        )

    guidance = rubric.get("operator_guidance", {})
    if guidance.get("stop_line") != NO_ANSWER_OBSERVABILITY_STOP_LINE:
        raise CityOpsContractError("no-answer observability stop line drift")
    for key in ["not_customer_copy", "not_worker_instruction", "not_dashboard_spec"]:
        if guidance.get(key) is not True:
            raise CityOpsContractError(f"no-answer observability guidance drift: {key}")

    serialized = json.dumps(rubric, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("no-answer observability persisted secret, identifier, or PII pattern")


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
