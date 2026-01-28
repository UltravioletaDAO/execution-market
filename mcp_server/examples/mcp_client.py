#!/usr/bin/env python3
"""
Example: MCP Protocol Client for Chamba

This example demonstrates how to connect to the Chamba MCP server
using the official MCP SDK with SSE (Server-Sent Events) transport.

MCP Transport Options (per MCP spec):
- stdio: For local process communication
- SSE/HTTP: For remote server communication (used here)
- Streamable HTTP: Newer transport option

Note: MCP does NOT use WebSocket. The correct transport for remote
servers is SSE (Server-Sent Events) over HTTP.

Requirements:
    pip install mcp httpx httpx-sse

Usage:
    python mcp_client.py
"""

import asyncio
import os
from typing import Optional, Any

from mcp import ClientSession
from mcp.client.sse import sse_client


# Configuration
MCP_SERVER_URL = os.environ.get(
    "CHAMBA_MCP_URL",
    "https://api.chamba.ultravioletadao.xyz/mcp/sse"
)
API_KEY = os.environ.get("CHAMBA_API_KEY", "")


async def main():
    """
    Main example demonstrating Chamba MCP client usage.

    This shows:
    - Connecting via SSE transport (the correct MCP transport)
    - Listing available tools
    - Calling tools to publish and manage tasks
    """

    print(f"Connecting to Chamba MCP server at {MCP_SERVER_URL}...")

    # Set up headers for authentication
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    # Connect using SSE transport
    async with sse_client(MCP_SERVER_URL, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            print("Connected to Chamba MCP server!")
            print(f"Server: {session.server_info}")

            # List available tools
            print("\n=== Available Tools ===")
            tools = await session.list_tools()

            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description[:60]}...")

            # Example: Get server status
            print("\n=== Server Status ===")
            try:
                result = await session.call_tool(
                    "chamba_server_status",
                    {}
                )
                print(f"Status: {result.content}")
            except Exception as e:
                print(f"Error getting status: {e}")

            # Example: Get fee structure
            print("\n=== Fee Structure ===")
            try:
                result = await session.call_tool(
                    "chamba_get_fee_structure",
                    {}
                )
                print(f"Fees: {result.content}")
            except Exception as e:
                print(f"Error getting fees: {e}")

            # Example: Publish a task (requires valid API key)
            if API_KEY:
                print("\n=== Publishing Task ===")
                try:
                    result = await session.call_tool(
                        "chamba_publish_task",
                        {
                            "agent_id": "example_agent",
                            "title": "Verify coffee shop hours",
                            "instructions": """
                                Visit the coffee shop at 456 Oak Street.
                                Take a photo showing:
                                1. The storefront with visible hours
                                2. Whether currently open/closed
                                Report the current hours.
                            """,
                            "category": "physical_presence",
                            "bounty_usd": 10.00,
                            "deadline_hours": 24,
                            "evidence_required": ["photo_geo", "text_response"],
                            "location_hint": "San Francisco, CA"
                        }
                    )
                    print(f"Task created: {result.content}")
                except Exception as e:
                    print(f"Error publishing task: {e}")
            else:
                print("\n(Skipping task publishing - no API key provided)")


async def list_tools_only():
    """Minimal example: just list available tools."""

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("Chamba MCP Tools:")
            for tool in tools.tools:
                print(f"  {tool.name}")


if __name__ == "__main__":
    print("Chamba MCP Client Example")
    print("=" * 50)
    print("Transport: SSE (Server-Sent Events) over HTTP")
    print("Note: MCP uses SSE/HTTP, NOT WebSocket")
    print("=" * 50)
    print()

    asyncio.run(main())
