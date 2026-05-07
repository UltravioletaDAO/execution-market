import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.closure import FORBIDDEN_CLOSURE_SOURCES
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.session_rebuild_consumer import (
    CONSUMER_SAFE_CLAIM,
    REPORT_BLOCKED_CLAIMS,
    REPORT_SAFE_CLAIM,
    SESSION_REBUILD_CONSUMER_SCHEMA,
    SESSION_REBUILD_REPORT_SCHEMA,
    build_session_rebuild_report,
    load_session_rebuild_consumer_bundle,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def copy_proof_block(tmp_path: Path) -> Path:
    target = tmp_path / "proof_block"
    shutil.copytree(PROOF_BLOCK_DIR, target)
    return target


def mutate_json(path: Path, mutator):
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    mutator(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def read_fixture_report() -> dict:
    with (PROOF_BLOCK_DIR / "session_rebuild_report.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_read_only_session_rebuild_consumer_preserves_boundaries():
    bundle = load_session_rebuild_consumer_bundle()

    assert bundle["schema"] == SESSION_REBUILD_CONSUMER_SCHEMA
    assert bundle["consumer_verdict"] == "read_only_session_rebuild_consumer_landed"
    assert CONSUMER_SAFE_CLAIM in bundle["safe_to_claim"]
    assert bundle["source_read_contract"]["read_only"] is True
    assert bundle["source_read_contract"]["writes_live_sink"] is False
    assert bundle["source_read_contract"]["raw_transcript_required"] is False
    assert bundle["source_read_contract"]["forbidden_sources"] == FORBIDDEN_CLOSURE_SOURCES

    boundaries = bundle["preserved_boundaries"]
    assert boundaries["promotion_class"] == "conservative_memory_delta"
    assert boundaries["guidance_tone"] == "cautionary_or_corrective"
    assert boundaries["guidance_placement"] == "operator_visible_before_worker_copy"
    assert boundaries["copyable_worker_instruction"]["allowed"] is False

    readiness = bundle["readiness"]
    assert readiness["telemetry_session_rebuild_ready"] is False
    assert readiness["telemetry_acontext_sink_ready"] is False
    assert readiness["consumer_promotes_readiness"] is False


def test_session_rebuild_consumer_refuses_missing_artifact(tmp_path):
    proof_block = copy_proof_block(tmp_path)
    (proof_block / "acontext_export_preview.json").unlink()

    with pytest.raises(CityOpsContractError, match="missing persisted proof-block artifact"):
        load_session_rebuild_consumer_bundle(artifact_dir=proof_block)


def test_session_rebuild_consumer_refuses_forbidden_active_source(tmp_path):
    proof_block = copy_proof_block(tmp_path)
    mutate_json(
        proof_block / "session_rebuild_preview.json",
        lambda payload: payload["source_read_contract"]["allowed_sources"].append(
            "raw_transcript"
        ),
    )

    with pytest.raises(CityOpsContractError, match="forbidden source 'raw_transcript'"):
        load_session_rebuild_consumer_bundle(artifact_dir=proof_block)


def test_session_rebuild_consumer_refuses_claim_limit_drift(tmp_path):
    proof_block = copy_proof_block(tmp_path)
    mutate_json(
        proof_block / "proof_block_telemetry_gate.json",
        lambda payload: payload["do_not_claim_yet"].remove("closure_proof_ready"),
    )

    with pytest.raises(CityOpsContractError, match="not_safe_to_claim"):
        load_session_rebuild_consumer_bundle(artifact_dir=proof_block)


def test_session_rebuild_consumer_refuses_worker_copyability_strengthening(tmp_path):
    proof_block = copy_proof_block(tmp_path)
    mutate_json(
        proof_block / "session_rebuild_preview.json",
        lambda payload: payload["promotion"]["copyable_worker_instruction"].update(
            {"allowed": True, "reason": "promoted without repeated proof"}
        ),
    )

    with pytest.raises(CityOpsContractError, match="copyable_worker_instruction"):
        load_session_rebuild_consumer_bundle(artifact_dir=proof_block)


def test_session_rebuild_consumer_refuses_readiness_promotion(tmp_path):
    proof_block = copy_proof_block(tmp_path)
    mutate_json(
        proof_block / "session_rebuild_preview.json",
        lambda payload: payload["readiness"].update(
            {"preview_promotes_readiness": True}
        ),
    )

    with pytest.raises(CityOpsContractError, match="preview_promotes_readiness"):
        load_session_rebuild_consumer_bundle(artifact_dir=proof_block)


def test_session_rebuild_report_fixture_matches_bundle_only_generation():
    report = build_session_rebuild_report()

    assert report == read_fixture_report()
    assert report["schema"] == SESSION_REBUILD_REPORT_SCHEMA
    assert report["report_verdict"] == "read_only_session_rebuild_report_fixture_landed"
    assert report["derived_from"]["schema"] == SESSION_REBUILD_CONSUMER_SCHEMA
    assert report["source_read_contract"]["allowed_sources"] == [
        SESSION_REBUILD_CONSUMER_SCHEMA
    ]
    assert report["source_read_contract"]["derives_from_consumer_bundle_only"] is True
    assert report["source_read_contract"]["read_only"] is True
    assert report["source_read_contract"]["writes_live_sink"] is False
    assert report["source_read_contract"]["raw_transcript_required"] is False
    assert report["source_read_contract"]["forbidden_sources"] == FORBIDDEN_CLOSURE_SOURCES


def test_session_rebuild_report_preserves_identity_claims_and_boundaries():
    bundle = load_session_rebuild_consumer_bundle()
    report = build_session_rebuild_report(consumer_bundle=bundle)

    assert report["identity"] == {
        "proof_anchor_id": bundle["proof_anchor_id"],
        "coordination_session_id": bundle["coordination_session_id"],
        "compact_decision_id": bundle["compact_decision_id"],
        "review_packet_id": bundle["review_packet_id"],
    }
    assert report["claim_boundaries"]["inherited_safe_to_claim"] == bundle[
        "safe_to_claim"
    ]
    assert CONSUMER_SAFE_CLAIM in report["claim_boundaries"]["safe_to_claim"]
    assert REPORT_SAFE_CLAIM in report["claim_boundaries"]["safe_to_claim"]
    for blocked_claim in REPORT_BLOCKED_CLAIMS:
        assert blocked_claim in report["claim_boundaries"]["do_not_claim_yet"]
        assert blocked_claim not in report["claim_boundaries"]["safe_to_claim"]

    assert report["promotion_boundaries"] == bundle["preserved_boundaries"]
    assert report["promotion_boundaries"]["promotion_class"] == "conservative_memory_delta"
    assert report["promotion_boundaries"]["guidance_tone"] == "cautionary_or_corrective"
    assert (
        report["promotion_boundaries"]["guidance_placement"]
        == "operator_visible_before_worker_copy"
    )
    assert (
        report["promotion_boundaries"]["copyable_worker_instruction"]["allowed"]
        is False
    )
    assert report["readiness"]["report_promotes_readiness"] is False
    assert report["readiness"]["consumer_promotes_readiness"] is False


def test_session_rebuild_report_refuses_safe_readiness_claim():
    bundle = load_session_rebuild_consumer_bundle()
    bundle["safe_to_claim"].append("session_rebuild_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims safe"):
        build_session_rebuild_report(consumer_bundle=bundle)


def test_session_rebuild_report_refuses_worker_copyable_upgrade():
    bundle = load_session_rebuild_consumer_bundle()
    bundle["preserved_boundaries"]["copyable_worker_instruction"]["allowed"] = True

    with pytest.raises(CityOpsContractError, match="copyable_worker_instruction"):
        build_session_rebuild_report(consumer_bundle=bundle)


def test_session_rebuild_report_refuses_readiness_promotion():
    bundle = load_session_rebuild_consumer_bundle()
    bundle["readiness"]["decision"]["session_rebuild_ready"] = True

    with pytest.raises(CityOpsContractError, match="session_rebuild_ready"):
        build_session_rebuild_report(consumer_bundle=bundle)
