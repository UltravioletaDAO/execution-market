import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_FILENAME,
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    AAS_MINIMUM_LADDER_TEMPLATE_SCHEMA,
    REQUIRED_FAMILY_ORDER,
    REQUIRED_LADDER_STEPS,
    build_aas_minimum_ladder_template,
    load_aas_minimum_ladder_template,
    write_aas_minimum_ladder_template,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_template() -> dict:
    with (ARTIFACT_DIR / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_aas_minimum_ladder_template_matches_persisted_artifact():
    template = build_aas_minimum_ladder_template()

    assert template == read_template()
    assert load_aas_minimum_ladder_template() == template
    assert template["schema"] == AAS_MINIMUM_LADDER_TEMPLATE_SCHEMA
    assert template["scope"] == "internal_planning_adjacent_aas_package_template_only"
    assert template["family_order"] == REQUIRED_FAMILY_ORDER
    assert template["promotion_rule"] == REQUIRED_LADDER_STEPS
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in template["safe_to_claim"]


def test_template_is_internal_only_not_customer_or_dispatch_ready():
    template = build_aas_minimum_ladder_template()

    assert template["global_readiness"] == {
        "template_exists": True,
        "adjacent_family_count": 5,
        "customer_copy_ready": False,
        "customer_visible_catalog_ready": False,
        "public_service_catalog_ready": False,
        "controlled_concierge_pilot_ready": False,
        "customer_pilot_exposure_allowed": False,
        "front_door_sku_ready": False,
        "operator_publish_approval": False,
        "customer_delivery_approval": False,
        "publication_approved": False,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "worker_skill_dna_ready": False,
        "worker_copyable_doctrine_ready": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
    }
    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_municipal_doctrine",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        assert claim in template["do_not_claim_yet"]
        assert claim not in template["safe_to_claim"]


def test_each_family_requires_full_ladder_and_own_evidence():
    template = build_aas_minimum_ladder_template()
    rows = {row["family_id"]: row for row in template["families"]}

    assert set(rows) == set(REQUIRED_FAMILY_ORDER)
    assert rows["compliance_desk_as_a_service"]["caas_source_pattern"] == (
        "posting_compliance_check"
    )
    assert rows["document_handoff_logistics_as_a_service"]["caas_source_pattern"] == (
        "packet_submission_attempt"
    )
    for row in rows.values():
        assert row["required_ladder_steps"] == REQUIRED_LADDER_STEPS
        assert row["required_evidence"]
        assert row["specific_blocked_claims"]
        assert row["readiness"]["customer_copy_ready"] is False
        assert row["readiness"]["autonomous_dispatch_ready"] is False
        assert row["readiness"]["worker_copyable_doctrine_ready"] is False
        assert "customer_copy_ready" in row["blocked_claims"]
        assert "exact_gps_or_raw_metadata_exposure_allowed" in row["blocked_claims"]


def test_write_aas_minimum_ladder_template_persists_valid_artifact(tmp_path):
    path = write_aas_minimum_ladder_template(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME
    assert load_aas_minimum_ladder_template(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_template_fails_closed_on_missing_adjacent_family():
    from mcp_server.city_ops import aas_minimum_ladder_template as module

    definitions = copy.deepcopy(module.FAMILY_DEFINITIONS)
    definitions.pop("procurement_admin_ops_as_a_service")

    with pytest.raises(CityOpsContractError, match="family definitions drifted"):
        build_aas_minimum_ladder_template(family_definitions=definitions)


def test_loader_fails_closed_on_global_readiness_promotion(tmp_path):
    template = build_aas_minimum_ladder_template()
    template["global_readiness"]["public_service_catalog_ready"] = True
    (tmp_path / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME).write_text(
        json.dumps(template), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_aas_minimum_ladder_template(artifact_dir=tmp_path)


def test_loader_fails_closed_on_family_readiness_promotion(tmp_path):
    template = build_aas_minimum_ladder_template()
    template["families"][0]["readiness"]["reputation_ready"] = True
    (tmp_path / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME).write_text(
        json.dumps(template), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_aas_minimum_ladder_template(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    template = build_aas_minimum_ladder_template()
    template["safe_to_claim"].append("aas_catalog_ready")
    (tmp_path / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME).write_text(
        json.dumps(template), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_aas_minimum_ladder_template(artifact_dir=tmp_path)


def test_loader_fails_closed_on_dropped_blocked_claim(tmp_path):
    template = build_aas_minimum_ladder_template()
    template["do_not_claim_yet"] = [
        claim
        for claim in template["do_not_claim_yet"]
        if claim != "worker_copyable_municipal_doctrine"
    ]
    (tmp_path / AAS_MINIMUM_LADDER_TEMPLATE_FILENAME).write_text(
        json.dumps(template), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        load_aas_minimum_ladder_template(artifact_dir=tmp_path)
