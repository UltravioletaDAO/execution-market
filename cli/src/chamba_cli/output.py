"""
Output formatting for Chamba CLI.

Provides:
- Table format for lists
- JSON output option
- Rich console colors
- Progress bars
"""

import json
import sys
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from contextlib import contextmanager

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.text import Text
from rich import box

from .api import Task, Submission, WalletBalance, WithdrawResult


# Global console instance
console = Console()
error_console = Console(stderr=True)


# ============================================================================
# Output Format Helpers
# ============================================================================

class OutputFormat:
    """Output format constants."""
    TABLE = "table"
    JSON = "json"
    MINIMAL = "minimal"


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M")


def format_usd(amount: float) -> str:
    """Format USD amount."""
    return f"${amount:,.2f}"


def format_status(status: str) -> Text:
    """Format status with colors."""
    colors = {
        "published": "cyan",
        "accepted": "blue",
        "in_progress": "yellow",
        "submitted": "magenta",
        "verifying": "magenta",
        "completed": "green",
        "disputed": "red",
        "expired": "dim",
        "cancelled": "dim"
    }
    color = colors.get(status, "white")
    return Text(status, style=color)


def format_category(category: str) -> str:
    """Format category for display."""
    return category.replace("_", " ").title()


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


# ============================================================================
# Table Formatters
# ============================================================================

def print_tasks_table(tasks: List[Task], title: str = "Tasks") -> None:
    """Print tasks as a rich table."""
    if not tasks:
        console.print("[dim]No tasks found.[/dim]")
        return

    table = Table(title=title, box=box.ROUNDED)

    table.add_column("ID", style="dim", width=8)
    table.add_column("Title", style="bold")
    table.add_column("Category", style="cyan")
    table.add_column("Bounty", style="green", justify="right")
    table.add_column("Status")
    table.add_column("Deadline", style="yellow")

    for task in tasks:
        table.add_row(
            task.id[:8],
            truncate(task.title, 40),
            format_category(task.category),
            format_usd(task.bounty_usd),
            format_status(task.status),
            format_datetime(task.deadline)
        )

    console.print(table)


def print_task_detail(task: Task) -> None:
    """Print detailed task information."""
    panel_content = f"""
[bold]Title:[/bold] {task.title}

[bold]Category:[/bold] {format_category(task.category)}
[bold]Status:[/bold] {task.status}
[bold]Bounty:[/bold] {format_usd(task.bounty_usd)} ({task.payment_token})

[bold]Instructions:[/bold]
{task.instructions}

[bold]Evidence Required:[/bold] {', '.join(task.evidence_required)}
{f'[bold]Evidence Optional:[/bold] {", ".join(task.evidence_optional)}' if task.evidence_optional else ''}

[bold]Deadline:[/bold] {format_datetime(task.deadline)}
[bold]Created:[/bold] {format_datetime(task.created_at)}
{f'[bold]Location Hint:[/bold] {task.location_hint}' if task.location_hint else ''}
{f'[bold]Min Reputation:[/bold] {task.min_reputation}' if task.min_reputation else ''}
{f'[bold]Executor:[/bold] {task.executor_id}' if task.executor_id else ''}
"""

    console.print(Panel(
        panel_content.strip(),
        title=f"Task {task.id}",
        border_style="blue"
    ))


def print_submissions_table(submissions: List[Submission], title: str = "Submissions") -> None:
    """Print submissions as a rich table."""
    if not submissions:
        console.print("[dim]No submissions found.[/dim]")
        return

    table = Table(title=title, box=box.ROUNDED)

    table.add_column("ID", style="dim", width=8)
    table.add_column("Executor", style="cyan", width=8)
    table.add_column("Status")
    table.add_column("Score", style="yellow", justify="right")
    table.add_column("Submitted", style="dim")
    table.add_column("Notes", max_width=30)

    for sub in submissions:
        status_color = {
            "pending": "yellow",
            "approved": "green",
            "rejected": "red"
        }.get(sub.status, "white")

        table.add_row(
            sub.id[:8],
            sub.executor_id[:8] if sub.executor_id else "-",
            Text(sub.status, style=status_color),
            f"{sub.pre_check_score:.2f}",
            format_datetime(sub.submitted_at),
            truncate(sub.notes, 30) if sub.notes else "-"
        )

    console.print(table)


def print_wallet_balance(balance: WalletBalance) -> None:
    """Print wallet balance information."""
    panel_content = f"""
[bold green]Available:[/bold green] {format_usd(balance.available_usd)} {balance.token}
[bold yellow]Pending:[/bold yellow] {format_usd(balance.pending_usd)} {balance.token}

[dim]Total Earned:[/dim] {format_usd(balance.total_earned_usd)}
[dim]Total Withdrawn:[/dim] {format_usd(balance.total_withdrawn_usd)}
"""

    console.print(Panel(
        panel_content.strip(),
        title="Wallet Balance",
        border_style="green"
    ))


def print_withdraw_result(result: WithdrawResult) -> None:
    """Print withdrawal result."""
    if result.success:
        console.print(Panel(
            f"""
[bold green]Withdrawal Successful[/bold green]

Amount: {format_usd(result.amount_usd)}
Destination: {result.destination or 'Default wallet'}
{f'Transaction: {result.tx_hash}' if result.tx_hash else ''}
""".strip(),
            border_style="green"
        ))
    else:
        error_console.print(Panel(
            f"""
[bold red]Withdrawal Failed[/bold red]

{result.error or 'Unknown error'}
""".strip(),
            border_style="red"
        ))


def print_transactions_table(transactions: List[Dict[str, Any]], title: str = "Transactions") -> None:
    """Print transactions as a rich table."""
    if not transactions:
        console.print("[dim]No transactions found.[/dim]")
        return

    table = Table(title=title, box=box.ROUNDED)

    table.add_column("Date", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Amount", justify="right")
    table.add_column("Task", style="dim", width=8)
    table.add_column("Status")

    for tx in transactions:
        tx_type = tx.get("type", "unknown")
        amount = tx.get("amount_usd", 0)

        # Color amount based on type
        if tx_type in ["earned", "payment_received"]:
            amount_text = Text(f"+{format_usd(amount)}", style="green")
        elif tx_type in ["withdrawn", "payment_sent"]:
            amount_text = Text(f"-{format_usd(amount)}", style="red")
        else:
            amount_text = Text(format_usd(amount))

        table.add_row(
            tx.get("created_at", "-")[:16] if tx.get("created_at") else "-",
            tx_type.replace("_", " ").title(),
            amount_text,
            tx.get("task_id", "-")[:8] if tx.get("task_id") else "-",
            tx.get("status", "-")
        )

    console.print(table)


def print_analytics(analytics: Dict[str, Any]) -> None:
    """Print analytics information."""
    panel_content = f"""
[bold]Period:[/bold] {analytics.get('period_days', 30)} days

[bold cyan]Tasks[/bold cyan]
  Created: {analytics.get('tasks_created', 0)}
  Completed: {analytics.get('tasks_completed', 0)}
  Completion Rate: {analytics.get('completion_rate', 0):.1%}
  Avg Completion Time: {analytics.get('avg_completion_time_hours', 0):.1f}h

[bold green]Financials[/bold green]
  Total Spent: {format_usd(analytics.get('total_spent_usd', 0))}
"""

    # Add by-status breakdown if available
    by_status = analytics.get("by_status", {})
    if by_status:
        panel_content += "\n[bold]By Status:[/bold]\n"
        for status, count in by_status.items():
            panel_content += f"  {status}: {count}\n"

    # Add by-category breakdown if available
    by_category = analytics.get("by_category", {})
    if by_category:
        panel_content += "\n[bold]By Category:[/bold]\n"
        for category, count in by_category.items():
            panel_content += f"  {format_category(category)}: {count}\n"

    console.print(Panel(
        panel_content.strip(),
        title="Analytics",
        border_style="blue"
    ))


# ============================================================================
# JSON Output
# ============================================================================

def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    if hasattr(data, "__dataclass_fields__"):
        # Convert dataclass to dict
        from dataclasses import asdict
        data = asdict(data)
    elif isinstance(data, list) and data and hasattr(data[0], "__dataclass_fields__"):
        from dataclasses import asdict
        data = [asdict(item) for item in data]

    # Handle datetime objects
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    json_str = json.dumps(data, indent=2, default=json_serializer)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)


# ============================================================================
# Messages and Errors
# ============================================================================

def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[bold green]OK[/bold green] {message}")


def print_error(message: str) -> None:
    """Print error message."""
    error_console.print(f"[bold red]Error:[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[bold blue]Info:[/bold blue] {message}")


# ============================================================================
# Progress Indicators
# ============================================================================

@contextmanager
def spinner(message: str = "Processing..."):
    """Context manager for spinner progress indicator."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        progress.add_task(description=message, total=None)
        yield


@contextmanager
def progress_bar(total: int, description: str = "Progress"):
    """Context manager for progress bar."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(description=description, total=total)
        yield lambda: progress.advance(task)


def wait_animation(
    check_fn: Callable[[], bool],
    message: str = "Waiting...",
    timeout_seconds: int = 3600,
    poll_interval: float = 5.0
) -> bool:
    """
    Display waiting animation until condition is met.

    Args:
        check_fn: Function that returns True when done
        message: Message to display
        timeout_seconds: Maximum wait time
        poll_interval: Check interval in seconds

    Returns:
        True if condition was met, False if timeout
    """
    import time

    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task(description=message, total=None)

        while time.time() - start_time < timeout_seconds:
            if check_fn():
                return True
            time.sleep(poll_interval)
            elapsed = int(time.time() - start_time)
            progress.update(task, description=f"{message} ({elapsed}s)")

    return False


# ============================================================================
# Prompts
# ============================================================================

def confirm(message: str, default: bool = False) -> bool:
    """Ask for confirmation."""
    from rich.prompt import Confirm
    return Confirm.ask(message, default=default)


def prompt(message: str, default: Optional[str] = None) -> str:
    """Prompt for input."""
    from rich.prompt import Prompt
    return Prompt.ask(message, default=default)


def prompt_password(message: str = "Password") -> str:
    """Prompt for password (hidden input)."""
    from rich.prompt import Prompt
    return Prompt.ask(message, password=True)


# ============================================================================
# Conditional Output
# ============================================================================

def output(
    data: Any,
    format: str = OutputFormat.TABLE,
    table_printer: Optional[Callable] = None,
    detail_printer: Optional[Callable] = None
) -> None:
    """
    Output data in the specified format.

    Args:
        data: Data to output
        format: Output format (table, json, minimal)
        table_printer: Function to print as table
        detail_printer: Function to print detail view
    """
    if format == OutputFormat.JSON:
        print_json(data)
    elif format == OutputFormat.MINIMAL:
        # Minimal output for scripting
        if isinstance(data, list):
            for item in data:
                if hasattr(item, 'id'):
                    print(item.id)
                else:
                    print(item)
        elif hasattr(data, 'id'):
            print(data.id)
        else:
            print(data)
    elif table_printer:
        table_printer(data)
    elif detail_printer:
        detail_printer(data)
    else:
        console.print(data)
