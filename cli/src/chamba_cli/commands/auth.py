"""
Authentication commands for Chamba CLI.

Commands:
    chamba login --wallet <address>    # Login with wallet
    chamba logout                      # Remove credentials
    chamba status                      # Show auth status
"""

import sys
import re
from typing import Optional

import click

from ..config import (
    get_config_manager,
    get_api_key,
    DEFAULT_API_URL,
)
from ..api import ChambaAPIClient, APIError, reset_client
from ..output import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
    spinner,
    confirm,
    prompt,
)


def is_valid_wallet_address(address: str) -> bool:
    """Validate Ethereum wallet address format."""
    if not address:
        return False
    # Basic Ethereum address format: 0x followed by 40 hex characters
    pattern = r"^0x[a-fA-F0-9]{40}$"
    return bool(re.match(pattern, address))


@click.group(name="auth")
def auth_group():
    """Authentication and profile management."""
    pass


@click.command()
@click.option(
    "--wallet", "-w",
    required=True,
    help="Wallet address (0x...)"
)
@click.option(
    "--api-key", "-k",
    help="API key (or set CHAMBA_API_KEY env var)"
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
    "--executor-id", "-e",
    help="Executor ID (for worker mode)"
)
@click.option(
    "--agent-id", "-a",
    help="Agent ID (for agent mode)"
)
def login(
    wallet: str,
    api_key: Optional[str],
    api_url: str,
    profile_name: str,
    executor_id: Optional[str],
    agent_id: Optional[str],
):
    """
    Authenticate with Chamba using a wallet address.

    Examples:

        # Login as worker
        chamba login --wallet 0x1234...abcd

        # Login with executor ID (pre-registered worker)
        chamba login --wallet 0x1234...abcd --executor-id exec_abc123

        # Login as agent
        chamba login --wallet 0x1234...abcd --agent-id agent_xyz789
    """
    # Validate wallet address
    if not is_valid_wallet_address(wallet):
        print_error(f"Invalid wallet address format: {wallet}")
        print_info("Expected format: 0x followed by 40 hexadecimal characters")
        sys.exit(1)

    config_mgr = get_config_manager()

    # Get API key if not provided
    if not api_key:
        existing_key = get_api_key()
        if existing_key:
            api_key = existing_key
        else:
            api_key = prompt("Enter your API key (or press Enter to skip)")

    # Validate connection if API key provided
    if api_key:
        with spinner("Validating API connection..."):
            try:
                client = ChambaAPIClient(api_key=api_key, base_url=api_url)
                # Try health check
                client._request_with_retry("GET", "/v1/health")
                client.close()
            except APIError as e:
                print_warning(f"API validation warning: {e}")
            except Exception:
                # Health endpoint might not exist, continue anyway
                pass

    # Determine mode based on provided IDs
    mode = "unknown"
    if executor_id:
        mode = "worker"
    elif agent_id:
        mode = "agent"
    else:
        # Ask user
        mode_choice = prompt(
            "Login mode",
            default="worker"
        )
        mode = mode_choice.lower()

        if mode == "worker" and not executor_id:
            executor_id = prompt("Enter your executor ID (or press Enter for new registration)")
        elif mode == "agent" and not agent_id:
            agent_id = prompt("Enter your agent ID")

    # Save profile
    profile = config_mgr.set_profile(
        name=profile_name,
        api_key=api_key or "",
        api_url=api_url,
        executor_id=executor_id,
    )

    # Store wallet address in profile metadata (extend config if needed)
    # For now, we'll store it in a way that's backward compatible

    print_success(f"Logged in successfully as profile '{profile_name}'")
    print_info(f"Wallet: {wallet}")
    print_info(f"Mode: {mode}")

    if executor_id:
        print_info(f"Executor ID: {executor_id}")
    if agent_id:
        print_info(f"Agent ID: {agent_id}")

    # Reset client to pick up new config
    reset_client()


@click.command()
def logout():
    """Log out and remove stored credentials."""
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


@click.command()
def status():
    """Show current authentication status."""
    config_mgr = get_config_manager()
    active_name = config_mgr.config.active_profile
    active_profile = config_mgr.config.get_active_profile()

    console.print()

    if not active_profile:
        print_warning("Not logged in")
        print_info("Run 'chamba login --wallet <address>' to authenticate")
        return

    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    # Build status table
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Profile", active_name)
    table.add_row("API URL", active_profile.api_url)

    api_key = get_api_key()
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        table.add_row("API Key", masked_key)
    else:
        table.add_row("API Key", "[dim]Not set[/dim]")

    executor_id = config_mgr.get_executor_id()
    if executor_id:
        table.add_row("Executor ID", executor_id)
        table.add_row("Mode", "[cyan]Worker[/cyan]")
    else:
        table.add_row("Executor ID", "[dim]Not set[/dim]")
        table.add_row("Mode", "[yellow]Agent[/yellow]")

    console.print(Panel(
        table,
        title="Authentication Status",
        border_style="green" if api_key else "yellow"
    ))

    # List all profiles
    profiles = config_mgr.list_profiles()
    if len(profiles) > 1:
        console.print()
        console.print("[bold]Available profiles:[/bold]")
        for name in profiles.keys():
            marker = "[green]* [/green]" if name == active_name else "  "
            console.print(f"  {marker}{name}")


# Register commands to group
auth_group.add_command(login)
auth_group.add_command(logout)
auth_group.add_command(status)
