"""
Task commands for Chamba CLI (Worker perspective).

Commands:
    chamba tasks list --location "lat,lng" --radius 10
    chamba tasks apply <task-id>
    chamba tasks submit <task-id> --evidence <file>
"""

import sys
import json
from typing import Optional, Tuple
from pathlib import Path

import click

from ..config import get_api_key, get_config_manager
from ..api import (
    ChambaAPIClient,
    APIError,
    Task,
    TaskStatus,
    TaskCategory,
    EvidenceType,
    get_client,
)
from ..output import (
    console,
    print_tasks_table,
    print_task_detail,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_json,
    spinner,
    confirm,
    OutputFormat,
)


def parse_location(location_str: str) -> Tuple[float, float]:
    """
    Parse location string in format "lat,lng".

    Args:
        location_str: Location string like "19.4326,-99.1332"

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        click.BadParameter: If format is invalid
    """
    try:
        parts = location_str.split(",")
        if len(parts) != 2:
            raise ValueError("Expected format: lat,lng")
        lat = float(parts[0].strip())
        lng = float(parts[1].strip())

        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
        if not (-180 <= lng <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {lng}")

        return (lat, lng)
    except ValueError as e:
        raise click.BadParameter(
            f"Invalid location format: {e}. Expected: 'lat,lng' (e.g., '19.4326,-99.1332')"
        )


@click.group(name="tasks")
def tasks_group():
    """Task operations for workers."""
    pass


@tasks_group.command("list")
@click.option(
    "--location", "-l",
    help="Location as 'lat,lng' (e.g., '19.4326,-99.1332')"
)
@click.option(
    "--radius", "-r",
    type=float,
    default=10.0,
    help="Search radius in kilometers (default: 10)"
)
@click.option(
    "--status", "-s",
    type=click.Choice([s.value for s in TaskStatus]),
    default="published",
    help="Filter by status (default: published)"
)
@click.option(
    "--category", "-c",
    type=click.Choice([c.value for c in TaskCategory]),
    help="Filter by category"
)
@click.option(
    "--min-bounty",
    type=float,
    help="Minimum bounty amount in USD"
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum results (default: 20)"
)
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json", "minimal"]),
    default="table",
    help="Output format"
)
@click.pass_context
def list_tasks(
    ctx,
    location: Optional[str],
    radius: float,
    status: str,
    category: Optional[str],
    min_bounty: Optional[float],
    limit: int,
    output: str,
):
    """
    List available tasks, optionally filtered by location.

    Examples:

        # List all published tasks
        chamba tasks list

        # List tasks near a location
        chamba tasks list --location "19.4326,-99.1332" --radius 5

        # List high-value tasks
        chamba tasks list --min-bounty 10 --category physical_presence

        # Get JSON output for scripting
        chamba tasks list --output json
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'chamba login --wallet <address>' first.")
        sys.exit(1)

    # Parse location if provided
    lat, lng = None, None
    if location:
        lat, lng = parse_location(location)

    try:
        with spinner("Fetching tasks..."):
            client = get_client()

            # Build query params
            params = {
                "status": status,
                "limit": limit,
            }
            if category:
                params["category"] = category
            if min_bounty:
                params["min_bounty"] = min_bounty
            if lat is not None and lng is not None:
                params["lat"] = lat
                params["lng"] = lng
                params["radius_km"] = radius

            # Use list_tasks with geo params
            tasks = client.list_tasks(
                status=status,
                category=category,
                limit=limit,
            )

            # Client-side geo filtering if API doesn't support it
            if lat is not None and lng is not None:
                # Note: In production, this would be done server-side
                # This is a placeholder for client-side filtering
                pass

        if output == OutputFormat.JSON:
            print_json([t.__dict__ for t in tasks])
        elif output == OutputFormat.MINIMAL:
            for task in tasks:
                print(task.id)
        else:
            title = "Available Tasks"
            if location:
                title += f" near ({lat:.4f}, {lng:.4f})"
            print_tasks_table(tasks, title=title)

            if location:
                print_info(f"Showing tasks within {radius}km radius")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks_group.command("apply")
@click.argument("task_id")
@click.option(
    "--message", "-m",
    help="Message to the agent"
)
@click.pass_context
def apply_task(ctx, task_id: str, message: Optional[str]):
    """
    Apply to a task as a worker.

    Once your application is accepted, you can start working on the task
    and submit evidence when complete.

    Examples:

        chamba tasks apply abc123

        chamba tasks apply abc123 --message "I can complete this within 2 hours"
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'chamba login --wallet <address>' first.")
        sys.exit(1)

    config_mgr = get_config_manager()
    executor_id = config_mgr.get_executor_id()

    if not executor_id:
        print_error("No executor ID configured.")
        print_info("Run 'chamba login --wallet <addr> --executor-id <id>' to set up worker mode.")
        sys.exit(1)

    try:
        # First, show task details
        with spinner("Fetching task details..."):
            client = get_client()
            task = client.get_task(task_id)

        print_task_detail(task)
        console.print()

        if task.status != "published":
            print_warning(f"Task is not available for application (status: {task.status})")
            sys.exit(1)

        if not confirm(f"Apply to this task for ${task.bounty_usd:.2f}?"):
            print_info("Application cancelled")
            return

        with spinner("Submitting application..."):
            result = client.apply_to_task(task_id, message)

        if result.get("status") == "accepted":
            print_success(f"You have been assigned to task {task_id}")
            print_info("Start working and submit evidence when complete:")
            print_info(f"  chamba tasks submit {task_id} --evidence @evidence.json")
        else:
            print_success(f"Application submitted for task {task_id}")
            print_info("Your application is pending approval from the agent.")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks_group.command("submit")
@click.argument("task_id")
@click.option(
    "--evidence", "-e",
    required=True,
    help="Evidence JSON string or @file.json"
)
@click.option(
    "--notes", "-n",
    help="Additional notes about the submission"
)
@click.pass_context
def submit_task(ctx, task_id: str, evidence: str, notes: Optional[str]):
    """
    Submit evidence for a completed task.

    Evidence should be provided as JSON matching the task's evidence schema.
    Use @filename.json to read from a file.

    Examples:

        # Inline JSON evidence
        chamba tasks submit abc123 --evidence '{"photo_geo": {"url": "...", "lat": 19.43, "lng": -99.13}}'

        # From file
        chamba tasks submit abc123 --evidence @evidence.json --notes "Completed as requested"
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'chamba login --wallet <address>' first.")
        sys.exit(1)

    config_mgr = get_config_manager()
    executor_id = config_mgr.get_executor_id()

    if not executor_id:
        print_error("No executor ID configured.")
        print_info("Run 'chamba login --wallet <addr> --executor-id <id>' to set up worker mode.")
        sys.exit(1)

    # Parse evidence
    try:
        if evidence.startswith("@"):
            file_path = Path(evidence[1:])
            if not file_path.exists():
                print_error(f"Evidence file not found: {file_path}")
                sys.exit(1)
            with open(file_path) as f:
                evidence_data = json.load(f)
        else:
            evidence_data = json.loads(evidence)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in evidence: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error reading evidence: {e}")
        sys.exit(1)

    try:
        # Show task details first
        with spinner("Validating task..."):
            client = get_client()
            task = client.get_task(task_id)

        console.print(f"[bold]Task:[/bold] {task.title}")
        console.print(f"[bold]Bounty:[/bold] ${task.bounty_usd:.2f}")
        console.print(f"[bold]Required evidence:[/bold] {', '.join(task.evidence_required)}")
        console.print()

        # Validate evidence has required fields
        missing = []
        for req in task.evidence_required:
            if req not in evidence_data:
                missing.append(req)

        if missing:
            print_warning(f"Missing required evidence: {', '.join(missing)}")
            if not confirm("Submit anyway?"):
                print_info("Submission cancelled")
                return

        if not confirm("Submit this evidence?"):
            print_info("Submission cancelled")
            return

        with spinner("Submitting evidence..."):
            submission = client.submit_evidence(task_id, evidence_data, notes)

        print_success(f"Evidence submitted: {submission.id}")
        print_info(f"Pre-check score: {submission.pre_check_score:.2f}")
        print_info(f"Status: {submission.status}")

        if submission.pre_check_score >= 0.8:
            print_info("Pre-check passed. Awaiting agent review.")
        else:
            print_warning("Pre-check score is low. Agent may request additional evidence.")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks_group.command("status")
@click.argument("task_id")
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
@click.pass_context
def task_status(ctx, task_id: str, output: str):
    """
    Get detailed status of a task.

    Examples:

        chamba tasks status abc123

        chamba tasks status abc123 --output json
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'chamba login --wallet <address>' first.")
        sys.exit(1)

    try:
        with spinner("Fetching task..."):
            client = get_client()
            task = client.get_task(task_id)

        if output == OutputFormat.JSON:
            print_json(task.__dict__)
        else:
            print_task_detail(task)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks_group.command("my")
@click.option(
    "--status", "-s",
    type=click.Choice([s.value for s in TaskStatus]),
    help="Filter by status"
)
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json", "minimal"]),
    default="table",
    help="Output format"
)
@click.pass_context
def my_tasks(ctx, status: Optional[str], output: str):
    """
    List tasks assigned to you.

    Examples:

        chamba tasks my

        chamba tasks my --status in_progress
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'chamba login --wallet <address>' first.")
        sys.exit(1)

    config_mgr = get_config_manager()
    executor_id = config_mgr.get_executor_id()

    if not executor_id:
        print_error("No executor ID configured.")
        print_info("Run 'chamba login --wallet <addr> --executor-id <id>' to set up worker mode.")
        sys.exit(1)

    try:
        with spinner("Fetching your tasks..."):
            client = get_client()
            tasks = client.get_my_tasks(status=status)

        if output == OutputFormat.JSON:
            print_json([t.__dict__ for t in tasks])
        elif output == OutputFormat.MINIMAL:
            for task in tasks:
                print(task.id)
        else:
            print_tasks_table(tasks, title="My Tasks")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)
