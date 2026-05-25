"""Local Data Collection adjacent-AAS internal/admin read surface.

This module advances Local Data Collection as a Service by exactly one rung: from
an internal package record to a read-only operator coverage surface. It remains
internal/admin visibility only. It consumes only the Local Data Collection
internal package record and does not register a public route, create customer
copy, publish a dataset or analytics product, price work, dispatch work, prove
live Acontext/runtime parity, attach ERC-8004 reputation, expose exact GPS/raw
metadata, certify statistical representativeness or exactness, provide continuous
monitoring, or publish worker-copyable data-collection doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import READINESS_FALSE_FLAGS
from .contracts import CityOpsContractError
from .local_data_collection_fixture_review_gate import (
    ARTIFACT_DIR,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
)
from .local_data_collection_internal_package_record import (
    LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME,
    LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SCHEMA,
    PACKAGE_ID,
)

LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SCHEMA = (
    "city_ops.local_data_collection_operator_read_surface.v1"
)
LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME = (
    "local_data_collection_operator_read_surface.json"
)
LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SAFE_CLAIM = (
    "local_data_collection_operator_read_surface_landed"
)

SURFACE_ID = "execution_market.aas.local_data_collection.operator_read_surface.001"
SCOPE = "internal_admin_local_data_collection_read_surface_only"
SURFACE_STATUS = "read_only_operator_surface_landed_not_dataset_not_customer_ready"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

READ_SURFACE_BLOCKED_CLAIMS = [
    "read_surface_public_route_ready",
    "read_surface_customer_delivery_ready",
    "read_surface_publication_ready",
    "read_surface_catalog_ready",
    "read_surface_dataset_ready",
    "read_surface_analytics_ready",
    "analytics_ready",
    "read_surface_pricing_ready",
    "read_surface_dispatch_ready",
    "read_surface_reputation_ready",
    "read_surface_worker_skill_dna_ready",
    "read_surface_worker_doctrine_ready",
    "read_surface_live_acontext_ready",
    "read_surface_statistical_representativeness_ready",
    "read_surface_continuous_monitoring_ready",
    "read_surface_official_dataset_certification_ready",
    "read_surface_predictive_analytics_ready",
    "read_surface_exactness_certification_ready",
    "local_data_collection_operator_surface_public_route_ready",
    "local_data_collection_operator_surface_customer_delivery_ready",
    "local_data_collection_operator_surface_catalog_ready",
    "local_data_collection_operator_surface_dataset_ready",
    "local_data_collection_operator_surface_analytics_ready",
    "local_data_collection_operator_surface_pricing_ready",
    "local_data_collection_operator_surface_dispatch_ready",
    "local_data_collection_operator_surface_reputation_ready",
    "local_data_collection_operator_surface_worker_doctrine_ready",
    "local_data_collection_operator_surface_live_acontext_ready",
    "local_data_collection_operator_surface_statistical_representativeness_ready",
    "local_data_collection_operator_surface_continuous_monitoring_ready",
    "local_data_collection_operator_surface_official_dataset_certification_ready",
    "local_data_collection_operator_surface_predictive_analytics_ready",
    "local_data_collection_operator_surface_exactness_certification_ready",
    "local_data_collection_customer_output_schema_ready",
    "local_data_collection_internal_sample_output_ready",
    "local_data_collection_operator_approval_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(READ_SURFACE_BLOCKED_CLAIMS) | {
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "pilot_authorized",
    "catalog_customer_ready",
    "public_pricing_or_customer_quote_ready",
    "customer_dataset_ready",
    "public_dataset_ready",
    "analytics_ready",
    "statistically_representative_dataset_ready",
    "statistical_representativeness",
    "continuous_monitoring_ready",
    "continuous_monitoring",
    "official_dataset_certification_ready",
    "official_dataset_certification",
    "predictive_analytics_ready",
    "predictive_analytics",
    "measurement_exactness_certified",
    "exactness_beyond_observed_method",
    "autonomous_dispatch_ready",
    "dispatch_routing_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_data_collection_doctrine",
    "live_acontext_ready",
    "runtime_parity_proven",
    "acontext_sink_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
}

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "catalog_visible",
    "dataset_visible",
    "analytics_visible",
    "pricing_enabled",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "writes_municipal_memory",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
    "claims_statistical_representativeness",
    "claims_continuous_monitoring",
    "claims_official_dataset_certification",
    "claims_predictive_analytics",
    "claims_exactness_certification",
]

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_review_fixtures",
    "reads_raw_transcripts",
    "reads_raw_photo_metadata",
    "reads_unreviewed_sensor_data",
    "reads_private_subject_identity",
    "writes_customer_copy",
    "writes_catalog_copy",
    "writes_dataset",
    "writes_analytics",
    "writes_pricing_quote",
    "writes_dispatch_instructions",
    "writes_live_acontext",
    "writes_municipal_memory",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "publishes_worker_doctrine",
    "exposes_gps_or_metadata",
    "creates_statistical_representativeness_claim",
    "creates_continuous_monitoring_claim",
    "creates_official_dataset_certification_claim",
    "creates_predictive_analytics_claim",
    "creates_exactness_certification_claim",
]

_PACKAGE_FALSE_FLAGS = [
    "customer_copy_changed",
    "customer_delivery_allowed",
    "publication_allowed",
    "catalog_allowed",
    "dataset_publication_allowed",
    "analytics_publication_allowed",
    "pricing_quote_allowed",
    "dispatch_allowed",
    "reputation_attachment_allowed",
    "worker_skill_dna_allowed",
    "worker_copyable_doctrine_allowed",
    "live_acontext_or_runtime_parity_claimed",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "statistical_representativeness_claim_allowed",
    "continuous_monitoring_claim_allowed",
    "official_dataset_certification_allowed",
    "exactness_beyond_method_allowed",
    "predictive_analytics_allowed",
]

SURFACE_REVIEW_CHECKS = [
    "source_package_safe_claims_present",
    "surface_consumes_only_internal_package_record",
    "source_artifact_ids_and_digest_preserved",
    "access_policy_internal_admin_only",
    "operator_cards_are_pass_through_not_customer_copy_or_dataset",
    "safe_and_blocked_claims_remain_adjacent",
    "no_raw_transcript_exact_location_private_identity_or_metadata_inputs",
    "customer_public_dataset_analytics_pricing_dispatch_reputation_runtime_exactness_"
    "representativeness_monitoring_and_worker_doctrine_still_blocked",
    "next_ladder_steps_require_separate_artifacts",
]


def build_local_data_collection_operator_read_surface(
    *, package_record: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the read-only internal/admin Local Data Collection operator surface.

    The surface consumes only the Local Data Collection internal package record
    and reshapes package state into operator cards without semantic
    reinterpretation. It proves read-only internal visibility, not customer
    delivery, public/catalog exposure, dataset publication, analytics, pricing,
    dispatch, reputation, live runtime parity, exact-location release,
    statistical/exactness certification, continuous monitoring, or worker doctrine.
    """

    source_record = package_record or _load_source_package_record_only()
    _assert_source_package_record_is_conservative(source_record)

    safe_to_claim = _dedupe(
        [
            *source_record.get("safe_to_claim", []),
            LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_record.get("do_not_claim_yet", []),
            *READ_SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    package = source_record["internal_package_record"]
    reviewed_output = package["packaged_reviewed_output"]
    evidence = package["packaged_evidence_contract"]
    source_package_digest = _digest_record(source_record)
    source_artifacts = list(package["source_artifacts"])
    package_state = {flag: package[flag] for flag in _PACKAGE_FALSE_FLAGS}

    surface = {
        "schema": LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SCHEMA,
        "surface_id": SURFACE_ID,
        "scope": SCOPE,
        "surface_status": SURFACE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_package_id": source_record["package_id"],
        "source_package_schema": source_record["schema"],
        "source_package_file": LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME,
        "source_package_digest_sha256": source_package_digest,
        "source_safe_claims_inherited": [
            LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
        ],
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME],
            "source_package_digest_sha256": source_package_digest,
            "consumes_only": [LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME],
            "source_artifact_lineage_passed_through": source_artifacts,
            "forbidden_inputs": [
                "raw_transcript",
                "raw_review_fixture",
                "raw_photo_metadata",
                "unreviewed_memory",
                "unreviewed_sensor_data",
                "private_operator_context",
                "private_subject_identity",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
                "freeform_worker_chat",
            ],
            **{flag: False for flag in _FALSE_DERIVED_FLAGS},
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **{flag: False for flag in _FALSE_ACCESS_FLAGS},
        },
        "mount_contract": {
            "mount_status": "internal_admin_read_surface_contract_landed_not_network_route",
            "method": "GET",
            "suggested_internal_path": (
                "/internal/admin/aas/local-data-collection/operator-read-surface"
            ),
            "network_route_registered": False,
            "response_fields": [
                "coverage_summary",
                "operator_cards",
                "safe_to_claim",
                "do_not_claim_yet",
                "readiness",
            ],
        },
        "coverage_summary": {
            "covered_package_records": 1,
            "source_fixture_count": len(source_artifacts),
            "package_status": source_record["package_status"],
            "review_status": package["review_status"],
            "source_package_digest_sha256": source_package_digest,
            "source_artifact_ids": [artifact.get("fixture_id") for artifact in source_artifacts],
            "required_evidence_fields_present": list(REQUIRED_EVIDENCE_FIELDS),
            "required_output_fields_present": list(REQUIRED_OUTPUT_FIELDS),
            "operator_cards_are_pass_through": True,
            "package_state_passed_through_without_reinterpretation": True,
            "customer_dataset_or_analytics_created": False,
            "promotion_blocked_until_separate_artifacts": True,
        },
        "operator_cards": [
            {
                "card": "package_position",
                "status": "visible_internal_admin_only",
                "values": {
                    "package_id": source_record["package_id"],
                    "offer_id": source_record["offer_id"],
                    "covered_steps": list(COVERED_LADDER_STEPS),
                    "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
                },
            },
            {
                "card": "source_artifact_lineage",
                "status": "package_artifact_ids_and_digest_pass_through",
                "values": {
                    "source_package_id": source_record["package_id"],
                    "source_package_file": LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME,
                    "source_package_digest_sha256": source_package_digest,
                    "source_artifacts": source_artifacts,
                },
            },
            {
                "card": "evidence_contract",
                "status": "package_payload_pass_through_no_raw_metadata",
                "values": {field: evidence[field] for field in REQUIRED_EVIDENCE_FIELDS},
            },
            {
                "card": "reviewed_output",
                "status": "package_payload_pass_through_not_customer_copy_or_dataset",
                "values": {field: reviewed_output[field] for field in REQUIRED_OUTPUT_FIELDS},
            },
            {
                "card": "package_state",
                "status": "package_state_pass_through_all_false",
                "values": package_state,
            },
            {
                "card": "safe_to_claim",
                "status": "visible_without_softening",
                "values": list(safe_to_claim),
            },
            {
                "card": "do_not_claim_yet",
                "status": "visible_without_softening",
                "values": list(do_not_claim_yet),
            },
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "surface_review_checks": [
            {
                "check_id": check,
                "status": "passed_for_internal_read_surface_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check in SURFACE_REVIEW_CHECKS
        ],
        "operator_instruction": (
            "Use this only as a read-only internal/admin operator surface for the "
            "Local Data Collection package record. Do not treat it as customer copy, "
            "a customer dataset, analytics output, catalog copy, pricing authority, "
            "dispatch authorization, reputation evidence, live Acontext parity, "
            "exact-location release, representativeness/continuous-monitoring/"
            "official-certification/exactness proof, predictive analytics, or "
            "worker-copyable data-collection doctrine."
        ),
        "next_smallest_proof": (
            "Create a Local Data Collection customer-output schema gate that consumes "
            "this surface and still keeps publication, delivery, catalog, dataset, "
            "analytics, pricing, dispatch, reputation, runtime, privacy, exactness, "
            "representativeness, monitoring, certification, and worker-doctrine readiness false."
        ),
    }
    _assert_read_surface_is_conservative(surface, source_record=source_record)
    return surface


def write_local_data_collection_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Local Data Collection internal/admin operator read surface."""

    surface = build_local_data_collection_operator_read_surface()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2) + "\n", encoding="utf-8")
    return path


def load_local_data_collection_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Local Data Collection read surface."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    if not isinstance(surface, dict):
        raise CityOpsContractError(
            "Local Data Collection operator read surface must be JSON object"
        )
    _assert_read_surface_is_conservative(
        surface,
        source_record=_load_source_package_record_for_dir(source_dir),
    )
    return surface


def _load_source_package_record_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME).exists():
        return _load_source_package_record_only(artifact_dir=source_dir)
    return _load_source_package_record_only()


def _load_source_package_record_only(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError(
            "Local Data Collection operator read surface source must be JSON object"
        )
    _assert_source_package_record_is_conservative(record)
    return record


def _assert_source_package_record_is_conservative(record: dict[str, Any]) -> None:
    if record.get("schema") != LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError(
            "Local Data Collection read surface source package schema drift"
        )
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("Local Data Collection read surface source package id drift")
    if record.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Local Data Collection read surface source family drift")
    if record.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Local Data Collection read surface source offer drift")
    if LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in record.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Local Data Collection read surface source safe claim missing")
    if record.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Local Data Collection read surface source promoted readiness")
    for flag in READINESS_FALSE_FLAGS:
        if record.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection read surface source promoted readiness: {flag}"
            )
    package = record.get("internal_package_record")
    if not isinstance(package, dict):
        raise CityOpsContractError("Local Data Collection read surface source package payload missing")
    if package.get("uses_only_local_reviewed_fixture_artifact") is not True:
        raise CityOpsContractError("Local Data Collection read surface source package input drift")
    for false_flag in _PACKAGE_FALSE_FLAGS:
        if package.get(false_flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection read surface source promoted {false_flag}"
            )
    evidence = package.get("packaged_evidence_contract", {})
    if not set(REQUIRED_EVIDENCE_FIELDS).issubset(set(evidence.keys())):
        raise CityOpsContractError("Local Data Collection read surface source lost evidence fields")
    output = package.get("packaged_reviewed_output", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(output.keys())):
        raise CityOpsContractError("Local Data Collection read surface source lost output fields")
    source_artifacts = package.get("source_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 1:
        raise CityOpsContractError("Local Data Collection read surface source artifacts drift")
    if not source_artifacts[0].get("fixture_id"):
        raise CityOpsContractError("Local Data Collection read surface source artifact id missing")


def _assert_read_surface_is_conservative(
    surface: dict[str, Any], *, source_record: dict[str, Any]
) -> None:
    _assert_source_package_record_is_conservative(source_record)
    if surface.get("schema") != LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("Local Data Collection operator read surface schema drift")
    if surface.get("surface_id") != SURFACE_ID:
        raise CityOpsContractError("Local Data Collection operator read surface id drift")
    if surface.get("scope") != SCOPE:
        raise CityOpsContractError("Local Data Collection operator read surface scope drift")
    if surface.get("surface_status") != SURFACE_STATUS:
        raise CityOpsContractError("Local Data Collection operator read surface status drift")
    if surface.get("source_package_id") != source_record.get("package_id"):
        raise CityOpsContractError(
            "Local Data Collection operator read surface source package drift"
        )
    if surface.get("source_package_digest_sha256") != _digest_record(source_record):
        raise CityOpsContractError(
            "Local Data Collection operator read surface source digest drift"
        )

    keys = list(surface.keys())
    if keys.index("do_not_claim_yet") != keys.index("safe_to_claim") + 1:
        raise CityOpsContractError(
            "Local Data Collection operator read surface separated claim boundaries"
        )
    _assert_claim_boundaries(
        surface.get("safe_to_claim", []), surface.get("do_not_claim_yet", [])
    )
    if LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SAFE_CLAIM not in surface.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Local Data Collection operator read surface safe claim missing")
    if LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in surface.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Local Data Collection operator read surface source claim missing")
    missing_blocked = (
        set(source_record.get("do_not_claim_yet", [])) | set(READ_SURFACE_BLOCKED_CLAIMS)
    ) - set(surface.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            "Local Data Collection operator read surface missing blocked claims: "
            f"{sorted(missing_blocked)}"
        )

    ladder = surface.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Local Data Collection operator read surface covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Local Data Collection operator read surface next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Local Data Collection operator read surface promoted readiness")

    for section_name, flags in (
        ("derived_from", _FALSE_DERIVED_FLAGS),
        ("access_policy", _FALSE_ACCESS_FLAGS),
    ):
        section = surface.get(section_name, {})
        for flag in flags:
            if section.get(flag) is not False:
                raise CityOpsContractError(
                    f"Local Data Collection operator read surface {section_name} overclaims {flag}"
                )
    derived = surface.get("derived_from", {})
    if derived.get("consumes_only") != [LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME]:
        raise CityOpsContractError("Local Data Collection operator read surface input drift")
    if derived.get("source_artifact_lineage_passed_through") != source_record[
        "internal_package_record"
    ]["source_artifacts"]:
        raise CityOpsContractError(
            "Local Data Collection operator read surface source artifacts drift"
        )
    access = surface.get("access_policy", {})
    if access.get("audience") != "internal_admin_only" or access.get(
        "requires_admin_context"
    ) is not True:
        raise CityOpsContractError("Local Data Collection operator read surface access policy drift")
    if surface.get("mount_contract", {}).get("network_route_registered") is not False:
        raise CityOpsContractError(
            "Local Data Collection operator read surface registered network route"
        )

    for flag in READINESS_FALSE_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection operator read surface promoted readiness: {flag}"
            )

    summary = surface.get("coverage_summary", {})
    if summary.get("covered_package_records") != 1:
        raise CityOpsContractError("Local Data Collection operator read surface coverage count drift")
    if summary.get("operator_cards_are_pass_through") is not True:
        raise CityOpsContractError(
            "Local Data Collection operator read surface reinterpreted operator cards"
        )
    if summary.get("package_state_passed_through_without_reinterpretation") is not True:
        raise CityOpsContractError(
            "Local Data Collection operator read surface reinterpreted package state"
        )
    if summary.get("customer_dataset_or_analytics_created") is not False:
        raise CityOpsContractError(
            "Local Data Collection operator read surface created dataset or analytics"
        )
    if summary.get("promotion_blocked_until_separate_artifacts") is not True:
        raise CityOpsContractError(
            "Local Data Collection operator read surface stopped blocking promotion"
        )

    cards = surface.get("operator_cards")
    if not isinstance(cards, list) or len(cards) != 7:
        raise CityOpsContractError("Local Data Collection operator read surface cards drift")
    cards_by_name = {card.get("card"): card for card in cards if isinstance(card, dict)}
    for required_card in (
        "package_position",
        "source_artifact_lineage",
        "evidence_contract",
        "reviewed_output",
        "package_state",
        "safe_to_claim",
        "do_not_claim_yet",
    ):
        if required_card not in cards_by_name:
            raise CityOpsContractError(
                "Local Data Collection operator read surface missing required card"
            )
    if cards_by_name["reviewed_output"].get("status") != (
        "package_payload_pass_through_not_customer_copy_or_dataset"
    ):
        raise CityOpsContractError(
            "Local Data Collection operator read surface promoted reviewed output"
        )
    if cards_by_name["evidence_contract"].get("values") != source_record[
        "internal_package_record"
    ]["packaged_evidence_contract"]:
        raise CityOpsContractError(
            "Local Data Collection operator read surface reinterpreted evidence"
        )
    if cards_by_name["reviewed_output"].get("values") != source_record[
        "internal_package_record"
    ]["packaged_reviewed_output"]:
        raise CityOpsContractError(
            "Local Data Collection operator read surface reinterpreted reviewed output"
        )
    if cards_by_name["package_state"].get("values") != {
        flag: source_record["internal_package_record"][flag] for flag in _PACKAGE_FALSE_FLAGS
    }:
        raise CityOpsContractError(
            "Local Data Collection operator read surface reinterpreted package state"
        )

    checks = surface.get("surface_review_checks")
    if (
        not isinstance(checks, list)
        or [item.get("check_id") for item in checks] != SURFACE_REVIEW_CHECKS
    ):
        raise CityOpsContractError("Local Data Collection operator read surface review checks drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_read_surface_only":
            raise CityOpsContractError(
                "Local Data Collection operator read surface review check status drift"
            )
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Local Data Collection operator read surface review check stopped blocking promotion"
            )

    _assert_no_private_metadata_or_data_overclaims(surface)


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(
            f"Local Data Collection operator read surface has forbidden safe claims: {forbidden}"
        )
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(
            f"Local Data Collection operator read surface claim overlap: {overlap}"
        )


def _assert_no_private_metadata_or_data_overclaims(surface: dict[str, Any]) -> None:
    serialized = json.dumps(surface, sort_keys=True).lower()
    forbidden_fragments = [
        "latitude",
        "longitude",
        "gps:",
        "gps coordinate retained",
        "exact address retained",
        "raw image metadata retained",
        "private subject identity was copied",
        "private contact detail was copied",
        "raw transcript is authority",
        "customer dataset authorized",
        "public dataset authorized",
        "analytics publication authorized",
        "statistical representativeness certified",
        "continuous monitoring provided",
        "official dataset certification provided",
        "predictive analytics provided",
        "certified exactness provided",
        "customer delivery authorized",
        "catalog route authorized",
        "pricing quote authorized",
        "dispatch route authorized",
        "reputation receipt authorized",
        "worker-copyable doctrine authorized",
    ]
    if any(fragment in serialized for fragment in forbidden_fragments):
        raise CityOpsContractError(
            "Local Data Collection operator read surface exposed private metadata or overclaimed authority"
        )


def _digest_record(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
