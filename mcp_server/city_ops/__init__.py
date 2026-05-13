"""City-as-a-Service deterministic proof utilities."""

from .contracts import (
    CityOpsContractError,
    CompactDecisionObject,
    CopyableWorkerInstruction,
    ReadinessPosture,
)
from .acontext_live_preflight import build_acontext_live_preflight_result
from .acontext_transport import build_acontext_transport_parity_result
from .closure import build_acontext_export_preview, build_session_rebuild_preview
from .coordination_intelligence import build_coordination_intelligence_snapshot
from .decision_projection import project_compact_decision
from .decision_support_readiness_matrix import (
    build_decision_support_readiness_matrix,
    load_decision_support_readiness_matrix,
    write_decision_support_readiness_matrix_fixture,
)
from .decision_support_matrix_card import (
    build_decision_support_matrix_card,
    load_decision_support_matrix_card,
    write_decision_support_matrix_card_fixture,
)
from .decision_support_matrix_route_preflight import (
    build_decision_support_matrix_route_preflight,
    load_decision_support_matrix_route_preflight,
    write_decision_support_matrix_route_preflight_fixture,
)
from .decision_support_matrix_admin_route import (
    build_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight,
    build_internal_admin_decision_support_matrix_route_mount_manifest,
    build_internal_admin_decision_support_matrix_route_preflight,
    load_internal_admin_decision_support_matrix_card,
    load_internal_admin_decision_support_matrix_operator_display_adapter,
    write_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight,
    write_internal_admin_decision_support_matrix_route_mount_manifest,
    write_internal_admin_decision_support_matrix_route_preflight,
)
from .decision_support_matrix_operator_consumer import (
    build_decision_support_matrix_operator_consumer,
    load_decision_support_matrix_operator_consumer,
    write_decision_support_matrix_operator_consumer_fixture,
)
from .decision_support_matrix_operator_display_adapter import (
    build_decision_support_matrix_operator_display_adapter,
    load_decision_support_matrix_operator_display_adapter,
    write_decision_support_matrix_operator_display_adapter_fixture,
)
from .decision_support_route_handoff_packet import (
    build_decision_support_route_handoff_packet,
    load_internal_admin_route_mount_manifest,
    write_decision_support_route_handoff_packet_fixture,
)
from .observability import build_proof_block_telemetry_gate
from .operator_debug_surface import build_operator_debug_surface
from .phase1_offer_fixture_specs import build_phase1_offer_fixture_spec_summary
from .phase1_operator_coverage_summary import (
    build_phase1_operator_coverage_summary,
    load_phase1_operator_coverage_summary,
    write_phase1_operator_coverage_summary,
)
from .phase1_packet_submission_internal_package_record import (
    build_phase1_packet_submission_internal_package_record,
    load_phase1_packet_submission_internal_package_record,
    write_phase1_packet_submission_internal_package_record,
)
from .phase1_remaining_offer_internal_package_records import (
    build_phase1_counter_reality_check_internal_package_record,
    build_phase1_posting_compliance_internal_package_record,
    load_phase1_counter_reality_check_internal_package_record,
    load_phase1_posting_compliance_internal_package_record,
    write_phase1_counter_reality_check_internal_package_record,
    write_phase1_posting_compliance_internal_package_record,
)
from .phase1_controlled_pilot_readiness_board import (
    build_phase1_controlled_pilot_readiness_board,
    load_phase1_controlled_pilot_readiness_board,
    write_phase1_controlled_pilot_readiness_board,
)
from .phase1_customer_output_schema_review_gate import (
    build_phase1_customer_output_schema_review_gate,
    load_phase1_customer_output_schema_review_gate,
    write_phase1_customer_output_schema_review_gate,
)
from .phase1_operator_reviewed_sample_outputs import (
    build_phase1_operator_reviewed_sample_outputs,
    load_phase1_operator_reviewed_sample_outputs,
    write_phase1_operator_reviewed_sample_outputs,
)
from .phase1_sample_publication_approval_checklist import (
    build_phase1_sample_publication_approval_checklist,
    load_phase1_sample_publication_approval_checklist,
    write_phase1_sample_publication_approval_checklist,
)
from .phase1_customer_facing_draft_packet import (
    build_phase1_customer_facing_draft_packet,
    load_phase1_customer_facing_draft_packet,
    write_phase1_customer_facing_draft_packet,
)
from .phase1_draft_packet_operator_review_decision import (
    build_phase1_draft_packet_operator_review_decision,
    load_phase1_draft_packet_operator_review_decision,
    write_phase1_draft_packet_operator_review_decision,
)
from .phase1_offer_card_human_operator_approval_record import (
    build_phase1_offer_card_human_operator_approval_record,
    load_phase1_offer_card_human_operator_approval_record,
    write_phase1_offer_card_human_operator_approval_record,
)
from .phase1_offer_card_approval_coverage_matrix import (
    build_phase1_offer_card_approval_coverage_matrix,
    load_phase1_offer_card_approval_coverage_matrix,
    write_phase1_offer_card_approval_coverage_matrix,
)
from .phase1_approved_offer_customer_delivery_hold_checklist import (
    build_phase1_approved_offer_customer_delivery_hold_checklist,
    load_phase1_approved_offer_customer_delivery_hold_checklist,
    write_phase1_approved_offer_customer_delivery_hold_checklist,
)
from .aas_minimum_ladder_template import (
    build_aas_minimum_ladder_template,
    load_aas_minimum_ladder_template,
    write_aas_minimum_ladder_template,
)
from .compliance_desk_fixture_review_gate import (
    build_compliance_desk_fixture_review_gate,
    load_compliance_desk_fixture_review_gate,
    write_compliance_desk_fixture_review_gate,
)
from .compliance_desk_local_reviewed_fixture import (
    build_compliance_desk_local_reviewed_fixture,
    load_compliance_desk_local_reviewed_fixture,
    write_compliance_desk_local_reviewed_fixture,
)
from .compliance_desk_internal_package_record import (
    build_compliance_desk_internal_package_record,
    load_compliance_desk_internal_package_record,
    write_compliance_desk_internal_package_record,
)
from .compliance_desk_operator_read_surface import (
    build_compliance_desk_operator_read_surface,
    load_compliance_desk_operator_read_surface,
    write_compliance_desk_operator_read_surface,
)
from .compliance_desk_customer_output_schema_gate import (
    build_compliance_desk_customer_output_schema_gate,
    load_compliance_desk_customer_output_schema_gate,
    write_compliance_desk_customer_output_schema_gate,
)
from .compliance_desk_internal_sample_output import (
    build_compliance_desk_internal_sample_output,
    load_compliance_desk_internal_sample_output,
    write_compliance_desk_internal_sample_output,
)
from .compliance_desk_sample_output_review_decision import (
    build_compliance_desk_sample_output_review_decision,
    load_compliance_desk_sample_output_review_decision,
    write_compliance_desk_sample_output_review_decision,
)
from .document_handoff_fixture_review_gate import (
    build_document_handoff_fixture_review_gate,
    load_document_handoff_fixture_review_gate,
    write_document_handoff_fixture_review_gate,
)
from .document_handoff_local_reviewed_fixture import (
    build_document_handoff_local_reviewed_fixture,
    load_document_handoff_local_reviewed_fixture,
    write_document_handoff_local_reviewed_fixture,
)
from .document_handoff_internal_package_record import (
    build_document_handoff_internal_package_record,
    load_document_handoff_internal_package_record,
    write_document_handoff_internal_package_record,
)
from .document_handoff_operator_read_surface import (
    build_document_handoff_operator_read_surface,
    load_document_handoff_operator_read_surface,
    write_document_handoff_operator_read_surface,
)
from .phase1_operator_coverage_renderer import (
    build_phase1_operator_coverage_renderer,
    load_phase1_operator_coverage_renderer,
    write_phase1_operator_coverage_renderer,
)
from .phase1_operator_coverage_read_surface import (
    build_phase1_operator_coverage_read_surface,
    load_phase1_operator_coverage_read_surface,
    write_phase1_operator_coverage_read_surface,
)
from .phase1_review_normalizer import (
    build_phase1_review_normalizer_summary,
    normalize_phase1_review_output,
)
from .phase1_review_output_schemas import (
    build_phase1_review_output_schema_bundle,
    validate_phase1_review_output,
)
from .phase1_reviewed_fixtures import (
    build_counter_reality_check_reviewed_fixture,
    build_packet_submission_attempt_reviewed_fixture,
    build_phase1_reviewed_fixture_registry_summary,
    build_posting_compliance_check_reviewed_fixture,
)
from .persisted_artifact_guardrail import build_persisted_artifact_guardrail_report
from .proof_block_readiness import build_proof_block_readiness_summary
from .proof_observability import build_proof_observability_snapshot
from .session_rebuild_consumer import build_session_rebuild_report

__all__ = [
    "CityOpsContractError",
    "CompactDecisionObject",
    "CopyableWorkerInstruction",
    "ReadinessPosture",
    "build_acontext_export_preview",
    "build_acontext_live_preflight_result",
    "build_acontext_transport_parity_result",
    "build_coordination_intelligence_snapshot",
    "build_operator_debug_surface",
    "build_decision_support_readiness_matrix",
    "load_decision_support_readiness_matrix",
    "write_decision_support_readiness_matrix_fixture",
    "build_decision_support_matrix_card",
    "load_decision_support_matrix_card",
    "write_decision_support_matrix_card_fixture",
    "build_decision_support_matrix_route_preflight",
    "load_decision_support_matrix_route_preflight",
    "write_decision_support_matrix_route_preflight_fixture",
    "load_internal_admin_decision_support_matrix_card",
    "build_internal_admin_decision_support_matrix_route_preflight",
    "write_internal_admin_decision_support_matrix_route_preflight",
    "load_internal_admin_decision_support_matrix_operator_display_adapter",
    "build_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight",
    "write_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight",
    "build_internal_admin_decision_support_matrix_route_mount_manifest",
    "write_internal_admin_decision_support_matrix_route_mount_manifest",
    "build_decision_support_matrix_operator_consumer",
    "load_decision_support_matrix_operator_consumer",
    "write_decision_support_matrix_operator_consumer_fixture",
    "build_decision_support_matrix_operator_display_adapter",
    "load_decision_support_matrix_operator_display_adapter",
    "write_decision_support_matrix_operator_display_adapter_fixture",
    "build_decision_support_route_handoff_packet",
    "load_internal_admin_route_mount_manifest",
    "write_decision_support_route_handoff_packet_fixture",
    "build_phase1_offer_fixture_spec_summary",
    "build_phase1_operator_coverage_summary",
    "load_phase1_operator_coverage_summary",
    "write_phase1_operator_coverage_summary",
    "build_phase1_packet_submission_internal_package_record",
    "load_phase1_packet_submission_internal_package_record",
    "write_phase1_packet_submission_internal_package_record",
    "build_phase1_counter_reality_check_internal_package_record",
    "build_phase1_posting_compliance_internal_package_record",
    "load_phase1_counter_reality_check_internal_package_record",
    "load_phase1_posting_compliance_internal_package_record",
    "write_phase1_counter_reality_check_internal_package_record",
    "write_phase1_posting_compliance_internal_package_record",
    "build_phase1_controlled_pilot_readiness_board",
    "load_phase1_controlled_pilot_readiness_board",
    "write_phase1_controlled_pilot_readiness_board",
    "build_phase1_customer_output_schema_review_gate",
    "load_phase1_customer_output_schema_review_gate",
    "write_phase1_customer_output_schema_review_gate",
    "build_phase1_operator_reviewed_sample_outputs",
    "load_phase1_operator_reviewed_sample_outputs",
    "write_phase1_operator_reviewed_sample_outputs",
    "build_phase1_sample_publication_approval_checklist",
    "load_phase1_sample_publication_approval_checklist",
    "write_phase1_sample_publication_approval_checklist",
    "build_phase1_customer_facing_draft_packet",
    "load_phase1_customer_facing_draft_packet",
    "write_phase1_customer_facing_draft_packet",
    "build_phase1_draft_packet_operator_review_decision",
    "load_phase1_draft_packet_operator_review_decision",
    "write_phase1_draft_packet_operator_review_decision",
    "build_phase1_offer_card_human_operator_approval_record",
    "load_phase1_offer_card_human_operator_approval_record",
    "write_phase1_offer_card_human_operator_approval_record",
    "build_phase1_offer_card_approval_coverage_matrix",
    "load_phase1_offer_card_approval_coverage_matrix",
    "write_phase1_offer_card_approval_coverage_matrix",
    "build_phase1_approved_offer_customer_delivery_hold_checklist",
    "load_phase1_approved_offer_customer_delivery_hold_checklist",
    "write_phase1_approved_offer_customer_delivery_hold_checklist",
    "build_aas_minimum_ladder_template",
    "load_aas_minimum_ladder_template",
    "write_aas_minimum_ladder_template",
    "build_compliance_desk_fixture_review_gate",
    "load_compliance_desk_fixture_review_gate",
    "write_compliance_desk_fixture_review_gate",
    "build_compliance_desk_local_reviewed_fixture",
    "load_compliance_desk_local_reviewed_fixture",
    "write_compliance_desk_local_reviewed_fixture",
    "build_compliance_desk_internal_package_record",
    "load_compliance_desk_internal_package_record",
    "write_compliance_desk_internal_package_record",
    "build_compliance_desk_operator_read_surface",
    "load_compliance_desk_operator_read_surface",
    "write_compliance_desk_operator_read_surface",
    "build_compliance_desk_customer_output_schema_gate",
    "load_compliance_desk_customer_output_schema_gate",
    "write_compliance_desk_customer_output_schema_gate",
    "build_compliance_desk_internal_sample_output",
    "load_compliance_desk_internal_sample_output",
    "write_compliance_desk_internal_sample_output",
    "build_compliance_desk_sample_output_review_decision",
    "load_compliance_desk_sample_output_review_decision",
    "write_compliance_desk_sample_output_review_decision",
    "build_document_handoff_fixture_review_gate",
    "load_document_handoff_fixture_review_gate",
    "write_document_handoff_fixture_review_gate",
    "build_document_handoff_local_reviewed_fixture",
    "load_document_handoff_local_reviewed_fixture",
    "write_document_handoff_local_reviewed_fixture",
    "build_document_handoff_internal_package_record",
    "load_document_handoff_internal_package_record",
    "write_document_handoff_internal_package_record",
    "build_phase1_operator_coverage_renderer",
    "load_phase1_operator_coverage_renderer",
    "write_phase1_operator_coverage_renderer",
    "build_phase1_operator_coverage_read_surface",
    "load_phase1_operator_coverage_read_surface",
    "write_phase1_operator_coverage_read_surface",
    "build_phase1_review_normalizer_summary",
    "build_phase1_review_output_schema_bundle",
    "build_counter_reality_check_reviewed_fixture",
    "build_packet_submission_attempt_reviewed_fixture",
    "build_phase1_reviewed_fixture_registry_summary",
    "build_posting_compliance_check_reviewed_fixture",
    "build_persisted_artifact_guardrail_report",
    "validate_phase1_review_output",
    "normalize_phase1_review_output",
    "build_proof_block_readiness_summary",
    "build_proof_block_telemetry_gate",
    "build_proof_observability_snapshot",
    "build_session_rebuild_report",
    "build_session_rebuild_preview",
    "project_compact_decision",
]
