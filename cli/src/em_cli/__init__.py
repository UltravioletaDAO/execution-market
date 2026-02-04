"""
Execution Market CLI - Command-line interface for the Execution Market human task execution layer.

This package provides a CLI for both AI agents and human workers to interact
with the Execution Market platform.

Usage:
    # As a CLI
    $ em login
    $ em tasks list
    $ em tasks create --title "..." --category physical_presence ...

    # As a library
    from em_cli.api import EMAPIClient
    client = EMAPIClient(api_key="...")
    task = client.create_task(...)
"""

__version__ = "0.1.0"
__author__ = "Ultravioleta DAO"


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name in ("get_config_manager", "get_api_key", "get_api_url",
                "get_executor_id", "ConfigManager", "Profile", "Config"):
        from . import config
        return getattr(config, name)

    if name in ("EMAPIClient", "APIError", "Task", "Submission",
                "WalletBalance", "WithdrawResult", "TaskStatus",
                "TaskCategory", "EvidenceType", "get_client", "reset_client"):
        from . import api
        return getattr(api, name)

    if name in ("cli", "main"):
        from . import em
        return getattr(em, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Version
    "__version__",
    "__author__",
    # Config
    "get_config_manager",
    "get_api_key",
    "get_api_url",
    "get_executor_id",
    "ConfigManager",
    "Profile",
    "Config",
    # API
    "EMAPIClient",
    "APIError",
    "Task",
    "Submission",
    "WalletBalance",
    "WithdrawResult",
    "TaskStatus",
    "TaskCategory",
    "EvidenceType",
    "get_client",
    "reset_client",
    # CLI
    "cli",
    "main",
]
