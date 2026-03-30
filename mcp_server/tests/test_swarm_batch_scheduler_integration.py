"""
Integration Tests for BatchScheduler (Module #59)
===================================================

Tests wiring into SwarmIntegrator and CoordinatorPipeline.
"""

import pytest

from mcp_server.swarm.batch_scheduler import BatchScheduler, BatchStrategy
from mcp_server.swarm.integrator import SwarmIntegrator, SwarmMode


# ──────────────────────────────────────────────────────────────
# 1. SwarmIntegrator Registration
# ──────────────────────────────────────────────────────────────


class TestIntegratorRegistration:
    def test_set_batch_scheduler(self):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        scheduler = BatchScheduler()
        result = integrator.set_batch_scheduler(scheduler)
        assert result is integrator  # fluent API
        assert integrator._batch_scheduler is scheduler

    def test_batch_scheduler_registered_as_component(self):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        scheduler = BatchScheduler()
        integrator.set_batch_scheduler(scheduler)
        assert "batch_scheduler" in integrator._component_statuses
        assert integrator._component_statuses["batch_scheduler"].healthy

    def test_batch_scheduler_in_wiring_diagram(self):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        scheduler = BatchScheduler()
        integrator.set_batch_scheduler(scheduler)
        diagram = integrator.get_wiring_diagram()
        assert "BatchScheduler" in diagram
        assert "#59" in diagram

    def test_auto_wire_into_existing_pipeline(self):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)

        # Import CoordinatorPipeline
        from mcp_server.swarm.coordinator_pipeline import CoordinatorPipeline

        pipeline = CoordinatorPipeline(coordinator=None, signal_harness=None)
        integrator.set_coordinator_pipeline(pipeline)

        scheduler = BatchScheduler()
        integrator.set_batch_scheduler(scheduler)

        assert pipeline.batch_scheduler is scheduler


# ──────────────────────────────────────────────────────────────
# 2. CoordinatorPipeline Integration
# ──────────────────────────────────────────────────────────────


class TestPipelineIntegration:
    def test_set_batch_scheduler(self):
        from mcp_server.swarm.coordinator_pipeline import CoordinatorPipeline

        pipeline = CoordinatorPipeline(coordinator=None, signal_harness=None)
        scheduler = BatchScheduler()
        result = pipeline.set_batch_scheduler(scheduler)
        assert result is pipeline  # fluent API
        assert pipeline.batch_scheduler is scheduler

    def test_batch_scheduler_in_status(self):
        from mcp_server.swarm.coordinator_pipeline import CoordinatorPipeline

        pipeline = CoordinatorPipeline(coordinator=None, signal_harness=None)
        status = pipeline.status()
        assert status["batch_scheduler"] is False

        scheduler = BatchScheduler()
        pipeline.set_batch_scheduler(scheduler)
        status = pipeline.status()
        assert status["batch_scheduler"] is True


# ──────────────────────────────────────────────────────────────
# 3. Factory Integration
# ──────────────────────────────────────────────────────────────


class TestFactoryIntegration:
    def test_create_with_batch_scheduler(self):
        scheduler = BatchScheduler(strategy=BatchStrategy.CHAIN)
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.PASSIVE,
            components={"batch_scheduler": scheduler},
        )
        assert integrator._batch_scheduler is scheduler
        assert "batch_scheduler" in integrator._component_statuses


# ──────────────────────────────────────────────────────────────
# 4. Wiring Diagram
# ──────────────────────────────────────────────────────────────


class TestWiringDiagram:
    def test_diagram_with_pipeline_and_scheduler(self):
        from mcp_server.swarm.coordinator_pipeline import CoordinatorPipeline

        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        pipeline = CoordinatorPipeline(coordinator=None, signal_harness=None)
        scheduler = BatchScheduler()

        integrator.set_coordinator_pipeline(pipeline)
        integrator.set_batch_scheduler(scheduler)

        diagram = integrator.get_wiring_diagram()
        assert "BatchScheduler" in diagram
        assert "wired to CoordinatorPipeline" in diagram

    def test_diagram_without_pipeline(self):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        scheduler = BatchScheduler()
        integrator.set_batch_scheduler(scheduler)

        diagram = integrator.get_wiring_diagram()
        assert "BatchScheduler" in diagram
        assert "wired to CoordinatorPipeline" not in diagram


# ──────────────────────────────────────────────────────────────
# 5. Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_set_batch_scheduler_without_pipeline(self):
        """Should not crash when no pipeline exists."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        scheduler = BatchScheduler()
        integrator.set_batch_scheduler(scheduler)  # Should not raise
        assert integrator._batch_scheduler is scheduler

    def test_set_batch_scheduler_twice(self):
        """Second registration should replace first."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        s1 = BatchScheduler(strategy=BatchStrategy.CHAIN)
        s2 = BatchScheduler(strategy=BatchStrategy.HYBRID)
        integrator.set_batch_scheduler(s1)
        integrator.set_batch_scheduler(s2)
        assert integrator._batch_scheduler is s2

    def test_pipeline_batch_scheduler_initially_none(self):
        from mcp_server.swarm.coordinator_pipeline import CoordinatorPipeline

        pipeline = CoordinatorPipeline(coordinator=None, signal_harness=None)
        assert pipeline.batch_scheduler is None
