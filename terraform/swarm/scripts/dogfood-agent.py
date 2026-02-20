#!/usr/bin/env python3
"""
KarmaCadabra Dogfood Agent Runner
==================================
Run a single KC agent locally against Execution Market production.
Tests the complete agent lifecycle with real wallet authentication.

Usage:
    # Run builder agent (default)
    python dogfood-agent.py

    # Run specific archetype
    python dogfood-agent.py --archetype explorer --name blaze

    # Create a test task
    python dogfood-agent.py --create-task

    # Run all 8 archetypes in sequence
    python dogfood-agent.py --all-archetypes
"""

import argparse
import asyncio
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add KC repo to path
KC_REPO = Path(__file__).resolve().parents[3] / ".." / "ultravioletadao" / "karmacadabra"
if KC_REPO.exists():
    sys.path.insert(0, str(KC_REPO))
else:
    # Try relative from execution-market root
    EM_ROOT = Path(__file__).resolve().parents[2]
    KC_ALT = EM_ROOT.parent / "ultravioletadao" / "karmacadabra"
    if KC_ALT.exists():
        sys.path.insert(0, str(KC_ALT))

try:
    from em_bridge.wallet import AgentWalletManager, generate_mnemonic
    from em_bridge.auth import ERC8128Auth
    from em_bridge.client import EMBridgeClient
    from em_bridge.discovery import TaskMatcher
    from em_bridge.scheduler import AgentScheduler, AgentPortfolio
    from em_bridge.archetypes import get_all_archetypes, get_sell_skills, get_buy_needs
except ImportError as e:
    print(f"ERROR: Cannot import em_bridge: {e}")
    print(f"Ensure karmacadabra repo is at: {KC_REPO}")
    print("Or install: pip install -e path/to/karmacadabra")
    sys.exit(1)


# Agent names for each archetype (matching terraform/swarm/config/agent-wallets.json)
AGENT_NAMES = {
    "explorer": "blaze",
    "builder": "aurora",
    "connector": "cipher",
    "analyst": "drift",
    "creator": "echo",
    "guardian": "flux",
    "strategist": "horizon",
    "teacher": "ion",
}


def get_mnemonic():
    """Get swarm mnemonic from env or generate new one."""
    # Check env first
    mnemonic = os.getenv("KC_SWARM_MNEMONIC")
    if mnemonic:
        return mnemonic
    
    # Check local file
    mnemonic_file = Path.home() / ".kc-swarm-mnemonic"
    if mnemonic_file.exists():
        return mnemonic_file.read_text().strip()
    
    # Generate new
    mnemonic = generate_mnemonic()
    mnemonic_file.write_text(mnemonic)
    mnemonic_file.chmod(0o600)
    print(f"Generated new swarm mnemonic → {mnemonic_file}")
    return mnemonic


async def run_agent(archetype: str, name: str, create_task: bool = False):
    """Run a single KC agent against production."""
    print(f"\n{'=' * 60}")
    print(f"  KC Dogfood Agent: {name} ({archetype})")
    print(f"{'=' * 60}")
    
    mnemonic = get_mnemonic()
    wm = AgentWalletManager(mnemonic)
    addr, pk = wm.get_wallet(archetype)
    
    print(f"  Wallet: {addr}")
    print(f"  API: https://api.execution.market")
    
    async with EMBridgeClient(pk, name, archetype) as client:
        # 1. Health check
        health = await client.health_check()
        status = "✅" if health["status"] == "healthy" else "❌"
        print(f"\n  {status} Health: {health['status']} (uptime {health['uptime_seconds']:.0f}s)")
        
        # 2. Auth test
        info = client.get_agent_info()
        print(f"  ✅ Auth: ERC-8128 wallet signing active")
        
        # 3. Task discovery
        all_tasks = await client.get_my_tasks()
        h2a_tasks = await client.discover_tasks()
        print(f"  ✅ Discovery: {len(all_tasks)} total tasks, {len(h2a_tasks)} H2A tasks")
        
        # 4. Scoring
        matcher = TaskMatcher(archetype)
        skills = get_sell_skills(archetype)
        needs = get_buy_needs(archetype)
        print(f"  ✅ Skills: {len(skills)} sell, {len(needs)} buy")
        
        if all_tasks:
            scored = matcher.filter_tasks(all_tasks, min_score=0)
            print(f"\n  📊 Top tasks for {archetype}:")
            for task, score in scored[:5]:
                emoji = "🟢" if score.total_score >= 60 else "🟡" if score.total_score >= 40 else "🔴"
                print(f"    {emoji} [{score.total_score:5.1f}] {task.title[:50]}")
        
        # 5. Scheduler status
        portfolio = AgentPortfolio(
            max_concurrent_tasks=3,
            max_budget_per_task=Decimal("5.00"),
            total_budget_limit=Decimal("25.00"),
        )
        scheduler = AgentScheduler(client, portfolio)
        status = scheduler.get_portfolio_status()
        print(f"\n  ⏰ Portfolio: {status['available_slots']} slots, "
              f"${status['max_budget_per_task']}/task max")
        
        # 6. Optionally create a task
        if create_task:
            print(f"\n  📝 Creating test task...")
            task = await client.post_task(
                title=f"[KC DOGFOOD] {archetype.title()} Agent {name} Test",
                description=f"Automated dogfood test from KC {archetype} agent {name}. "
                           f"Validates wallet auth → task publish pipeline.",
                bounty_usd=Decimal("0.10"),
                category="simple_action",
                deadline_hours=1,
                evidence_required=["text_response"],
                payment_network="base"
            )
            print(f"  ✅ Task created: {task.id}")
            print(f"     Status: {task.status.value}")
            print(f"     Escrow: {task.escrow_tx}")
    
    print(f"\n  {'=' * 58}")
    print(f"  ✅ Agent {name} ({archetype}) — All systems operational")
    print(f"  {'=' * 58}\n")


async def run_all_archetypes(create_task: bool = False):
    """Run all 8 archetypes sequentially."""
    print("\n" + "=" * 60)
    print("  KarmaCadabra Full Swarm Dogfood")
    print("  Testing all 8 archetypes against production")
    print("=" * 60)
    
    results = {}
    for archetype in get_all_archetypes():
        name = AGENT_NAMES.get(archetype, archetype)
        try:
            await run_agent(archetype, name, create_task=create_task)
            results[archetype] = "✅"
        except Exception as e:
            print(f"\n  ❌ {archetype} failed: {e}")
            results[archetype] = f"❌ {e}"
    
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for arch, result in results.items():
        name = AGENT_NAMES.get(arch, arch)
        print(f"  {result} {name:10s} ({arch})")
    
    passed = sum(1 for r in results.values() if r == "✅")
    print(f"\n  {passed}/{len(results)} agents operational")


def main():
    parser = argparse.ArgumentParser(description="KC Dogfood Agent Runner")
    parser.add_argument("--archetype", default="builder", 
                       choices=list(get_all_archetypes()),
                       help="Agent archetype (default: builder)")
    parser.add_argument("--name", default=None,
                       help="Agent name (default: auto from archetype)")
    parser.add_argument("--create-task", action="store_true",
                       help="Create a test task on production ($0.10)")
    parser.add_argument("--all-archetypes", action="store_true",
                       help="Test all 8 archetypes")
    
    args = parser.parse_args()
    
    name = args.name or AGENT_NAMES.get(args.archetype, args.archetype)
    
    if args.all_archetypes:
        asyncio.run(run_all_archetypes(create_task=args.create_task))
    else:
        asyncio.run(run_agent(args.archetype, name, create_task=args.create_task))


if __name__ == "__main__":
    main()
