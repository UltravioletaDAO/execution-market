"""
KarmaCadabra V2 Swarm Coordination

Eighteen core components:
- ReputationBridge: Connects on-chain ERC-8004 reputation with internal scoring
- LifecycleManager: Manages agent states, budgets, and health
- SwarmOrchestrator: Routes tasks to the best available agent
- AutoJobClient: Enriches scoring with AutoJob's evidence-based intelligence
- SwarmCoordinator: Top-level operational controller (integrates all above)
- EventListener: Polls EM API for task lifecycle events (feedback input)
- EvidenceParser: Extracts Skill DNA from task completion evidence (feedback learning)
- HeartbeatHandler: Condensed coordination cycle for OpenClaw heartbeat integration
- SwarmBootstrap: Production-aware coordinator initialization from live data
- StrategyEngine: Intelligent multi-strategy routing decision layer
- SwarmAnalytics: Comprehensive performance analytics and decision support
- SwarmDaemon: Production-ready continuous coordination loop
- AcontextAdapter: Memory and observability integration (local file-based)
- ConfigManager: Production configuration system (files, env vars, presets, validation)
- ContextInjector: Agent-specific context injection (capabilities, reputation, budget)
- HealthDashboard: Real-time health monitoring across all swarm dependencies
- MCP Tools: MCP protocol tools for agent-native swarm interaction
- SealIssuer: Automated describe-net seal issuance on reputation milestones
"""

from .reputation_bridge import ReputationBridge
from .lifecycle_manager import LifecycleManager, AgentState
from .orchestrator import SwarmOrchestrator
from .autojob_client import AutoJobClient, EnrichedOrchestrator
from .coordinator import SwarmCoordinator, EMApiClient
from .event_listener import EventListener
from .evidence_parser import EvidenceParser, SkillDNA, WorkerRegistry
from .heartbeat_handler import SwarmHeartbeatHandler, HeartbeatReport
from .bootstrap import SwarmBootstrap, BootstrapResult
from .strategy_engine import StrategyEngine
from .analytics import SwarmAnalytics, TaskEvent, TimeWindow
from .daemon import SwarmDaemon, DaemonConfig, CycleResult
from .config_manager import SwarmConfigManager
from .swarm_context_injector import SwarmContextInjector, AgentContextBlock
from .swarm_health_dashboard import SwarmHealthDashboard, HealthReport, HealthStatus
from .mcp_tools import register_swarm_tools
from .seal_issuer import SealIssuer, SealIssuance, SealType, WorkerPerformance

__all__ = [
    "ReputationBridge",
    "LifecycleManager",
    "AgentState",
    "SwarmOrchestrator",
    "AutoJobClient",
    "EnrichedOrchestrator",
    "SwarmCoordinator",
    "EMApiClient",
    "EventListener",
    "EvidenceParser",
    "SkillDNA",
    "WorkerRegistry",
    "SwarmHeartbeatHandler",
    "HeartbeatReport",
    "SwarmBootstrap",
    "BootstrapResult",
    "StrategyEngine",
    "SwarmAnalytics",
    "TaskEvent",
    "TimeWindow",
    "SwarmDaemon",
    "DaemonConfig",
    "CycleResult",
    "SwarmConfigManager",
    "SwarmContextInjector",
    "AgentContextBlock",
    "SwarmHealthDashboard",
    "HealthReport",
    "HealthStatus",
    "register_swarm_tools",
    "SealIssuer",
    "SealIssuance",
    "SealType",
    "WorkerPerformance",
]
