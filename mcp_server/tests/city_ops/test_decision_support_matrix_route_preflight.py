import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.decision_support_matrix_card import (
    DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    build_decision_support_matrix_card,
)
from mcp_server.city_ops.decision_support_readiness_matrix import (
    DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
)
from mcp_server.city_ops.decision_support_matrix_route_preflight import (
    DECISION_SUPPORT_MATRIX_AUTHENTICATED_ADMIN_ROUTE_SAFE_CLAIM,
    DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME,
    DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SAFE_CLAIM,
    DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SCHEMA,
    build_decision_support_matrix_route_preflight,
    load_decision_support_matrix_route_preflight,
    write_decision_support_matrix_route_preflight_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_preflight() -> dict:
    with (PROOF_BLOCK_DIR / DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_route_preflight_consumes_card_only_and_fails_closed_by_default():
    preflight = build_decision_support_matrix_route_preflight()

    assert preflight["schema"] == DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SCHEMA
    assert preflight["derived_from"]["read_only"] is True
    assert preflight["derived_from"]["source_artifacts"] == [
        DECISION_SUPPORT_MATRIX_CARD_FILENAME
    ]
    assert preflight["derived_from"]["consumes_only"] == [
        DECISION_SUPPORT_MATRIX_CARD_FILENAME
    ]
    assert preflight["route_contract"]["route_registered_by_this_slice"] is False
    assert preflight["route_contract"]["allowed_interpretation"] == (
        "pass_through_matrix_fields_only"
    )
    assert preflight["access_policy"]["audience"] == "internal_admin_only"
    assert preflight["access_policy"]["requires_admin_context"] is True
    assert preflight["readiness"]["route_preflight_landed"] is True
    assert preflight["readiness"]["route_mount_ready"] is False
    assert preflight["readiness"]["authenticated_internal_admin_route_ready"] is False
    assert preflight["readiness"]["route_response_verified"] is False
    assert preflight["preflight_verdict"] == (
        "decision_support_matrix_route_preflight_blocked_until_admin_auth_and_parity"
    )
    assert DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SAFE_CLAIM in preflight[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_route_preflight_matches_persisted_fixture():
    preflight = build_decision_support_matrix_route_preflight()

    assert preflight == read_fixture_preflight()
    assert load_decision_support_matrix_route_preflight() == preflight


def test_route_preflight_can_be_mount_ready_without_external_claims():
    card = build_decision_support_matrix_card()
    preflight = build_decision_support_matrix_route_preflight(
        card=card,
        route_probe={
            "route_handler_registered": True,
            "admin_auth_boundary_present": True,
            "route_path": card["render_contract"]["suggested_internal_path"],
            "card_payload_parity_verified": True,
            "response_interpretation": "pass_through_matrix_fields_only",
        },
    )

    assert preflight["readiness"]["route_mount_ready"] is True
    assert preflight["readiness"]["authenticated_internal_admin_route_ready"] is True
    assert preflight["readiness"]["route_response_verified"] is True
    assert DECISION_SUPPORT_MATRIX_AUTHENTICATED_ADMIN_ROUTE_SAFE_CLAIM in preflight[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "route_mount_ready" not in preflight["claim_boundaries"]["do_not_claim_yet"]
    assert "authenticated_internal_admin_route_ready" not in preflight[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert preflight["readiness"]["public_route_ready"] is False
    assert preflight["access_policy"]["public_route_registered"] is False
    assert preflight["access_policy"]["customer_visible"] is False
    assert preflight["access_policy"]["dispatch_enabled"] is False
    assert preflight["access_policy"]["writes_live_acontext"] is False
    assert preflight["preflight_verdict"] == (
        "decision_support_matrix_route_preflight_mount_ready_internal_admin_only"
    )


def test_route_preflight_refuses_promoted_card_readiness():
    card = copy.deepcopy(build_decision_support_matrix_card())
    card["readiness"]["public_route_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted card readiness"):
        build_decision_support_matrix_route_preflight(card=card)


def test_route_preflight_refuses_external_route_drift(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        tmp_path / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    )
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        tmp_path / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    )
    path = write_decision_support_matrix_route_preflight_fixture(artifact_dir=tmp_path)
    preflight = json.loads(path.read_text(encoding="utf-8"))
    preflight["access_policy"]["public_route_registered"] = True
    preflight["route_probe"]["public_route_registered"] = True
    path.write_text(json.dumps(preflight), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="external route drift"):
        load_decision_support_matrix_route_preflight(artifact_dir=tmp_path)


def test_write_route_preflight_persists_valid_artifact(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        tmp_path / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    )
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        tmp_path / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    )
    path = write_decision_support_matrix_route_preflight_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME
    assert load_decision_support_matrix_route_preflight(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )
