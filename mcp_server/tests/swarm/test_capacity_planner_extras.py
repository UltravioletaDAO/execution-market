"""
Test Suite: CapacityPlanner — Workforce Intelligence Engine
=============================================================

The CapacityPlanner forecasts skill gaps, capacity needs, and bottlenecks
in the worker pool. The swarm coordinator uses this to proactively recruit
before demand spikes, identify single-point-of-failure workers, and
balance workload distribution.

Tests cover:
    1. Skill gap analysis (demand vs supply, severity classification)
    2. Capacity forecasting (utilization, headroom, status)
    3. Concentration risk (HHI, Gini, top-worker share)
    4. Workload balance (per-worker stats, overloaded/underutilized)
    5. Recruitment plan (combining all analyses)
    6. Full report (comprehensive dashboard output)
    7. Helper functions (skill extraction, Gini coefficient)
    8. Edge cases (empty inputs, single worker, perfect balance)
"""

from mcp_server.swarm.capacity_planner import (
    CapacityPlanner,
    SkillDemand,
    WorkloadEntry,
    TARGET_UTILIZATION_LOW,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════


def _agents(count=5, skills=None):
    """Create a list of agent dicts with skills."""
    agents = []
    default_skills = skills or {
        0: {"photo": 0.8, "verify": 0.7},
        1: {"delivery": 0.9, "photo": 0.6},
        2: {"survey": 0.5, "research": 0.8},
        3: {"photo": 0.9, "delivery": 0.7},
        4: {"translate": 0.6, "write": 0.5},
    }
    for i in range(count):
        agent_skills = default_skills.get(i, {"general": 0.5})
        agents.append(
            {
                "agent_id": i,
                "wallet": f"0x{i:040x}",
                "skills": {s: {"confidence": q} for s, q in agent_skills.items()},
            }
        )
    return agents


def _tasks(specs=None):
    """Create task dicts from specifications.

    specs: list of (category, worker_wallet) tuples
    """
    if specs is None:
        specs = [
            ("photo", "0x001"),
            ("delivery", "0x001"),
            ("photo", "0x002"),
            ("verify", "0x001"),
            ("survey", "0x003"),
        ]
    tasks = []
    for i, spec in enumerate(specs):
        if isinstance(spec, tuple):
            cat, worker = spec
        else:
            cat, worker = spec, None
        tasks.append(
            {
                "id": f"task-{i}",
                "category": cat,
                "assigned_worker": worker,
                "title": f"Test {cat} task",
            }
        )
    return tasks


# ══════════════════════════════════════════════════════════════
# Data Type Tests
# ══════════════════════════════════════════════════════════════


class TestSkillDemand:
    def test_critical_severity(self):
        sd = SkillDemand(
            skill="video",
            demand_count=5,
            supply_count=0,
            gap=5,
            coverage_ratio=0.0,
            avg_quality=0.0,
        )
        assert sd.severity == "critical"
        assert sd.is_critical is True

    def test_high_severity(self):
        sd = SkillDemand(
            skill="photo",
            demand_count=10,
            supply_count=3,
            gap=7,
            coverage_ratio=0.3,
            avg_quality=0.7,
        )
        assert sd.severity == "high"
        assert sd.is_critical is False

    def test_medium_severity(self):
        sd = SkillDemand(
            skill="photo",
            demand_count=10,
            supply_count=8,
            gap=2,
            coverage_ratio=0.8,
            avg_quality=0.7,
        )
        assert sd.severity == "medium"

    def test_healthy_severity(self):
        sd = SkillDemand(
            skill="photo",
            demand_count=5,
            supply_count=10,
            gap=0,
            coverage_ratio=2.0,
            avg_quality=0.9,
        )
        assert sd.severity == "healthy"
        assert sd.is_critical is False


class TestWorkloadEntry:
    def test_overloaded_flag(self):
        we = WorkloadEntry(
            wallet="0x1",
            task_count=10,
            share=0.6,
            is_overloaded=True,
            is_underutilized=False,
        )
        assert we.is_overloaded

    def test_underutilized_flag(self):
        we = WorkloadEntry(
            wallet="0x2",
            task_count=1,
            share=0.02,
            is_overloaded=False,
            is_underutilized=True,
        )
        assert we.is_underutilized


# ══════════════════════════════════════════════════════════════
# Skill Gap Analysis Tests
# ══════════════════════════════════════════════════════════════


class TestSkillGapAnalysis:
    def test_basic_gap_detection(self):
        planner = CapacityPlanner()
        agents = _agents(
            3,
            {
                0: {"photo": 0.8},
                1: {"delivery": 0.9},
                2: {"photo": 0.7},
            },
        )
        tasks = _tasks(
            [("photo", None), ("photo", None), ("video", None), ("delivery", None)]
        )

        result = planner.analyze_skill_gaps(agents, tasks)

        assert result["total_skills_seen"] >= 3
        # Video has zero supply — should be critical
        critical = result["critical_gaps"]
        critical_skills = [g["skill"] for g in critical]
        assert "video" in critical_skills

    def test_full_coverage(self):
        planner = CapacityPlanner()
        agents = _agents(
            3,
            {
                0: {"photo": 0.9, "delivery": 0.8},
                1: {"photo": 0.7, "delivery": 0.9},
                2: {"photo": 0.8},
            },
        )
        # Use titles that won't trigger keyword extraction of extra skills
        tasks = [
            {"category": "photo", "title": "Take a pic"},
            {"category": "delivery", "title": "Drop off package"},
        ]

        result = planner.analyze_skill_gaps(agents, tasks)
        assert result["overall_coverage"] == 1.0
        assert result["critical_count"] == 0

    def test_empty_tasks(self):
        planner = CapacityPlanner()
        result = planner.analyze_skill_gaps(_agents(3), [])

        # Supply-only skills appear but no demand
        assert result["in_demand_skills"] == 0
        assert result["overall_coverage"] == 1.0

    def test_skill_quality_extraction(self):
        planner = CapacityPlanner()
        agents = [
            {
                "skills": {
                    "photo": {"confidence": 0.9, "level": "EXPERT"},
                    "delivery": {"confidence": 0.3},
                }
            }
        ]
        tasks = _tasks([("photo", None)])

        result = planner.analyze_skill_gaps(agents, tasks)
        photo_demand = [d for d in result["skill_demands"] if d["skill"] == "photo"]
        assert len(photo_demand) == 1
        assert photo_demand[0]["avg_quality"] > 0

    def test_list_skills(self):
        """Agents with skills as list (no quality scores)."""
        planner = CapacityPlanner()
        agents = [{"skills": ["photo", "delivery"]}]
        tasks = _tasks([("photo", None)])

        result = planner.analyze_skill_gaps(agents, tasks)
        photo = [d for d in result["skill_demands"] if d["skill"] == "photo"]
        assert photo[0]["supply_count"] == 1

    def test_category_based_skills(self):
        planner = CapacityPlanner()
        agents = [{"categories": ["photo", "delivery"], "skills": {}}]
        tasks = _tasks([("photo", None)])

        result = planner.analyze_skill_gaps(agents, tasks)
        photo = [d for d in result["skill_demands"] if d["skill"] == "photo"]
        assert photo[0]["supply_count"] == 1

    def test_required_skills_dict(self):
        planner = CapacityPlanner()
        tasks = [
            {"required_skills": {"photo": True, "video": True}, "category": "media"}
        ]
        agents = []

        result = planner.analyze_skill_gaps(agents, tasks)
        skills = [d["skill"] for d in result["skill_demands"]]
        assert "photo" in skills
        assert "video" in skills

    def test_severity_sorting(self):
        planner = CapacityPlanner()
        agents = [{"skills": {"photo": 0.8}}]
        tasks = _tasks(
            [
                ("video", None),
                ("video", None),
                ("video", None),
                ("photo", None),
            ]
        )

        result = planner.analyze_skill_gaps(agents, tasks)
        # Critical (video) should come before healthy (photo)
        demands = result["skill_demands"]
        video_idx = next(i for i, d in enumerate(demands) if d["skill"] == "video")
        photo_idx = next(i for i, d in enumerate(demands) if d["skill"] == "photo")
        assert video_idx < photo_idx

    def test_numeric_skill_quality(self):
        """Agent skills as numeric values (0-100 range)."""
        planner = CapacityPlanner()
        agents = [{"skills": {"photo": 85}}]
        tasks = _tasks([("photo", None)])

        result = planner.analyze_skill_gaps(agents, tasks)
        photo = [d for d in result["skill_demands"] if d["skill"] == "photo"]
        assert photo[0]["avg_quality"] == 0.85  # Normalized from 85/100


# ══════════════════════════════════════════════════════════════
# Capacity Forecast Tests
# ══════════════════════════════════════════════════════════════


class TestCapacityForecast:
    def test_surplus_state(self):
        planner = CapacityPlanner()
        agents = _agents(10)

        result = planner.forecast_capacity(agents, projected_daily_tasks=2.0)
        assert result.status == "surplus"
        assert result.utilization < TARGET_UTILIZATION_LOW
        assert result.workers_needed == 0
        assert result.headroom > 0

    def test_balanced_state(self):
        planner = CapacityPlanner()
        agents = _agents(5)

        # 5 agents * 0.7 active * 3 tasks/day = 10.5 capacity
        # 5 tasks/day → utilization = 0.476 → balanced
        result = planner.forecast_capacity(agents, projected_daily_tasks=5.0)
        assert result.status == "balanced"

    def test_shortage_state(self):
        planner = CapacityPlanner()
        agents = _agents(2)

        # 2 agents * 0.7 * 3 = 4.2 capacity, 10 demand → shortage
        result = planner.forecast_capacity(agents, projected_daily_tasks=10.0)
        assert result.status in ("shortage", "critical")
        assert result.workers_needed > 0

    def test_critical_state(self):
        planner = CapacityPlanner()
        agents = _agents(1)

        # 1 agent * 0.7 * 3 = 2.1 capacity, 10 demand → critical
        result = planner.forecast_capacity(agents, projected_daily_tasks=10.0)
        assert result.status == "critical"

    def test_custom_active_fraction(self):
        planner = CapacityPlanner()
        agents = _agents(10)

        result_low = planner.forecast_capacity(agents, 20.0, active_fraction=0.3)
        result_high = planner.forecast_capacity(agents, 20.0, active_fraction=0.9)

        assert result_low.current_capacity_daily < result_high.current_capacity_daily

    def test_custom_tasks_per_worker(self):
        planner = CapacityPlanner(tasks_per_worker_per_day=10.0)
        agents = _agents(5)

        result = planner.forecast_capacity(agents, projected_daily_tasks=5.0)
        # int(5 * 0.7) = 3 active agents * 10 = 30 capacity for 5 demand → surplus
        assert result.status == "surplus"

    def test_zero_demand(self):
        planner = CapacityPlanner()
        agents = _agents(5)

        result = planner.forecast_capacity(agents, projected_daily_tasks=0.0)
        assert result.status == "surplus"
        assert result.utilization == 0.0

    def test_single_agent(self):
        planner = CapacityPlanner()
        agents = _agents(1)

        result = planner.forecast_capacity(agents, projected_daily_tasks=2.0)
        # 1 * 0.7 * 3 = 2.1 capacity
        assert result.current_capacity_daily > 0

    def test_tight_state(self):
        planner = CapacityPlanner()
        agents = _agents(3)

        # 3 * 0.7 * 3 = 6.3 capacity
        # Need demand between 0.8*6.3=5.04 and 6.3 → tight
        result = planner.forecast_capacity(agents, projected_daily_tasks=5.5)
        assert result.status == "tight"


# ══════════════════════════════════════════════════════════════
# Concentration Risk Tests
# ══════════════════════════════════════════════════════════════


class TestConcentrationRisk:
    def test_single_worker_critical(self):
        planner = CapacityPlanner()
        tasks = _tasks(
            [
                ("photo", "0x001"),
                ("delivery", "0x001"),
                ("photo", "0x001"),
                ("verify", "0x001"),
            ]
        )

        result = planner.concentration_risk(_agents(3), tasks)
        assert result.top_worker_share == 1.0
        assert result.risk_level == "critical"
        assert result.active_workers == 1

    def test_two_workers_high_concentration(self):
        planner = CapacityPlanner()
        tasks = _tasks(
            [
                ("photo", "0x001"),
                ("delivery", "0x001"),
                ("photo", "0x001"),
                ("verify", "0x001"),
                ("survey", "0x002"),
            ]
        )

        result = planner.concentration_risk(_agents(5), tasks)
        assert result.top_worker_share == 0.8
        assert result.risk_level in ("high", "critical")

    def test_balanced_distribution(self):
        planner = CapacityPlanner()
        tasks = _tasks(
            [
                ("photo", "0x001"),
                ("delivery", "0x002"),
                ("photo", "0x003"),
                ("verify", "0x004"),
                ("survey", "0x005"),
            ]
        )

        result = planner.concentration_risk(_agents(5), tasks)
        assert result.top_worker_share == 0.2
        assert result.risk_level == "healthy"

    def test_hhi_index_calculation(self):
        planner = CapacityPlanner()
        # Perfect monopoly: HHI = 1.0
        tasks = _tasks([("photo", "0x001")] * 10)
        result = planner.concentration_risk(_agents(5), tasks)
        assert result.herfindahl_index == 1.0

    def test_hhi_balanced(self):
        planner = CapacityPlanner()
        # 5 workers, each 2 tasks: shares = [0.2]*5, HHI = 5 * 0.04 = 0.2
        tasks = _tasks(
            [
                ("a", "0x001"),
                ("b", "0x001"),
                ("c", "0x002"),
                ("d", "0x002"),
                ("e", "0x003"),
                ("f", "0x003"),
                ("g", "0x004"),
                ("h", "0x004"),
                ("i", "0x005"),
                ("j", "0x005"),
            ]
        )
        result = planner.concentration_risk(_agents(5), tasks)
        assert abs(result.herfindahl_index - 0.2) < 0.01

    def test_gini_coefficient_monopoly(self):
        planner = CapacityPlanner()
        tasks = _tasks([("photo", "0x001")] * 10)
        result = planner.concentration_risk(_agents(5), tasks)
        # Single worker → Gini should be 0 (only one value, no inequality among workers)
        assert result.gini_coefficient == 0.0

    def test_recommendations_generated(self):
        planner = CapacityPlanner()
        tasks = _tasks([("photo", "0x001")] * 10)
        result = planner.concentration_risk(_agents(5), tasks)
        assert len(result.recommendations) > 0

    def test_unassigned_tasks_filtered(self):
        planner = CapacityPlanner()
        tasks = [
            {"category": "photo", "title": "t"},  # No worker assigned
            {"category": "delivery", "assigned_worker": "0x001", "title": "t"},
        ]
        result = planner.concentration_risk(_agents(3), tasks)
        assert result.total_tasks == 1  # Only the assigned one counts

    def test_worker_id_fallback(self):
        planner = CapacityPlanner()
        tasks = [{"category": "photo", "worker_id": "w1", "title": "t"}]
        result = planner.concentration_risk(_agents(3), tasks)
        assert result.active_workers == 1


# ══════════════════════════════════════════════════════════════
# Workload Balance Tests
# ══════════════════════════════════════════════════════════════


class TestWorkloadBalance:
    def test_balanced_distribution(self):
        planner = CapacityPlanner()
        tasks = _tasks(
            [
                ("a", "0x001"),
                ("b", "0x002"),
                ("c", "0x003"),
                ("d", "0x004"),
            ]
        )

        result = planner.workload_balance(_agents(4), tasks)
        assert result["active_workers"] == 4
        assert result["balance_score"] > 0.8

    def test_unbalanced_distribution(self):
        planner = CapacityPlanner()
        tasks = _tasks(
            [
                ("a", "0x001"),
                ("b", "0x001"),
                ("c", "0x001"),
                ("d", "0x001"),
                ("e", "0x001"),
                ("f", "0x001"),
                ("g", "0x002"),
            ]
        )

        result = planner.workload_balance(_agents(5), tasks)
        assert result["overloaded_count"] >= 1

    def test_empty_tasks(self):
        planner = CapacityPlanner()
        result = planner.workload_balance(_agents(5), [])

        assert result["total_tasks"] == 0
        assert result["active_workers"] == 0
        assert result["balance_score"] == 1.0  # Vacuously balanced

    def test_single_worker_zero_balance(self):
        planner = CapacityPlanner()
        tasks = _tasks([("a", "0x001")] * 5)

        result = planner.workload_balance(_agents(5), tasks)
        assert result["active_workers"] == 1
        assert result["balance_score"] == 0.0

    def test_categories_tracked(self):
        planner = CapacityPlanner()
        tasks = _tasks(
            [
                ("photo", "0x001"),
                ("delivery", "0x001"),
                ("photo", "0x002"),
            ]
        )

        result = planner.workload_balance(_agents(3), tasks)
        workers = result["workers"]
        worker1 = [w for w in workers if w["wallet"] == "0x001"][0]
        assert len(worker1["categories"]) == 2

    def test_avg_tasks_per_worker(self):
        planner = CapacityPlanner()
        tasks = _tasks([("a", "0x001"), ("b", "0x002"), ("c", "0x003")])

        result = planner.workload_balance(_agents(3), tasks)
        assert result["avg_tasks_per_worker"] == 1.0

    def test_underutilized_detection(self):
        planner = CapacityPlanner()
        # 25 tasks total, one worker has only 1 (share=0.04 < 0.05)
        tasks = _tasks([("a", "0x001")] * 24 + [("b", "0x002")])

        result = planner.workload_balance(_agents(5), tasks)
        assert result["underutilized_count"] >= 1

    def test_workers_sorted_by_count(self):
        planner = CapacityPlanner()
        tasks = _tasks(
            [
                ("a", "0x002"),
                ("b", "0x002"),
                ("c", "0x002"),
                ("d", "0x001"),
            ]
        )

        result = planner.workload_balance(_agents(3), tasks)
        workers = result["workers"]
        assert workers[0]["wallet"] == "0x002"
        assert workers[0]["task_count"] > workers[1]["task_count"]


# ══════════════════════════════════════════════════════════════
# Recruitment Plan Tests
# ══════════════════════════════════════════════════════════════


class TestRecruitmentPlan:
    def test_critical_skill_gaps_generate_targets(self):
        planner = CapacityPlanner()
        agents = [{"skills": {"photo": 0.8}}]
        tasks = _tasks([("video", None), ("video", None), ("video", None)])

        plan = planner.recruitment_plan(agents, tasks)
        assert plan["critical_count"] > 0
        critical = [t for t in plan["targets"] if t["priority"] == "critical"]
        assert any(t["skill"] == "video" for t in critical)

    def test_capacity_shortage_generates_target(self):
        planner = CapacityPlanner()
        agents = _agents(1)
        tasks = _tasks([("photo", "0x001")] * 5)

        plan = planner.recruitment_plan(agents, tasks, projected_daily_tasks=20.0)
        assert plan["workers_needed"] > 0
        general = [t for t in plan["targets"] if t["skill"] == "general"]
        assert len(general) > 0

    def test_concentration_risk_generates_target(self):
        planner = CapacityPlanner()
        agents = _agents(3)
        tasks = _tasks([("photo", "0x001")] * 10)

        plan = planner.recruitment_plan(agents, tasks)
        div = [t for t in plan["targets"] if t["skill"] == "diversification"]
        assert len(div) > 0

    def test_healthy_pool_no_targets(self):
        planner = CapacityPlanner()
        agents = _agents(10, {i: {"photo": 0.8, "delivery": 0.9} for i in range(10)})
        tasks = _tasks([("photo", f"0x{i:03x}") for i in range(10)])

        plan = planner.recruitment_plan(agents, tasks, projected_daily_tasks=5.0)
        assert plan["critical_count"] == 0
        assert plan["capacity_status"] == "surplus"


# ══════════════════════════════════════════════════════════════
# Full Report Tests
# ══════════════════════════════════════════════════════════════


class TestFullReport:
    def test_all_sections_present(self):
        planner = CapacityPlanner()
        agents = _agents(5)
        tasks = _tasks()

        report = planner.full_report(agents, tasks)

        assert "health_score" in report
        assert "skill_gaps" in report
        assert "capacity" in report
        assert "concentration_risk" in report
        assert "workload_balance" in report
        assert "recruitment_plan" in report
        assert "summary" in report

    def test_health_score_range(self):
        planner = CapacityPlanner()
        agents = _agents(5)
        tasks = _tasks()

        report = planner.full_report(agents, tasks)
        assert 0 <= report["health_score"] <= 100

    def test_summary_aggregation(self):
        planner = CapacityPlanner()
        agents = _agents(5)
        tasks = _tasks()

        report = planner.full_report(agents, tasks)
        summary = report["summary"]
        assert summary["total_agents"] == 5
        assert summary["total_recent_tasks"] == 5

    def test_healthy_pool_high_score(self):
        planner = CapacityPlanner()
        # 10 agents with good skill coverage, balanced workload
        agents = _agents(10, {i: {"photo": 0.8, "delivery": 0.9} for i in range(10)})
        tasks = _tasks([("photo", f"0x{i:03x}") for i in range(10)])

        report = planner.full_report(agents, tasks, projected_daily_tasks=5.0)
        assert report["health_score"] >= 50


# ══════════════════════════════════════════════════════════════
# Helper Function Tests
# ══════════════════════════════════════════════════════════════


class TestHelpers:
    def test_gini_perfect_equality(self):
        result = CapacityPlanner._gini_coefficient([10, 10, 10, 10])
        assert result == 0.0

    def test_gini_high_inequality(self):
        result = CapacityPlanner._gini_coefficient([0, 0, 0, 100])
        assert result > 0.5

    def test_gini_empty(self):
        result = CapacityPlanner._gini_coefficient([])
        assert result == 0.0

    def test_gini_all_zeros(self):
        result = CapacityPlanner._gini_coefficient([0, 0, 0])
        assert result == 0.0

    def test_gini_single_value(self):
        result = CapacityPlanner._gini_coefficient([42])
        assert result == 0.0

    def test_extract_task_skills_combined(self):
        planner = CapacityPlanner()
        task = {
            "required_skills": ["video", "editing"],
            "category": "media",
            "title": "Write a research report",
        }
        skills = planner._extract_task_skills(task)
        assert "video" in skills
        assert "editing" in skills
        assert "media" in skills
        assert "write" in skills
        assert "research" in skills

    def test_extract_agent_skills_with_levels(self):
        planner = CapacityPlanner()
        agent = {
            "skills": {
                "photo": {"confidence": 0.9, "level": "EXPERT"},
                "delivery": {"level": "BEGINNER"},
            }
        }
        skills = planner._extract_agent_skills(agent)
        assert skills["photo"] == 1.0  # max(0.9, 1.0)
        assert skills["delivery"] == 0.5  # max(default conf 0.5, 0.3)

    def test_extract_agent_skills_numeric(self):
        planner = CapacityPlanner()
        agent = {"skills": {"photo": 85}}
        skills = planner._extract_agent_skills(agent)
        assert skills["photo"] == 0.85


# ══════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_very_large_pool(self):
        planner = CapacityPlanner()
        agents = [{"skills": {"photo": 0.5}} for _ in range(100)]
        tasks = [
            {"category": "photo", "assigned_worker": f"0x{i:040x}", "title": "t"}
            for i in range(50)
        ]

        report = planner.full_report(agents, tasks)
        assert report["health_score"] > 0

    def test_many_skills(self):
        planner = CapacityPlanner()
        agents = [{"skills": {f"skill_{i}": 0.5 for i in range(20)}}]
        tasks = [{"category": f"skill_{i}", "title": f"Task {i}"} for i in range(20)]

        result = planner.analyze_skill_gaps(agents, tasks)
        assert result["total_skills_seen"] >= 20

    def test_inf_coverage_for_no_demand(self):
        planner = CapacityPlanner()
        # Agent has skills but no tasks demand them
        agents = [{"skills": {"rare_skill": 0.9}}]
        tasks = []

        result = planner.analyze_skill_gaps(agents, tasks)
        # Supply-only skills should have coverage_ratio = inf
        rare = [d for d in result["skill_demands"] if d["skill"] == "rare_skill"]
        if rare:
            assert rare[0]["coverage_ratio"] == float("inf")
