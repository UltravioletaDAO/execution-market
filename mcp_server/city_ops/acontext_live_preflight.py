"""Live Acontext transport preflight for City-as-a-Service proof blocks.

The local transport parity fixture gives the future Acontext sink an exact
write/retrieve contract.  This module adds the next safe seam: a preflight that
checks whether a live local Acontext run can even be attempted, while refusing
to perform a sink write or promote readiness by itself.

It is deliberately conservative.  A successful preflight means "the live
transport test may be attempted"; it does not mean ``acontext_sink_ready``.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .acontext_transport import (
    ACONTEXT_TRANSPORT_BLOCKED_CLAIMS,
    ACONTEXT_TRANSPORT_SAFE_CLAIM,
    build_acontext_transport_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir

ACONTEXT_LIVE_PREFLIGHT_SCHEMA = "city_ops.acontext_live_preflight.v1"
ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM = "acontext_live_preflight_landed"
ACONTEXT_LIVE_PREFLIGHT_BLOCKED_CLAIMS = [
    *ACONTEXT_TRANSPORT_BLOCKED_CLAIMS,
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "acontext_live_transport_parity_landed",
]
DEFAULT_ACONTEXT_API_URL = "http://localhost:8029/api/v1"
DEFAULT_ACONTEXT_DASHBOARD_URL = "http://localhost:3000"


def probe_local_acontext_environment(
    *,
    api_url: str = DEFAULT_ACONTEXT_API_URL,
    dashboard_url: str = DEFAULT_ACONTEXT_DASHBOARD_URL,
    timeout_seconds: float = 1.0,
    run_docker_check: bool = True,
    run_http_checks: bool = True,
) -> dict[str, Any]:
    """Probe local prerequisites for the live Acontext transport test.

    The probe is read-only.  It may execute ``docker info`` and HTTP GETs, but
    it never creates an Acontext project/session/artifact and never writes a
    City-as-a-Service proof packet.
    """

    docker_probe = _probe_docker_info(timeout_seconds) if run_docker_check else {
        "checked": False,
        "available": False,
        "exit_code": None,
        "error": "docker check skipped",
    }
    sdk_available = importlib.util.find_spec("acontext") is not None
    api_probe = _probe_http(api_url, timeout_seconds) if run_http_checks else {
        "checked": False,
        "url": api_url,
        "reachable": False,
        "status_code": None,
        "error": "api check skipped",
    }
    dashboard_probe = _probe_http(dashboard_url, timeout_seconds) if run_http_checks else {
        "checked": False,
        "url": dashboard_url,
        "reachable": False,
        "status_code": None,
        "error": "dashboard check skipped",
    }

    return {
        "docker": docker_probe,
        "python_sdk": {
            "checked": True,
            "package": "acontext",
            "available": sdk_available,
        },
        "api": api_probe,
        "dashboard": dashboard_probe,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_blocked_acontext_preflight_probe(
    *,
    api_url: str = DEFAULT_ACONTEXT_API_URL,
    dashboard_url: str = DEFAULT_ACONTEXT_DASHBOARD_URL,
) -> dict[str, Any]:
    """Return a deterministic blocked probe for fixture generation/tests."""

    return {
        "docker": {
            "checked": True,
            "available": False,
            "exit_code": 1,
            "error": "docker daemon unavailable in cron context",
        },
        "python_sdk": {
            "checked": True,
            "package": "acontext",
            "available": False,
        },
        "api": {
            "checked": True,
            "url": api_url,
            "reachable": False,
            "status_code": None,
            "error": "local Acontext API not reachable",
        },
        "dashboard": {
            "checked": True,
            "url": dashboard_url,
            "reachable": False,
            "status_code": None,
            "error": "local Acontext dashboard not reachable",
        },
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_live_preflight_result(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    packet: dict[str, Any] | None = None,
    probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative readiness report for the live Acontext transport run.

    The returned artifact answers only: are the prerequisites present to attempt
    the live write/retrieve parity test?  It must not mark any sink/write/rebuild
    readiness claim safe.
    """

    source_packet = packet or build_acontext_transport_packet(
        proof_anchor_id,
        artifact_dir=artifact_dir,
    )
    source_probe = probe or probe_local_acontext_environment()
    _assert_preflight_inputs(source_packet, source_probe)

    readiness = _derive_preflight_readiness(source_probe)
    claim_boundaries = source_packet["stored_payload"]["claim_boundaries"]
    safe_to_claim = _dedupe(
        [
            *claim_boundaries.get("safe_to_claim", []),
            ACONTEXT_TRANSPORT_SAFE_CLAIM,
            ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *claim_boundaries.get("do_not_claim_yet", []),
            *ACONTEXT_LIVE_PREFLIGHT_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_blocked_claims_safe(safe_to_claim)

    return {
        "schema": ACONTEXT_LIVE_PREFLIGHT_SCHEMA,
        "preflight_id": f"acontext_live_preflight:{source_packet['proof_anchor_id']}",
        "proof_anchor_id": source_packet["proof_anchor_id"],
        "coordination_session_id": source_packet["coordination_session_id"],
        "compact_decision_id": source_packet["compact_decision_id"],
        "review_packet_id": source_packet["review_packet_id"],
        "packet_id": source_packet["packet_id"],
        "source_packet": {
            "schema": source_packet["schema"],
            "packet_id": source_packet["packet_id"],
            "transport_mode": source_packet["transport_contract"]["transport_mode"],
            "live_acontext_write_performed": source_packet["transport_contract"][
                "live_acontext_write_performed"
            ],
        },
        "target": {
            "intended_sink": "acontext",
            "api_url": source_probe["api"]["url"],
            "dashboard_url": source_probe["dashboard"]["url"],
            "namespace": source_packet["namespace"],
        },
        "probe": source_probe,
        "readiness": readiness,
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "inherited_safe_to_claim": list(claim_boundaries.get("safe_to_claim", [])),
            "do_not_claim_yet": do_not_claim_yet,
        },
        "planned_live_transport_contract": {
            "derive_packet_from": source_packet["source_report"]["schema"],
            "write_payload": "city_ops.acontext_transport_packet.v1.stored_payload",
            "retrieve_by": ["proof_anchor_id", "packet_id", "namespace"],
            "must_reuse_assertion": "assert_acontext_transport_parity(packet, retrieval)",
            "must_not_read": [
                "raw_transcripts",
                "unreviewed_worker_uploads",
                "private_operator_context",
                "freeform_chat_as_authority",
            ],
            "may_attempt_when": [
                "docker_available",
                "acontext_python_sdk_available",
                "local_acontext_api_reachable",
                "local_acontext_dashboard_reachable",
            ],
        },
        "preflight_verdict": (
            "live_transport_can_be_attempted_without_readiness_claim"
            if readiness["ready_to_attempt_live_transport"]
            else "live_transport_blocked_before_sink_write"
        ),
        "next_smallest_proof": _next_smallest_proof(readiness),
    }


def write_acontext_live_preflight_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    probe: dict[str, Any] | None = None,
) -> Path:
    """Write the deterministic live Acontext preflight fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    result = build_acontext_live_preflight_result(
        proof_anchor_id,
        artifact_dir=base_dir,
        probe=probe or build_blocked_acontext_preflight_probe(),
    )
    path = base_dir / "acontext_live_preflight_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _derive_preflight_readiness(probe: dict[str, Any]) -> dict[str, Any]:
    docker_available = bool(probe["docker"].get("available"))
    sdk_available = bool(probe["python_sdk"].get("available"))
    api_reachable = bool(probe["api"].get("reachable"))
    dashboard_reachable = bool(probe["dashboard"].get("reachable"))
    blockers: list[str] = []
    if not docker_available:
        blockers.append("docker_daemon_unavailable")
    if not sdk_available:
        blockers.append("acontext_python_sdk_missing")
    if not api_reachable:
        blockers.append("local_acontext_api_unreachable")
    if not dashboard_reachable:
        blockers.append("local_acontext_dashboard_unreachable")

    ready_to_attempt = not blockers
    return {
        "docker_available": docker_available,
        "acontext_python_sdk_available": sdk_available,
        "local_acontext_api_reachable": api_reachable,
        "local_acontext_dashboard_reachable": dashboard_reachable,
        "ready_to_attempt_live_transport": ready_to_attempt,
        "acontext_sink_ready": False,
        "session_rebuild_ready": False,
        "runtime_parity_proven": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "blockers": blockers,
    }


def _assert_preflight_inputs(packet: dict[str, Any], probe: dict[str, Any]) -> None:
    if packet.get("schema") != "city_ops.acontext_transport_packet.v1":
        raise CityOpsContractError("Acontext live preflight requires transport packet")
    transport = packet.get("transport_contract") or {}
    if transport.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("Preflight cannot accept a packet after live write")
    if transport.get("writes_live_sink") is not False:
        raise CityOpsContractError("Preflight cannot write live sink")
    if probe.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("Preflight probe must not perform live Acontext writes")
    if probe.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("Preflight probe must not perform live Acontext retrievals")
    for key in ("docker", "python_sdk", "api", "dashboard"):
        if not isinstance(probe.get(key), dict):
            raise CityOpsContractError(f"Acontext live preflight probe missing {key}")
    if "url" not in probe["api"] or "url" not in probe["dashboard"]:
        raise CityOpsContractError("Acontext live preflight probe missing target URLs")


def _assert_no_blocked_claims_safe(safe_to_claim: list[str]) -> None:
    blocked = sorted(set(safe_to_claim).intersection(ACONTEXT_LIVE_PREFLIGHT_BLOCKED_CLAIMS))
    if blocked:
        raise CityOpsContractError(
            f"Acontext live preflight cannot mark blocked claims safe: {blocked}"
        )


def _next_smallest_proof(readiness: dict[str, Any]) -> list[str]:
    if readiness["ready_to_attempt_live_transport"]:
        return [
            "run the existing packet through the local Acontext write path",
            "retrieve by proof_anchor_id, packet_id, and namespace",
            "reuse assert_acontext_transport_parity before claiming any live parity label",
            "keep acontext_sink_ready=false until live retrieval proves no semantic strengthening",
        ]
    return [
        "start Docker and local Acontext without changing CaaS semantics",
        "install or expose the Acontext Python SDK/CLI in this environment",
        "verify http://localhost:8029/api/v1 and http://localhost:3000 are reachable",
        "rerun this preflight before attempting any live Acontext sink write",
    ]


def _probe_docker_info(timeout_seconds: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        return {
            "checked": True,
            "available": False,
            "exit_code": None,
            "error": str(exc),
        }
    except subprocess.TimeoutExpired:
        return {
            "checked": True,
            "available": False,
            "exit_code": None,
            "error": "docker info timed out",
        }

    output = (completed.stderr or completed.stdout or "").strip()
    return {
        "checked": True,
        "available": completed.returncode == 0,
        "exit_code": completed.returncode,
        "error": None if completed.returncode == 0 else output[:500],
    }


def _probe_http(url: str, timeout_seconds: float) -> dict[str, Any]:
    request = Request(url, method="GET", headers={"User-Agent": "em-caas-preflight"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status_code = int(response.status)
    except URLError as exc:
        return {
            "checked": True,
            "url": url,
            "reachable": False,
            "status_code": None,
            "error": str(exc),
        }
    except TimeoutError as exc:
        return {
            "checked": True,
            "url": url,
            "reachable": False,
            "status_code": None,
            "error": str(exc),
        }
    return {
        "checked": True,
        "url": url,
        "reachable": 200 <= status_code < 500,
        "status_code": status_code,
        "error": None,
    }


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
