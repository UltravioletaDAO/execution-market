import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.coordinator import SwarmCoordinator


def main():
    print("Testing SwarmCoordinator against Live EM API...")

    coordinator = SwarmCoordinator.create(em_api_url="https://api.execution.market")

    print("\n--- Health Check ---")
    try:
        health = coordinator.em_client.get_health()
        print(f"Health: {health}")
    except Exception as e:
        print(f"Error checking health: {e}")

    print("\n--- Fetching recent tasks ---")
    try:
        tasks = coordinator.em_client.list_tasks(limit=5)
        print(f"Fetched {len(tasks)} tasks.")
        for task in tasks:
            print(
                f"- Task {task.get('id')}: {task.get('title')} ({task.get('status')})"
            )
    except Exception as e:
        print(f"Error fetching tasks: {e}")


if __name__ == "__main__":
    main()
