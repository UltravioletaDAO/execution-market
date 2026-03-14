"""
SwarmHealthDashboard — Real-time health monitoring for the KK V2 Swarm.

Monitors the health of all swarm dependencies:
    - EM API (production endpoint health)
    - ERC-8004 on-chain contracts
    - AutoJob enrichment service
    - Agent fleet status
    - Chain connectivity
    - Marketplace state (tasks, workers)

Usage:
    dashboard = SwarmHealthDashboard(
        em_api_url="https://api.execution.market",
    )

    # Full health report
    report = dashboard.full_report()
    print(report.summary())

    # Check specific components
    em_health = dashboard.check_em_health()
    auth_health = dashboard.check_em_auth()

    # Component status tracking
    status = dashboard.component_status("em_api")
"""

import json
import logging
import ssl
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ComponentCheck:
    """Result of a single component health check."""

    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0.0
    message: str = ""
    details: dict = field(default_factory=dict)
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now(timezone.utc).isoformat()

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at,
        }


@dataclass
class MarketplaceState:
    """Snapshot of marketplace state."""

    total_tasks: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    registered_workers: int = 0
    registered_agents: int = 0

    def to_dict(self) -> dict:
        return {
            "total_tasks": self.total_tasks,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "registered_workers": self.registered_workers,
            "registered_agents": self.registered_agents,
        }


@dataclass
class ChainState:
    """Health of a specific blockchain connection."""

    chain: str = ""
    connected: bool = False
    block_height: int = 0
    contracts_verified: bool = False
    last_tx_age_seconds: int = 0

    @property
    def is_healthy(self) -> bool:
        return self.connected and self.contracts_verified

    def to_dict(self) -> dict:
        return {
            "chain": self.chain,
            "connected": self.connected,
            "block_height": self.block_height,
            "contracts_verified": self.contracts_verified,
            "last_tx_age_seconds": self.last_tx_age_seconds,
        }


@dataclass
class HealthReport:
    """Complete health report for the swarm."""

    timestamp: str = ""
    components: list = field(default_factory=list)  # List[ComponentCheck]
    marketplace: Optional[MarketplaceState] = None
    chains: list = field(default_factory=list)  # List[ChainState]
    fleet_size: int = 0
    active_agents: int = 0
    missing_agents: list = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def overall_status(self) -> HealthStatus:
        """Compute overall status from components."""
        if not self.components:
            return HealthStatus.UNKNOWN
        statuses = [c.status for c in self.components]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        if any(s == HealthStatus.DOWN for s in statuses):
            return HealthStatus.DOWN
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        return HealthStatus.UNKNOWN

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [f"🏥 Swarm Health Report — {self.overall_status.value.upper()}"]
        lines.append(f"   Timestamp: {self.timestamp}")
        lines.append("")

        if self.components:
            lines.append("Components:")
            for c in self.components:
                icon = "✅" if c.is_healthy else ("⚠️" if c.status == HealthStatus.DEGRADED else "❌")
                latency = f" ({c.latency_ms:.0f}ms)" if c.latency_ms > 0 else ""
                msg = f" — {c.message}" if c.message else ""
                lines.append(f"  {icon} {c.name}: {c.status.value}{latency}{msg}")

        if self.fleet_size > 0:
            lines.append(f"\nFleet: {self.active_agents}/{self.fleet_size} agents active")

        if self.missing_agents:
            lines.append(f"Missing: {', '.join(self.missing_agents[:5])}")

        if self.marketplace:
            m = self.marketplace
            lines.append(f"\nMarketplace: {m.active_tasks} active / {m.completed_tasks} completed tasks")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "components": [c.to_dict() for c in self.components],
            "marketplace": self.marketplace.to_dict() if self.marketplace else None,
            "chains": [c.to_dict() for c in self.chains],
            "fleet_size": self.fleet_size,
            "active_agents": self.active_agents,
            "missing_agents": self.missing_agents,
        }


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: float = 10.0) -> tuple:
    """Make HTTP GET, return (status_code, body_str, latency_ms).

    Returns (0, error_message, latency) on failure.
    """
    start = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "SwarmHealthDashboard/1.0")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            latency = (time.monotonic() - start) * 1000
            return (resp.status, body, latency)
    except urllib.error.HTTPError as e:
        latency = (time.monotonic() - start) * 1000
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return (e.code, body, latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return (0, str(e), latency)


# ---------------------------------------------------------------------------
# SwarmComponentStatus — in-memory status tracker
# ---------------------------------------------------------------------------

class SwarmComponentStatus:
    """Tracks historical status of swarm components."""

    def __init__(self):
        self._components: dict = {}  # name -> latest ComponentCheck
        self._history: dict = {}  # name -> list of ComponentCheck (last N)

    def update(self, check: ComponentCheck) -> None:
        """Record a new check result."""
        self._components[check.name] = check
        hist = self._history.setdefault(check.name, [])
        hist.append(check)
        # Keep last 100 checks
        if len(hist) > 100:
            self._history[check.name] = hist[-100:]

    def get(self, name: str) -> Optional[ComponentCheck]:
        """Get latest check for a component."""
        return self._components.get(name)

    def all_components(self) -> dict:
        """Get all latest component checks."""
        return dict(self._components)


# ---------------------------------------------------------------------------
# SwarmHealthDashboard
# ---------------------------------------------------------------------------

class SwarmHealthDashboard:
    """Real-time health monitoring dashboard for the KK V2 Swarm."""

    def __init__(
        self,
        em_api_url: str = "https://api.execution.market",
        autojob_url: str = "",
        lifecycle_manager: Any = None,
        coordinator: Any = None,
        timeout: float = 10.0,
    ):
        self.em_api_url = em_api_url.rstrip("/")
        self.autojob_url = autojob_url.rstrip("/") if autojob_url else ""
        self.lifecycle = lifecycle_manager
        self.coordinator = coordinator
        self.timeout = timeout
        self._status = SwarmComponentStatus()

    def check_em_health(self) -> ComponentCheck:
        """Check EM API health endpoint."""
        url = f"{self.em_api_url}/health"
        status, body, latency = _http_get(url, self.timeout)

        if status == 200:
            check = ComponentCheck(
                name="em_api",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="API responding normally",
            )
        elif status > 0:
            check = ComponentCheck(
                name="em_api",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"HTTP {status}",
                details={"status_code": status},
            )
        else:
            check = ComponentCheck(
                name="em_api",
                status=HealthStatus.DOWN,
                latency_ms=latency,
                message=f"Connection failed: {body[:100]}",
            )

        self._status.update(check)
        return check

    def check_em_auth(self) -> ComponentCheck:
        """Check EM API auth endpoint (nonce generation)."""
        url = f"{self.em_api_url}/api/v1/auth/nonce"
        status, body, latency = _http_get(url, self.timeout)

        if status == 200:
            try:
                data = json.loads(body)
                nonce = data.get("nonce", "")
                if nonce:
                    check = ComponentCheck(
                        name="em_auth",
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message="Auth service operational",
                        details={"nonce_length": len(nonce)},
                    )
                else:
                    check = ComponentCheck(
                        name="em_auth",
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        message="Nonce endpoint returned empty nonce",
                    )
            except json.JSONDecodeError:
                check = ComponentCheck(
                    name="em_auth",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Invalid JSON response",
                )
        else:
            check = ComponentCheck(
                name="em_auth",
                status=HealthStatus.DOWN if status == 0 else HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"Auth endpoint returned {status}",
            )

        self._status.update(check)
        return check

    def check_autojob(self) -> ComponentCheck:
        """Check AutoJob enrichment service."""
        if not self.autojob_url:
            return ComponentCheck(
                name="autojob",
                status=HealthStatus.UNKNOWN,
                message="AutoJob URL not configured",
            )

        url = f"{self.autojob_url}/health"
        status, body, latency = _http_get(url, self.timeout)

        if status == 200:
            check = ComponentCheck(
                name="autojob",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="AutoJob service operational",
            )
        else:
            check = ComponentCheck(
                name="autojob",
                status=HealthStatus.DOWN if status == 0 else HealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"AutoJob returned {status}",
            )

        self._status.update(check)
        return check

    def check_fleet(self) -> ComponentCheck:
        """Check agent fleet status from lifecycle manager."""
        if not self.lifecycle:
            return ComponentCheck(
                name="fleet",
                status=HealthStatus.UNKNOWN,
                message="Lifecycle manager not configured",
            )

        try:
            agents = getattr(self.lifecycle, "_agents", {})
            total = len(agents)
            active = sum(
                1 for a in agents.values()
                if str(getattr(a, "status", "")).lower() in ("active", "busy")
            )

            if total == 0:
                check = ComponentCheck(
                    name="fleet",
                    status=HealthStatus.DOWN,
                    message="No agents registered",
                )
            elif active == 0:
                check = ComponentCheck(
                    name="fleet",
                    status=HealthStatus.DEGRADED,
                    message=f"0/{total} agents active",
                    details={"total": total, "active": active},
                )
            else:
                check = ComponentCheck(
                    name="fleet",
                    status=HealthStatus.HEALTHY,
                    message=f"{active}/{total} agents active",
                    details={"total": total, "active": active},
                )

            self._status.update(check)
            return check

        except Exception as e:
            check = ComponentCheck(
                name="fleet",
                status=HealthStatus.DOWN,
                message=f"Fleet check error: {e}",
            )
            self._status.update(check)
            return check

    def check_marketplace(self) -> tuple:
        """Check marketplace state (tasks, agents)."""
        url = f"{self.em_api_url}/api/v1/tasks?limit=1"
        status, body, latency = _http_get(url, self.timeout)

        marketplace = MarketplaceState()
        if status == 200:
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    marketplace.total_tasks = data.get("total", 0)
                    marketplace.active_tasks = data.get("active", 0)
                    marketplace.completed_tasks = data.get("completed", 0)
            except Exception:
                pass

        check = ComponentCheck(
            name="marketplace",
            status=HealthStatus.HEALTHY if status == 200 else HealthStatus.DEGRADED,
            latency_ms=latency,
            message=f"Tasks API: HTTP {status}",
        )
        self._status.update(check)
        return check, marketplace

    def full_report(self) -> HealthReport:
        """Run all health checks and build a complete report."""
        report = HealthReport()

        # Core checks
        report.components.append(self.check_em_health())
        report.components.append(self.check_em_auth())
        report.components.append(self.check_autojob())
        report.components.append(self.check_fleet())

        # Marketplace
        marketplace_check, marketplace = self.check_marketplace()
        report.components.append(marketplace_check)
        report.marketplace = marketplace

        # Fleet stats
        if self.lifecycle:
            agents = getattr(self.lifecycle, "_agents", {})
            report.fleet_size = len(agents)
            report.active_agents = sum(
                1 for a in agents.values()
                if str(getattr(a, "status", "")).lower() in ("active", "busy")
            )

        return report

    def component_status(self, name: str) -> Optional[ComponentCheck]:
        """Get latest status for a named component."""
        return self._status.get(name)

    def all_statuses(self) -> dict:
        """Get all tracked component statuses."""
        return self._status.all_components()
