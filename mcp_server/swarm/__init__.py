"""
KarmaCadabra V2 Swarm Coordination

Twenty core components:
- ReputationBridge: Connects on-chain ERC-8004 reputation with internal scoring
- LifecycleManager: Manages agent states, budgets, and health
- SwarmOrchestrator: Routes tasks to the best available agent
- AutoJobClient: Enriches scoring with AutoJob's evidence-based intelligence
- SwarmCoordinator: Top-level operational controller (integrates all above)
- SwarmScheduler: Deadline-aware priority scheduling & dynamic strategy selection
- SwarmRunner: Production daemon loop — 7-phase coordination cycle
- EventListener: Polls EM API for task lifecycle events (feedback input)
- EvidenceParser: Extracts Skill DNA from task completion evidence (feedback learning)
- HeartbeatHandler: Condensed coordination cycle for OpenClaw heartbeat integration
- SwarmBootstrap: Production-aware coordinator initialization from live data
- StatePersistence: Durable state + retry backoff for crash recovery
- SwarmAnalytics: Metrics aggregation, trend analysis, and fleet alerting
- SealBridge: Analytics-to-on-chain reputation pipeline (describe-net integration)
- MCP Tools: MCP protocol tools for agent-native swarm interaction
- AcontextAdapter: IRC-based coordination via Acontext (V2: TTL locks, auctions, heartbeats)
- SwarmDashboard: Real-time fleet health monitoring (single pane of glass)
- ConfigManager: Centralized configuration with validation and hot reload
- FeedbackPipeline: Closes the feedback loop from completions to intelligence
"""

from .reputation_bridge import ReputationBridge
from .lifecycle_manager import LifecycleManager, AgentState
from .orchestrator import SwarmOrchestrator
from .autojob_client import AutoJobClient, EnrichedOrchestrator
from .coordinator import SwarmCoordinator, EMApiClient
from .runner import SwarmRunner, RunMode, CycleResult
from .event_listener import EventListener
from .evidence_parser import EvidenceParser, SkillDNA, WorkerRegistry
from .heartbeat_handler import SwarmHeartbeatHandler, HeartbeatReport
from .bootstrap import SwarmBootstrap, BootstrapResult, DEFAULT_AGENTS
from .state_persistence import (
    SwarmStatePersistence,
    PersistedState,
    RetryBackoff,
)
from .analytics import SwarmAnalytics, TaskEvent, AgentMetrics, FleetSnapshot, Alert
from .seal_bridge import (
    SealBridge,
    SealRecommendation,
    SealProfile,
    SealQuadrant,
    BatchSealRequest,
)
from .scheduler import (
    SwarmScheduler,
    CircuitBreaker,
    RetryScheduler,
    AgentLoadBalancer,
    UrgencyLevel,
)
from .dashboard import (
    SwarmDashboard,
    DashboardSnapshot,
    AgentStatus,
    FleetStatus,
    Severity,
    HealthReport,
)
from .config_manager import (
    ConfigManager,
    SwarmConfig,
    Environment,
    ConfigValidationError,
    validate_config,
)
from .feedback_pipeline import FeedbackPipeline, CompletionFeedback, PipelineRunResult
from .mcp_tools import register_swarm_tools

__all__ = [
    "ReputationBridge",
    "LifecycleManager",
    "AgentState",
    "SwarmOrchestrator",
    "AutoJobClient",
    "EnrichedOrchestrator",
    "SwarmCoordinator",
    "EMApiClient",
    "SwarmRunner",
    "RunMode",
    "CycleResult",
    "EventListener",
    "EvidenceParser",
    "SkillDNA",
    "WorkerRegistry",
    "SwarmHeartbeatHandler",
    "HeartbeatReport",
    "SwarmBootstrap",
    "BootstrapResult",
    "DEFAULT_AGENTS",
    "SwarmStatePersistence",
    "PersistedState",
    "RetryBackoff",
    "SwarmAnalytics",
    "TaskEvent",
    "AgentMetrics",
    "FleetSnapshot",
    "Alert",
    "SealBridge",
    "SealRecommendation",
    "SealProfile",
    "SealQuadrant",
    "BatchSealRequest",
    "SwarmScheduler",
    "CircuitBreaker",
    "RetryScheduler",
    "AgentLoadBalancer",
    "UrgencyLevel",
    "SwarmDashboard",
    "DashboardSnapshot",
    "AgentStatus",
    "FleetStatus",
    "Severity",
    "HealthReport",
    "ConfigManager",
    "SwarmConfig",
    "Environment",
    "ConfigValidationError",
    "validate_config",
    "FeedbackPipeline",
    "CompletionFeedback",
    "PipelineRunResult",
    "register_swarm_tools",
]
