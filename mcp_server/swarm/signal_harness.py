"""
SignalHarness — Bootstrap all available signals into DecisionSynthesizer
========================================================================

The glue layer that connects the swarm's intelligence modules to the
DecisionSynthesizer's signal interface. Instead of manually wiring each
adapter, the harness discovers and connects available signal sources.

Usage:
    from mcp_server.swarm.signal_harness import SignalHarness

    harness = SignalHarness()

    # Connect available adapters
    harness.connect_reputation(reputation_bridge)
    harness.connect_availability(availability_bridge)
    harness.connect_verification(verification_adapter)
    # ... etc

    # Get the fully-wired synthesizer
    synthesizer = harness.synthesizer

    # Route a task
    decision = synthesizer.synthesize(task, candidates)

    # Diagnostic: which signals are live?
    status = harness.status()
    # {"connected": 5, "available": 13, "signals": ["skill_match", ...]}

The harness is the single place where signals are added. New signals
require ONE change here (a connect method + wiring), not scattered
changes across coordinator, integrator, and bootstrap.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .decision_synthesizer import (
    DecisionSynthesizer,
    SignalType,
    DEFAULT_WEIGHTS,
)

logger = logging.getLogger("em.swarm.signal_harness")


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────


@dataclass
class ConnectedSignal:
    """Metadata for a connected signal."""

    signal_type: SignalType
    source_name: str
    connected_at: float = field(default_factory=time.time)
    call_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    avg_latency_ms: float = 0.0


# ──────────────────────────────────────────────────────────────
# SignalHarness
# ──────────────────────────────────────────────────────────────


class SignalHarness:
    """
    Bootstrap and manage signal connections for DecisionSynthesizer.

    Central wiring point for all intelligence signals. Each connect_*
    method wraps the source's scorer function with telemetry (call count,
    error tracking, latency measurement) and registers it with the
    synthesizer.
    """

    def __init__(
        self,
        synthesizer: Optional[DecisionSynthesizer] = None,
    ):
        self.synthesizer = synthesizer or DecisionSynthesizer()
        self._connections: dict[SignalType, ConnectedSignal] = {}
        self._created_at = time.time()

    # ─── Instrumented Wrapper ────────────────────────────────

    def _wrap_scorer(
        self,
        signal_type: SignalType,
        source_name: str,
        scorer: Callable,
    ) -> Callable:
        """
        Wrap a scorer with telemetry tracking.

        Returns a new callable that:
        1. Counts invocations
        2. Tracks errors
        3. Measures latency
        4. Falls back to None on error (graceful degradation)
        """
        conn = ConnectedSignal(
            signal_type=signal_type,
            source_name=source_name,
        )
        self._connections[signal_type] = conn

        def instrumented_scorer(task: dict, candidate: dict) -> Optional[float]:
            conn.call_count += 1
            start = time.monotonic()
            try:
                result = scorer(task, candidate)
                elapsed_ms = (time.monotonic() - start) * 1000
                # Running average
                conn.avg_latency_ms = (
                    conn.avg_latency_ms * (conn.call_count - 1) + elapsed_ms
                ) / conn.call_count
                return result
            except Exception as e:
                conn.error_count += 1
                conn.last_error = str(e)
                logger.warning(
                    "Signal %s from %s failed: %s",
                    signal_type.value,
                    source_name,
                    e,
                )
                return None  # Synthesizer skips None signals

        return instrumented_scorer

    # ─── Signal Connectors ───────────────────────────────────

    def connect_reputation(self, bridge) -> "SignalHarness":
        """Connect ReputationBridge as REPUTATION signal."""
        def scorer(task, candidate):
            wallet = candidate.get("wallet", "")
            if not wallet:
                return None
            score = bridge.get_composite_score(wallet)
            return score * 100  # Normalize to 0-100

        wrapped = self._wrap_scorer(
            SignalType.REPUTATION, "ReputationBridge", scorer
        )
        self.synthesizer.register_signal(SignalType.REPUTATION, wrapped)
        logger.info("Connected REPUTATION signal from ReputationBridge")
        return self

    def connect_availability(self, bridge) -> "SignalHarness":
        """Connect AvailabilityBridge as AVAILABILITY signal."""
        def scorer(task, candidate):
            agent_id = candidate.get("id", candidate.get("agent_id", ""))
            prob = bridge.predict_availability(agent_id)
            return prob * 100  # Probability → 0-100

        wrapped = self._wrap_scorer(
            SignalType.AVAILABILITY, "AvailabilityBridge", scorer
        )
        self.synthesizer.register_signal(SignalType.AVAILABILITY, wrapped)
        logger.info("Connected AVAILABILITY signal from AvailabilityBridge")
        return self

    def connect_verification(self, adapter) -> "SignalHarness":
        """Connect VerificationAdapter as VERIFICATION_QUALITY signal (#13)."""
        def scorer(task, candidate):
            worker_id = candidate.get("id", candidate.get("wallet", ""))
            return adapter.score(worker_id, task)

        wrapped = self._wrap_scorer(
            SignalType.VERIFICATION_QUALITY, "VerificationAdapter", scorer
        )
        self.synthesizer.register_signal(
            SignalType.VERIFICATION_QUALITY, wrapped
        )
        logger.info("Connected VERIFICATION_QUALITY signal from VerificationAdapter")
        return self

    def connect_skill_match(self, matcher) -> "SignalHarness":
        """Connect a skill matching function as SKILL_MATCH signal."""
        def scorer(task, candidate):
            return matcher.match_score(task, candidate) * 100

        wrapped = self._wrap_scorer(
            SignalType.SKILL_MATCH, "SkillMatcher", scorer
        )
        self.synthesizer.register_signal(SignalType.SKILL_MATCH, wrapped)
        logger.info("Connected SKILL_MATCH signal from SkillMatcher")
        return self

    def connect_reliability(self, source) -> "SignalHarness":
        """Connect reliability scoring as RELIABILITY signal."""
        def scorer(task, candidate):
            agent_id = candidate.get("id", candidate.get("agent_id", ""))
            return source.get_reliability_score(agent_id)

        wrapped = self._wrap_scorer(
            SignalType.RELIABILITY, "ReliabilitySource", scorer
        )
        self.synthesizer.register_signal(SignalType.RELIABILITY, wrapped)
        logger.info("Connected RELIABILITY signal from ReliabilitySource")
        return self

    def connect_speed(self, source) -> "SignalHarness":
        """Connect speed scoring as SPEED signal."""
        def scorer(task, candidate):
            agent_id = candidate.get("id", candidate.get("agent_id", ""))
            return source.get_speed_score(agent_id)

        wrapped = self._wrap_scorer(
            SignalType.SPEED, "SpeedSource", scorer
        )
        self.synthesizer.register_signal(SignalType.SPEED, wrapped)
        logger.info("Connected SPEED signal from SpeedSource")
        return self

    def connect_custom(
        self,
        signal_type: SignalType,
        source_name: str,
        scorer: Callable[[dict, dict], float],
    ) -> "SignalHarness":
        """
        Connect a custom signal source.

        Args:
            signal_type: The SignalType to register.
            source_name: Human-readable name for diagnostics.
            scorer: Callable(task, candidate) -> float (0-100).
        """
        wrapped = self._wrap_scorer(signal_type, source_name, scorer)
        self.synthesizer.register_signal(signal_type, wrapped)
        logger.info(f"Connected {signal_type.value} signal from {source_name}")
        return self

    # ─── Disconnection ────────────────────────────────────────

    def disconnect(self, signal_type: SignalType) -> bool:
        """Disconnect a signal source."""
        if signal_type in self._connections:
            self.synthesizer.unregister_signal(signal_type)
            del self._connections[signal_type]
            logger.info(f"Disconnected {signal_type.value} signal")
            return True
        return False

    def disconnect_all(self) -> int:
        """Disconnect all signals. Returns count disconnected."""
        count = len(self._connections)
        for stype in list(self._connections.keys()):
            self.disconnect(stype)
        return count

    # ─── Diagnostics ──────────────────────────────────────────

    @property
    def connected_count(self) -> int:
        """Number of currently connected signals."""
        return len(self._connections)

    @property
    def total_available(self) -> int:
        """Total number of possible signal types."""
        return len(SignalType)

    def status(self) -> dict:
        """Full diagnostic status of the signal harness."""
        connections = {}
        total_calls = 0
        total_errors = 0

        for stype, conn in self._connections.items():
            connections[stype.value] = {
                "source": conn.source_name,
                "connected_at": datetime.fromtimestamp(
                    conn.connected_at, tz=timezone.utc
                ).isoformat(),
                "calls": conn.call_count,
                "errors": conn.error_count,
                "error_rate": (
                    round(conn.error_count / conn.call_count, 3)
                    if conn.call_count > 0
                    else 0.0
                ),
                "avg_latency_ms": round(conn.avg_latency_ms, 2),
                "last_error": conn.last_error,
                "weight": DEFAULT_WEIGHTS.get(stype, 0.0),
            }
            total_calls += conn.call_count
            total_errors += conn.error_count

        return {
            "connected": self.connected_count,
            "available": self.total_available,
            "coverage": round(
                self.connected_count / max(1, len(DEFAULT_WEIGHTS)), 3
            ),
            "total_calls": total_calls,
            "total_errors": total_errors,
            "uptime_seconds": round(time.time() - self._created_at, 1),
            "signals": connections,
        }

    def health_summary(self) -> dict:
        """Compact health summary for integrator reporting."""
        healthy_count = sum(
            1
            for conn in self._connections.values()
            if conn.error_count == 0
            or (conn.call_count > 0 and conn.error_count / conn.call_count < 0.1)
        )

        return {
            "healthy": healthy_count == len(self._connections),
            "connected": self.connected_count,
            "healthy_signals": healthy_count,
            "degraded_signals": len(self._connections) - healthy_count,
        }

    def get_signal_stats(self, signal_type: SignalType) -> Optional[dict]:
        """Get stats for a specific connected signal."""
        conn = self._connections.get(signal_type)
        if not conn:
            return None
        return {
            "source": conn.source_name,
            "calls": conn.call_count,
            "errors": conn.error_count,
            "avg_latency_ms": round(conn.avg_latency_ms, 2),
        }
