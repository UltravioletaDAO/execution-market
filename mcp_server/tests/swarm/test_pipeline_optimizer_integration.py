"""
Integration tests for PipelineOptimizer (Module #60) with SwarmIntegrator.
"""

from mcp_server.swarm.pipeline_optimizer import PipelineOptimizer
from mcp_server.swarm.integrator import SwarmIntegrator


# ──────────────────────────────────────────────────────────────
# 1. SwarmIntegrator Registration
# ──────────────────────────────────────────────────────────────


class TestIntegratorRegistration:
    def test_basic_registration(self):
        integrator = SwarmIntegrator()
        optimizer = PipelineOptimizer()
        result = integrator.set_pipeline_optimizer(optimizer)
        assert result is integrator  # Fluent API
        assert integrator._pipeline_optimizer is optimizer
        assert "pipeline_optimizer" in integrator._component_statuses

    def test_registration_reports_healthy(self):
        integrator = SwarmIntegrator()
        optimizer = PipelineOptimizer()
        integrator.set_pipeline_optimizer(optimizer)
        status = integrator._component_statuses["pipeline_optimizer"]
        assert status.healthy is True
        assert status.initialized is True

    def test_factory_registration(self):
        optimizer = PipelineOptimizer()
        integrator = SwarmIntegrator.create_with_components(
            components={"pipeline_optimizer": optimizer}
        )
        assert integrator._pipeline_optimizer is optimizer
        assert "pipeline_optimizer" in integrator._component_statuses


# ──────────────────────────────────────────────────────────────
# 2. Wiring Diagram
# ──────────────────────────────────────────────────────────────


class TestWiringDiagram:
    def test_optimizer_in_diagram(self):
        integrator = SwarmIntegrator()
        optimizer = PipelineOptimizer()
        integrator.set_pipeline_optimizer(optimizer)
        diagram = integrator.get_wiring_diagram()
        assert "PipelineOptimizer (#60)" in diagram
        assert "Optimization Layer" in diagram

    def test_optimizer_not_in_diagram_when_absent(self):
        integrator = SwarmIntegrator()
        diagram = integrator.get_wiring_diagram()
        assert "PipelineOptimizer" not in diagram


# ──────────────────────────────────────────────────────────────
# 3. Component Count
# ──────────────────────────────────────────────────────────────


class TestComponentCount:
    def test_optimizer_counted(self):
        integrator = SwarmIntegrator()
        integrator.set_pipeline_optimizer(PipelineOptimizer())
        assert len(integrator._component_statuses) == 1

    def test_multiple_components(self):
        from mcp_server.swarm.task_validator import TaskValidator
        from mcp_server.swarm.batch_scheduler import BatchScheduler

        integrator = SwarmIntegrator()
        integrator.set_pipeline_optimizer(PipelineOptimizer())
        integrator.set_task_validator(TaskValidator())
        integrator.set_batch_scheduler(BatchScheduler())
        assert len(integrator._component_statuses) == 3


# ──────────────────────────────────────────────────────────────
# 4. Full Stack Integration
# ──────────────────────────────────────────────────────────────


class TestFullStack:
    def test_optimizer_with_batch_and_validator(self):
        from mcp_server.swarm.task_validator import TaskValidator
        from mcp_server.swarm.batch_scheduler import BatchScheduler

        integrator = SwarmIntegrator.create_with_components(
            components={
                "pipeline_optimizer": PipelineOptimizer(),
                "task_validator": TaskValidator(),
                "batch_scheduler": BatchScheduler(),
            }
        )
        assert integrator._pipeline_optimizer is not None
        assert integrator._task_validator is not None
        assert integrator._batch_scheduler is not None
        assert len(integrator._component_statuses) == 3

    def test_optimizer_analyze_after_registration(self):
        optimizer = PipelineOptimizer()
        integrator = SwarmIntegrator()
        integrator.set_pipeline_optimizer(optimizer)

        # Record some data and analyze
        optimizer.record("batch", duration_ms=10, tasks_in=50, tasks_out=8)
        optimizer.record("validate", duration_ms=1, tasks_in=8, tasks_out=7)
        report = optimizer.analyze()
        assert report.total_executions == 2


# ──────────────────────────────────────────────────────────────
# 5. Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_double_registration(self):
        integrator = SwarmIntegrator()
        opt1 = PipelineOptimizer()
        opt2 = PipelineOptimizer()
        integrator.set_pipeline_optimizer(opt1)
        integrator.set_pipeline_optimizer(opt2)
        assert integrator._pipeline_optimizer is opt2

    def test_registration_order_doesnt_matter(self):
        from mcp_server.swarm.task_validator import TaskValidator
        from mcp_server.swarm.batch_scheduler import BatchScheduler

        # Register in reverse order
        integrator = SwarmIntegrator()
        integrator.set_pipeline_optimizer(PipelineOptimizer())
        integrator.set_batch_scheduler(BatchScheduler())
        integrator.set_task_validator(TaskValidator())
        assert len(integrator._component_statuses) == 3
