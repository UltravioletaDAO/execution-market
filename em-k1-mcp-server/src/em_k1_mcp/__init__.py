"""em-k1-mcp — MCP server for the Booster K1 humanoid robot.

This package exposes a FastMCP server that lets Claude Code (or any MCP
client) drive a Booster K1 humanoid through a backend abstraction. Three
backends are shipped:

* :class:`em_k1_mcp.backends.mock.MockK1Backend` — deterministic, no hardware.
* :class:`em_k1_mcp.backends.isaac_sim.IsaacSimK1Backend` — stub for NVIDIA Isaac Sim.
* :class:`em_k1_mcp.backends.hardware.HardwareK1Backend` — wraps the real
  ``booster_robotics_sdk`` (installed manually when the robot arrives).

The package also wires the K1 into Execution Market via two tools
(``em_claim_task``, ``em_submit_evidence``) so the robot can act as a
registered worker on the marketplace.
"""

__version__ = "0.1.0"
