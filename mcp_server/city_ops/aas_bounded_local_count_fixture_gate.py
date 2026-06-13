"""Internal/admin Bounded Local Count fixture schema and review gate.

This slice implements the smallest safe follow-up to the June 12 bounded local
count evidence contract. It validates only internal/admin fixture packets for a
single bounded count question. It records no operator answer, approval,
collection authorization, customer/worker/public copy, catalog/pricing/route,
dispatch, runtime movement, reputation, payment, location/private-context
release, authority claim, or stopped-project integration.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA = (
    "city_ops.aas_bounded_local_count_fixture_gate.v1"
)
AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME = (
    "aas_bounded_local_count_fixture_gate.json"
)
AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM = (
    "internal_admin_aas_bounded_local_count_fixture_gate_landed"
)
AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_ID = (
    "execution_market.aas.bounded_local_count.fixture_gate.2026_06_13_0000"
)
AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS = (
    "internal_admin_fixture_schema_review_gate_only_no_answer_no_approval_no_collection_or_exposure"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "planning"
    / "CITY_AS_A_SERVICE_11PM_BOUNDED_LOCAL_COUNT_EVIDENCE_CONTRACT_2026_06_12.md"
)
SOURCE_CONTRACT_DOC_PATH = (
    "docs/planning/CITY_AS_A_SERVICE_11PM_BOUNDED_LOCAL_COUNT_EVIDENCE_CONTRACT_2026_06_12.md"
)
SOURCE_CONTRACT_SAFE_CLAIM = (
    "internal_admin_aas_11pm_bounded_local_count_evidence_contract_2026_06_12_landed"
)

REQUIRED_PACKET_FIELDS = [
    "schema",
    "status",
    "count_question",
    "observation_window",
    "place_boundary",
    "count_method",
    "observed_value",
    "coverage_limits",
    "uncertainty_statement",
    "evidence_digest_reference",
    "redaction_review_state",
    "blocked_claims_snapshot",
]

ALLOWED_PACKET_SCHEMA = "execution_market.aas.bounded_local_count.evidence_contract.v0"
ALLOWED_PACKET_STATUS = "internal_admin_contract_only_no_answer_no_approval"
ALLOWED_COUNT_METHODS = [
    "direct_visual_count",
    "posted_count",
    "receipt_or_log_count",
    "visible_subset",
    "unable_to_count",
]
ALLOWED_REDACTION_REVIEW_STATES = [
    "not_reviewed",
    "reviewed_internal_only",
]

REQUIRED_BLOCKED_CLAIMS = [
    "customer_public_worker_surface",
    "dataset_publication_or_representativeness",
    "catalog_pricing_queue_dispatch",
    "reputation_worker_skill_dna",
    "payment_production_change",
    "exact_location_raw_metadata_private_context_release",
    "authority_or_certification_claim",
    "worker_copyable_doctrine",
]

FALSE_FLAGS = {
    "gate_records_operator_answer": False,
    "gate_records_operator_approval": False,
    "gate_creates_answer_receipt": False,
    "gate_authorizes_collection_site_access_or_worker_tasking": False,
    "gate_creates_customer_public_or_worker_copy": False,
    "gate_creates_catalog_pricing_quote_route_or_queue": False,
    "gate_launches_dispatch_or_worker_instruction": False,
    "gate_publishes_dataset_report_dashboard_or_benchmark": False,
    "gate_claims_representativeness_statistical_validity_or_certification": False,
    "gate_emits_reputation_or_worker_skill_dna": False,
    "gate_reverifies_payment_or_production": False,
    "gate_mutates_runtime_acontext_or_irc": False,
    "gate_exposes_exact_location_raw_metadata_private_context_or_pii": False,
    "gate_grants_legal_regulatory_safety_repair_or_insurance_authority": False,
    "gate_publishes_worker_copyable_doctrine": False,
    "gate_integrates_or_expands_stopped_projects": False,
}

BOUNDING_RULES = [
    "count_question_must_be_one_bounded_observable_count_or_range_question",
    "observation_window_must_be_bounded_and_non_sensitive",
    "place_boundary_must_be_generalized_or_opaque_without_exact_location",
    "count_method_must_be_one_allowed_method",
    "observed_value_must_be_integer_range_or_unable_to_count",
    "coverage_limits_must_be_non_empty",
    "uncertainty_statement_must_be_present_and_plain_language",
    "evidence_reference_must_be_digest_or_opaque_reference_only",
    "redaction_state_must_not_exceed_internal_review",
    "blocked_claims_snapshot_must_preserve_all_contract_blockers",
]

FORBIDDEN_QUESTION_FRAGMENTS = [
    "citywide",
    "representative",
    "statistically valid",
    "complete dataset",
    "continuous",
    "always",
    "everywhere",
    "all locations",
    "all sites",
    "forecast",
    "predict",
    "diagnose",
    "certify",
]

FORBIDDEN_PACKET_FRAGMENTS = [
    "customer-ready",
    "customer ready",
    "public catalog",
    "priced offer",
    "queue ready",
    "dispatch ready",
    "worker instruction",
    "worker-copyable",
    "worker copyable",
    "erc-8004 reputation",
    "erc8004 reputation",
    "worker skill dna",
    "payment ready",
    "production ready",
    "acontext ready",
    "runtime mutation",
    "gps coordinates",
    "latitude",
    "longitude",
    "raw metadata",
    "private context",
    "pii",
    "official measurement",
    "certified count",
    "representative sample",
    "statistically valid",
    "regulatory ready",
    "legal authority",
    "insurance-ready",
    "repair-authorized",
    "autojob",
    "frontier academy",
    "kk v2",
    "karmacadabra v2",
]

AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS = [
    "bounded_local_count_fixture_gate_records_operator_answer",
    "bounded_local_count_fixture_gate_records_operator_approval",
    "bounded_local_count_fixture_gate_creates_answer_receipt",
    "bounded_local_count_fixture_gate_authorizes_collection_site_access_or_worker_tasking",
    "bounded_local_count_fixture_gate_creates_customer_public_or_worker_copy",
    "bounded_local_count_fixture_gate_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "bounded_local_count_fixture_gate_publishes_dataset_report_dashboard_or_benchmark",
    "bounded_local_count_fixture_gate_claims_representativeness_statistical_validity_or_certification",
    "bounded_local_count_fixture_gate_emits_erc8004_reputation_or_worker_skill_dna",
    "bounded_local_count_fixture_gate_reverifies_payment_or_production",
    "bounded_local_count_fixture_gate_mutates_runtime_acontext_or_irc_session_manager",
    "bounded_local_count_fixture_gate_releases_exact_location_raw_metadata_private_context_or_pii",
    "bounded_local_count_fixture_gate_grants_legal_regulatory_safety_repair_insurance_or_statistical_authority",
    "bounded_local_count_fixture_gate_publishes_worker_copyable_doctrine",
    "bounded_local_count_fixture_gate_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "collection_authorized",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "dataset_published",
    "representative_dataset_ready",
    "statistical_validity_claimed",
    "certified_count_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "runtime_parity_proven",
    "live_acontext_ready",
    "gps_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
    "legal_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    if not path.exists():
        raise CityOpsContractError(f"AAS bounded local count source missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.extend(_walk_strings(str(key)))
            out.extend(_walk_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_walk_strings(item))
        return out
    return []


def _assert_no_forbidden_packet_language(packet: dict[str, Any]) -> None:
    joined = "\n".join(_walk_strings(packet)).lower()
    for fragment in FORBIDDEN_PACKET_FRAGMENTS:
        if fragment in joined:
            raise CityOpsContractError(
                f"AAS bounded local count packet contains forbidden fragment: {fragment}"
            )


def _assert_bounded_count_question(question: Any) -> None:
    if not isinstance(question, str) or not (12 <= len(question.strip()) <= 220):
        raise CityOpsContractError("AAS bounded local count question must be a bounded string")
    lowered = question.lower()
    if not any(marker in lowered for marker in ["count", "how many", "number of"]):
        raise CityOpsContractError("AAS bounded local count question lacks count grammar")
    for fragment in FORBIDDEN_QUESTION_FRAGMENTS:
        if fragment in lowered:
            raise CityOpsContractError(
                f"AAS bounded local count question is unbounded or authoritative: {fragment}"
            )


def _assert_non_empty_string(value: Any, field: str, *, min_len: int = 3) -> str:
    if not isinstance(value, str) or len(value.strip()) < min_len:
        raise CityOpsContractError(f"AAS bounded local count field {field} must be non-empty")
    return value.strip()


def _assert_observed_value(value: Any) -> None:
    if isinstance(value, int) and value >= 0:
        return
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped == "unable_to_count":
            return
        if re.fullmatch(r"\d+\s*(-|–)\s*\d+", stripped):
            lo, hi = [int(part.strip()) for part in re.split(r"-|–", stripped)]
            if lo <= hi:
                return
    raise CityOpsContractError(
        "AAS bounded local count observed_value must be integer, range, or unable_to_count"
    )


def validate_bounded_local_count_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless a bounded count packet preserves the evidence contract."""

    if not isinstance(packet, dict):
        raise CityOpsContractError("AAS bounded local count packet must be an object")
    missing = [field for field in REQUIRED_PACKET_FIELDS if field not in packet]
    if missing:
        raise CityOpsContractError(f"AAS bounded local count packet missing fields: {missing}")
    if packet.get("schema") != ALLOWED_PACKET_SCHEMA:
        raise CityOpsContractError("AAS bounded local count packet schema drift")
    if packet.get("status") != ALLOWED_PACKET_STATUS:
        raise CityOpsContractError("AAS bounded local count packet status drift")

    _assert_no_forbidden_packet_language(packet)
    _assert_bounded_count_question(packet["count_question"])
    _assert_non_empty_string(packet.get("observation_window"), "observation_window", min_len=6)
    _assert_non_empty_string(packet.get("place_boundary"), "place_boundary", min_len=6)

    if packet.get("count_method") not in ALLOWED_COUNT_METHODS:
        raise CityOpsContractError("AAS bounded local count method is not allowed")
    _assert_observed_value(packet.get("observed_value"))

    coverage_limits = packet.get("coverage_limits")
    if not isinstance(coverage_limits, list) or not coverage_limits or not all(
        isinstance(item, str) and item.strip() for item in coverage_limits
    ):
        raise CityOpsContractError("AAS bounded local count coverage limits missing")

    uncertainty = _assert_non_empty_string(
        packet.get("uncertainty_statement"), "uncertainty_statement", min_len=20
    ).lower()
    if not any(
        marker in uncertainty
        for marker in ["uncertain", "uncertainty", "not representative", "visibility", "bounded"]
    ):
        raise CityOpsContractError("AAS bounded local count uncertainty statement is too strong")

    evidence_ref = _assert_non_empty_string(
        packet.get("evidence_digest_reference"), "evidence_digest_reference", min_len=8
    )
    if evidence_ref.startswith(("http://", "https://", "data:", "file://")):
        raise CityOpsContractError("AAS bounded local count evidence reference exposes raw path")

    if packet.get("redaction_review_state") not in ALLOWED_REDACTION_REVIEW_STATES:
        raise CityOpsContractError("AAS bounded local count redaction state promoted")

    blocked = packet.get("blocked_claims_snapshot")
    if not isinstance(blocked, list):
        raise CityOpsContractError("AAS bounded local count blocked claims must be a list")
    missing_blockers = set(REQUIRED_BLOCKED_CLAIMS) - set(blocked)
    if missing_blockers:
        raise CityOpsContractError(
            f"AAS bounded local count missing blocked claims: {sorted(missing_blockers)}"
        )

    readiness = packet.get("readiness", {})
    if readiness is not None:
        if not isinstance(readiness, dict):
            raise CityOpsContractError("AAS bounded local count readiness must be an object")
        for key, value in readiness.items():
            key_lower = str(key).lower()
            if value is True or any(fragment.replace(" ", "_") in key_lower for fragment in FORBIDDEN_PACKET_FRAGMENTS):
                raise CityOpsContractError(
                    f"AAS bounded local count readiness promoted forbidden claim: {key}"
                )

    return packet


def sample_valid_bounded_local_count_packet() -> dict[str, Any]:
    return {
        "schema": ALLOWED_PACKET_SCHEMA,
        "status": ALLOWED_PACKET_STATUS,
        "count_question": "Count visible queue markers inside one operator-approved zone.",
        "observation_window": "single bounded daytime observation window",
        "place_boundary": "opaque_site_ref_alpha_general_area_only",
        "count_method": "direct_visual_count",
        "observed_value": "3-5",
        "coverage_limits": [
            "rear area not visible",
            "temporary obstruction prevented exact count",
        ],
        "uncertainty_statement": (
            "This is a bounded internal observation with visibility limits; it is not representative."
        ),
        "evidence_digest_reference": "sha256:example_non_secret_digest_reference_only",
        "redaction_review_state": "not_reviewed",
        "blocked_claims_snapshot": REQUIRED_BLOCKED_CLAIMS.copy(),
    }


def build_aas_bounded_local_count_fixture_gate() -> dict[str, Any]:
    source_digest = _file_digest(SOURCE_CONTRACT_DOC)
    fixture_packet = sample_valid_bounded_local_count_packet()
    gate = {
        "schema": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA,
        "gate_id": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_ID,
        "gate_status": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS,
        "source_contract": {
            "file": SOURCE_CONTRACT_DOC_PATH,
            "safe_claim": SOURCE_CONTRACT_SAFE_CLAIM,
            "digest_sha256": source_digest,
        },
        "fixture_schema": {
            "required_fields": REQUIRED_PACKET_FIELDS,
            "allowed_packet_schema": ALLOWED_PACKET_SCHEMA,
            "allowed_packet_status": ALLOWED_PACKET_STATUS,
            "allowed_count_methods": ALLOWED_COUNT_METHODS,
            "allowed_redaction_review_states": ALLOWED_REDACTION_REVIEW_STATES,
            "required_blocked_claims": REQUIRED_BLOCKED_CLAIMS,
            "bounding_rules": BOUNDING_RULES,
            "forbidden_question_fragments": FORBIDDEN_QUESTION_FRAGMENTS,
            "forbidden_packet_fragments": FORBIDDEN_PACKET_FRAGMENTS,
        },
        "sample_internal_fixture_packet": fixture_packet,
        "sample_internal_fixture_packet_digest_sha256": _stable_digest(fixture_packet),
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "collection_authorized": False,
            "selected_decision": None,
            "recommended_posture": "pause_aas_proof_layering",
        },
        "readiness": {
            "internal_admin_bounded_local_count_fixture_gate_landed": True,
            **FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": [
                SOURCE_CONTRACT_SAFE_CLAIM,
                AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS),
        },
        "stopped_project_firewall": {
            "source": "DREAM-PRIORITIES.md explicit stop list",
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
        },
        "next_gate_before_any_exposure": (
            "separate_human_operator_approval_for_exact_count_question_method_redaction_delivery_and_blocked_claims"
        ),
    }
    _assert_gate(gate)
    validate_bounded_local_count_packet(fixture_packet)
    return gate


def _assert_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA:
        raise CityOpsContractError("AAS bounded local count gate schema drift")
    if gate.get("gate_status") != AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS:
        raise CityOpsContractError("AAS bounded local count gate status drift")
    for key, expected in FALSE_FLAGS.items():
        if gate.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS bounded local count gate promoted {key}")
    state = gate.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
        "collection_authorized",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS bounded local count gate promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS bounded local count gate selected a decision")
    safe = set(gate.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(gate.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS bounded local count gate safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS bounded local count gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS bounded local count gate missing blocked claims: {sorted(missing_blocked)}"
        )
    if safe & blocked:
        raise CityOpsContractError("AAS bounded local count gate safe/blocked overlap")
    firewall = gate.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS bounded local count gate allowed {key}")


def load_aas_bounded_local_count_fixture_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME
    gate = json.loads(path.read_text(encoding="utf-8"))
    _assert_gate(gate)
    validate_bounded_local_count_packet(gate["sample_internal_fixture_packet"])
    return gate


def write_aas_bounded_local_count_fixture_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_aas_bounded_local_count_fixture_gate()
    path = target_dir / AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
