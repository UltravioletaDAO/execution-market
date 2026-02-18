"""Shared formatting helpers used across MCP tools."""

from datetime import datetime


def format_bounty(amount: float) -> str:
    """Format bounty amount as currency."""
    return f"${amount:.2f}"


def format_datetime(dt_str: str) -> str:
    """Format ISO datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return dt_str
