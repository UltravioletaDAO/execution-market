#!/usr/bin/env python3
"""
Quick script to post a Chamba task.

Usage:
    python post_task.py "Verify business open" "Go to 123 Main St, photo storefront" 0.50 4
    
Args:
    title: Task title
    instructions: Detailed instructions
    bounty: USD amount (e.g., 0.50)
    hours: Deadline in hours
"""

import sys
import os
import json

# Add parent dir to path for chamba module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chamba import ChambaClient, TaskCategory

def main():
    if len(sys.argv) < 5:
        print("Usage: post_task.py <title> <instructions> <bounty_usd> <deadline_hours> [category] [evidence_type]")
        print("\nCategories: physical_presence, knowledge_access, human_authority, simple_action, digital_physical")
        print("Evidence: photo, photo_geo, video, document, signature, text_response")
        sys.exit(1)
    
    title = sys.argv[1]
    instructions = sys.argv[2]
    bounty = float(sys.argv[3])
    hours = float(sys.argv[4])
    category = sys.argv[5] if len(sys.argv) > 5 else "physical_presence"
    evidence = sys.argv[6] if len(sys.argv) > 6 else "photo_geo"
    
    api_key = os.environ.get("CHAMBA_API_KEY")
    if not api_key:
        print("Error: CHAMBA_API_KEY environment variable not set")
        sys.exit(1)
    
    client = ChambaClient(api_key=api_key)
    
    task = client.create_task(
        title=title,
        instructions=instructions,
        category=category,
        bounty_usd=bounty,
        evidence_required=[evidence],
        deadline_hours=hours
    )
    
    print(json.dumps({
        "task_id": task.id,
        "title": task.title,
        "bounty_usd": task.bounty_usd,
        "status": task.status.value,
        "deadline": task.deadline.isoformat()
    }, indent=2))

if __name__ == "__main__":
    main()
