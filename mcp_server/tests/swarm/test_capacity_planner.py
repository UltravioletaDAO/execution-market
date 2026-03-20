"""
Tests for swarm.capacity_planner module.

Covers:
    - SkillDemand severity classification
    - Skill gap analysis (various supply/demand scenarios)
    - Capacity forecasting (surplus, balanced, shortage, critical)
    - Concentration risk (Herfindahl, Gini, risk levels)
    - Workload balance (distribution, overload detection)
    - Recruitment plan generation
    - Full report generation
    - Edge cases (empty data, single worker, no tasks)
"""

import pytest
from dataclasses import asdict

from mcp_server.swarm.capacity_planner import (
    CapacityPlanner,
    SkillDemand,
    ConcentrationReport,
    CapacityEstimate,
    RecruitmentTarget,
    WorkloadEntry,
    MAX_HEALTHY_CONCENTRATION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agents(skills_list: list) -> list:
    """Create agent dicts from a list of skill sets.

    Example: [{"python": 0.8, "aws": 0.7}, {"photography": 0.6}]
    """
    agents = []
    for i, skills in enumerate(skills_list):
        agents.append({
            "wallet": f"0x{i:04X}",
            "skills": {
                k: {"level": "INTERMEDIATE", "confidence": v}
                for k, v in skills.items()
            },
        })
    return agents


def make_tasks(categories_and_workers: list) -> list:
    """Create task dicts from [(category, worker_wallet), ...].

    If worker is None, task is unassigned.
    """
    tasks = []
    for i, (cat, worker) in enumerate(categories_and_workers):
        task = {
            "id": f"task_{i}",
            "category": cat,
            "title": f"Test task {i} ({cat})",
        }
        if worker:
            task["assigned_worker"] = worker
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# SkillDemand
# ---------------------------------------------------------------------------

class TestSkillDemand:
    def test_critical_gap(self):
        sd = SkillDemand("photography", demand_count=5, supply_count=0,
                         gap=5, coverage_ratio=0.0, avg_quality=0.0)
        assert sd.is_critical
        assert sd.severity == "critical"

    def test_high_gap(self):
        sd = SkillDemand("photography", demand_count=5, supply_count=2,
                         gap=3, coverage_ratio=0.4, avg_quality=0.5)
        assert not sd.is_critical
        assert sd.severity == "high"

    def test_medium_gap(self):
        sd = SkillDemand("photography", demand_count=5, supply_count=4,
                         gap=1, coverage_ratio=0.8, avg_quality=0.7)
        assert sd.severity == "medium"

    def test_healthy(self):
        sd = SkillDemand("photography", demand_count=3, supply_count=5,
                         gap=0, coverage_ratio=1.67, avg_quality=0.8)
        assert sd.severity == "healthy"

    def test_no_demand(self):
        sd = SkillDemand("obscure", demand_count=0, supply_count=2,
                         gap=0, coverage_ratio=float('inf'), avg_quality=0.5)
        assert sd.severity == "healthy"


# ---------------------------------------------------------------------------
# Skill Gap Analysis
# ---------------------------------------------------------------------------

class TestSkillGapAnalysis:
    def setup_method(self):
        self.planner = CapacityPlanner()

    def test_empty_inputs(self):
        result = self.planner.analyze_skill_gaps([], [])
        assert result["critical_count"] == 0
        assert result["overall_coverage"] == 1.0
        assert result["total_skills_seen"] == 0

    def test_perfect_coverage(self):
        """Tasks with categories matching agent skills → no critical gaps.

        Note: title-based extraction may add extra skills (e.g., 'photo'
        from 'photography' in the title). We add those to agent skills too.
        """
        agents = make_agents([
            {"data_collection": 0.8, "research": 0.7},
            {"data_collection": 0.6, "research": 0.9},
        ])
        tasks = make_tasks([
            ("data_collection", None),
            ("research", None),
        ])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        # Both categories fully covered
        assert result["critical_count"] == 0

    def test_critical_gap_detected(self):
        agents = make_agents([{"python": 0.8}])
        tasks = make_tasks([
            ("photography", None),
            ("photography", None),
            ("photography", None),
        ])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        critical = result["critical_gaps"]
        # Photography has demand but no supply
        photo_gaps = [g for g in critical if g["skill"] == "photography"]
        assert len(photo_gaps) == 1
        assert photo_gaps[0]["demand_count"] == 3

    def test_partial_coverage(self):
        agents = make_agents([
            {"photography": 0.8},
        ])
        tasks = make_tasks([
            ("photography", None),
            ("photography", None),
            ("photography", None),
        ])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        photo_demands = [
            d for d in result["skill_demands"]
            if d["skill"] == "photography"
        ]
        assert len(photo_demands) == 1
        # 1 worker for 3 tasks → coverage_ratio ~0.33
        assert photo_demands[0]["coverage_ratio"] < 1.0

    def test_skill_quality_tracked(self):
        agents = make_agents([
            {"python": 0.9},
            {"python": 0.7},
        ])
        tasks = make_tasks([("python", None)])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        python_demand = [d for d in result["skill_demands"] if d["skill"] == "python"]
        assert len(python_demand) == 1
        # Average quality should be (0.9 + 0.7) / 2 = 0.8
        assert python_demand[0]["avg_quality"] == pytest.approx(0.8, abs=0.1)

    def test_title_based_skill_extraction(self):
        agents = make_agents([{"photography": 0.8}])
        tasks = [{
            "id": "t1",
            "category": "verification",
            "title": "Take a photo of the building",
        }]
        result = self.planner.analyze_skill_gaps(agents, tasks)
        skills = [d["skill"] for d in result["skill_demands"]]
        assert "photo" in skills  # Extracted from title

    def test_sorted_by_severity(self):
        agents = make_agents([{"python": 0.8}])
        tasks = make_tasks([
            ("photography", None),  # Critical (no supply)
            ("python", None),       # Healthy (has supply)
            ("video", None),        # Critical (no supply)
        ])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        # First items should be critical
        demands = result["skill_demands"]
        if len(demands) >= 2:
            assert demands[0]["severity"] in ("critical", "high")


# ---------------------------------------------------------------------------
# Capacity Forecast
# ---------------------------------------------------------------------------

class TestCapacityForecast:
    def setup_method(self):
        self.planner = CapacityPlanner(tasks_per_worker_per_day=3)

    def test_surplus(self):
        agents = make_agents([{"a": 0.5}] * 10)  # 10 workers
        cap = self.planner.forecast_capacity(agents, projected_daily_tasks=2)
        assert cap.status == "surplus"
        assert cap.headroom > 0
        assert cap.workers_needed == 0

    def test_balanced(self):
        agents = make_agents([{"a": 0.5}] * 5)  # 5 workers → ~10.5 capacity
        cap = self.planner.forecast_capacity(agents, projected_daily_tasks=6)
        assert cap.status in ("balanced", "tight")
        assert cap.utilization < 1.0

    def test_shortage(self):
        agents = make_agents([{"a": 0.5}] * 2)  # 2 workers → ~4.2 capacity
        cap = self.planner.forecast_capacity(agents, projected_daily_tasks=6)
        assert cap.status in ("shortage", "critical", "tight")

    def test_critical(self):
        agents = make_agents([{"a": 0.5}])  # 1 worker → ~2.1 capacity
        cap = self.planner.forecast_capacity(agents, projected_daily_tasks=10)
        assert cap.status == "critical"
        assert cap.workers_needed > 0

    def test_empty_agents(self):
        cap = self.planner.forecast_capacity([], projected_daily_tasks=5)
        # Should handle gracefully (1 active agent minimum)
        assert cap.workers_needed > 0

    def test_active_fraction(self):
        agents = make_agents([{"a": 0.5}] * 10)
        cap_high = self.planner.forecast_capacity(agents, 5, active_fraction=0.9)
        cap_low = self.planner.forecast_capacity(agents, 5, active_fraction=0.3)
        assert cap_high.current_capacity_daily > cap_low.current_capacity_daily

    def test_utilization_calculation(self):
        agents = make_agents([{"a": 0.5}] * 5)  # ~10.5 capacity
        cap = self.planner.forecast_capacity(agents, projected_daily_tasks=5)
        assert 0 < cap.utilization < 1.0


# ---------------------------------------------------------------------------
# Concentration Risk
# ---------------------------------------------------------------------------

class TestConcentrationRisk:
    def setup_method(self):
        self.planner = CapacityPlanner()

    def test_no_tasks(self):
        agents = make_agents([{"a": 0.5}] * 3)
        report = self.planner.concentration_risk(agents, [])
        assert report.risk_level == "no_data"
        assert report.total_tasks == 0

    def test_perfectly_balanced(self):
        agents = make_agents([{"a": 0.5}] * 5)
        tasks = make_tasks([
            ("data", "0x0000"),
            ("data", "0x0001"),
            ("data", "0x0002"),
            ("data", "0x0003"),
            ("data", "0x0004"),
        ])
        report = self.planner.concentration_risk(agents, tasks)
        assert report.risk_level == "healthy"
        assert report.top_worker_share < MAX_HEALTHY_CONCENTRATION
        assert report.herfindahl_index < 0.5

    def test_monopoly(self):
        agents = make_agents([{"a": 0.5}] * 3)
        tasks = make_tasks([
            ("photo", "0x0000"),
            ("photo", "0x0000"),
            ("photo", "0x0000"),
            ("photo", "0x0000"),
            ("photo", "0x0000"),
        ])
        report = self.planner.concentration_risk(agents, tasks)
        assert report.risk_level in ("high", "critical")
        assert report.top_worker_share == 1.0
        assert report.herfindahl_index == 1.0
        assert len(report.recommendations) > 0

    def test_duopoly(self):
        agents = make_agents([{"a": 0.5}] * 5)
        tasks = make_tasks([
            ("photo", "0x0000"),
            ("photo", "0x0000"),
            ("photo", "0x0000"),
            ("photo", "0x0001"),
            ("photo", "0x0001"),
        ])
        report = self.planner.concentration_risk(agents, tasks)
        assert report.top_worker_share == 0.6
        assert report.active_workers == 2

    def test_herfindahl_range(self):
        agents = make_agents([{"a": 0.5}] * 4)
        tasks = make_tasks([
            ("a", "0x0000"), ("a", "0x0001"),
            ("a", "0x0002"), ("a", "0x0003"),
        ])
        report = self.planner.concentration_risk(agents, tasks)
        assert 0 <= report.herfindahl_index <= 1.0

    def test_gini_coefficient(self):
        agents = make_agents([{"a": 0.5}] * 3)
        # Very unequal distribution
        tasks = make_tasks([
            ("a", "0x0000"), ("a", "0x0000"), ("a", "0x0000"),
            ("a", "0x0000"), ("a", "0x0000"),
            ("a", "0x0001"),
        ])
        report = self.planner.concentration_risk(agents, tasks)
        assert report.gini_coefficient > 0.2  # Should show inequality

    def test_inactive_worker_warning(self):
        agents = make_agents([{"a": 0.5}] * 10)
        # Only 1 worker does all tasks
        tasks = make_tasks([("a", "0x0000")] * 10)
        report = self.planner.concentration_risk(agents, tasks)
        inactive_recs = [r for r in report.recommendations if "inactive" in r.lower()]
        assert len(inactive_recs) > 0


# ---------------------------------------------------------------------------
# Workload Balance
# ---------------------------------------------------------------------------

class TestWorkloadBalance:
    def setup_method(self):
        self.planner = CapacityPlanner()

    def test_empty(self):
        result = self.planner.workload_balance([], [])
        assert result["total_tasks"] == 0
        assert result["balance_score"] == 1.0

    def test_single_worker(self):
        agents = make_agents([{"a": 0.5}])
        tasks = make_tasks([("a", "0x0000")] * 5)
        result = self.planner.workload_balance(agents, tasks)
        assert result["active_workers"] == 1
        assert result["balance_score"] == 0.0

    def test_balanced_workers(self):
        agents = make_agents([{"a": 0.5}] * 3)
        tasks = make_tasks([
            ("a", "0x0000"), ("a", "0x0000"),
            ("a", "0x0001"), ("a", "0x0001"),
            ("a", "0x0002"), ("a", "0x0002"),
        ])
        result = self.planner.workload_balance(agents, tasks)
        assert result["balance_score"] > 0.8  # Should be very balanced

    def test_overloaded_detection(self):
        agents = make_agents([{"a": 0.5}] * 3)
        tasks = make_tasks([("a", "0x0000")] * 8 + [("a", "0x0001")])
        result = self.planner.workload_balance(agents, tasks)
        overloaded = [w for w in result["workers"] if w["is_overloaded"]]
        assert len(overloaded) >= 1

    def test_category_tracking(self):
        agents = make_agents([{"a": 0.5}])
        tasks = make_tasks([
            ("photo", "0x0000"),
            ("video", "0x0000"),
            ("photo", "0x0000"),
        ])
        result = self.planner.workload_balance(agents, tasks)
        worker = result["workers"][0]
        assert "photo" in worker["categories"]
        assert "video" in worker["categories"]


# ---------------------------------------------------------------------------
# Recruitment Plan
# ---------------------------------------------------------------------------

class TestRecruitmentPlan:
    def setup_method(self):
        self.planner = CapacityPlanner()

    def test_no_gaps_no_plan(self):
        agents = make_agents([{"photo": 0.8, "video": 0.7}] * 5)
        tasks = make_tasks([("photo", "0x0000"), ("video", "0x0001")])
        plan = self.planner.recruitment_plan(agents, tasks, projected_daily_tasks=2)
        assert plan["critical_count"] == 0

    def test_critical_skill_gap(self):
        agents = make_agents([{"python": 0.8}])
        tasks = make_tasks([
            ("photography", None), ("photography", None),
            ("photography", None),
        ])
        plan = self.planner.recruitment_plan(agents, tasks)
        targets = plan["targets"]
        photo_targets = [t for t in targets if t["skill"] == "photography"]
        assert len(photo_targets) == 1
        assert photo_targets[0]["priority"] == "critical"

    def test_capacity_shortage_in_plan(self):
        agents = make_agents([{"a": 0.5}])
        tasks = make_tasks([("a", "0x0000")] * 5)
        plan = self.planner.recruitment_plan(agents, tasks, projected_daily_tasks=20)
        general_targets = [t for t in plan["targets"] if t["skill"] == "general"]
        assert len(general_targets) > 0

    def test_concentration_in_plan(self):
        agents = make_agents([{"a": 0.5}] * 3)
        tasks = make_tasks([("a", "0x0000")] * 10)
        plan = self.planner.recruitment_plan(agents, tasks, projected_daily_tasks=5)
        div_targets = [t for t in plan["targets"] if t["skill"] == "diversification"]
        assert len(div_targets) > 0

    def test_sorted_by_urgency(self):
        agents = make_agents([{"python": 0.8}])
        tasks = make_tasks([
            ("photography", None),
            ("video", None),
        ])
        plan = self.planner.recruitment_plan(agents, tasks)
        targets = plan["targets"]
        if len(targets) >= 2:
            assert targets[0]["urgency_score"] >= targets[-1]["urgency_score"]


# ---------------------------------------------------------------------------
# Full Report
# ---------------------------------------------------------------------------

class TestFullReport:
    def test_report_structure(self):
        planner = CapacityPlanner()
        agents = make_agents([
            {"photography": 0.8, "field_work": 0.7},
            {"photography": 0.6, "research": 0.9},
        ])
        tasks = make_tasks([
            ("photography", "0x0000"),
            ("research", "0x0001"),
            ("video", None),
        ])
        report = planner.full_report(agents, tasks, projected_daily_tasks=5)

        assert "health_score" in report
        assert "skill_gaps" in report
        assert "capacity" in report
        assert "concentration_risk" in report
        assert "workload_balance" in report
        assert "recruitment_plan" in report
        assert "summary" in report
        assert 0 <= report["health_score"] <= 100

    def test_healthy_report(self):
        planner = CapacityPlanner()
        agents = make_agents([
            {"a": 0.8, "b": 0.7, "c": 0.6}
            for _ in range(5)
        ])
        tasks = make_tasks([
            ("a", f"0x{i:04X}") for i in range(5)
        ])
        report = planner.full_report(agents, tasks, projected_daily_tasks=3)
        assert report["health_score"] > 30

    def test_empty_report(self):
        planner = CapacityPlanner()
        report = planner.full_report([], [])
        assert "health_score" in report
        assert report["summary"]["total_agents"] == 0


# ---------------------------------------------------------------------------
# Gini Coefficient
# ---------------------------------------------------------------------------

class TestGiniCoefficient:
    def test_perfect_equality(self):
        g = CapacityPlanner._gini_coefficient([10, 10, 10, 10])
        assert g == pytest.approx(0.0, abs=0.01)

    def test_perfect_inequality(self):
        g = CapacityPlanner._gini_coefficient([0, 0, 0, 100])
        assert g > 0.5

    def test_empty(self):
        g = CapacityPlanner._gini_coefficient([])
        assert g == 0.0

    def test_single_value(self):
        g = CapacityPlanner._gini_coefficient([50])
        assert g == 0.0

    def test_moderate_inequality(self):
        g = CapacityPlanner._gini_coefficient([1, 2, 3, 4, 5])
        assert 0 < g < 1


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def setup_method(self):
        self.planner = CapacityPlanner()

    def test_agent_with_list_skills(self):
        """Agent has skills as a list instead of dict."""
        agents = [{"wallet": "0x0000", "skills": ["python", "aws"]}]
        tasks = make_tasks([("python", None)])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        assert result["total_skills_seen"] >= 1

    def test_agent_with_numeric_skills(self):
        """Agent has skills as {name: score}."""
        agents = [{"wallet": "0x0000", "skills": {"python": 85, "aws": 70}}]
        tasks = make_tasks([("python", None)])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        python_d = [d for d in result["skill_demands"] if d["skill"] == "python"]
        assert len(python_d) == 1
        assert python_d[0]["avg_quality"] > 0.5

    def test_agent_with_categories(self):
        """Agent has categories field."""
        agents = [{"wallet": "0x0000", "skills": {}, "categories": ["data_collection", "research"]}]
        tasks = make_tasks([("data_collection", None)])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        assert result["critical_count"] == 0  # data_collection covered by category

    def test_task_with_required_skills_dict(self):
        tasks = [{"id": "t1", "required_skills": {"python": "required", "aws": "preferred"}}]
        agents = make_agents([{"python": 0.9}])
        result = self.planner.analyze_skill_gaps(agents, tasks)
        skills = [d["skill"] for d in result["skill_demands"]]
        assert "python" in skills
        assert "aws" in skills

    def test_large_pool(self):
        """Test with many agents and tasks."""
        agents = make_agents([{"a": 0.5, "b": 0.6}] * 50)
        tasks = make_tasks([("a", f"0x{i % 50:04X}") for i in range(100)])
        report = self.planner.full_report(agents, tasks, projected_daily_tasks=50)
        assert report["summary"]["total_agents"] == 50
        assert report["summary"]["total_recent_tasks"] == 100
