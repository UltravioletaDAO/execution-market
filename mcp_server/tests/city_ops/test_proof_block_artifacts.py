import json
from pathlib import Path

from mcp_server.city_ops.closure import FORBIDDEN_CLOSURE_SOURCES
from mcp_server.city_ops.proof_block_artifacts import (
    PROOF_BLOCK_FILENAMES,
    build_redirect_outdated_packet_001_proof_block,
    write_redirect_outdated_packet_001_proof_block,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def load_fixture(filename: str):
    with (PROOF_BLOCK_DIR / filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_persisted_proof_block_fixtures_match_builder_output():
    proof_block = build_redirect_outdated_packet_001_proof_block()

    assert load_fixture("proof_block_telemetry_gate.json") == proof_block["telemetry_gate"]
    assert load_fixture("session_rebuild_preview.json") == proof_block[
        "session_rebuild_preview"
    ]
    assert load_fixture("acontext_export_preview.json") == proof_block[
        "acontext_export_preview"
    ]


def test_persisted_closure_previews_keep_forbidden_sources_explicit():
    for filename in ("session_rebuild_preview.json", "acontext_export_preview.json"):
        artifact = load_fixture(filename)
        source_contract = artifact["source_read_contract"]

        assert source_contract["raw_transcript_required"] is False
        assert source_contract["forbidden_sources"] == FORBIDDEN_CLOSURE_SOURCES
        assert artifact.get("preview_promotes_readiness") is False or artifact[
            "readiness"
        ].get("preview_promotes_readiness") is False


def test_proof_block_writer_regenerates_all_persisted_consumers(tmp_path):
    written = write_redirect_outdated_packet_001_proof_block(tmp_path)
    proof_block = build_redirect_outdated_packet_001_proof_block()

    assert set(written) == set(PROOF_BLOCK_FILENAMES)
    for key, filename in PROOF_BLOCK_FILENAMES.items():
        with (tmp_path / filename).open("r", encoding="utf-8") as fh:
            assert json.load(fh) == proof_block[key]
