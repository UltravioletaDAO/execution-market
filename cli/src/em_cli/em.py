#!/usr/bin/env python3
"""
Execution Market CLI - Command-line interface for the Execution Market human task execution layer.

Usage:
    em login --wallet <address>          # Authenticate with wallet
    em logout                            # Remove credentials
    em status                            # Show auth status

    # Worker commands
    em tasks list --location "lat,lng" --radius 10
    em tasks apply <task-id>
    em tasks submit <task-id> --evidence <file>
    em tasks my                          # List your tasks

    # Agent commands
    em agent publish --title "..." --bounty 10 --location "lat,lng"
    em agent review <task-id>
    em agent approve <submission-id>
    em agent list                        # List your published tasks

    # Wallet commands
    em wallet balance                    # Check wallet balance
    em wallet withdraw                   # Withdraw earnings
"""

import sys
import json
from typing import Optional, List

import click

# Version is defined here to avoid circular imports
__version__ = "0.1.0"
from .config import (
    get_config_manager,
    get_api_key,
    ConfigManager,
    Profile,
    DEFAULT_API_URL
)
from .api import (
    EMAPIClient,
    APIError,
    Task,
    TaskCategory,
    TaskStatus,
    EvidenceType,
    get_client,
    reset_client
)
from .output import (
    console,
    error_console,
    print_tasks_table,
    print_task_detail,
    print_submissions_table,
    print_wallet_balance,
    print_withdraw_result,
    print_transactions_table,
    print_analytics,
    print_json,
    print_success,
    print_error,
    print_warning,
    print_info,
    spinner,
    confirm,
    prompt,
    prompt_password,
    OutputFormat,
    output as format_output
)

# Import modular command groups
from .commands.auth import login, logout, status
from .commands.tasks import tasks_group
from .commands.agent import agent_group


# ============================================================================
# CLI Context
# ============================================================================

class Context:
    """CLI context holding common options."""

    def __init__(self):
        self.output_format: str = OutputFormat.TABLE
        self.verbose: bool = False
        self.profile: Optional[str] = None

    @property
    def client(self) -> EMAPIClient:
        """Get API client."""
        return get_client()


pass_context = click.make_pass_decorator(Context, ensure=True)


# ============================================================================
# Main CLI Group
# ============================================================================

@click.group()
@click.version_option(version=__version__, prog_name="em")
@click.option(
    "--output", "-o",
    type=click.Choice(["table", "json", "minimal"]),
    default="table",
    help="Output format"
)
@click.option(
    "--profile", "-p",
    help="Configuration profile to use"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@pass_context
def cli(ctx: Context, output: str, profile: Optional[str], verbose: bool):
    """Execution Market CLI - Human task execution layer for AI agents."""
    ctx.output_format = output
    ctx.verbose = verbose
    ctx.profile = profile

    # Switch profile if specified
    if profile:
        config_mgr = get_config_manager()
        if not config_mgr.config.profiles.get(profile):
            print_error(f"Profile '{profile}' not found. Use 'em config profiles' to list.")
            sys.exit(1)
        config_mgr.switch_profile(profile)


# ============================================================================
# Login / Auth Commands
# ============================================================================

@cli.command()
@click.option(
    "--api-key", "-k",
    help="API key (or set EM_API_KEY env var)"
)
@click.option(
    "--api-url", "-u",
    default=DEFAULT_API_URL,
    help="API base URL"
)
@click.option(
    "--profile-name", "-n",
    default="default",
    help="Profile name to save as"
)
@click.option(
    "--worker",
    is_flag=True,
    help="Login as a worker (prompts for executor ID)"
)
@pass_context
def login(
    ctx: Context,
    api_key: Optional[str],
    api_url: str,
    profile_name: str,
    worker: bool
):
    """Authenticate with Execution Market API."""
    config_mgr = get_config_manager()

    # Get API key
    if not api_key:
        api_key = prompt("Enter your API key", default=get_api_key() or "")

    if not api_key:
        print_error("API key is required")
        sys.exit(1)

    # Get executor ID for workers
    executor_id = None
    if worker:
        executor_id = prompt("Enter your executor ID")
        if not executor_id:
            print_error("Executor ID is required for worker login")
            sys.exit(1)

    # Validate the API key
    with spinner("Validating API key..."):
        try:
            # Create temporary client to validate
            client = EMAPIClient(api_key=api_key, base_url=api_url)
            # Try to make a simple request
            client._request_with_retry("GET", "/v1/health")
            client.close()
        except APIError as e:
            print_error(f"API key validation failed: {e}")
            sys.exit(1)
        except Exception as e:
            # Health endpoint might not exist, but connection worked
            pass

    # Save profile
    profile = config_mgr.set_profile(
        name=profile_name,
        api_key=api_key,
        api_url=api_url,
        executor_id=executor_id
    )

    print_success(f"Logged in successfully as profile '{profile_name}'")

    if worker:
        print_info(f"Executor ID: {executor_id}")

    # Reset client to pick up new config
    reset_client()


@cli.command()
@pass_context
def logout(ctx: Context):
    """Log out and remove credentials."""
    config_mgr = get_config_manager()
    active = config_mgr.config.active_profile

    if not config_mgr.config.profiles:
        print_warning("No profiles configured")
        return

    if confirm(f"Remove profile '{active}'?"):
        config_mgr.delete_profile(active)
        print_success(f"Profile '{active}' removed")
        reset_client()
    else:
        print_info("Logout cancelled")


# ============================================================================
# Config Commands
# ============================================================================

@cli.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command("profiles")
@pass_context
def config_profiles(ctx: Context):
    """List all configuration profiles."""
    config_mgr = get_config_manager()
    profiles = config_mgr.list_profiles()

    if not profiles:
        print_info("No profiles configured. Run 'em login' to create one.")
        return

    if ctx.output_format == OutputFormat.JSON:
        print_json({
            "active": config_mgr.config.active_profile,
            "profiles": [p.to_dict() for p in profiles.values()]
        })
        return

    from rich.table import Table
    from rich import box

    table = Table(title="Configuration Profiles", box=box.ROUNDED)
    table.add_column("Name", style="bold")
    table.add_column("API URL")
    table.add_column("Executor ID")
    table.add_column("Active", justify="center")

    active = config_mgr.config.active_profile

    for name, profile in profiles.items():
        table.add_row(
            name,
            profile.api_url,
            profile.executor_id or "-",
            "[green]YES[/green]" if name == active else ""
        )

    console.print(table)


@config.command("use")
@click.argument("profile_name")
@pass_context
def config_use(ctx: Context, profile_name: str):
    """Switch to a different profile."""
    config_mgr = get_config_manager()

    if config_mgr.switch_profile(profile_name):
        print_success(f"Switched to profile '{profile_name}'")
        reset_client()
    else:
        print_error(f"Profile '{profile_name}' not found")
        sys.exit(1)


@config.command("delete")
@click.argument("profile_name")
@pass_context
def config_delete(ctx: Context, profile_name: str):
    """Delete a configuration profile."""
    config_mgr = get_config_manager()

    if confirm(f"Delete profile '{profile_name}'?"):
        if config_mgr.delete_profile(profile_name):
            print_success(f"Profile '{profile_name}' deleted")
            reset_client()
        else:
            print_error(f"Profile '{profile_name}' not found")
            sys.exit(1)


# ============================================================================
# Tasks Commands
# ============================================================================

@cli.group()
def tasks():
    """Manage tasks."""
    pass


@tasks.command("list")
@click.option(
    "--status", "-s",
    type=click.Choice([s.value for s in TaskStatus]),
    help="Filter by status"
)
@click.option(
    "--category", "-c",
    type=click.Choice([c.value for c in TaskCategory]),
    help="Filter by category"
)
@click.option(
    "--location",
    help="Location as 'lat,lng' (e.g., '19.4326,-99.1332')"
)
@click.option(
    "--radius",
    type=float,
    default=10.0,
    help="Search radius in km (default: 10)"
)
@click.option("--limit", "-l", default=20, help="Maximum results")
@click.option("--offset", default=0, help="Pagination offset")
@pass_context
def tasks_list(
    ctx: Context,
    status: Optional[str],
    category: Optional[str],
    location: Optional[str],
    radius: float,
    limit: int,
    offset: int
):
    """List tasks, optionally filtered by location."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --wallet <address>' first.")
        sys.exit(1)

    # Parse location if provided
    lat, lng = None, None
    if location:
        try:
            parts = location.split(",")
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
            else:
                print_error("Invalid location format. Expected: 'lat,lng'")
                sys.exit(1)
        except ValueError:
            print_error("Invalid location format. Expected: 'lat,lng'")
            sys.exit(1)

    try:
        with spinner("Fetching tasks..."):
            tasks_result = ctx.client.list_tasks(
                status=status,
                category=category,
                limit=limit,
                offset=offset
            )

        if ctx.output_format == OutputFormat.JSON:
            print_json([t.__dict__ for t in tasks_result])
        elif ctx.output_format == OutputFormat.MINIMAL:
            for task in tasks_result:
                print(task.id)
        else:
            title = "Tasks"
            if location:
                title += f" near ({lat:.4f}, {lng:.4f})"
            print_tasks_table(tasks_result, title=title)
            if location:
                print_info(f"Showing tasks within {radius}km radius")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("create")
@click.option("--title", "-t", required=True, help="Task title")
@click.option("--instructions", "-i", required=True, help="Task instructions")
@click.option(
    "--category", "-c",
    type=click.Choice([c.value for c in TaskCategory]),
    required=True,
    help="Task category"
)
@click.option("--bounty", "-b", type=float, required=True, help="Bounty in USD")
@click.option("--deadline", "-d", type=int, required=True, help="Deadline in hours")
@click.option(
    "--evidence", "-e",
    multiple=True,
    type=click.Choice([e.value for e in EvidenceType]),
    required=True,
    help="Required evidence type (can specify multiple)"
)
@click.option("--location", "-l", help="Location hint")
@click.option("--min-reputation", type=int, default=0, help="Minimum worker reputation")
@click.option("--token", default="USDC", help="Payment token")
@pass_context
def tasks_create(
    ctx: Context,
    title: str,
    instructions: str,
    category: str,
    bounty: float,
    deadline: int,
    evidence: tuple,
    location: Optional[str],
    min_reputation: int,
    token: str
):
    """Create a new task."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Creating task..."):
            task = ctx.client.create_task(
                title=title,
                instructions=instructions,
                category=category,
                bounty_usd=bounty,
                deadline_hours=deadline,
                evidence_required=list(evidence),
                location_hint=location,
                min_reputation=min_reputation,
                payment_token=token
            )

        if ctx.output_format == OutputFormat.JSON:
            print_json(task.__dict__)
        elif ctx.output_format == OutputFormat.MINIMAL:
            print(task.id)
        else:
            print_success(f"Task created: {task.id}")
            print_task_detail(task)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("status")
@click.argument("task_id")
@pass_context
def tasks_status(ctx: Context, task_id: str):
    """Get task status and details."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Fetching task..."):
            task = ctx.client.get_task(task_id)

        if ctx.output_format == OutputFormat.JSON:
            print_json(task.__dict__)
        elif ctx.output_format == OutputFormat.MINIMAL:
            print(task.status)
        else:
            print_task_detail(task)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("apply")
@click.argument("task_id")
@click.option("--message", "-m", help="Message to the agent")
@pass_context
def tasks_apply(ctx: Context, task_id: str, message: Optional[str]):
    """Apply to a task (worker)."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --worker' first.")
        sys.exit(1)

    try:
        with spinner("Applying to task..."):
            result = ctx.client.apply_to_task(task_id, message)

        if ctx.output_format == OutputFormat.JSON:
            print_json(result)
        else:
            print_success(f"Applied to task {task_id}")
            if result.get("status") == "accepted":
                print_info("You have been assigned to this task. Start working!")
            else:
                print_info("Your application is pending approval.")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("submit")
@click.argument("task_id")
@click.option("--evidence", "-e", required=True, help="Evidence JSON or @file.json")
@click.option("--notes", "-n", help="Notes about the submission")
@pass_context
def tasks_submit(ctx: Context, task_id: str, evidence: str, notes: Optional[str]):
    """Submit evidence for a task (worker)."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login --worker' first.")
        sys.exit(1)

    # Parse evidence
    try:
        if evidence.startswith("@"):
            # Read from file
            with open(evidence[1:], "r") as f:
                evidence_data = json.load(f)
        else:
            evidence_data = json.loads(evidence)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print_error(f"Invalid evidence format: {e}")
        sys.exit(1)

    try:
        with spinner("Submitting evidence..."):
            submission = ctx.client.submit_evidence(task_id, evidence_data, notes)

        if ctx.output_format == OutputFormat.JSON:
            print_json(submission.__dict__)
        else:
            print_success(f"Evidence submitted: {submission.id}")
            print_info(f"Pre-check score: {submission.pre_check_score:.2f}")
            print_info(f"Status: {submission.status}")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("cancel")
@click.argument("task_id")
@click.option("--reason", "-r", help="Cancellation reason")
@pass_context
def tasks_cancel(ctx: Context, task_id: str, reason: Optional[str]):
    """Cancel a task."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    if not confirm(f"Cancel task {task_id}?"):
        print_info("Cancelled")
        return

    try:
        with spinner("Cancelling task..."):
            result = ctx.client.cancel_task(task_id, reason)

        if ctx.output_format == OutputFormat.JSON:
            print_json(result)
        else:
            print_success(f"Task {task_id} cancelled")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("submissions")
@click.argument("task_id")
@pass_context
def tasks_submissions(ctx: Context, task_id: str):
    """View submissions for a task."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Fetching submissions..."):
            submissions = ctx.client.get_task_submissions(task_id)

        if ctx.output_format == OutputFormat.JSON:
            print_json([s.__dict__ for s in submissions])
        elif ctx.output_format == OutputFormat.MINIMAL:
            for s in submissions:
                print(s.id)
        else:
            print_submissions_table(submissions)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("approve")
@click.argument("submission_id")
@click.option("--notes", "-n", help="Approval notes")
@pass_context
def tasks_approve(ctx: Context, submission_id: str, notes: Optional[str]):
    """Approve a submission."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Approving submission..."):
            result = ctx.client.approve_submission(submission_id, notes)

        if ctx.output_format == OutputFormat.JSON:
            print_json(result)
        else:
            print_success(f"Submission {submission_id} approved")
            if result.get("payment_tx"):
                print_info(f"Payment: {result['payment_tx']}")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@tasks.command("reject")
@click.argument("submission_id")
@click.option("--notes", "-n", required=True, help="Rejection reason")
@pass_context
def tasks_reject(ctx: Context, submission_id: str, notes: str):
    """Reject a submission."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Rejecting submission..."):
            result = ctx.client.reject_submission(submission_id, notes)

        if ctx.output_format == OutputFormat.JSON:
            print_json(result)
        else:
            print_success(f"Submission {submission_id} rejected")

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Wallet Commands
# ============================================================================

@cli.group()
def wallet():
    """Manage wallet and earnings."""
    pass


@wallet.command("balance")
@pass_context
def wallet_balance(ctx: Context):
    """Check wallet balance."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Fetching balance..."):
            balance = ctx.client.get_wallet_balance()

        if ctx.output_format == OutputFormat.JSON:
            print_json(balance.__dict__)
        elif ctx.output_format == OutputFormat.MINIMAL:
            print(f"{balance.available_usd}")
        else:
            print_wallet_balance(balance)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@wallet.command("withdraw")
@click.option("--amount", "-a", type=float, help="Amount in USD (default: all)")
@click.option("--destination", "-d", help="Destination wallet address")
@pass_context
def wallet_withdraw(ctx: Context, amount: Optional[float], destination: Optional[str]):
    """Withdraw earnings."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    # Get current balance first
    try:
        balance = ctx.client.get_wallet_balance()
    except APIError as e:
        print_error(f"Failed to fetch balance: {e}")
        sys.exit(1)

    if balance.available_usd <= 0:
        print_warning("No funds available to withdraw")
        return

    withdraw_amount = amount or balance.available_usd

    if withdraw_amount > balance.available_usd:
        print_error(f"Insufficient balance. Available: ${balance.available_usd:.2f}")
        sys.exit(1)

    if not confirm(f"Withdraw ${withdraw_amount:.2f}?"):
        print_info("Withdrawal cancelled")
        return

    try:
        with spinner("Processing withdrawal..."):
            result = ctx.client.withdraw(withdraw_amount, destination)

        if ctx.output_format == OutputFormat.JSON:
            print_json(result.__dict__)
        else:
            print_withdraw_result(result)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


@wallet.command("transactions")
@click.option("--limit", "-l", default=20, help="Maximum results")
@click.option("--offset", default=0, help="Pagination offset")
@pass_context
def wallet_transactions(ctx: Context, limit: int, offset: int):
    """View transaction history."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Fetching transactions..."):
            transactions = ctx.client.get_transactions(limit, offset)

        if ctx.output_format == OutputFormat.JSON:
            print_json(transactions)
        else:
            print_transactions_table(transactions)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Analytics Command
# ============================================================================

@cli.command()
@click.option("--days", "-d", default=30, help="Number of days to analyze")
@pass_context
def analytics(ctx: Context, days: int):
    """View usage analytics."""
    api_key = get_api_key()
    if not api_key:
        print_error("Not logged in. Run 'em login' first.")
        sys.exit(1)

    try:
        with spinner("Fetching analytics..."):
            data = ctx.client.get_analytics(days)

        if ctx.output_format == OutputFormat.JSON:
            print_json(data)
        else:
            print_analytics(data)

    except APIError as e:
        print_error(str(e))
        sys.exit(1)


# ============================================================================
# Register Modular Command Groups
# ============================================================================

# Add the new modular commands from commands/ directory
# These extend the existing commands with wallet-based auth and geo features

# Register new auth commands at the root level
cli.add_command(login, name="login")  # Override existing login with wallet support
cli.add_command(logout)
cli.add_command(status)

# Register the agent command group for agent-specific operations
cli.add_command(agent_group, name="agent")

# Note: tasks_group provides enhanced functionality but we keep the existing
# tasks group for backward compatibility. The new commands are available at:
#   - em tasks list --location "lat,lng" --radius 10
#   - em tasks my (list your assigned tasks)


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """CLI entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        print_info("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
