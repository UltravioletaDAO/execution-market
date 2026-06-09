"""MCP tool packages for em-k1-mcp.

Each module groups related tools and exposes a ``register_*`` function that
attaches them to a :class:`FastMCP` instance, matching the convention used
in the main Execution Market server (``mcp_server/tools/``).
"""

from .locomotion import register_locomotion_tools
from .manipulation import register_manipulation_tools
from .perception import register_perception_tools
from .em_integration import register_em_integration_tools

__all__ = [
    "register_locomotion_tools",
    "register_manipulation_tools",
    "register_perception_tools",
    "register_em_integration_tools",
]
