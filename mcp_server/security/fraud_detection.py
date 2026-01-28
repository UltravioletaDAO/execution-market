"""
Fraud Detection Module (NOW-109, NOW-110)

Detects fraudulent patterns in the Chamba human execution marketplace:
- Multi-device detection: Same worker using multiple devices (Sybil attack)
- Wash trading: Same entity as agent AND worker (self-dealing)
- Collusion: Repeated agent-worker pairs with suspicious patterns
- Gaming: Rapid completions, inflated bounties, circular payments

Architecture:
    FraudDetector maintains in-memory profiles for real-time detection.
    For production, profiles should be persisted to database and
    loaded on startup. The detector emits FraudAlerts that can trigger:
    - Automatic task holds
    - Manual review queues
    - Account suspensions
    - Payment freezes

Example:
    >>> detector = FraudDetector()
    >>> alert = detector.check_multi_device("worker_123", "device_abc")
    >>> if alert:
    ...     print(f"FRAUD: {alert.signal} - {alert.risk_level}")
"""

import logging
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class FraudSignal(str, Enum):
    """Types of fraud signals that can be detected."""
    # Multi-device fraud (NOW-109)
    MULTI_DEVICE = "multi_device"
    DEVICE_SPOOFING = "device_spoofing"
    DEVICE_FARM = "device_farm"

    # Wash trading signals (NOW-110)
    SAME_IP_AGENT_WORKER = "same_ip_agent_worker"
    INSTANT_APPROVAL = "instant_approval"
    INFLATED_BOUNTY = "inflated_bounty"
    RAPID_COMPLETION = "rapid_completion"

    # Collusion signals
    CIRCULAR_PAYMENTS = "circular_payments"
    REPEATED_PAIRING = "repeated_pairing"
    COORDINATED_TIMING = "coordinated_timing"

    # Account manipulation
    NEW_ACCOUNT_HIGH_VALUE = "new_account_high_value"
    WALLET_CLUSTERING = "wallet_clustering"


class RiskLevel(str, Enum):
    """Risk severity levels for fraud alerts."""
    LOW = "low"           # Monitor only
    MEDIUM = "medium"     # Flag for review
    HIGH = "high"         # Hold payment, require review
    CRITICAL = "critical" # Block immediately, freeze funds


@dataclass
class FraudConfig:
    """Configuration for fraud detection thresholds."""
    # Multi-device thresholds
    max_devices_per_worker: int = 3
    device_switch_cooldown_hours: int = 24
    suspicious_device_switches: int = 5  # per day

    # Wash trading thresholds
    instant_approval_seconds: float = 30.0
    inflated_bounty_multiplier: float = 3.0
    rapid_completion_minutes: float = 5.0
    min_review_time_seconds: float = 10.0

    # Collusion thresholds
    suspicious_pairing_count: int = 3  # same pair in 30 days
    pairing_window_days: int = 30
    circular_payment_depth: int = 3

    # Account thresholds
    new_account_days: int = 7
    new_account_max_value: float = 50.0

    # Timing thresholds
    coordinated_timing_window_seconds: float = 60.0

    # Risk scoring weights
    weight_multi_device: float = 0.3
    weight_wash_trading: float = 0.4
    weight_collusion: float = 0.2
    weight_account: float = 0.1


@dataclass
class FraudAlert:
    """A detected fraud signal with evidence."""
    id: str
    signal: FraudSignal
    risk_level: RiskLevel
    entities: List[str]  # worker_ids, agent_ids involved
    evidence: Dict[str, Any]
    detected_at: datetime
    task_id: Optional[str] = None
    resolved: bool = False
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API."""
        return {
            "id": self.id,
            "signal": self.signal.value,
            "risk_level": self.risk_level.value,
            "entities": self.entities,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat(),
            "task_id": self.task_id,
            "resolved": self.resolved,
            "resolution": self.resolution,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }


@dataclass
class DeviceRecord:
    """Record of a device seen for an entity."""
    device_id: str
    device_fingerprint: str
    first_seen: datetime
    last_seen: datetime
    ip_addresses: Set[str] = field(default_factory=set)
    task_count: int = 0


@dataclass
class TaskRecord:
    """Minimal task record for pattern analysis."""
    task_id: str
    agent_id: str
    worker_id: Optional[str]
    bounty_usd: float
    created_at: datetime
    accepted_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    agent_ip: Optional[str] = None
    worker_ip: Optional[str] = None


@dataclass
class EntityProfile:
    """Profile tracking an entity's behavior patterns."""
    entity_id: str
    entity_type: str  # 'worker' or 'agent'
    created_at: datetime
    devices: Dict[str, DeviceRecord] = field(default_factory=dict)
    ip_addresses: Set[str] = field(default_factory=set)
    wallet_addresses: Set[str] = field(default_factory=set)
    connected_entities: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    task_ids: List[str] = field(default_factory=list)
    alert_ids: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    flags: Set[str] = field(default_factory=set)

    @property
    def device_count(self) -> int:
        """Number of unique devices used."""
        return len(self.devices)

    @property
    def is_new_account(self) -> bool:
        """Check if account is less than 7 days old."""
        age = datetime.now(timezone.utc) - self.created_at
        return age.days < 7

    @property
    def alert_count(self) -> int:
        """Number of alerts associated with this entity."""
        return len(self.alert_ids)


class FraudDetector:
    """
    Real-time fraud detection for the Chamba marketplace.

    Maintains entity profiles and checks for fraud patterns on each
    relevant action (task acceptance, submission, approval).

    Example:
        >>> detector = FraudDetector()
        >>>
        >>> # Check device on task acceptance
        >>> alert = detector.check_multi_device("worker_123", "device_abc")
        >>> if alert and alert.risk_level == RiskLevel.HIGH:
        ...     raise FraudException("Suspicious device activity")
        >>>
        >>> # Check wash trading on approval
        >>> alerts = detector.check_wash_trading(
        ...     task_id="task_456",
        ...     agent_id="agent_789",
        ...     worker_id="worker_123",
        ...     agent_ip="1.2.3.4",
        ...     worker_ip="1.2.3.4",  # Same IP!
        ...     approval_time_seconds=5.0,  # Instant!
        ...     bounty=100.0,
        ...     avg_bounty=20.0,  # Inflated!
        ... )
        >>> for alert in alerts:
        ...     print(f"WASH TRADING: {alert.signal}")
    """

    def __init__(self, config: Optional[FraudConfig] = None):
        """Initialize detector with optional custom config."""
        self.config = config or FraudConfig()
        self._profiles: Dict[str, EntityProfile] = {}
        self._alerts: Dict[str, FraudAlert] = {}
        self._ip_to_entities: Dict[str, Set[str]] = defaultdict(set)
        self._wallet_to_entities: Dict[str, Set[str]] = defaultdict(set)
        self._task_records: Dict[str, TaskRecord] = {}
        self._device_to_workers: Dict[str, Set[str]] = defaultdict(set)

    def _get_or_create_profile(
        self,
        entity_id: str,
        entity_type: str = "worker"
    ) -> EntityProfile:
        """Get existing profile or create new one."""
        if entity_id not in self._profiles:
            self._profiles[entity_id] = EntityProfile(
                entity_id=entity_id,
                entity_type=entity_type,
                created_at=datetime.now(timezone.utc),
            )
        return self._profiles[entity_id]

    def _create_alert(
        self,
        signal: FraudSignal,
        risk_level: RiskLevel,
        entities: List[str],
        evidence: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> FraudAlert:
        """Create and store a fraud alert."""
        alert = FraudAlert(
            id=f"alert_{uuid.uuid4().hex[:12]}",
            signal=signal,
            risk_level=risk_level,
            entities=entities,
            evidence=evidence,
            detected_at=datetime.now(timezone.utc),
            task_id=task_id,
        )

        self._alerts[alert.id] = alert

        # Link alert to entity profiles
        for entity_id in entities:
            if entity_id in self._profiles:
                self._profiles[entity_id].alert_ids.append(alert.id)

        logger.warning(
            f"FRAUD ALERT [{alert.risk_level.value.upper()}]: "
            f"{alert.signal.value} - entities={entities} - task={task_id}"
        )

        return alert

    def _generate_device_fingerprint(
        self,
        device_id: str,
        user_agent: Optional[str] = None,
        screen_res: Optional[str] = None,
    ) -> str:
        """Generate a device fingerprint for deduplication."""
        parts = [device_id]
        if user_agent:
            parts.append(user_agent)
        if screen_res:
            parts.append(screen_res)

        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    # =========================================================================
    # NOW-109: Multi-Device Detection
    # =========================================================================

    def check_multi_device(
        self,
        worker_id: str,
        device_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        screen_res: Optional[str] = None,
    ) -> Optional[FraudAlert]:
        """
        Detect if a worker is using too many devices (Sybil indicator).

        Multi-device fraud patterns:
        1. Same worker on many physical devices (Sybil attack setup)
        2. Rapid device switching (device spoofing)
        3. Same device used by multiple workers (device farm)

        Args:
            worker_id: Worker's unique identifier
            device_id: Device identifier (from client)
            ip_address: Optional IP for additional correlation
            user_agent: Optional browser/app user agent
            screen_res: Optional screen resolution

        Returns:
            FraudAlert if suspicious, None otherwise
        """
        profile = self._get_or_create_profile(worker_id, "worker")
        fingerprint = self._generate_device_fingerprint(device_id, user_agent, screen_res)
        now = datetime.now(timezone.utc)

        # Track device
        if device_id in profile.devices:
            record = profile.devices[device_id]
            record.last_seen = now
            record.task_count += 1
            if ip_address:
                record.ip_addresses.add(ip_address)
        else:
            profile.devices[device_id] = DeviceRecord(
                device_id=device_id,
                device_fingerprint=fingerprint,
                first_seen=now,
                last_seen=now,
                ip_addresses={ip_address} if ip_address else set(),
                task_count=1,
            )

        # Track IP
        if ip_address:
            profile.ip_addresses.add(ip_address)
            self._ip_to_entities[ip_address].add(worker_id)

        # Track device to worker mapping (for device farm detection)
        self._device_to_workers[device_id].add(worker_id)

        # Check 1: Too many devices for one worker
        if profile.device_count > self.config.max_devices_per_worker:
            return self._create_alert(
                signal=FraudSignal.MULTI_DEVICE,
                risk_level=RiskLevel.HIGH,
                entities=[worker_id],
                evidence={
                    "device_count": profile.device_count,
                    "max_allowed": self.config.max_devices_per_worker,
                    "devices": list(profile.devices.keys()),
                    "current_device": device_id,
                },
            )

        # Check 2: Rapid device switching
        recent_devices = [
            d for d in profile.devices.values()
            if (now - d.last_seen).total_seconds() < 24 * 3600
        ]
        if len(recent_devices) >= self.config.suspicious_device_switches:
            return self._create_alert(
                signal=FraudSignal.DEVICE_SPOOFING,
                risk_level=RiskLevel.MEDIUM,
                entities=[worker_id],
                evidence={
                    "devices_in_24h": len(recent_devices),
                    "threshold": self.config.suspicious_device_switches,
                    "device_ids": [d.device_id for d in recent_devices],
                },
            )

        # Check 3: Device farm - same device used by multiple workers
        workers_on_device = self._device_to_workers[device_id]
        if len(workers_on_device) > 1:
            return self._create_alert(
                signal=FraudSignal.DEVICE_FARM,
                risk_level=RiskLevel.CRITICAL,
                entities=list(workers_on_device),
                evidence={
                    "device_id": device_id,
                    "worker_count": len(workers_on_device),
                    "worker_ids": list(workers_on_device),
                },
            )

        return None

    # =========================================================================
    # NOW-110: Wash Trading Detection
    # =========================================================================

    def check_wash_trading(
        self,
        task_id: str,
        agent_id: str,
        worker_id: str,
        agent_ip: Optional[str],
        worker_ip: Optional[str],
        approval_time_seconds: float,
        bounty: float,
        avg_bounty: float,
        completion_time_minutes: Optional[float] = None,
    ) -> List[FraudAlert]:
        """
        Detect wash trading patterns (same entity as agent and worker).

        Wash trading signals:
        1. Same IP for agent and worker
        2. Instant approval (no real review)
        3. Inflated bounty (self-dealing)
        4. Suspiciously rapid completion

        Args:
            task_id: Task being analyzed
            agent_id: Agent who created/approved task
            worker_id: Worker who completed task
            agent_ip: IP address of agent actions
            worker_ip: IP address of worker actions
            approval_time_seconds: Time from submission to approval
            bounty: Task bounty in USD
            avg_bounty: Average bounty for similar tasks
            completion_time_minutes: Optional time from accept to submit

        Returns:
            List of FraudAlerts (may have multiple signals)
        """
        alerts: List[FraudAlert] = []

        # Ensure profiles exist
        agent_profile = self._get_or_create_profile(agent_id, "agent")
        worker_profile = self._get_or_create_profile(worker_id, "worker")

        # Track connection
        agent_profile.connected_entities[worker_id] += 1
        worker_profile.connected_entities[agent_id] += 1

        # Store task record
        self._task_records[task_id] = TaskRecord(
            task_id=task_id,
            agent_id=agent_id,
            worker_id=worker_id,
            bounty_usd=bounty,
            created_at=datetime.now(timezone.utc),
            agent_ip=agent_ip,
            worker_ip=worker_ip,
        )

        # Track IPs
        if agent_ip:
            agent_profile.ip_addresses.add(agent_ip)
            self._ip_to_entities[agent_ip].add(agent_id)
        if worker_ip:
            worker_profile.ip_addresses.add(worker_ip)
            self._ip_to_entities[worker_ip].add(worker_id)

        # Signal 1: Same IP for agent and worker
        if agent_ip and worker_ip and agent_ip == worker_ip:
            alerts.append(self._create_alert(
                signal=FraudSignal.SAME_IP_AGENT_WORKER,
                risk_level=RiskLevel.CRITICAL,
                entities=[agent_id, worker_id],
                evidence={
                    "shared_ip": agent_ip,
                    "agent_id": agent_id,
                    "worker_id": worker_id,
                    "task_id": task_id,
                },
                task_id=task_id,
            ))

        # Signal 2: Instant approval
        if approval_time_seconds < self.config.instant_approval_seconds:
            # More suspicious if less than minimum review time
            risk = RiskLevel.HIGH if approval_time_seconds < self.config.min_review_time_seconds else RiskLevel.MEDIUM

            alerts.append(self._create_alert(
                signal=FraudSignal.INSTANT_APPROVAL,
                risk_level=risk,
                entities=[agent_id, worker_id],
                evidence={
                    "approval_time_seconds": approval_time_seconds,
                    "threshold_seconds": self.config.instant_approval_seconds,
                    "task_id": task_id,
                    "bounty": bounty,
                },
                task_id=task_id,
            ))

        # Signal 3: Inflated bounty
        if avg_bounty > 0 and bounty > avg_bounty * self.config.inflated_bounty_multiplier:
            alerts.append(self._create_alert(
                signal=FraudSignal.INFLATED_BOUNTY,
                risk_level=RiskLevel.HIGH,
                entities=[agent_id],
                evidence={
                    "bounty": bounty,
                    "avg_bounty": avg_bounty,
                    "multiplier": bounty / avg_bounty,
                    "threshold_multiplier": self.config.inflated_bounty_multiplier,
                    "task_id": task_id,
                },
                task_id=task_id,
            ))

        # Signal 4: Rapid completion
        if (
            completion_time_minutes is not None
            and completion_time_minutes < self.config.rapid_completion_minutes
        ):
            alerts.append(self._create_alert(
                signal=FraudSignal.RAPID_COMPLETION,
                risk_level=RiskLevel.MEDIUM,
                entities=[worker_id],
                evidence={
                    "completion_time_minutes": completion_time_minutes,
                    "threshold_minutes": self.config.rapid_completion_minutes,
                    "task_id": task_id,
                },
                task_id=task_id,
            ))

        return alerts

    # =========================================================================
    # Collusion Detection
    # =========================================================================

    def check_collusion(
        self,
        agent_id: str,
        worker_id: str,
        task_id: Optional[str] = None,
    ) -> Optional[FraudAlert]:
        """
        Detect agent-worker collusion patterns.

        Collusion indicators:
        1. Repeated pairing (same agent always picks same worker)
        2. Circular payments (A pays B pays C pays A)
        3. Wallet clustering (same wallet appears in multiple entities)

        Args:
            agent_id: Agent identifier
            worker_id: Worker identifier
            task_id: Optional task for context

        Returns:
            FraudAlert if collusion detected, None otherwise
        """
        agent_profile = self._get_or_create_profile(agent_id, "agent")
        worker_profile = self._get_or_create_profile(worker_id, "worker")

        # Update connection count
        pairing_count = agent_profile.connected_entities.get(worker_id, 0)

        # Check 1: Repeated pairing
        if pairing_count >= self.config.suspicious_pairing_count:
            return self._create_alert(
                signal=FraudSignal.REPEATED_PAIRING,
                risk_level=RiskLevel.MEDIUM,
                entities=[agent_id, worker_id],
                evidence={
                    "pairing_count": pairing_count,
                    "threshold": self.config.suspicious_pairing_count,
                    "window_days": self.config.pairing_window_days,
                },
                task_id=task_id,
            )

        # Check 2: Wallet clustering
        shared_wallets = agent_profile.wallet_addresses & worker_profile.wallet_addresses
        if shared_wallets:
            return self._create_alert(
                signal=FraudSignal.WALLET_CLUSTERING,
                risk_level=RiskLevel.CRITICAL,
                entities=[agent_id, worker_id],
                evidence={
                    "shared_wallets": list(shared_wallets),
                    "agent_wallets": list(agent_profile.wallet_addresses),
                    "worker_wallets": list(worker_profile.wallet_addresses),
                },
                task_id=task_id,
            )

        # Check 3: Circular payments (simplified check)
        # Full implementation would trace payment graph
        circular = self._detect_circular_payments(agent_id, worker_id)
        if circular:
            return self._create_alert(
                signal=FraudSignal.CIRCULAR_PAYMENTS,
                risk_level=RiskLevel.HIGH,
                entities=circular,
                evidence={
                    "payment_cycle": circular,
                    "depth": len(circular),
                },
                task_id=task_id,
            )

        return None

    def _detect_circular_payments(
        self,
        start_entity: str,
        current_entity: str,
        visited: Optional[Set[str]] = None,
        path: Optional[List[str]] = None,
        depth: int = 0,
    ) -> Optional[List[str]]:
        """
        Detect circular payment patterns using DFS.

        Returns list of entities in cycle if found, None otherwise.
        """
        if visited is None:
            visited = set()
        if path is None:
            path = []

        if depth > self.config.circular_payment_depth:
            return None

        if current_entity in visited:
            if current_entity == start_entity and depth > 1:
                return path + [current_entity]
            return None

        visited.add(current_entity)
        path.append(current_entity)

        profile = self._profiles.get(current_entity)
        if profile:
            for connected in profile.connected_entities:
                result = self._detect_circular_payments(
                    start_entity, connected, visited.copy(), path.copy(), depth + 1
                )
                if result:
                    return result

        return None

    # =========================================================================
    # New Account Monitoring
    # =========================================================================

    def check_new_account_risk(
        self,
        worker_id: str,
        task_value: float,
        account_created_at: datetime,
    ) -> Optional[FraudAlert]:
        """
        Check if a new account is attempting high-value tasks.

        Args:
            worker_id: Worker identifier
            task_value: Value of task being accepted
            account_created_at: When the account was created

        Returns:
            FraudAlert if suspicious, None otherwise
        """
        profile = self._get_or_create_profile(worker_id, "worker")
        profile.created_at = account_created_at

        account_age = datetime.now(timezone.utc) - account_created_at

        if (
            account_age.days < self.config.new_account_days
            and task_value > self.config.new_account_max_value
        ):
            return self._create_alert(
                signal=FraudSignal.NEW_ACCOUNT_HIGH_VALUE,
                risk_level=RiskLevel.MEDIUM,
                entities=[worker_id],
                evidence={
                    "account_age_days": account_age.days,
                    "task_value": task_value,
                    "max_value_for_new": self.config.new_account_max_value,
                    "threshold_days": self.config.new_account_days,
                },
            )

        return None

    # =========================================================================
    # Risk Scoring
    # =========================================================================

    def get_risk_score(
        self,
        entity_id: str,
    ) -> Tuple[RiskLevel, List[str], float]:
        """
        Calculate overall risk score for an entity.

        Combines signals from:
        - Alert history
        - Connection patterns
        - Behavioral indicators

        Args:
            entity_id: Entity to score

        Returns:
            Tuple of (RiskLevel, list of reasons, numeric score)
        """
        profile = self._profiles.get(entity_id)
        if not profile:
            return RiskLevel.LOW, ["No profile history"], 0.0

        score = 0.0
        reasons: List[str] = []

        # Factor 1: Alert count and severity
        alert_score = 0.0
        for alert_id in profile.alert_ids:
            alert = self._alerts.get(alert_id)
            if alert and not alert.resolved:
                severity_weights = {
                    RiskLevel.LOW: 0.1,
                    RiskLevel.MEDIUM: 0.25,
                    RiskLevel.HIGH: 0.5,
                    RiskLevel.CRITICAL: 1.0,
                }
                alert_score += severity_weights.get(alert.risk_level, 0.1)
                reasons.append(f"Unresolved {alert.signal.value} alert")

        score += min(alert_score, 1.0) * 0.4  # Cap at 40% from alerts

        # Factor 2: Multi-device
        if profile.device_count > 1:
            device_risk = min(
                (profile.device_count - 1) / self.config.max_devices_per_worker,
                1.0
            )
            score += device_risk * self.config.weight_multi_device
            if device_risk > 0.5:
                reasons.append(f"{profile.device_count} devices used")

        # Factor 3: Connection concentration
        if profile.connected_entities:
            max_connection = max(profile.connected_entities.values())
            if max_connection >= self.config.suspicious_pairing_count:
                connection_risk = min(
                    max_connection / (self.config.suspicious_pairing_count * 2),
                    1.0
                )
                score += connection_risk * self.config.weight_collusion
                reasons.append(f"High connection concentration ({max_connection})")

        # Factor 4: New account
        if profile.is_new_account:
            score += 0.1 * self.config.weight_account
            reasons.append("New account")

        # Determine risk level
        if score >= 0.7:
            level = RiskLevel.CRITICAL
        elif score >= 0.5:
            level = RiskLevel.HIGH
        elif score >= 0.25:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        # Update profile
        profile.risk_score = score

        return level, reasons, score

    # =========================================================================
    # Wallet Management
    # =========================================================================

    def register_wallet(
        self,
        entity_id: str,
        wallet_address: str,
        entity_type: str = "worker",
    ) -> Optional[FraudAlert]:
        """
        Register a wallet address for an entity.

        Checks for wallet clustering (same wallet used by multiple entities).

        Args:
            entity_id: Entity identifier
            wallet_address: Wallet address to register
            entity_type: 'worker' or 'agent'

        Returns:
            FraudAlert if wallet already associated with other entity
        """
        wallet_normalized = wallet_address.lower()
        profile = self._get_or_create_profile(entity_id, entity_type)

        # Check if wallet is already used by another entity
        existing_entities = self._wallet_to_entities.get(wallet_normalized, set())
        other_entities = existing_entities - {entity_id}

        alert = None
        if other_entities:
            alert = self._create_alert(
                signal=FraudSignal.WALLET_CLUSTERING,
                risk_level=RiskLevel.CRITICAL,
                entities=[entity_id] + list(other_entities),
                evidence={
                    "wallet_address": wallet_address,
                    "claiming_entity": entity_id,
                    "existing_entities": list(other_entities),
                },
            )

        # Register wallet (even if already used by another entity)
        # This allows check_collusion to detect shared wallets later
        profile.wallet_addresses.add(wallet_normalized)
        self._wallet_to_entities[wallet_normalized].add(entity_id)

        return alert

    # =========================================================================
    # Alert Management
    # =========================================================================

    def resolve_alert(
        self,
        alert_id: str,
        resolution: str,
        resolved_by: str,
    ) -> bool:
        """
        Resolve a fraud alert.

        Args:
            alert_id: Alert to resolve
            resolution: Resolution description
            resolved_by: Admin/system identifier

        Returns:
            True if resolved, False if not found
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return False

        alert.resolved = True
        alert.resolution = resolution
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = resolved_by

        logger.info(
            f"Alert {alert_id} resolved by {resolved_by}: {resolution}"
        )

        return True

    def get_alerts(
        self,
        entity_id: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        include_resolved: bool = False,
        limit: int = 100,
    ) -> List[FraudAlert]:
        """
        Get alerts with optional filtering.

        Args:
            entity_id: Filter by entity
            risk_level: Filter by minimum risk level
            include_resolved: Include resolved alerts
            limit: Maximum alerts to return

        Returns:
            List of matching FraudAlerts
        """
        alerts = list(self._alerts.values())

        # Filter by entity
        if entity_id:
            alerts = [a for a in alerts if entity_id in a.entities]

        # Filter by risk level
        if risk_level:
            level_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
            min_idx = level_order.index(risk_level)
            alerts = [a for a in alerts if level_order.index(a.risk_level) >= min_idx]

        # Filter resolved
        if not include_resolved:
            alerts = [a for a in alerts if not a.resolved]

        # Sort by severity and time
        alerts.sort(
            key=lambda a: (
                -[RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL].index(a.risk_level),
                -a.detected_at.timestamp(),
            )
        )

        return alerts[:limit]

    def get_entity_profile(self, entity_id: str) -> Optional[EntityProfile]:
        """Get profile for an entity."""
        return self._profiles.get(entity_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get fraud detection statistics."""
        unresolved_alerts = [a for a in self._alerts.values() if not a.resolved]

        return {
            "total_profiles": len(self._profiles),
            "total_alerts": len(self._alerts),
            "unresolved_alerts": len(unresolved_alerts),
            "alerts_by_level": {
                level.value: len([a for a in unresolved_alerts if a.risk_level == level])
                for level in RiskLevel
            },
            "alerts_by_signal": {
                signal.value: len([a for a in unresolved_alerts if a.signal == signal])
                for signal in FraudSignal
            },
            "unique_ips_tracked": len(self._ip_to_entities),
            "unique_wallets_tracked": len(self._wallet_to_entities),
            "unique_devices_tracked": len(self._device_to_workers),
        }

    # =========================================================================
    # Batch Analysis
    # =========================================================================

    def analyze_task_batch(
        self,
        tasks: List[TaskRecord],
    ) -> List[FraudAlert]:
        """
        Analyze a batch of tasks for coordinated fraud.

        Useful for detecting patterns that only appear across multiple tasks.

        Args:
            tasks: List of task records to analyze

        Returns:
            List of detected fraud alerts
        """
        alerts: List[FraudAlert] = []

        # Group by agent
        by_agent: Dict[str, List[TaskRecord]] = defaultdict(list)
        for task in tasks:
            by_agent[task.agent_id].append(task)

        # Check each agent's tasks
        for agent_id, agent_tasks in by_agent.items():
            # Check for coordinated timing
            if len(agent_tasks) >= 3:
                sorted_tasks = sorted(agent_tasks, key=lambda t: t.created_at)
                for i in range(len(sorted_tasks) - 2):
                    t1, t2, t3 = sorted_tasks[i:i+3]
                    gap1 = (t2.created_at - t1.created_at).total_seconds()
                    gap2 = (t3.created_at - t2.created_at).total_seconds()

                    if (
                        gap1 < self.config.coordinated_timing_window_seconds
                        and gap2 < self.config.coordinated_timing_window_seconds
                    ):
                        alerts.append(self._create_alert(
                            signal=FraudSignal.COORDINATED_TIMING,
                            risk_level=RiskLevel.MEDIUM,
                            entities=[agent_id],
                            evidence={
                                "task_ids": [t1.task_id, t2.task_id, t3.task_id],
                                "time_gaps_seconds": [gap1, gap2],
                                "threshold_seconds": self.config.coordinated_timing_window_seconds,
                            },
                        ))
                        break

        return alerts
