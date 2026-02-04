"""
Execution Market CLI command modules.

This package organizes CLI commands into logical groups:
- auth: Authentication and profile management
- tasks: Task operations for workers
- agent: Agent-specific operations (publish, review, approve)
"""

from .auth import auth_group, login, logout, status
from .tasks import tasks_group
from .agent import agent_group

__all__ = [
    "auth_group",
    "login",
    "logout",
    "status",
    "tasks_group",
    "agent_group",
]
