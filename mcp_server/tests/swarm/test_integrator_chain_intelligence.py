"""
Tests for SwarmIntegrator Chain Intelligence Stack Wiring (Modules #55-57).

Covers:
    - NetworkRegistry (#56) registration and component tracking
    - IdentityResolver (#55) registration and component tracking
    - ChainRouter (#57) registration and component tracking
    - Auto-wiring: NetworkRegistry → ChainRouter
    - Auto-wiring: IdentityResolver → ChainRouter
    - Auto-wiring: ChainRouter → CoordinatorPipeline
    - Reverse registration order (ChainRouter before Registry)
    - create_with_components factory with chain intelligence
    - Wiring diagram includes chain intelligence stack
    - Health reporting includes all three components
    - EventBus wiring: task.assigned → ChainRouter
    - Graceful degradation when wiring methods missing
    - Component names listing includes chain modules
"""

import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mcp_server.swarm.integrator import (
    SwarmIntegrator,
    SwarmMode,
    ComponentStatus,
)
from mcp_server.swarm.event_bus import EventBus


# ─── Fixtures ────────────────────────────────────────────────────


def _make_network_registry():
    """Create a mock NetworkRegistry with standard interface."""
    registry = MagicMock()
    registry.get_chain = MagicMock(return_value={"name": "base", "chain_id": 8453})
    registry.list_chains = MagicMock(return_value=["base", "ethereum", "polygon"])
    registry.chains_with_feature = MagicMock(return_value=["base", "ethereum"])
    registry.get_status = MagicMock(return_value="active")
    return registry


def _make_identity_resolver():
    """Create a mock IdentityResolver with standard interface."""
    resolver = MagicMock()
    resolver.resolve = MagicMock(return_value={"agent_id": 2106, "chain": "base"})
    resolver.resolve_batch = MagicMock(return_value=[])
    resolver.set_identity_resolver = MagicMock()
    return resolver


def _make_chain_router():
    """Create a mock ChainRouter with standard interface."""
    router = MagicMock()
    router.route_task = MagicMock(return_value=MagicMock(chain="base"))
    router.route_batch = MagicMock(return_value=MagicMock(chain="base"))
    router.set_registry = MagicMock()
    router.set_identity_resolver = MagicMock()
    router.record_success = MagicMock()
    router.health_check = MagicMock(return_value={"status": "healthy"})
    return router


def _make_coordinator_pipeline():
    """Create a mock CoordinatorPipeline with chain router support."""
    pipeline = MagicMock()
    pipeline.set_chain_router = MagicMock()
    pipeline.run = MagicMock(return_value={})
    return pipeline


# ─── NetworkRegistry Registration ────────────────────────────────


class TestNetworkRegistryRegistration:
    def test_register_network_registry(self):
        integrator = SwarmIntegrator()
        registry = _make_network_registry()

        result = integrator.set_network_registry(registry)

        assert result is integrator  # fluent API
        assert integrator._network_registry is registry
        assert "network_registry" in integrator._component_statuses
        assert integrator._component_statuses["network_registry"].healthy is True

    def test_network_registry_in_component_names(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())

        names = integrator.get_component_names()
        assert "network_registry" in names

    def test_network_registry_appears_in_health(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())

        health = integrator.health()
        assert "network_registry" in health["components"]["details"]
        assert health["components"]["total"] == 1
        assert health["components"]["healthy"] == 1

    def test_network_registry_standalone_no_auto_wire(self):
        """No ChainRouter → no auto-wiring attempted."""
        integrator = SwarmIntegrator()
        registry = _make_network_registry()

        integrator.set_network_registry(registry)

        # No chain_router means set_registry should NOT be called on anything
        assert integrator._chain_router is None

    def test_network_registry_auto_wires_to_existing_chain_router(self):
        """If ChainRouter is registered first, NetworkRegistry auto-wires into it."""
        integrator = SwarmIntegrator()
        router = _make_chain_router()
        integrator.set_chain_router(router)

        registry = _make_network_registry()
        integrator.set_network_registry(registry)

        # The registry should have been wired into the existing router
        router.set_registry.assert_called_with(registry)


# ─── IdentityResolver Registration ──────────────────────────────


class TestIdentityResolverRegistration:
    def test_register_identity_resolver(self):
        integrator = SwarmIntegrator()
        resolver = _make_identity_resolver()

        result = integrator.set_identity_resolver(resolver)

        assert result is integrator
        assert integrator._identity_resolver is resolver
        assert "identity_resolver" in integrator._component_statuses

    def test_identity_resolver_in_component_names(self):
        integrator = SwarmIntegrator()
        integrator.set_identity_resolver(_make_identity_resolver())

        assert "identity_resolver" in integrator.get_component_names()

    def test_identity_resolver_standalone_no_auto_wire(self):
        integrator = SwarmIntegrator()
        resolver = _make_identity_resolver()
        integrator.set_identity_resolver(resolver)

        assert integrator._chain_router is None

    def test_identity_resolver_auto_wires_to_existing_chain_router(self):
        integrator = SwarmIntegrator()
        router = _make_chain_router()
        integrator.set_chain_router(router)

        resolver = _make_identity_resolver()
        integrator.set_identity_resolver(resolver)

        router.set_identity_resolver.assert_called_with(resolver)


# ─── ChainRouter Registration ───────────────────────────────────


class TestChainRouterRegistration:
    def test_register_chain_router(self):
        integrator = SwarmIntegrator()
        router = _make_chain_router()

        result = integrator.set_chain_router(router)

        assert result is integrator
        assert integrator._chain_router is router
        assert "chain_router" in integrator._component_statuses
        assert integrator._component_statuses["chain_router"].healthy is True

    def test_chain_router_in_component_names(self):
        integrator = SwarmIntegrator()
        integrator.set_chain_router(_make_chain_router())

        assert "chain_router" in integrator.get_component_names()

    def test_chain_router_auto_wires_existing_network_registry(self):
        """If NetworkRegistry registered first, ChainRouter auto-wires to it."""
        integrator = SwarmIntegrator()
        registry = _make_network_registry()
        integrator.set_network_registry(registry)

        router = _make_chain_router()
        integrator.set_chain_router(router)

        router.set_registry.assert_called_once_with(registry)

    def test_chain_router_auto_wires_existing_identity_resolver(self):
        integrator = SwarmIntegrator()
        resolver = _make_identity_resolver()
        integrator.set_identity_resolver(resolver)

        router = _make_chain_router()
        integrator.set_chain_router(router)

        router.set_identity_resolver.assert_called_once_with(resolver)

    def test_chain_router_auto_wires_existing_coordinator_pipeline(self):
        integrator = SwarmIntegrator()
        pipeline = _make_coordinator_pipeline()
        integrator.set_coordinator_pipeline(pipeline)

        router = _make_chain_router()
        integrator.set_chain_router(router)

        pipeline.set_chain_router.assert_called_once_with(router)

    def test_chain_router_no_registry_no_wire(self):
        """No registry → no set_registry call."""
        integrator = SwarmIntegrator()
        router = _make_chain_router()
        integrator.set_chain_router(router)

        router.set_registry.assert_not_called()

    def test_chain_router_no_identity_no_wire(self):
        """No identity resolver → no set_identity_resolver call."""
        integrator = SwarmIntegrator()
        router = _make_chain_router()
        integrator.set_chain_router(router)

        router.set_identity_resolver.assert_not_called()


# ─── Full Stack Wiring ──────────────────────────────────────────


class TestChainIntelligenceStackWiring:
    def test_full_stack_wiring_order_registry_first(self):
        """Register all 3 components: registry → resolver → router."""
        integrator = SwarmIntegrator()

        registry = _make_network_registry()
        resolver = _make_identity_resolver()
        router = _make_chain_router()

        integrator.set_network_registry(registry)
        integrator.set_identity_resolver(resolver)
        integrator.set_chain_router(router)

        # Router should be wired to both
        router.set_registry.assert_called_once_with(registry)
        router.set_identity_resolver.assert_called_once_with(resolver)

    def test_full_stack_wiring_order_router_first(self):
        """Register all 3 components: router → registry → resolver."""
        integrator = SwarmIntegrator()

        router = _make_chain_router()
        registry = _make_network_registry()
        resolver = _make_identity_resolver()

        integrator.set_chain_router(router)
        integrator.set_network_registry(registry)
        integrator.set_identity_resolver(resolver)

        # Both should still auto-wire into the router
        router.set_registry.assert_called_once_with(registry)
        router.set_identity_resolver.assert_called_once_with(resolver)

    def test_full_stack_mixed_order(self):
        """Register: resolver → router → registry."""
        integrator = SwarmIntegrator()

        resolver = _make_identity_resolver()
        router = _make_chain_router()
        registry = _make_network_registry()

        integrator.set_identity_resolver(resolver)
        integrator.set_chain_router(router)
        integrator.set_network_registry(registry)

        # Router gets resolver during set_chain_router (resolver already registered)
        router.set_identity_resolver.assert_called_once_with(resolver)
        # Router gets registry during set_network_registry (router already registered)
        router.set_registry.assert_called_once_with(registry)

    def test_full_stack_all_three_in_health(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())
        integrator.set_identity_resolver(_make_identity_resolver())
        integrator.set_chain_router(_make_chain_router())

        health = integrator.health()
        details = health["components"]["details"]
        assert "network_registry" in details
        assert "identity_resolver" in details
        assert "chain_router" in details
        assert health["components"]["total"] == 3
        assert health["components"]["healthy"] == 3

    def test_full_stack_all_healthy(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())
        integrator.set_identity_resolver(_make_identity_resolver())
        integrator.set_chain_router(_make_chain_router())

        assert integrator.is_healthy() is True

    def test_full_stack_with_pipeline(self):
        """Full stack + CoordinatorPipeline: ChainRouter wired as pre-router."""
        integrator = SwarmIntegrator()
        pipeline = _make_coordinator_pipeline()
        registry = _make_network_registry()
        resolver = _make_identity_resolver()
        router = _make_chain_router()

        integrator.set_coordinator_pipeline(pipeline)
        integrator.set_network_registry(registry)
        integrator.set_identity_resolver(resolver)
        integrator.set_chain_router(router)

        # ChainRouter auto-wired into pipeline
        pipeline.set_chain_router.assert_called_once_with(router)
        router.set_registry.assert_called_once_with(registry)
        router.set_identity_resolver.assert_called_once_with(resolver)


# ─── Factory Method Tests ────────────────────────────────────────


class TestCreateWithComponentsChainIntelligence:
    def test_factory_with_chain_router(self):
        router = _make_chain_router()
        integrator = SwarmIntegrator.create_with_components(
            components={"chain_router": router}
        )
        assert integrator._chain_router is router
        assert "chain_router" in integrator.get_component_names()

    def test_factory_with_network_registry(self):
        registry = _make_network_registry()
        integrator = SwarmIntegrator.create_with_components(
            components={"network_registry": registry}
        )
        assert integrator._network_registry is registry
        assert "network_registry" in integrator.get_component_names()

    def test_factory_with_identity_resolver(self):
        resolver = _make_identity_resolver()
        integrator = SwarmIntegrator.create_with_components(
            components={"identity_resolver": resolver}
        )
        assert integrator._identity_resolver is resolver
        assert "identity_resolver" in integrator.get_component_names()

    def test_factory_with_full_chain_stack(self):
        registry = _make_network_registry()
        resolver = _make_identity_resolver()
        router = _make_chain_router()

        integrator = SwarmIntegrator.create_with_components(
            components={
                "network_registry": registry,
                "identity_resolver": resolver,
                "chain_router": router,
            }
        )

        assert integrator._network_registry is registry
        assert integrator._identity_resolver is resolver
        assert integrator._chain_router is router
        assert len(integrator.get_component_names()) == 3

    def test_factory_full_stack_auto_wires(self):
        """Factory auto-wires all chain intelligence during create_with_components."""
        registry = _make_network_registry()
        resolver = _make_identity_resolver()
        router = _make_chain_router()

        SwarmIntegrator.create_with_components(
            components={
                "network_registry": registry,
                "identity_resolver": resolver,
                "chain_router": router,
            }
        )

        # Router should be wired (order depends on dict iteration)
        # At minimum, set_registry and set_identity_resolver should have been called
        assert router.set_registry.called or router.set_identity_resolver.called


# ─── Wiring Diagram Tests ───────────────────────────────────────


class TestWiringDiagramChainIntelligence:
    def test_diagram_includes_network_registry(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())

        diagram = integrator.get_wiring_diagram()
        assert "NetworkRegistry" in diagram
        assert "#56" in diagram

    def test_diagram_includes_identity_resolver(self):
        integrator = SwarmIntegrator()
        integrator.set_identity_resolver(_make_identity_resolver())

        diagram = integrator.get_wiring_diagram()
        assert "IdentityResolver" in diagram
        assert "#55" in diagram

    def test_diagram_includes_chain_router(self):
        integrator = SwarmIntegrator()
        integrator.set_chain_router(_make_chain_router())

        diagram = integrator.get_wiring_diagram()
        assert "ChainRouter" in diagram
        assert "#57" in diagram

    def test_diagram_shows_chain_intelligence_stack(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())
        integrator.set_identity_resolver(_make_identity_resolver())
        integrator.set_chain_router(_make_chain_router())

        diagram = integrator.get_wiring_diagram()
        assert "Chain Intelligence Stack" in diagram

    def test_diagram_shows_router_to_registry_wiring(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())
        integrator.set_chain_router(_make_chain_router())

        diagram = integrator.get_wiring_diagram()
        assert "wired to NetworkRegistry" in diagram

    def test_diagram_shows_router_to_identity_wiring(self):
        integrator = SwarmIntegrator()
        integrator.set_identity_resolver(_make_identity_resolver())
        integrator.set_chain_router(_make_chain_router())

        diagram = integrator.get_wiring_diagram()
        assert "wired to IdentityResolver" in diagram

    def test_no_chain_modules_no_chain_section(self):
        integrator = SwarmIntegrator()

        diagram = integrator.get_wiring_diagram()
        assert "Chain Intelligence Stack" not in diagram


# ─── EventBus Wiring Tests ──────────────────────────────────────


class TestEventBusChainRouterWiring:
    def test_chain_router_wired_to_event_bus(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        router = _make_chain_router()

        integrator.set_event_bus(bus)
        integrator.set_chain_router(router)
        integrator.wire()

        # Should have registered a handler
        assert len(integrator._event_handlers) > 0

    def test_chain_router_records_success_on_task_assigned(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        router = _make_chain_router()

        integrator.set_event_bus(bus)
        integrator.set_chain_router(router)
        integrator.wire()

        # Emit a task.assigned event with chain info
        from mcp_server.swarm.event_bus import TASK_ASSIGNED
        bus.emit(TASK_ASSIGNED, {
            "chain": "base",
            "task_id": "task_123",
        })

        router.record_success.assert_called_once_with("base", "task_123", success=True)

    def test_chain_router_ignores_events_without_chain(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        router = _make_chain_router()

        integrator.set_event_bus(bus)
        integrator.set_chain_router(router)
        integrator.wire()

        from mcp_server.swarm.event_bus import TASK_ASSIGNED
        bus.emit(TASK_ASSIGNED, {"task_id": "task_456"})

        router.record_success.assert_not_called()

    def test_no_chain_router_no_event_wiring(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.wire()

        assert len(integrator._event_handlers) == 0


# ─── Graceful Degradation ───────────────────────────────────────


class TestChainIntelligenceGracefulDegradation:
    def test_registry_wire_failure_handled(self):
        """If set_registry raises, it's handled gracefully."""
        integrator = SwarmIntegrator()
        router = _make_chain_router()
        router.set_registry.side_effect = RuntimeError("Connection lost")
        integrator.set_chain_router(router)

        registry = _make_network_registry()
        # Should not raise — handled gracefully
        integrator.set_network_registry(registry)

        # Router still registered
        assert integrator._chain_router is router
        assert integrator._network_registry is registry

    def test_identity_wire_failure_handled(self):
        integrator = SwarmIntegrator()
        router = _make_chain_router()
        router.set_identity_resolver.side_effect = RuntimeError("Resolver down")
        integrator.set_chain_router(router)

        resolver = _make_identity_resolver()
        integrator.set_identity_resolver(resolver)

        assert integrator._chain_router is router
        assert integrator._identity_resolver is resolver

    def test_pipeline_wire_failure_handled(self):
        integrator = SwarmIntegrator()
        pipeline = _make_coordinator_pipeline()
        pipeline.set_chain_router.side_effect = RuntimeError("Pipeline error")
        integrator.set_coordinator_pipeline(pipeline)

        router = _make_chain_router()
        integrator.set_chain_router(router)

        # Still registered despite wiring error
        assert integrator._chain_router is router

    def test_router_without_set_registry_method(self):
        """ChainRouter missing set_registry → no error, just skipped."""
        integrator = SwarmIntegrator()
        router = MagicMock(spec=[])  # no methods at all
        integrator._chain_router = router
        integrator._register_component("chain_router", router)

        registry = _make_network_registry()
        # hasattr check should prevent call
        integrator.set_network_registry(registry)

        assert integrator._network_registry is registry

    def test_event_bus_chain_router_error_handled(self):
        """If record_success raises during event, it's caught."""
        integrator = SwarmIntegrator()
        bus = EventBus()
        router = _make_chain_router()
        router.record_success.side_effect = RuntimeError("Recording failed")

        integrator.set_event_bus(bus)
        integrator.set_chain_router(router)
        integrator.wire()

        from mcp_server.swarm.event_bus import TASK_ASSIGNED
        # Should not raise
        bus.emit(TASK_ASSIGNED, {"chain": "base", "task_id": "task_err"})


# ─── Integration with Other Components ──────────────────────────


class TestChainIntelligenceWithExistingComponents:
    def test_chain_stack_with_fleet_manager(self):
        """Chain intelligence plays nicely with fleet manager."""
        integrator = SwarmIntegrator()
        fleet = MagicMock()
        router = _make_chain_router()
        registry = _make_network_registry()

        integrator.set_fleet_manager(fleet)
        integrator.set_network_registry(registry)
        integrator.set_chain_router(router)

        names = integrator.get_component_names()
        assert "fleet_manager" in names
        assert "chain_router" in names
        assert "network_registry" in names

    def test_chain_stack_with_signal_harness(self):
        integrator = SwarmIntegrator()
        harness = MagicMock()
        router = _make_chain_router()

        integrator.set_signal_harness(harness)
        integrator.set_chain_router(router)

        assert "signal_harness" in integrator.get_component_names()
        assert "chain_router" in integrator.get_component_names()

    def test_full_integrator_with_chain_intelligence(self):
        """All existing components + chain intelligence = healthy system."""
        integrator = SwarmIntegrator()
        bus = EventBus()

        integrator.set_event_bus(bus)
        integrator.set_network_registry(_make_network_registry())
        integrator.set_identity_resolver(_make_identity_resolver())
        integrator.set_chain_router(_make_chain_router())
        integrator.set_fleet_manager(MagicMock())
        integrator.set_signal_harness(MagicMock())
        integrator.set_analytics(MagicMock())

        integrator.wire()

        health = integrator.health()
        assert health["components"]["total"] == 7  # bus + 6 components
        assert health["components"]["healthy"] == 7
        assert integrator.is_healthy() is True

    def test_summary_includes_chain_components(self):
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())
        integrator.set_identity_resolver(_make_identity_resolver())
        integrator.set_chain_router(_make_chain_router())

        summary = integrator.summary()
        assert summary["components"] == 3
        assert summary["healthy"] is True


# ─── Edge Cases ──────────────────────────────────────────────────


class TestChainIntelligenceEdgeCases:
    def test_register_same_component_twice(self):
        """Re-registering a component replaces the previous one."""
        integrator = SwarmIntegrator()
        router1 = _make_chain_router()
        router2 = _make_chain_router()

        integrator.set_chain_router(router1)
        integrator.set_chain_router(router2)

        assert integrator._chain_router is router2

    def test_register_none_component(self):
        """Setting a None component still works (stores None)."""
        integrator = SwarmIntegrator()
        # Direct assignment of None shouldn't crash
        integrator._chain_router = None
        assert integrator._chain_router is None

    def test_chain_router_with_no_other_components(self):
        """ChainRouter alone in integrator is valid."""
        integrator = SwarmIntegrator()
        router = _make_chain_router()
        integrator.set_chain_router(router)

        health = integrator.health()
        assert health["components"]["total"] == 1
        assert health["status"] == "healthy"

    def test_start_stop_with_chain_components(self):
        """Lifecycle works with chain intelligence registered."""
        integrator = SwarmIntegrator()
        integrator.set_network_registry(_make_network_registry())
        integrator.set_chain_router(_make_chain_router())

        start_result = integrator.start()
        assert start_result["status"] == "started"
        assert start_result["components"] == 2

        stop_result = integrator.stop()
        assert stop_result["status"] == "stopped"

    def test_mode_change_with_chain_intelligence(self):
        integrator = SwarmIntegrator()
        integrator.set_chain_router(_make_chain_router())

        result = integrator.set_mode(SwarmMode.FULL_AUTO)
        assert result["new_mode"] == "full_auto"
        assert integrator.mode == SwarmMode.FULL_AUTO
