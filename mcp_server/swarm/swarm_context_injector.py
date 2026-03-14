"""
SwarmContextInjector — Injects agent-specific context into prompts.

Each agent in the swarm operates with different capabilities, reputation,
budget constraints, and awareness of the broader swarm state. This module
builds personalized context blocks that get injected into agent prompts,
giving each agent situational awareness without overloading their context.

Context sections:
    - CapabilityProfile: Skills, tier, reliability from AutoJob data
    - ReputationBadge: On-chain ERC-8004 reputation summary
    - TaskFitness: How well the agent fits the current task
    - SwarmAwareness: What other agents are doing, fleet status
    - BudgetContext: Remaining budget, spending rate, warnings

Usage:
    injector = SwarmContextInjector(
        autojob_bridge=autojob_client,
        reputation_bridge=reputation_bridge,
        lifecycle_manager=lifecycle_manager,
    )

    # Build context for a specific agent
    ctx = injector.build_context("aurora", task=current_task)
    print(ctx.to_string())

    # Build for all agents
    batch = injector.build_batch(["aurora", "cipher", "echo"])

    # Estimate tokens
    print(f"Context size: ~{ctx.estimate_tokens()} tokens")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

TIER_DISPLAY = {
    "platinum": "🏆 Platinum",
    "gold": "🥇 Gold",
    "silver": "🥈 Silver",
    "bronze": "🥉 Bronze",
    "unranked": "⬜ Unranked",
}


def _score_bar(score: float, width: int = 10) -> str:
    """Render a score (0-100) as a visual bar.

    >>> _score_bar(75.0, 10)
    '████████░░'
    """
    if score < 0:
        score = 0.0
    if score > 100:
        score = 100.0
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _score_emoji(score: float) -> str:
    """Return a color emoji for a score (0-100).

    >>> _score_emoji(90)
    '🟢'
    """
    if score >= 80:
        return "🟢"
    if score >= 60:
        return "🔵"
    if score >= 40:
        return "🟡"
    if score >= 20:
        return "🟠"
    return "🔴"


# ---------------------------------------------------------------------------
# AgentContextBlock — structured context container
# ---------------------------------------------------------------------------

@dataclass
class AgentContextBlock:
    """Container for an agent's injected context sections."""

    agent_id: str
    sections: dict = field(default_factory=dict)  # section_name -> rendered string
    metadata: dict = field(default_factory=dict)

    def add_section(self, name: str, content: str) -> None:
        """Add a named section to the context block."""
        if content and content.strip():
            self.sections[name] = content.strip()

    def to_string(self) -> str:
        """Render all sections as a single context string."""
        if not self.sections:
            return ""
        parts = []
        for name, content in self.sections.items():
            parts.append(f"## {name}\n{content}")
        return "\n\n".join(parts)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "sections": dict(self.sections),
            "metadata": dict(self.metadata),
        }

    def estimate_tokens(self) -> int:
        """Rough token estimate (~4 chars per token)."""
        text = self.to_string()
        return len(text) // 4 if text else 0


# ---------------------------------------------------------------------------
# SwarmContextInjector
# ---------------------------------------------------------------------------

class SwarmContextInjector:
    """Builds personalized context blocks for swarm agents."""

    def __init__(
        self,
        autojob_bridge: Any = None,
        reputation_bridge: Any = None,
        lifecycle_manager: Any = None,
        coordinator: Any = None,
    ):
        self.autojob = autojob_bridge
        self.reputation = reputation_bridge
        self.lifecycle = lifecycle_manager
        self.coordinator = coordinator
        self._active_tasks: dict = {}  # agent_id -> list of task_ids

    def track_active_task(self, agent_id: str, task_id: str) -> None:
        """Track that an agent is working on a task."""
        self._active_tasks.setdefault(agent_id, []).append(task_id)

    def clear_active_task(self, agent_id: str, task_id: str) -> None:
        """Remove a task from an agent's active list."""
        if agent_id in self._active_tasks:
            self._active_tasks[agent_id] = [
                t for t in self._active_tasks[agent_id] if t != task_id
            ]

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_capability_profile(self, agent_id: str) -> str:
        """Build capability section from AutoJob leaderboard data."""
        if not self.autojob:
            return ""
        try:
            leaderboard = self.autojob.get_leaderboard()
            if not leaderboard:
                return ""

            # Find this agent in the leaderboard
            entry = None
            for item in leaderboard:
                wallet = item.get("wallet", item.get("agent_id", ""))
                if wallet == agent_id or item.get("agent_id") == agent_id:
                    entry = item
                    break

            if not entry:
                return ""

            lines = [f"**Agent:** {agent_id}"]

            tier = entry.get("tier", "unranked")
            tier_display = TIER_DISPLAY.get(tier, tier)
            lines.append(f"**Tier:** {tier_display}")

            # Skills
            skills = entry.get("top_skills", entry.get("skills", []))
            if skills:
                skill_list = ", ".join(skills[:5])
                lines.append(f"**Top Skills:** {skill_list}")

            # Reliability
            reliability = entry.get("reliability", entry.get("completion_rate", 0))
            if isinstance(reliability, (int, float)):
                pct = reliability * 100 if reliability <= 1 else reliability
                lines.append(f"**Reliability:** {_score_bar(pct)} {pct:.0f}%")

            # Completed tasks
            completed = entry.get("tasks_completed", entry.get("completed", 0))
            if completed:
                lines.append(f"**Tasks Completed:** {completed}")

            return "\n".join(lines)

        except Exception as e:
            logger.debug(f"AutoJob leaderboard error for {agent_id}: {e}")
            return ""

    def _build_reputation_badge(self, agent_id: str) -> str:
        """Build reputation section from ERC-8004 on-chain data."""
        if not self.reputation:
            return ""
        try:
            rep = self.reputation.compute_composite(agent_id)
            if not rep:
                return ""

            lines = []

            # Agent ID from rep
            if hasattr(rep, "agent_id") and rep.agent_id:
                lines.append(f"**Identity:** {rep.agent_id}")

            # Composite score
            composite = getattr(rep, "composite_score", getattr(rep, "score", 0))
            if composite:
                emoji = _score_emoji(composite)
                lines.append(f"**Reputation:** {emoji} {composite:.1f}/100 {_score_bar(composite)}")

            # Tier
            tier = getattr(rep, "tier", None)
            if tier:
                tier_display = TIER_DISPLAY.get(tier, tier)
                lines.append(f"**Tier:** {tier_display}")

            # Task track record
            completed = getattr(rep, "total_completed", getattr(rep, "em_completed", 0))
            if completed:
                lines.append(f"**Track Record:** {completed} tasks completed")

            # Chain ratings
            chain_count = getattr(rep, "chain_rating_count", 0)
            if chain_count:
                avg = getattr(rep, "chain_avg_rating", 0)
                lines.append(f"**On-Chain Ratings:** {chain_count} ratings, avg {avg:.1f}")

            return "\n".join(lines) if lines else ""

        except Exception as e:
            logger.debug(f"Reputation error for {agent_id}: {e}")
            return ""

    def _build_task_fitness(self, agent_id: str, task: Optional[dict] = None) -> str:
        """Build task fitness section showing how well agent fits current task."""
        if not task:
            return ""
        if not self.autojob and not self.reputation:
            return ""

        lines = []
        task_title = task.get("title", task.get("description", "Unknown task"))[:60]
        lines.append(f"**Current Task:** {task_title}")

        # Try to get match score from autojob
        match_score = None
        if self.autojob:
            try:
                enrichment = self.autojob.enrich_task(task)
                if enrichment:
                    rankings = enrichment.get("rankings", [])
                    for r in rankings:
                        if r.get("agent_id") == agent_id or r.get("wallet") == agent_id:
                            match_score = r.get("score", r.get("match_score"))
                            break
            except Exception:
                pass

        if match_score is not None:
            emoji = _score_emoji(match_score)
            lines.append(f"**Match Score:** {emoji} {match_score:.0f}/100 {_score_bar(match_score)}")

            if match_score >= 80:
                lines.append("**Guidance:** Excellent fit — you're well-suited for this task.")
            elif match_score >= 60:
                lines.append("**Guidance:** Good fit — proceed with confidence.")
            elif match_score >= 40:
                lines.append("**Guidance:** Moderate fit — consider if another agent might be better.")
            else:
                lines.append("**Guidance:** Weak fit — this task may be outside your strengths.")

        # Required skills from task
        required = task.get("required_skills", task.get("skills", []))
        if required:
            lines.append(f"**Required Skills:** {', '.join(required[:5])}")

        return "\n".join(lines) if lines else ""

    def _build_swarm_awareness(self, agent_id: str) -> str:
        """Build swarm awareness section showing what others are doing."""
        lines = []

        # Active tasks across the swarm
        all_active = {}
        for aid, tasks in self._active_tasks.items():
            if aid != agent_id and tasks:
                all_active[aid] = tasks

        if all_active:
            lines.append("**Active in Swarm:**")
            for aid, tasks in list(all_active.items())[:5]:
                lines.append(f"  • {aid}: {len(tasks)} task(s)")

        # Fleet status from lifecycle manager
        if self.lifecycle:
            try:
                status_counts = {}
                agents = getattr(self.lifecycle, "_agents", {})
                for aid, state in agents.items():
                    s = getattr(state, "status", state) if hasattr(state, "status") else str(state)
                    s = s.value if hasattr(s, "value") else str(s)
                    status_counts[s] = status_counts.get(s, 0) + 1

                if status_counts:
                    parts = [f"{v} {k}" for k, v in status_counts.items()]
                    lines.append(f"**Fleet Status:** {', '.join(parts)}")
            except Exception:
                pass

        return "\n".join(lines) if lines else ""

    def _build_budget_context(self, agent_id: str) -> str:
        """Build budget section showing remaining budget and warnings."""
        if not self.lifecycle:
            return ""

        try:
            agent = self.lifecycle.get_agent(agent_id)
            if not agent:
                return ""

            budget = getattr(agent, "budget", None)
            if not budget:
                return ""

            lines = []

            total = getattr(budget, "total_usd", getattr(budget, "daily_limit_usd", 0))
            spent = getattr(budget, "spent_usd", getattr(budget, "used_usd", 0))
            remaining = total - spent if total > 0 else 0

            if total > 0:
                usage_pct = (spent / total) * 100
                lines.append(f"**Budget:** ${spent:.2f} / ${total:.2f} ({usage_pct:.0f}% used)")
                lines.append(f"**Remaining:** ${remaining:.2f}")

                if usage_pct >= 90:
                    lines.append("⚠️ **WARNING:** Budget nearly exhausted!")
                elif usage_pct >= 70:
                    lines.append("⚡ **CAUTION:** Budget usage above 70%")

            return "\n".join(lines) if lines else ""

        except Exception as e:
            logger.debug(f"Budget context error for {agent_id}: {e}")
            return ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_context(
        self,
        agent_id: str,
        task: Optional[dict] = None,
    ) -> AgentContextBlock:
        """Build a complete context block for an agent."""
        block = AgentContextBlock(agent_id=agent_id)

        block.add_section("Capability Profile", self._build_capability_profile(agent_id))
        block.add_section("Reputation Badge", self._build_reputation_badge(agent_id))
        block.add_section("Task Fitness", self._build_task_fitness(agent_id, task))
        block.add_section("Swarm Awareness", self._build_swarm_awareness(agent_id))
        block.add_section("Budget Context", self._build_budget_context(agent_id))

        block.metadata["built_at"] = datetime.now(timezone.utc).isoformat()
        block.metadata["has_autojob"] = self.autojob is not None
        block.metadata["has_reputation"] = self.reputation is not None
        block.metadata["has_lifecycle"] = self.lifecycle is not None

        return block

    def build_batch(
        self,
        agent_ids: list,
        task: Optional[dict] = None,
    ) -> dict:
        """Build context blocks for multiple agents."""
        return {
            agent_id: self.build_context(agent_id, task)
            for agent_id in agent_ids
        }

    def status(self) -> dict:
        """Return injector status summary."""
        return {
            "autojob_connected": self.autojob is not None,
            "reputation_connected": self.reputation is not None,
            "lifecycle_connected": self.lifecycle is not None,
            "coordinator_connected": self.coordinator is not None,
            "active_tasks_tracked": sum(len(v) for v in self._active_tasks.values()),
            "agents_with_tasks": len(self._active_tasks),
        }
