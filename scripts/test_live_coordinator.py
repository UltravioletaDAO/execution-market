import sys
import os
import json
import logging
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../mcp_server')))

from swarm.coordinator import SwarmCoordinator

logging.basicConfig(level=logging.INFO)

async def run():
    print("Testing SwarmCoordinator against live API...")
    try:
        coordinator = SwarmCoordinator.create(
            em_api_url="https://api.execution.market",
            autojob_url="https://autojob.cc"
        )
        print("Coordinator created successfully.")
        
        # Fetch completed tasks
        print("\nFetching 'completed' tasks...")
        tasks = coordinator.em_client._request("GET", "/api/v1/tasks?status=completed&limit=5")
        tasks_list = tasks.get('data', [])
        print(f"Found {len(tasks_list)} completed tasks.")
        for i, t in enumerate(tasks_list[:5]):
            print(f"  {i+1}. [{t.get('id')}] {t.get('title')} (Bounty: {t.get('bounty_amount')} {t.get('token_symbol')})")

    except Exception as e:
        print(f"Error testing live coordinator: {e}")

if __name__ == "__main__":
    asyncio.run(run())
