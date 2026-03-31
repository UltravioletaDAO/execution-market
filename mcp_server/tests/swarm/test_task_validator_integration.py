"""
Tests for TaskValidator integration with SwarmIntegrator and CoordinatorPipeline.

Test classes:
    1. TestIntegratorRegistration — set_task_validator wiring
    2. TestPipelineIntegration — CoordinatorPipeline with TaskValidator
    3. TestFactoryIntegration — create_with_components support
    4. TestWiringDiagram — wiring diagram includes TaskValidator
    5. TestAutoWiring — auto-wire to CoordinatorPipeline
    6. TestStatusReporting — status includes task_validator
"""

import unittest
import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", ".."),
)

from mcp_server.swarm.task_validator import TaskValidator
from mcp_server.swarm.coordinator_pipeline import CoordinatorPipeline
from mcp_server.swarm.integrator import SwarmIntegrator


class TestIntegratorRegistration(unittest.TestCase):
    """Test TaskValidator registration in SwarmIntegrator."""

    def test_register_task_validator(self):
        integrator = SwarmIntegrator()
        validator = TaskValidator()
        result = integrator.set_task_validator(validator)
        self.assertIs(result, integrator)  # Fluent API
        self.assertIs(integrator._task_validator, validator)

    def test_component_tracked(self):
        integrator = SwarmIntegrator()
        validator = TaskValidator()
        integrator.set_task_validator(validator)
        self.assertIn("task_validator", integrator._component_statuses)
        self.assertTrue(integrator._component_statuses["task_validator"].healthy)

    def test_auto_wire_to_pipeline(self):
        """If CoordinatorPipeline exists, validator is auto-wired."""
        integrator = SwarmIntegrator()
        pipeline = CoordinatorPipeline()
        integrator.set_coordinator_pipeline(pipeline)
        validator = TaskValidator()
        integrator.set_task_validator(validator)
        self.assertIs(pipeline.task_validator, validator)

    def test_auto_wire_reverse_order(self):
        """Validator first, pipeline second — no auto-wire (pipeline method adds validator)."""
        integrator = SwarmIntegrator()
        validator = TaskValidator()
        integrator.set_task_validator(validator)
        # Pipeline added after — auto-wire doesn't happen in this direction
        # because set_coordinator_pipeline doesn't check for task_validator
        # This is expected — the wiring goes validator → pipeline only
        pipeline = CoordinatorPipeline()
        integrator.set_coordinator_pipeline(pipeline)
        # Validator should be stored in integrator
        self.assertIs(integrator._task_validator, validator)


class TestPipelineIntegration(unittest.TestCase):
    """Test TaskValidator wired into CoordinatorPipeline."""

    def test_set_task_validator(self):
        pipeline = CoordinatorPipeline()
        validator = TaskValidator()
        result = pipeline.set_task_validator(validator)
        self.assertIs(result, pipeline)  # Fluent API
        self.assertIs(pipeline.task_validator, validator)

    def test_status_includes_task_validator_false(self):
        pipeline = CoordinatorPipeline()
        s = pipeline.status()
        self.assertFalse(s["task_validator"])

    def test_status_includes_task_validator_true(self):
        pipeline = CoordinatorPipeline()
        pipeline.set_task_validator(TaskValidator())
        s = pipeline.status()
        self.assertTrue(s["task_validator"])

    def test_task_validator_property_default_none(self):
        pipeline = CoordinatorPipeline()
        self.assertIsNone(pipeline.task_validator)


class TestFactoryIntegration(unittest.TestCase):
    """Test create_with_components factory."""

    def test_factory_with_task_validator(self):
        validator = TaskValidator()
        integrator = SwarmIntegrator.create_with_components(
            components={"task_validator": validator}
        )
        self.assertIs(integrator._task_validator, validator)

    def test_factory_with_pipeline_and_validator(self):
        """When both are provided, auto-wiring should connect them."""
        validator = TaskValidator()
        pipeline = CoordinatorPipeline()
        # Order matters: pipeline first, then validator
        integrator = SwarmIntegrator.create_with_components(
            components={
                "coordinator_pipeline": pipeline,
                "task_validator": validator,
            }
        )
        self.assertIs(integrator._task_validator, validator)
        self.assertIs(integrator._coordinator_pipeline, pipeline)


class TestWiringDiagram(unittest.TestCase):
    """Test wiring diagram includes TaskValidator."""

    def test_diagram_includes_validator(self):
        integrator = SwarmIntegrator()
        integrator.set_task_validator(TaskValidator())
        diagram = integrator.get_wiring_diagram()
        self.assertIn("TaskValidator", diagram)
        self.assertIn("#58", diagram)

    def test_diagram_shows_pipeline_wiring(self):
        integrator = SwarmIntegrator()
        pipeline = CoordinatorPipeline()
        integrator.set_coordinator_pipeline(pipeline)
        integrator.set_task_validator(TaskValidator())
        diagram = integrator.get_wiring_diagram()
        self.assertIn("CoordinatorPipeline", diagram)

    def test_diagram_without_validator(self):
        integrator = SwarmIntegrator()
        diagram = integrator.get_wiring_diagram()
        self.assertNotIn("TaskValidator", diagram)


class TestStatusReporting(unittest.TestCase):
    """Test status reporting includes TaskValidator info."""

    def test_integrator_health_with_validator(self):
        integrator = SwarmIntegrator()
        validator = TaskValidator()
        integrator.set_task_validator(validator)
        health = integrator.health()
        self.assertIn("task_validator", health["components"]["details"])

    def test_validator_health_check_in_status(self):
        validator = TaskValidator()
        h = validator.health_check()
        self.assertTrue(h["healthy"])
        self.assertEqual(h["component"], "TaskValidator")


class TestEdgeCases(unittest.TestCase):
    """Edge cases for integration."""

    def test_set_none_validator(self):
        integrator = SwarmIntegrator()
        integrator.set_task_validator(None)
        self.assertIsNone(integrator._task_validator)

    def test_replace_validator(self):
        integrator = SwarmIntegrator()
        v1 = TaskValidator(min_bounty=0.01)
        v2 = TaskValidator(min_bounty=1.00)
        integrator.set_task_validator(v1)
        integrator.set_task_validator(v2)
        self.assertIs(integrator._task_validator, v2)

    def test_pipeline_replace_validator(self):
        pipeline = CoordinatorPipeline()
        v1 = TaskValidator()
        v2 = TaskValidator()
        pipeline.set_task_validator(v1)
        pipeline.set_task_validator(v2)
        self.assertIs(pipeline.task_validator, v2)


if __name__ == "__main__":
    unittest.main()
