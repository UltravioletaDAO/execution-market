"""FastMCP server entry point for em-k1-mcp.

Run with:

    python -m em_k1_mcp.server

Or, after ``pip install -e .``:

    em-k1-mcp

The MCP server exposes:

* Locomotion tools  : ``k1_stand``, ``k1_sit``, ``k1_walk_to``, ``k1_emergency_stop``
* Manipulation tools: ``k1_pick``, ``k1_place``, ``k1_grip``
* Perception tools  : ``k1_observe``
* EM integration    : ``em_claim_task``, ``em_submit_evidence``

Tools dispatch through a :class:`em_k1_mcp.backends.base.BaseK1Backend`,
which is selected by the ``K1_BACKEND`` env var (``mock`` by default).
"""

from __future__ import annotations

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .backends import get_backend
from .backends.base import BaseK1Backend
from .config import K1Config, load_config
from .tools.em_integration import register_em_integration_tools
from .tools.locomotion import register_locomotion_tools
from .tools.manipulation import register_manipulation_tools
from .tools.perception import register_perception_tools

logger = logging.getLogger(__name__)


SERVER_NAME = "em-k1-mcp"


def build_server(
    config: Optional[K1Config] = None,
    backend: Optional[BaseK1Backend] = None,
) -> FastMCP:
    """Construct and wire a FastMCP server.

    Args:
        config: Optional pre-loaded config. Tests pass a fixture.
        backend: Optional pre-instantiated backend. Tests pass a mock.

    Returns:
        A :class:`FastMCP` instance with all tools registered.
    """
    config = config or load_config()
    backend = backend or get_backend(config)

    logging.basicConfig(level=config.log_level)
    logger.info(
        "Starting %s — backend=%s, K1_HOST=%s, EM_API_URL=%s",
        SERVER_NAME,
        backend.name,
        config.k1_host,
        config.em_api_url,
    )

    mcp = FastMCP(SERVER_NAME)

    register_locomotion_tools(mcp, backend, config)
    register_manipulation_tools(mcp, backend, config)
    register_perception_tools(mcp, backend, config)
    register_em_integration_tools(mcp, config)

    # Stash references on the server for shutdown handlers / tests.
    mcp._em_k1_backend = backend  # type: ignore[attr-defined]
    mcp._em_k1_config = config  # type: ignore[attr-defined]

    return mcp


def main() -> None:
    """CLI entry point (``em-k1-mcp`` console script)."""
    mcp = build_server()
    # FastMCP.run() blocks; transport defaults to stdio which is what
    # Claude Code expects when you register via `claude mcp add`.
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
