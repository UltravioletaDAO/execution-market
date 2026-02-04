"""
Agent commands for Execution Market CLI.

Commands for AI agents or human agents to publish and manage tasks:
    em agent publish --title "..." --bounty 10 --location "lat,lng"
    em agent review <task-id>
    em agent approve <submission-id>
"""

import sys
import json
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

import click

from ..config import get_api_key, get_config_manager
from ..api import (
    EMAPIClient,
    APIError,
    TaskCategory,
    EvidenceType,
    get_client,
)
from ..output import (
    console,
    print_tasks_table,
    print_task_detail,
    print_submissions_table,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_json,
    spinner,
    confirm,
    prompt,
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


@click.group(name="agent")
def agent_group():
    """Agent operations for publishing and managing tasks."""
    pass


@agent_group.command("publish")
@click.option(
    "--title", "-t",
    required=True,
    help="Task title (5-255 characters)"
)
@click.option(
    "--instructions", "-i",
    help="Detailed instructions (20-5000 chars). Use @file.txt to read from file."
)
@click.option(
    "--bounty", "-b",
    type=float,
    required=True,
    help="Bounty amount in USD"
)
@click.option(
    "--location", "-l",
    help="Location as 'lat,lng' (e.g., '19.4326,-99.1332')"
)
@click.option(
    "--location-hint",
    help="Human-readable location hint (e.g., 'Downtown Mexico City')"
)
@click.option(
    "--radius",
    type=float,
    default=5.0,
    help="Location radius in km (default: 5)"
)
@click.option(
    "--category", "-c",
    type=click.Choice([c.value for c in TaskCategory]),
    default="physical_presence",
    help="Task category (default: physical_presence)"
)
@click.option(
    "--evidence", "-e",
    multiple=True,
    type=click.Choice([e.value for e in EvidenceType]),
    default=["photo_geo"],
    help="Required evidence types (can specify multiple)"
)
@click.option(
    "--deadline", "-d",
    type=int,
    default=24,
    help="Deadline in hours from now (default: 24)"
)
@click.option(
    "--min-reputation",
    type=int,
    default=0,
    help="Minimum worker reputation required"
)
@click.option(
    "--token",
    default="USDC",
    help="Payment token (default: USDC)"
)
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json", "minimal"]),
    default="table",
    help="Output format"
)
@click.pass_context
def publish(
    ctx,
    title: str,
    instructions: Optional[str],
    bounty: float,
    location: Optional[str],
    location_hint: Optional[str],
    radius: float,
    category: str,
    evidence: tuple,
    deadline: int,
    min_reputation: int,
    token: str,
    output: str,
):
    """
    Publish a new task as an agent.

    Creates a task with the specified parameters and escrows the bounty.

    Examples:

        # Simple task
        em agent publish \\
            --title "Verify store is open" \\
            --bounty 5 \\
            --location "19.4326,-99.1332" \\
            --instructions "Take a photo of the storefront showing the open/closed sign"

        # Task with multiple evidence types
        em agent publish \\
            --title "Document restaurant menu" \\
            --category knowledge_access \\
            --bounty 15 \\
            --evidence photo \\
            --evidence text_response \\
            --location-hint "La Cocina, 456 Oak St" \\
            --deadline 48 \\
            --instructions @menu_instructions.txt
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --wallet <address>' first.")
        sys.exit(1)

    # Handle instructions from file
    if instructions and instructions.startswith("@"):
        try:
            with open(instructions[1:]) as f:
                instructions = f.read()
        except FileNotFoundError:
            print_error(f"Instructions file not found: {instructions[1:]}")
            sys.exit(1)

    # If no instructions, prompt for them
    if not instructions:
        console.print("[yellow]Enter task instructions (end with Ctrl+D or empty line):[/yellow]")
        lines = []
        try:
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
        except EOFError:
            pass
        instructions = "\n".join(lines)

    if len(instructions) < 20:
        print_error("Instructions must be at least 20 characters")
        sys.exit(1)

    # Parse location if provided
    lat, lng = None, None
    if location:
        lat, lng = parse_location(location)

    # Validate bounty
    if bounty <= 0:
        print_error("Bounty must be greater than 0")
        sys.exit(1)

    if bounty < 1:
        print_warning(f"Low bounty (${bounty:.2f}) may result in slow task completion")

    # Show summary and confirm
    console.print()
    console.print("[bold]Task Summary[/bold]")
    console.print(f"  Title: {title}")
    console.print(f"  Category: {category}")
    console.print(f"  Bounty: ${bounty:.2f} {token}")
    console.print(f"  Deadline: {deadline} hours from now")
    console.print(f"  Evidence: {', '.join(evidence)}")
    if location:
        console.print(f"  Location: ({lat:.4f}, {lng:.4f}), radius {radius}km")
    if location_hint:
        console.print(f"  Location hint: {location_hint}")
    if min_reputation > 0:
        console.print(f"  Min reputation: {min_reputation}")
    console.print()
    console.print("[dim]Instructions:[/dim]")
    console.print(f"  {instructions[:200]}{'...' if len(instructions) > 200 else ''}")
    console.print()

    if not confirm(f"Publish this task and escrow ${bounty:.2f}?"):
        print_info("Task creation cancelled")
        return

    try:
        with spinner("Creating task and escrow..."):
            client = get_client()

            # Build task payload
            task = client.create_task(
                title=title,
                instructions=instructions,
                category=category,
                bounty_usd=bounty,
                deadline_hours=deadline,
                evidence_required=list(evidence),
                location_hint=location_hint,
                min_reputation=min_reputation,
                payment_token=token,
            )

        if output == OutputFormat.JSON:
            print_json(task.__dict__)
        elif output == OutputFormat.MINIMAL:
            print(task.id)
        else:
            print_success(f"Task published: {task.id}")
            print_task_detail(task)
            console.print()
            print_info("Monitor task status with:")
            print_info(f"  em agent review {task.id}")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@agent_group.command("review")
@click.argument("task_id")
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
@click.pass_context
def review(ctx, task_id: str, output: str):
    """
    Review a task and its submissions.

    Shows task details and all submissions for review.

    Examples:

        em agent review abc123

        em agent review abc123 --output json
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --wallet <address>' first.")
        sys.exit(1)

    try:
        with spinner("Fetching task and submissions..."):
            client = get_client()
            task = client.get_task(task_id)
            submissions = client.get_task_submissions(task_id)

        if output == OutputFormat.JSON:
            print_json({
                "task": task.__dict__,
                "submissions": [s.__dict__ for s in submissions],
            })
        else:
            print_task_detail(task)
            console.print()

            if submissions:
                print_submissions_table(submissions, title="Submissions")
                console.print()

                # Show quick actions
                pending = [s for s in submissions if s.status == "pending"]
                if pending:
                    console.print("[bold]Quick Actions:[/bold]")
                    for sub in pending[:3]:  # Show first 3
                        console.print(f"  em agent approve {sub.id}")
                        console.print(f"  em agent reject {sub.id} --reason '...'")
            else:
                print_info("No submissions yet")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@agent_group.command("approve")
@click.argument("submission_id")
@click.option(
    "--notes", "-n",
    help="Approval notes"
)
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
@click.pass_context
def approve(ctx, submission_id: str, notes: Optional[str], output: str):
    """
    Approve a submission and release payment.

    This will:
    1. Mark the submission as approved
    2. Release the escrowed bounty to the worker
    3. Mark the task as completed

    Examples:

        em agent approve sub_abc123

        em agent approve sub_abc123 --notes "Great work, thank you!"
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --wallet <address>' first.")
        sys.exit(1)

    try:
        with spinner("Processing approval..."):
            client = get_client()
            result = client.approve_submission(submission_id, notes)

        if output == OutputFormat.JSON:
            print_json(result)
        else:
            print_success(f"Submission {submission_id} approved")

            if result.get("payment_tx"):
                print_info(f"Payment transaction: {result['payment_tx']}")
            if result.get("amount_usd"):
                print_info(f"Amount paid: ${result['amount_usd']:.2f}")

            print_info("Task completed successfully")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@agent_group.command("reject")
@click.argument("submission_id")
@click.option(
    "--reason", "-r",
    required=True,
    help="Rejection reason (required)"
)
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
@click.pass_context
def reject(ctx, submission_id: str, reason: str, output: str):
    """
    Reject a submission.

    This will mark the submission as rejected and notify the worker.
    The task remains open for new submissions.

    Examples:

        em agent reject sub_abc123 --reason "Photo is blurry, please retake"
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --wallet <address>' first.")
        sys.exit(1)

    if not confirm(f"Reject submission {submission_id}?"):
        print_info("Rejection cancelled")
        return

    try:
        with spinner("Processing rejection..."):
            client = get_client()
            result = client.reject_submission(submission_id, reason)

        if output == OutputFormat.JSON:
            print_json(result)
        else:
            print_success(f"Submission {submission_id} rejected")
            print_info("Worker has been notified with your feedback")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@agent_group.command("list")
@click.option(
    "--status", "-s",
    type=click.Choice(["published", "accepted", "in_progress", "submitted", "completed", "disputed", "expired"]),
    help="Filter by status"
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum results"
)
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json", "minimal"]),
    default="table",
    help="Output format"
)
@click.pass_context
def list_agent_tasks(ctx, status: Optional[str], limit: int, output: str):
    """
    List tasks you have published.

    Examples:

        em agent list

        em agent list --status submitted
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --wallet <address>' first.")
        sys.exit(1)

    try:
        with spinner("Fetching your tasks..."):
            client = get_client()
            tasks = client.list_tasks(status=status, limit=limit)

        if output == OutputFormat.JSON:
            print_json([t.__dict__ for t in tasks])
        elif output == OutputFormat.MINIMAL:
            for task in tasks:
                print(task.id)
        else:
            print_tasks_table(tasks, title="Your Published Tasks")

            # Show summary stats
            if tasks:
                console.print()
                by_status = {}
                for t in tasks:
                    by_status[t.status] = by_status.get(t.status, 0) + 1
                stats = ", ".join([f"{k}: {v}" for k, v in by_status.items()])
                console.print(f"[dim]Status breakdown: {stats}[/dim]")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@agent_group.command("cancel")
@click.argument("task_id")
@click.option(
    "--reason", "-r",
    help="Cancellation reason"
)
@click.pass_context
def cancel(ctx, task_id: str, reason: Optional[str]):
    """
    Cancel a published task.

    This will cancel the task and refund the escrowed bounty.
    Can only be done if task hasn't been accepted yet.

    Examples:

        em agent cancel abc123 --reason "No longer needed"
    """
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --wallet <address>' first.")
        sys.exit(1)

    try:
        # Get task first to show details
        with spinner("Fetching task..."):
            client = get_client()
            task = client.get_task(task_id)

        console.print(f"[bold]Task:[/bold] {task.title}")
        console.print(f"[bold]Bounty:[/bold] ${task.bounty_usd:.2f}")
        console.print(f"[bold]Status:[/bold] {task.status}")
        console.print()

        if task.status not in ["published"]:
            print_warning(f"Task cannot be cancelled (status: {task.status})")
            print_info("Only 'published' tasks can be cancelled")
            sys.exit(1)

        if not confirm(f"Cancel this task and refund ${task.bounty_usd:.2f}?"):
            print_info("Cancellation aborted")
            return

        with spinner("Cancelling task..."):
            result = client.cancel_task(task_id, reason)

        print_success(f"Task {task_id} cancelled")
        if result.get("refund_tx"):
            print_info(f"Refund transaction: {result['refund_tx']}")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)
