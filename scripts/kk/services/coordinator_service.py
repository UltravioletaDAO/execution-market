"""
Karma Kadabra V2 — Phase 8: Coordinator Service

The coordinator agent's heartbeat action. On each wake cycle:

  1. Read all agent states from kk_swarm_state
  2. Identify idle, stale, and busy agents
  3. Browse EM for unassigned tasks
  4. Match tasks to idle agents based on skills
  5. Assign via kk_task_claims + kk_notifications
  6. Generate health summary

The coordinator does NOT execute tasks itself — it routes and monitors.

Usage:
  python coordinator_service.py                # Full coordination cycle
  python coordinator_service.py --dry-run      # Preview assignments
  python coordinator_service.py --summary      # Health summary only
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from em_client import AgentContext, EMClient, load_agent_context
from lib.swarm_state import (
    claim_task,
    get_agent_states,
    get_stale_agents,
    get_swarm_summary,
    send_notification,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("kk.coordinator")


# ---------------------------------------------------------------------------
# Skill matching
# ---------------------------------------------------------------------------


def load_agent_skills(workspaces_dir: Path, agent_name: str) -> set[str]:
    """Load an agent's skills from their workspace SOUL.md or skills data."""
    ws_dir = workspaces_dir / agent_name
    if not ws_dir.exists():
        ws_dir = workspaces_dir / f"kk-{agent_name}"
    if not ws_dir.exists():
        return set()

    # Try structured skills JSON first
    skills_file = ws_dir / "data" / "profile.json"
    if skills_file.exists():
        try:
            profile = json.loads(skills_file.read_text(encoding="utf-8"))
            return {s.get("skill", "").lower() for s in profile.get("top_skills", [])}
        except Exception:
            pass

    # Fallback: parse SOUL.md for skill lines
    soul_file = ws_dir / "SOUL.md"
    if soul_file.exists():
        try:
            text = soul_file.read_text(encoding="utf-8")
            skills = set()
            in_skills = False
            for line in text.splitlines():
                if "## Skills" in line:
                    in_skills = True
                    continue
                if in_skills and line.startswith("##"):
                    break
                if in_skills and line.startswith("- **"):
                    # Extract skill name from "- **SkillName** (Category)"
                    name = line.split("**")[1] if "**" in line else ""
                    if name:
                        skills.add(name.lower())
            return skills
        except Exception:
            pass

    return set()


def compute_skill_match(agent_skills: set[str], task_title: str, task_desc: str) -> float:
    """Compute match score between agent skills and task text.

    Returns 0.0-1.0 score.
    """
    if not agent_skills:
        return 0.1  # Minimal score for agents without skills data

    text = (task_title + " " + task_desc).lower()
    matches = sum(1 for skill in agent_skills if skill in text)

    if matches == 0:
        # Check for KK-tagged tasks (any agent can take these)
        if "[kk" in text:
            return 0.3
        return 0.0

    return min(1.0, matches / max(len(agent_skills), 1))


# ---------------------------------------------------------------------------
# Coordination cycle
# ---------------------------------------------------------------------------


async def coordination_cycle(
    workspaces_dir: Path,
    client: EMClient,
    dry_run: bool = False,
) -> dict:
    """Execute one coordinator cycle.

    Returns dict with assignments and health summary.
    """
    logger.info("Starting coordination cycle")

    # 1. Read all agent states
    all_agents = await get_agent_states()
    idle_agents = [a for a in all_agents if a.get("status") == "idle"]
    stale_agents = await get_stale_agents(stale_minutes=30)

    logger.info(f"  Agents: {len(all_agents)} total, {len(idle_agents)} idle, {len(stale_agents)} stale")

    # 2. Browse EM for unassigned tasks
    try:
        available_tasks = await client.browse_tasks(status="published", limit=30)
    except Exception as e:
        logger.error(f"  Browse tasks failed: {e}")
        available_tasks = []

    logger.info(f"  Available tasks: {len(available_tasks)}")

    # 3. Match and assign
    assignments = []
    for task in available_tasks:
        task_id = task.get("id", "")
        title = task.get("title", "")
        desc = task.get("instructions", task.get("description", ""))
        bounty = task.get("bounty_usd", 0)

        # Skip own tasks (coordinator should not assign itself)
        if task.get("agent_wallet", "") == client.agent.wallet_address:
            continue

        # Find best idle agent for this task
        best_agent = None
        best_score = 0.0

        for agent in idle_agents:
            agent_name = agent.get("agent_name", "")
            # Skip system agents (they have specific roles)
            if agent_name in ("kk-coordinator", "kk-validator"):
                continue

            agent_skills = load_agent_skills(workspaces_dir, agent_name)
            score = compute_skill_match(agent_skills, title, desc)

            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent and best_score > 0.0:
            agent_name = best_agent.get("agent_name", "")

            if dry_run:
                logger.info(f"  [DRY RUN] Would assign '{title}' to {agent_name} (score={best_score:.2f})")
                assignments.append({
                    "task_id": task_id,
                    "title": title,
                    "agent": agent_name,
                    "score": best_score,
                    "dry_run": True,
                })
            else:
                # Atomic claim
                claimed = await claim_task(task_id, agent_name)
                if claimed:
                    # Notify agent
                    notification = json.dumps({
                        "type": "task_assignment",
                        "task_id": task_id,
                        "title": title,
                        "bounty_usd": bounty,
                    })
                    await send_notification(agent_name, "kk-coordinator", notification)

                    logger.info(f"  Assigned '{title}' to {agent_name} (score={best_score:.2f})")
                    assignments.append({
                        "task_id": task_id,
                        "title": title,
                        "agent": agent_name,
                        "score": best_score,
                    })

                    # Remove agent from idle pool
                    idle_agents = [a for a in idle_agents if a.get("agent_name") != agent_name]
                else:
                    logger.info(f"  Task '{title}' already claimed — skipping")

    # 4. Health summary
    summary = await get_swarm_summary()

    # 5. Stale agent warnings
    if stale_agents:
        logger.warning(f"  Stale agents ({len(stale_agents)}):")
        for sa in stale_agents:
            logger.warning(f"    {sa['agent_name']}: {sa.get('minutes_stale', '?')} min since last heartbeat")

    return {
        "assignments": assignments,
        "summary": summary,
        "stale_agents": [s["agent_name"] for s in stale_agents],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    parser = argparse.ArgumentParser(description="KK Coordinator Service")
    parser.add_argument("--workspace", type=str, default=None)
    parser.add_argument("--workspaces-dir", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", action="store_true", help="Health summary only")
    args = parser.parse_args()

    base = Path(__file__).parent.parent
    workspace_dir = (
        Path(args.workspace)
        if args.workspace
        else base / "data" / "workspaces" / "kk-coordinator"
    )
    workspaces_dir = (
        Path(args.workspaces_dir)
        if args.workspaces_dir
        else base / "data" / "workspaces"
    )

    if workspace_dir.exists():
        agent = load_agent_context(workspace_dir)
    else:
        agent = AgentContext(
            name="kk-coordinator",
            wallet_address="",
            workspace_dir=workspace_dir,
        )

    print(f"\n{'=' * 60}")
    print(f"  Karma Kadabra — Coordinator")
    print(f"  Agent: {agent.name}")
    if args.dry_run:
        print(f"  ** DRY RUN **")
    print(f"{'=' * 60}\n")

    client = EMClient(agent)

    try:
        if args.summary:
            summary = await get_swarm_summary()
            print(json.dumps(summary, indent=2))
        else:
            result = await coordination_cycle(workspaces_dir, client, dry_run=args.dry_run)
            print(f"\n  Assignments: {len(result['assignments'])}")
            for a in result["assignments"]:
                status = "[DRY RUN]" if a.get("dry_run") else "[ASSIGNED]"
                print(f"    {status} {a['title'][:40]} -> {a['agent']} (score={a['score']:.2f})")
            if result["stale_agents"]:
                print(f"\n  Stale agents: {', '.join(result['stale_agents'])}")
            print(f"\n  Swarm summary: {json.dumps(result['summary'], indent=2)}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
