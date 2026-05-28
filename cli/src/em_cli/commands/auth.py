"""
Authentication commands (auth group) for Execution Market CLI.

Note: the primary `em login` lives in `em.py` as a top-level command. This
`em auth login` exists for users who prefer the explicit auth group namespace
and produces identical wallet-bound profiles.

Commands:
    em auth login --wallet-address 0x... [--wallet-name ...]
    em auth logout
    em auth status
"""

import sys
from typing import Optional

import click

from ..config import (
    get_config_manager,
    get_wallet,
    DEFAULT_API_URL,
    DEFAULT_CHAIN_ID,
)
from ..api import EMAPIClient, APIError, reset_client
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
    """Validate EVM wallet address format (0x + 40 hex chars)."""
    if not address:
        return False
    if not address.startswith("0x") or len(address) != 42:
        return False
    try:
        int(address[2:], 16)
    except ValueError:
        return False
    return True


@click.group(name="auth")
def auth_group():
    """Authentication and profile management."""
    pass


@click.command()
@click.option("--wallet-name", "-w", help="OWS wallet name (run `ows wallet list` to see)")
@click.option("--wallet-address", "-a", required=True, help="EVM 0x... address")
@click.option(
    "--chain-id",
    type=int,
    default=DEFAULT_CHAIN_ID,
    help=f"Chain ID for ERC-8128 keyid (default: {DEFAULT_CHAIN_ID} Base)",
)
@click.option("--api-url", "-u", default=DEFAULT_API_URL, help="API base URL")
@click.option("--profile-name", "-n", default="default", help="Profile name to save as")
@click.option("--executor-id", "-e", help="Executor ID (for worker mode)")
def login(
    wallet_name: Optional[str],
    wallet_address: str,
    chain_id: int,
    api_url: str,
    profile_name: str,
    executor_id: Optional[str],
):
    """
    Bind an OWS wallet for ERC-8128 signed requests.

    The private key NEVER leaves the OWS vault. This command stores the
    wallet name + address so subsequent requests can sign with them.

    Examples:
        em auth login --wallet-address 0x1234...abcd
        em auth login --wallet-name my-agent --wallet-address 0x... --executor-id exec_abc
    """
    if not is_valid_wallet_address(wallet_address):
        print_error(f"Invalid wallet address: {wallet_address!r} — expected 0x + 40 hex chars.")
        sys.exit(1)

    if not wallet_name:
        wallet_name = prompt("OWS wallet name (from `ows wallet list`)", default="my-agent")

    config_mgr = get_config_manager()

    # Light validation: try a signed health check.
    with spinner("Validating wallet signing..."):
        try:
            client = EMAPIClient(
                wallet_name=wallet_name,
                wallet_address=wallet_address,
                chain_id=chain_id,
                base_url=api_url,
            )
            client._request_with_retry("GET", "/v1/health")
            client.close()
        except APIError as e:
            print_warning(f"Health check returned {e.status_code}: {e.message}")
            print_info("Profile saved anyway — re-test with `em status`.")
        except Exception:
            pass  # Network error or health endpoint missing — proceed.

    config_mgr.set_profile(
        name=profile_name,
        wallet_name=wallet_name,
        wallet_address=wallet_address,
        chain_id=chain_id,
        api_url=api_url,
        executor_id=executor_id,
    )

    print_success(f"Logged in as profile '{profile_name}'")
    print_info(f"Wallet: {wallet_name} ({wallet_address})")
    print_info(f"Chain ID: {chain_id}")
    if executor_id:
        print_info(f"Executor ID: {executor_id}")

    reset_client()


@click.command()
def logout():
    """Log out and remove stored credentials (the OWS key is unaffected)."""
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
        print_info("Run 'em login' (or 'em auth login --wallet-address 0x...') to authenticate")
        return

    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Profile", active_name)
    table.add_row("API URL", active_profile.api_url)

    walletinfo = get_wallet()
    if walletinfo:
        wname, waddr, wchain = walletinfo
        masked = waddr[:6] + "..." + waddr[-4:]
        table.add_row("Wallet name", wname)
        table.add_row("Wallet address", masked)
        table.add_row("Chain ID", str(wchain))
    else:
        table.add_row("Wallet", "[dim]Not bound[/dim]")

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
        border_style="green" if walletinfo else "yellow",
    ))

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
