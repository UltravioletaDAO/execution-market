"""
Karma Kadabra V2 — Execution Market API Client

Shared HTTP client used by all KK agent services to interact
with the Execution Market REST API.

All agent operations go through this client:
  - Publish tasks (bounties for data/services)
  - Browse available tasks
  - Apply to tasks
  - Submit evidence
  - Approve/reject submissions
  - Rate workers/agents
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env.local")

logger = logging.getLogger("kk.em_client")

API_BASE = os.environ.get("EM_API_URL", "https://api.execution.market").rstrip("/")
API_V1 = f"{API_BASE}/api/v1"


@dataclass
class AgentContext:
    """Identity and state for one KK agent interacting with EM."""

    name: str
    wallet_address: str
    workspace_dir: Path
    api_key: str = ""
    erc8004_agent_id: int | None = None
    executor_id: str | None = None

    # Runtime state
    daily_spent_usd: float = 0.0
    daily_budget_usd: float = 2.0
    per_task_budget_usd: float = 0.50
    active_tasks: list[str] = field(default_factory=list)

    def can_spend(self, amount: float) -> bool:
        return (self.daily_spent_usd + amount) <= self.daily_budget_usd

    def record_spend(self, amount: float) -> None:
        self.daily_spent_usd += amount

    def reset_daily_budget(self) -> None:
        self.daily_spent_usd = 0.0


class EMClient:
    """Async HTTP client for the Execution Market API."""

    def __init__(self, agent: AgentContext, timeout: float = 30.0):
        self.agent = agent
        headers = {
            "Content-Type": "application/json",
            "X-Agent-Wallet": agent.wallet_address,
        }
        if agent.api_key:
            headers["X-API-Key"] = agent.api_key
        self._client = httpx.AsyncClient(
            base_url=API_V1,
            headers=headers,
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # -- Tasks -----------------------------------------------------------------

    async def publish_task(
        self,
        title: str,
        description: str,
        category: str,
        bounty_usdc: float,
        deadline_minutes: int = 60,
        evidence_requirements: list[dict] | None = None,
        location: dict | None = None,
        payment_network: str = "base",
    ) -> dict[str, Any]:
        """Publish a new task (bounty) on Execution Market."""
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "category": category,
            "bounty_usdc": bounty_usdc,
            "deadline_minutes": deadline_minutes,
            "payment_network": payment_network,
        }
        if evidence_requirements:
            payload["evidence_requirements"] = evidence_requirements
        if location:
            payload["location"] = location

        resp = await self._client.post("/tasks", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Get details of a specific task."""
        resp = await self._client.get(f"/tasks/{task_id}")
        resp.raise_for_status()
        return resp.json()

    async def browse_tasks(
        self,
        status: str = "published",
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Browse available tasks on EM."""
        params: dict[str, Any] = {"status": status, "limit": limit}
        if category:
            params["category"] = category
        resp = await self._client.get("/tasks/available", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("tasks", data if isinstance(data, list) else [])

    async def list_tasks(
        self,
        agent_wallet: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List tasks with filters."""
        params: dict[str, Any] = {"limit": limit}
        if agent_wallet:
            params["agent_wallet"] = agent_wallet
        if status:
            params["status"] = status
        resp = await self._client.get("/tasks", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("tasks", data if isinstance(data, list) else [])

    async def cancel_task(self, task_id: str) -> dict[str, Any]:
        """Cancel a published task."""
        resp = await self._client.post(f"/tasks/{task_id}/cancel")
        resp.raise_for_status()
        return resp.json()

    # -- Worker actions --------------------------------------------------------

    async def apply_to_task(
        self,
        task_id: str,
        executor_id: str,
        message: str = "",
    ) -> dict[str, Any]:
        """Apply (as worker) to a task."""
        payload: dict[str, Any] = {
            "executor_id": executor_id,
        }
        if message:
            payload["message"] = message
        resp = await self._client.post(f"/tasks/{task_id}/apply", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def submit_evidence(
        self,
        task_id: str,
        executor_id: str,
        evidence_url: str,
        evidence_type: str = "text",
        notes: str = "",
    ) -> dict[str, Any]:
        """Submit evidence for a task."""
        payload: dict[str, Any] = {
            "executor_id": executor_id,
            "evidence_url": evidence_url,
            "evidence_type": evidence_type,
        }
        if notes:
            payload["notes"] = notes
        resp = await self._client.post(f"/tasks/{task_id}/submit", json=payload)
        resp.raise_for_status()
        return resp.json()

    # -- Agent review actions --------------------------------------------------

    async def assign_task(self, task_id: str, executor_id: str) -> dict[str, Any]:
        """Assign an applicant to a task."""
        resp = await self._client.post(
            f"/tasks/{task_id}/assign",
            json={"executor_id": executor_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def approve_submission(
        self,
        submission_id: str,
        rating: int = 5,
        feedback: str = "",
    ) -> dict[str, Any]:
        """Approve a submission."""
        payload: dict[str, Any] = {"rating": rating}
        if feedback:
            payload["feedback"] = feedback
        resp = await self._client.post(
            f"/submissions/{submission_id}/approve",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def reject_submission(
        self,
        submission_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Reject a submission."""
        resp = await self._client.post(
            f"/submissions/{submission_id}/reject",
            json={"reason": reason},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_submissions(self, task_id: str) -> list[dict[str, Any]]:
        """Get submissions for a task."""
        resp = await self._client.get(f"/tasks/{task_id}/submissions")
        resp.raise_for_status()
        data = resp.json()
        return data.get("submissions", data if isinstance(data, list) else [])

    # -- Health ----------------------------------------------------------------

    async def health(self) -> dict[str, Any]:
        """Check API health."""
        resp = await self._client.get("/health")
        resp.raise_for_status()
        return resp.json()


def load_agent_context(workspace_dir: Path) -> AgentContext:
    """Load agent context from a workspace directory."""
    wallet_file = workspace_dir / "data" / "wallet.json"
    profile_file = workspace_dir / "data" / "profile.json"

    wallet_data = json.loads(wallet_file.read_text(encoding="utf-8")) if wallet_file.exists() else {}
    profile_data = json.loads(profile_file.read_text(encoding="utf-8")) if profile_file.exists() else {}

    name = workspace_dir.name.removeprefix("kk-") if workspace_dir.name.startswith("kk-") else workspace_dir.name

    return AgentContext(
        name=name,
        wallet_address=wallet_data.get("address", ""),
        workspace_dir=workspace_dir,
        api_key=os.environ.get("EM_API_KEY", ""),
    )
