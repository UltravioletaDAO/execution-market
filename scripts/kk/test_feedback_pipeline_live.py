#!/usr/bin/env python3
"""
Live test of the FeedbackPipeline against the production EM API.

Fetches real completed tasks, processes them through the feedback pipeline,
and generates worker intelligence from actual evidence submissions.

Usage:
    python3 scripts/kk/test_feedback_pipeline_live.py
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "mcp_server"))

from swarm.feedback_pipeline import FeedbackPipeline  # noqa: E402


def main():
    print("=" * 70)
    print("  FEEDBACK PIPELINE — LIVE INTEGRATION TEST")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # Create pipeline with temp state dir for this test
    state_dir = Path(__file__).parent / "data" / "feedback_live_test"
    state_dir.mkdir(parents=True, exist_ok=True)

    pipeline = FeedbackPipeline.create(
        em_api_url="https://api.execution.market",
        state_dir=str(state_dir),
    )

    # Test 1: Fetch completed tasks
    print("\n🔍 Test 1: Fetching completed tasks from EM API...")
    start = time.monotonic()
    completed = pipeline._fetch_completed_tasks()
    fetch_time = (time.monotonic() - start) * 1000
    print(f"   Found {len(completed)} completed tasks ({fetch_time:.0f}ms)")

    if not completed:
        print("   ⚠️  No completed tasks found — checking other statuses...")
        # Try approved tasks too (those have evidence)
        for status in ["approved", "in_review"]:
            result = pipeline._em_request(
                "GET", f"/api/v1/tasks?status={status}&limit=50"
            )
            if result:
                tasks = (
                    result
                    if isinstance(result, list)
                    else result.get("tasks", result.get("data", []))
                )
                print(f"   Found {len(tasks)} tasks with status={status}")
                if tasks:
                    completed.extend(tasks)

    if not completed:
        print("\n❌ No tasks with evidence found. Cannot run live test.")
        print("   This is normal if the marketplace is new or all tasks are pending.")
        return

    # Test 2: Process completions
    print(
        f"\n🔄 Test 2: Processing {min(len(completed), 20)} tasks through pipeline..."
    )
    tasks_to_process = completed[:20]

    processed = 0
    succeeded = 0
    workers_seen = set()
    quality_counts = {}

    for task in tasks_to_process:
        task_id = task.get("id", "?")
        task.get("title", "?")[:50]

        feedback = pipeline.process_completion_from_task(task)
        processed += 1

        if feedback.error:
            print(f"   ⚠️  {task_id}: {feedback.error}")
        else:
            succeeded += 1
            workers_seen.add(feedback.worker_id)
            quality_counts[feedback.quality.value] = (
                quality_counts.get(feedback.quality.value, 0) + 1
            )
            print(
                f"   ✅ {task_id}: quality={feedback.quality.value}, "
                f"score={feedback.quality_score:.2f}, "
                f"evidence={feedback.evidence_count}, "
                f"signals={feedback.skill_signals_count}, "
                f"worker={feedback.worker_id[:20]}..."
            )

    print("\n📊 Processing results:")
    print(f"   Processed: {processed}")
    print(f"   Succeeded: {succeeded}")
    print(f"   Workers seen: {len(workers_seen)}")
    print(f"   Quality distribution: {quality_counts}")

    # Test 3: Worker profiles
    print("\n👤 Test 3: Worker Profiles")
    for worker_id in list(workers_seen)[:5]:
        profile = pipeline.get_worker_profile(worker_id)
        if profile:
            dna = profile.get("skill_dna", {})
            rep = profile.get("reputation", {})
            composite = profile.get("composite_score", {})

            print(f"\n   Worker: {worker_id[:30]}...")
            print(f"     Tasks: {dna.get('task_count', 0)}")
            print(f"     Avg quality: {dna.get('avg_quality', 0):.3f}")
            top_skills = dna.get("top_skills", [])
            if top_skills:
                skills_str = ", ".join(
                    f"{s['skill']}={s['score']:.2f}" for s in top_skills[:3]
                )
                print(f"     Top skills: {skills_str}")
            if rep:
                print(f"     Bayesian score: {rep.get('bayesian_score', 0):.3f}")
                print(f"     Success rate: {rep.get('success_rate', 0):.3f}")
            if composite:
                print(
                    f"     Composite: {composite.get('total', 0):.1f} (tier={composite.get('tier', '?')})"
                )

    # Test 4: Leaderboard
    print("\n🏆 Test 4: Worker Leaderboard")
    leaderboard = pipeline.get_leaderboard(top_n=10)
    for i, entry in enumerate(leaderboard, 1):
        wid = entry["worker_id"][:25]
        print(
            f"   #{i}: {wid}... "
            f"score={entry['composite_score']:.1f} "
            f"tier={entry['tier']} "
            f"tasks={entry['tasks']} "
            f"quality={entry['avg_quality']:.2f}"
        )

    # Test 5: Pipeline stats
    print("\n📈 Test 5: Pipeline Stats")
    stats = pipeline.get_stats()
    print(f"   Workers: {stats['workers']['total']}")
    print(f"   Total tasks: {stats['workers']['total_tasks']}")
    print(f"   Avg quality: {stats['workers']['avg_quality']:.3f}")
    print(f"   Avg bayesian: {stats['reputations']['avg_bayesian_score']:.3f}")
    print(f"   Avg success rate: {stats['reputations']['avg_success_rate']:.3f}")

    # Save state for future use
    pipeline._save_state()
    pipeline._save_worker_registry()
    print(f"\n💾 State saved to {state_dir}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  RESULT: {'🟢 SUCCESS' if succeeded > 0 else '🔴 NO DATA PROCESSED'}")
    print(f"  {succeeded}/{processed} tasks processed successfully")
    print(f"  {len(workers_seen)} unique workers profiled")
    print(f"  {len(leaderboard)} workers in leaderboard")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
