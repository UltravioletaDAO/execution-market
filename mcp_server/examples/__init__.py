"""
Chamba MCP Server Examples

Example scripts demonstrating how to use the Chamba Human Execution Layer.

Available Examples:
    - agent_publish_task.py: Example agent publishing a task
    - worker_complete_task.py: Example worker flow
    - mcp_client.py: Using MCP protocol directly

Usage:
    # Run agent example
    python -m examples.agent_publish_task

    # Run worker example
    python -m examples.worker_complete_task

    # Run MCP client example (mock mode)
    python -m examples.mcp_client

    # Run MCP client example (real server)
    USE_MOCK=false CHAMBA_MCP_URL=http://localhost:8000/mcp python -m examples.mcp_client

Environment Variables:
    AGENT_ID: Your agent identifier (wallet address or ERC-8004 ID)
    EXECUTOR_ID: Your executor/worker ID
    CHAMBA_API_KEY: Your API key
    CHAMBA_MCP_URL: MCP server Streamable HTTP URL (e.g., http://localhost:8000/mcp)
    USE_MOCK: Set to 'false' to connect to real server
"""
