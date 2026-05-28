"""
Execution Market API client for CLI (v1.0.0 — OWS/ERC-8128 wallet signing).

Wraps the canonical async signer (`execution_market.OwsEM8128Client`) so the
click-based sync CLI can use it transparently. Each request goes:

    CLI cmd (sync) → _request_with_retry → asyncio.run(self._ows.post|get)
                                            ↓
                       OwsEM8128Client signs via OWS CLI subprocess,
                       sends signed httpx call, returns parsed JSON.

The OWS vault holds the private key; it never enters this process. See
`execution_market._signer` for the wire format (lowercase keyid, alg=eip191,
RFC 9421 HTTP Message Signatures).

Migration v1.0.0 (2026-05-28): removed all `Authorization: Bearer {api_key}`
paths. Backend has `EM_API_KEYS_ENABLED=false` so the old client returned
HTTP 403 in production. Users re-run `em login` to bind a wallet.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar

import httpx

# Canonical signer (lives in the execution-market SDK we just shipped).
from execution_market import OwsEM8128Client, OwsSignError, task_fingerprint, with_backoff

from .config import DEFAULT_API_URL, DEFAULT_CHAIN_ID, get_api_url, get_executor_id, get_wallet


logger = logging.getLogger(__name__)


# Type variable for generic responses
T = TypeVar("T")


class TaskStatus(str, Enum):
    """Task status values."""
    PUBLISHED = "published"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskCategory(str, Enum):
    """Task categories."""
    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"


class EvidenceType(str, Enum):
    """Evidence types."""
    PHOTO = "photo"
    PHOTO_GEO = "photo_geo"
    VIDEO = "video"
    DOCUMENT = "document"
    SIGNATURE = "signature"
    TEXT_RESPONSE = "text_response"
    RECEIPT = "receipt"
    TIMESTAMP_PROOF = "timestamp_proof"


@dataclass
class APIError(Exception):
    """API error with details."""
    message: str
    status_code: int
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message} (HTTP {self.status_code})"
        return f"{self.message} (HTTP {self.status_code})"


@dataclass
class Task:
    """An Execution Market task."""
    id: str
    title: str
    instructions: str
    category: str
    bounty_usd: float
    status: str
    deadline: datetime
    evidence_required: List[str]
    evidence_optional: Optional[List[str]] = None
    location_hint: Optional[str] = None
    executor_id: Optional[str] = None
    created_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    min_reputation: Optional[int] = None
    payment_token: str = "USDC"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from API response."""
        return cls(
            id=data["id"],
            title=data["title"],
            instructions=data["instructions"],
            category=data["category"],
            bounty_usd=data["bounty_usd"],
            status=data["status"],
            deadline=datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")),
            evidence_required=data.get("evidence_required", []),
            evidence_optional=data.get("evidence_optional"),
            location_hint=data.get("location_hint"),
            executor_id=data.get("executor_id"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            agent_id=data.get("agent_id"),
            min_reputation=data.get("min_reputation"),
            payment_token=data.get("payment_token", "USDC"),
        )


@dataclass
class Submission:
    """A task submission."""
    id: str
    task_id: str
    executor_id: str
    evidence: Dict[str, Any]
    status: str
    pre_check_score: float
    submitted_at: datetime
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Submission":
        """Create Submission from API response."""
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            executor_id=data["executor_id"],
            evidence=data.get("evidence", {}),
            status=data["status"],
            pre_check_score=data.get("pre_check_score", 0.0),
            submitted_at=datetime.fromisoformat(data["submitted_at"].replace("Z", "+00:00")),
            notes=data.get("notes"),
        )


@dataclass
class WalletBalance:
    """Wallet balance information."""
    available_usd: float
    pending_usd: float
    total_earned_usd: float
    total_withdrawn_usd: float
    token: str = "USDC"


@dataclass
class WithdrawResult:
    """Withdrawal result."""
    success: bool
    amount_usd: float
    tx_hash: Optional[str] = None
    destination: Optional[str] = None
    error: Optional[str] = None


class EMAPIClient:
    """
    Execution Market API client (wallet-signed, ERC-8128 via OWS).

    Example:
        >>> client = EMAPIClient()  # picks up wallet from `em login` / EM_WALLET_* env
        >>> tasks = client.list_tasks(status="published", limit=10)
        >>> for task in tasks:
        ...     print(f"{task.title}: ${task.bounty_usd}")

    Construct directly if you need a non-default wallet:
        >>> client = EMAPIClient(wallet_name="my-agent", wallet_address="0x...", chain_id=8453)
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    RETRY_BACKOFF = 2.0

    def __init__(
        self,
        wallet_name: Optional[str] = None,
        wallet_address: Optional[str] = None,
        chain_id: Optional[int] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize API client.

        Args:
            wallet_name: OWS wallet name (default: from config/env via get_wallet()).
            wallet_address: 0x... EVM address (default: from config/env).
            chain_id: EVM chain id for the keyid (default: 8453 Base, or from config).
            base_url: API base URL (default: from config/env).
            timeout: Request timeout in seconds (forwarded to httpx in the signer).
            max_retries: Maximum retry attempts on transient errors.

        Raises:
            APIError(401): if no wallet is configured anywhere. Run `em login` first.
        """
        # Resolve wallet identity. Explicit args override config/env.
        if wallet_name is None or wallet_address is None:
            walletinfo = get_wallet()
            if not walletinfo:
                raise APIError(
                    message="No wallet configured. Run 'em login' to bind one, "
                            "or set EM_WALLET_NAME + EM_WALLET_ADDRESS.",
                    status_code=401,
                )
            cfg_name, cfg_addr, cfg_chain = walletinfo
            wallet_name = wallet_name or cfg_name
            wallet_address = wallet_address or cfg_addr
            chain_id = chain_id if chain_id is not None else cfg_chain
        if chain_id is None:
            chain_id = DEFAULT_CHAIN_ID

        self.wallet_name = wallet_name
        self.wallet_address = wallet_address
        self.chain_id = chain_id
        self.base_url = base_url or get_api_url()
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else self.MAX_RETRIES

        # Lazily constructed; built fresh per __init__ since OwsEM8128Client
        # has no persistent connection state.
        self._ows: Optional[OwsEM8128Client] = None

    @property
    def ows(self) -> OwsEM8128Client:
        """Lazy-construct the signed httpx client (no persistent socket pool)."""
        if self._ows is None:
            self._ows = OwsEM8128Client(
                wallet_name=self.wallet_name,
                wallet_address=self.wallet_address,
                chain_id=self.chain_id,
                api_url=self.base_url,
            )
        return self._ows

    # ------------------------------------------------------------------
    # Async-to-sync bridge: the canonical signer is async; the CLI is sync.
    # ------------------------------------------------------------------

    @staticmethod
    def _run(coro: Any) -> Any:
        """Run an async coroutine to completion from sync CLI code.

        Each call spins a fresh event loop. The overhead (~1-5 ms) is
        dwarfed by the network round-trip, and it keeps us from holding
        an event loop alive across click commands.
        """
        return asyncio.run(coro)

    def _handle_http_error(self, exc: httpx.HTTPStatusError) -> APIError:
        """Convert httpx's status error to our APIError shape."""
        status = exc.response.status_code
        try:
            data = exc.response.json()
            return APIError(
                message=data.get("message", exc.response.text),
                status_code=status,
                code=data.get("code"),
                details=data.get("details"),
            )
        except Exception:
            return APIError(message=exc.response.text or f"HTTP {status}", status_code=status)

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a signed HTTP request with retry on transient errors.

        Args:
            method: "GET" or "POST".
            path: API path (e.g. "/v1/tasks" — leading slash, no host).
            json_body: JSON body for POST.
            params: querystring params for GET (rendered into path).
            extra_headers: e.g. {"X-Idempotency-Key": fingerprint}. Not signed
                (ERC-8128 only covers @method/@authority/@path/@query/content-digest),
                so safe to add.

        Returns:
            Parsed JSON body, or {} on 204.

        Raises:
            APIError: on permanent failure after retries.
        """
        # Render querystring directly into the path so it becomes part of @query.
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            path = f"{path}?{qs}" if qs else path

        last_error: Optional[Exception] = None
        delay = self.RETRY_DELAY

        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    data = self._run(self.ows.get(path))
                else:
                    data = self._run(
                        self.ows.post(path, data=json_body, extra_headers=extra_headers)
                    )
                # OwsEM8128Client returns parsed json directly; pass through.
                return data if isinstance(data, dict) else {"data": data}

            except OwsSignError as e:
                # Signing failures are not retryable — the vault is locked or
                # OWS isn't installed. Re-raise as a 401 so the CLI prints a
                # clear "run em login" message.
                raise APIError(message=f"Wallet signing failed: {e}", status_code=401) from e

            except httpx.HTTPStatusError as e:
                err = self._handle_http_error(e)
                # 4xx (except 429) is permanent — don't retry.
                if 400 <= err.status_code < 500 and err.status_code != 429:
                    raise err
                last_error = err

            except httpx.TimeoutException as e:
                last_error = APIError(message=f"Request timed out: {e}", status_code=408)

            except httpx.ConnectError as e:
                last_error = APIError(message=f"Connection failed: {e}", status_code=503)

            if attempt < self.max_retries:
                logger.debug(f"Retry {attempt + 1}/{self.max_retries} after {delay}s")
                time.sleep(delay)
                delay *= self.RETRY_BACKOFF

        if last_error:
            raise last_error
        raise APIError(message="Request failed", status_code=500)

    # =========================================================================
    # Task Operations (Agent)
    # =========================================================================

    def list_tasks(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks (signed → returns only YOUR tasks per backend filter)."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if category:
            params["category"] = category

        data = self._request_with_retry("GET", "/v1/tasks", params=params)
        return [Task.from_dict(t) for t in data.get("tasks", data.get("items", []))]

    def get_task(self, task_id: str) -> Task:
        """Get a task by ID (signed — owner can read non-`published` states)."""
        data = self._request_with_retry("GET", f"/v1/tasks/{task_id}")
        return Task.from_dict(data)

    def create_task(
        self,
        title: str,
        instructions: str,
        category: str,
        bounty_usd: float,
        deadline_hours: int,
        evidence_required: List[str],
        evidence_optional: Optional[List[str]] = None,
        location_hint: Optional[str] = None,
        min_reputation: int = 0,
        payment_token: str = "USDC",
        **kwargs: Any,
    ) -> Task:
        """
        Create a new task with an idempotency fingerprint.

        Sends `X-Idempotency-Key = task_fingerprint(body)` so a retry after a
        timeout cannot duplicate the task (backend dedupes via
        `mcp_server/api/routers/tasks.py:531-589`). The fingerprint is a
        SHA-256 of the identity-defining fields (title/instructions/location/
        bounty/deadline/evidence/network); metadata fields like agent_name
        don't affect it.
        """
        payload: Dict[str, Any] = {
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "evidence_required": evidence_required,
            "evidence_optional": evidence_optional,
            "location_hint": location_hint,
            "min_reputation": min_reputation,
            "payment_token": payment_token,
            **kwargs,
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        idem_key = task_fingerprint(payload)
        data = self._request_with_retry(
            "POST",
            "/v1/tasks",
            json_body=payload,
            extra_headers={"X-Idempotency-Key": idem_key},
        )
        return Task.from_dict(data)

    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Cancel a task."""
        payload: Dict[str, Any] = {}
        if reason:
            payload["reason"] = reason
        return self._request_with_retry("POST", f"/v1/tasks/{task_id}/cancel", json_body=payload)

    def get_task_submissions(self, task_id: str) -> List[Submission]:
        """Get submissions for a task."""
        data = self._request_with_retry("GET", f"/v1/tasks/{task_id}/submissions")
        return [Submission.from_dict(s) for s in data.get("submissions", data.get("items", []))]

    def approve_submission(
        self,
        submission_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve a submission (triggers escrow release on-chain)."""
        payload: Dict[str, Any] = {}
        if notes:
            payload["notes"] = notes
        return self._request_with_retry(
            "POST", f"/v1/submissions/{submission_id}/approve", json_body=payload
        )

    def reject_submission(self, submission_id: str, notes: str) -> Dict[str, Any]:
        """Reject a submission (triggers refund)."""
        return self._request_with_retry(
            "POST", f"/v1/submissions/{submission_id}/reject", json_body={"notes": notes}
        )

    # =========================================================================
    # Worker Operations
    # =========================================================================

    def list_available_tasks(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        min_bounty: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Task]:
        """List available tasks for workers (public endpoint, still signed)."""
        params: Dict[str, Any] = {"status": "published", "limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if location:
            params["location"] = location
        if min_bounty:
            params["min_bounty"] = min_bounty

        data = self._request_with_retry("GET", "/v1/tasks/available", params=params)
        return [Task.from_dict(t) for t in data.get("tasks", data.get("items", []))]

    def apply_to_task(self, task_id: str, message: Optional[str] = None) -> Dict[str, Any]:
        """Apply to a task as a worker."""
        executor_id = get_executor_id()
        if not executor_id:
            raise APIError(
                message="Executor ID not configured. Set EM_EXECUTOR_ID or run 'em login --worker'",
                status_code=400,
            )

        payload: Dict[str, Any] = {"executor_id": executor_id}
        if message:
            payload["message"] = message
        return self._request_with_retry("POST", f"/v1/tasks/{task_id}/apply", json_body=payload)

    def submit_evidence(
        self,
        task_id: str,
        evidence: Dict[str, Any],
        notes: Optional[str] = None,
    ) -> Submission:
        """Submit evidence for a task."""
        executor_id = get_executor_id()
        if not executor_id:
            raise APIError(
                message="Executor ID not configured. Set EM_EXECUTOR_ID or run 'em login --worker'",
                status_code=400,
            )

        payload: Dict[str, Any] = {"executor_id": executor_id, "evidence": evidence}
        if notes:
            payload["notes"] = notes
        data = self._request_with_retry("POST", f"/v1/tasks/{task_id}/submit", json_body=payload)
        return Submission.from_dict(data)

    def get_my_tasks(self, status: Optional[str] = None, limit: int = 20) -> List[Task]:
        """Get tasks assigned to current worker."""
        executor_id = get_executor_id()
        if not executor_id:
            raise APIError(message="Executor ID not configured", status_code=400)

        params: Dict[str, Any] = {"executor_id": executor_id, "limit": limit}
        if status:
            params["status"] = status
        data = self._request_with_retry("GET", "/v1/worker/tasks", params=params)
        return [Task.from_dict(t) for t in data.get("tasks", data.get("items", []))]

    # =========================================================================
    # Wallet / Balance
    # =========================================================================

    def get_wallet_balance(self) -> WalletBalance:
        """Get wallet balance for current user."""
        data = self._request_with_retry("GET", "/v1/wallet/balance")
        return WalletBalance(
            available_usd=data.get("available_usd", 0.0),
            pending_usd=data.get("pending_usd", 0.0),
            total_earned_usd=data.get("total_earned_usd", 0.0),
            total_withdrawn_usd=data.get("total_withdrawn_usd", 0.0),
            token=data.get("token", "USDC"),
        )

    def withdraw(
        self,
        amount_usd: Optional[float] = None,
        destination: Optional[str] = None,
    ) -> WithdrawResult:
        """Withdraw earnings."""
        payload: Dict[str, Any] = {}
        if amount_usd:
            payload["amount_usd"] = amount_usd
        if destination:
            payload["destination"] = destination

        data = self._request_with_retry("POST", "/v1/wallet/withdraw", json_body=payload)
        return WithdrawResult(
            success=data.get("success", False),
            amount_usd=data.get("amount_usd", 0.0),
            tx_hash=data.get("tx_hash"),
            destination=data.get("destination"),
            error=data.get("error"),
        )

    def get_transactions(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get transaction history."""
        data = self._request_with_retry(
            "GET", "/v1/wallet/transactions", params={"limit": limit, "offset": offset}
        )
        return data.get("transactions", data.get("items", []))

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics for the current user."""
        return self._request_with_retry("GET", "/v1/analytics", params={"days": days})

    # =========================================================================
    # Identity (ERC-8004)
    # =========================================================================

    def get_identity(self, network: Optional[str] = None) -> Dict[str, Any]:
        """Look up the current wallet's ERC-8004 identity on `network`."""
        path = f"/v1/reputation/identity/wallet/{self.wallet_address}"
        params: Dict[str, Any] = {}
        if network:
            params["network"] = network
        return self._request_with_retry("GET", path, params=params)

    def register_identity(self, network: str = "base") -> Dict[str, Any]:
        """Register ERC-8004 identity gasless via the Facilitator (idempotent)."""
        body = {
            "network": network,
            "recipient": self.wallet_address,
            "agent_uri": f"https://execution.market/agents/{self.wallet_address.lower()}",
        }
        return self._request_with_retry("POST", "/v1/reputation/register", json_body=body)

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def close(self) -> None:
        """No persistent state to close — OwsEM8128Client builds httpx per request."""
        self._ows = None

    def __enter__(self) -> "EMAPIClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# Global client instance (lazy)
_client: Optional[EMAPIClient] = None


def get_client() -> EMAPIClient:
    """Get or create the global API client (uses active profile / env wallet)."""
    global _client
    if _client is None:
        _client = EMAPIClient()
    return _client


def reset_client() -> None:
    """Reset the global API client (call after `em login` to pick up new wallet)."""
    global _client
    if _client:
        _client.close()
    _client = None
