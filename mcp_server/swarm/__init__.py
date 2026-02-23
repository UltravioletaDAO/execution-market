"""
KarmaKadabra V2 Swarm Module

Orchestrates autonomous AI agent swarms on Execution Market.

Components:
- reputation_bridge: Bridges EM reputation ↔ ERC-8004 on-chain reputation
- lifecycle_manager: Manages agent lifecycle (boot → active → sleep → wake)
- swarm_orchestrator: Coordinates multi-agent task distribution and economics

Usage:
    >>> from mcp_server.swarm import SwarmOrchestrator, LifecycleManager, ReputationBridge
    >>> 
    >>> bridge = ReputationBridge(network="base")
    >>> lifecycle = LifecycleManager(max_agents=48)
    >>> orchestrator = SwarmOrchestrator(lifecycle=lifecycle, bridge=bridge)
    >>> 
    >>> # Register agents
    >>> orchestrator.register_agent("agent_aurora", wallet="0x...", personality="explorer")
    >>> 
    >>> # Distribute a task to the best-matched agent
    >>> assignment = await orchestrator.assign_task(task_id="task_abc")
"""

from .reputation_bridge import ReputationBridge, BridgedReputation
from .lifecycle_manager import LifecycleManager, AgentState, AgentStatus
from .swarm_orchestrator import SwarmOrchestrator, TaskAssignment, AgentProfile

__all__ = [
    "ReputationBridge",
    "BridgedReputation",
    "LifecycleManager",
    "AgentState",
    "AgentStatus",
    "SwarmOrchestrator",
    "TaskAssignment",
    "AgentProfile",
]
