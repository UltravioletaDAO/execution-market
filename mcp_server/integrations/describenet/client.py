"""
describe.net API Client for Chamba (NOW-166 to NOW-170)

Handles all communication with the describe.net API for seal management.

API Endpoints (describe.net v1):
- POST /seals - Create a new seal
- GET /seals/{user_id} - Get user's seals
- DELETE /seals/{seal_id} - Revoke a seal
- POST /badges - Create a badge
- GET /badges/{user_id} - Get user's badges
- POST /verify - Verify seal authenticity
"""

import os
import logging
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json

import httpx

from .seals import Seal, Badge, SealStatus, WorkerSealType, RequesterSealType, BadgeType

logger = logging.getLogger(__name__)


class DescribeNetError(Exception):
    """Base exception for describe.net API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class DescribeNetAuthError(DescribeNetError):
    """Authentication error with describe.net."""
    pass


class DescribeNetRateLimitError(DescribeNetError):
    """Rate limit exceeded."""
    pass


@dataclass
class DescribeNetConfig:
    """Configuration for describe.net API client."""
    api_url: str = "https://api.describe.net/v1"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    chamba_org_id: str = "chamba"  # Organization ID on describe.net

    @classmethod
    def from_env(cls) -> "DescribeNetConfig":
        """Load configuration from environment variables."""
        return cls(
            api_url=os.environ.get("DESCRIBENET_API_URL", "https://api.describe.net/v1"),
            api_key=os.environ.get("DESCRIBENET_API_KEY"),
            api_secret=os.environ.get("DESCRIBENET_API_SECRET"),
            timeout_seconds=int(os.environ.get("DESCRIBENET_TIMEOUT", "30")),
            chamba_org_id=os.environ.get("DESCRIBENET_ORG_ID", "chamba"),
        )


class DescribeNetClient:
    """
    Client for interacting with describe.net seal API.

    Handles seal creation, verification, and synchronization
    between Chamba and describe.net.

    Usage:
        client = DescribeNetClient.from_env()
        seal = await client.create_seal(
            seal_type=WorkerSealType.SKILLFUL,
            user_id="worker_123",
            user_type="worker",
            criteria_snapshot={"rating": 85, "tasks": 15}
        )
    """

    def __init__(self, config: Optional[DescribeNetConfig] = None):
        """
        Initialize describe.net client.

        Args:
            config: API configuration (defaults to env vars)
        """
        self.config = config or DescribeNetConfig.from_env()
        self._client: Optional[httpx.AsyncClient] = None

    @classmethod
    def from_env(cls) -> "DescribeNetClient":
        """Create client from environment variables."""
        return cls(DescribeNetConfig.from_env())

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_url,
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers=self._build_headers(),
            )
        return self._client

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Chamba/1.0 (describe.net integration)",
            "X-Org-ID": self.config.chamba_org_id,
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _sign_request(self, method: str, path: str, body: Optional[str] = None) -> str:
        """
        Generate HMAC signature for request authentication.

        Args:
            method: HTTP method
            path: Request path
            body: Request body (JSON string)

        Returns:
            HMAC signature
        """
        if not self.config.api_secret:
            return ""

        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        message = f"{timestamp}.{method}.{path}"
        if body:
            message += f".{body}"

        signature = hmac.new(
            self.config.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"{timestamp}.{signature}"

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to describe.net API.

        Args:
            method: HTTP method
            path: API path
            data: Request body
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            DescribeNetError: On API errors
        """
        client = await self._get_client()

        body = json.dumps(data) if data else None
        signature = self._sign_request(method, path, body)

        headers = {}
        if signature:
            headers["X-Signature"] = signature

        try:
            response = await client.request(
                method=method,
                url=path,
                json=data,
                params=params,
                headers=headers,
            )

            if response.status_code == 401:
                raise DescribeNetAuthError(
                    "Authentication failed with describe.net",
                    status_code=401
                )

            if response.status_code == 429:
                raise DescribeNetRateLimitError(
                    "Rate limit exceeded",
                    status_code=429
                )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise DescribeNetError(
                    f"API error: {response.status_code}",
                    status_code=response.status_code,
                    response=error_data
                )

            return response.json() if response.content else {}

        except httpx.TimeoutException:
            raise DescribeNetError("Request timeout")
        except httpx.RequestError as e:
            raise DescribeNetError(f"Request failed: {e}")

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ============== SEAL OPERATIONS ==============

    async def create_seal(
        self,
        seal_type: WorkerSealType | RequesterSealType,
        user_id: str,
        user_type: str,
        criteria_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Seal:
        """
        Create a new seal on describe.net.

        Args:
            seal_type: Type of seal to create
            user_id: Chamba user ID
            user_type: "worker" or "requester"
            criteria_snapshot: Metrics at time of earning

        Returns:
            Created Seal object

        Raises:
            DescribeNetError: On API errors
        """
        data = {
            "seal_type": seal_type.value,
            "user_id": user_id,
            "user_type": user_type,
            "org_id": self.config.chamba_org_id,
            "criteria_snapshot": criteria_snapshot or {},
            "earned_at": datetime.now(timezone.utc).isoformat(),
        }

        response = await self._request("POST", "/seals", data=data)

        logger.info(f"Created seal {seal_type.value} for {user_type} {user_id}")

        return Seal(
            seal_type=seal_type.value,
            user_id=user_id,
            user_type=user_type,
            status=SealStatus.ACTIVE,
            earned_at=datetime.now(timezone.utc),
            criteria_snapshot=criteria_snapshot,
            describe_net_id=response.get("seal_id"),
        )

    async def get_user_seals(
        self,
        user_id: str,
        user_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Seal]:
        """
        Get all seals for a user.

        Args:
            user_id: Chamba user ID
            user_type: Filter by "worker" or "requester"
            active_only: Only return active seals

        Returns:
            List of Seal objects
        """
        params = {
            "org_id": self.config.chamba_org_id,
            "active_only": str(active_only).lower(),
        }
        if user_type:
            params["user_type"] = user_type

        response = await self._request("GET", f"/seals/{user_id}", params=params)

        seals = []
        for seal_data in response.get("seals", []):
            seals.append(Seal.from_dict(seal_data))

        return seals

    async def revoke_seal(
        self,
        seal_id: str,
        reason: str,
    ) -> bool:
        """
        Revoke a seal on describe.net.

        Args:
            seal_id: describe.net seal ID
            reason: Reason for revocation

        Returns:
            True if revoked successfully
        """
        data = {
            "reason": reason,
            "revoked_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._request("DELETE", f"/seals/{seal_id}", data=data)
            logger.info(f"Revoked seal {seal_id}: {reason}")
            return True
        except DescribeNetError as e:
            logger.error(f"Failed to revoke seal {seal_id}: {e}")
            return False

    async def verify_seal(
        self,
        seal_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Verify a seal's authenticity.

        Args:
            seal_id: describe.net seal ID
            user_id: Expected user ID

        Returns:
            Verification result with seal details
        """
        data = {
            "seal_id": seal_id,
            "user_id": user_id,
            "org_id": self.config.chamba_org_id,
        }

        response = await self._request("POST", "/verify", data=data)

        return {
            "valid": response.get("valid", False),
            "seal": Seal.from_dict(response["seal"]) if response.get("seal") else None,
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ============== BADGE OPERATIONS ==============

    async def create_badge(
        self,
        badge_type: BadgeType,
        user_id: str,
        user_type: str,
        level: int = 1,
        criteria_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Badge:
        """
        Create a new badge on describe.net.

        Args:
            badge_type: Type of badge to create
            user_id: Chamba user ID
            user_type: "worker" or "requester"
            level: Badge level (1=Bronze, 2=Silver, 3=Gold)
            criteria_snapshot: Metrics at time of earning

        Returns:
            Created Badge object
        """
        data = {
            "badge_type": badge_type.value,
            "user_id": user_id,
            "user_type": user_type,
            "level": level,
            "org_id": self.config.chamba_org_id,
            "criteria_snapshot": criteria_snapshot or {},
            "earned_at": datetime.now(timezone.utc).isoformat(),
        }

        response = await self._request("POST", "/badges", data=data)

        logger.info(f"Created badge {badge_type.value} (level {level}) for {user_type} {user_id}")

        return Badge(
            badge_type=badge_type,
            user_id=user_id,
            user_type=user_type,
            status=SealStatus.ACTIVE,
            earned_at=datetime.now(timezone.utc),
            criteria_snapshot=criteria_snapshot,
            describe_net_id=response.get("badge_id"),
            level=level,
        )

    async def get_user_badges(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> List[Badge]:
        """
        Get all badges for a user.

        Args:
            user_id: Chamba user ID
            active_only: Only return active badges

        Returns:
            List of Badge objects
        """
        params = {
            "org_id": self.config.chamba_org_id,
            "active_only": str(active_only).lower(),
        }

        response = await self._request("GET", f"/badges/{user_id}", params=params)

        badges = []
        for badge_data in response.get("badges", []):
            badges.append(Badge.from_dict(badge_data))

        return badges

    # ============== BULK OPERATIONS ==============

    async def sync_user_reputation(
        self,
        user_id: str,
        user_type: str,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sync full reputation state to describe.net.

        This is called after task completion to update
        all seals and badges based on current metrics.

        Args:
            user_id: Chamba user ID
            user_type: "worker" or "requester"
            metrics: Current reputation metrics

        Returns:
            Sync result with updated seals/badges
        """
        data = {
            "user_id": user_id,
            "user_type": user_type,
            "org_id": self.config.chamba_org_id,
            "metrics": metrics,
            "sync_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        response = await self._request("POST", "/sync", data=data)

        return {
            "seals_added": response.get("seals_added", []),
            "seals_revoked": response.get("seals_revoked", []),
            "badges_added": response.get("badges_added", []),
            "badges_upgraded": response.get("badges_upgraded", []),
        }

    async def get_reputation_summary(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get full reputation summary from describe.net.

        Args:
            user_id: Chamba user ID

        Returns:
            Full reputation summary including all seals and badges
        """
        response = await self._request(
            "GET",
            f"/reputation/{user_id}",
            params={"org_id": self.config.chamba_org_id}
        )

        return {
            "user_id": user_id,
            "seals": [Seal.from_dict(s) for s in response.get("seals", [])],
            "badges": [Badge.from_dict(b) for b in response.get("badges", [])],
            "reputation_score": response.get("reputation_score", 0),
            "trust_level": response.get("trust_level", "new"),
            "last_updated": response.get("last_updated"),
        }

    # ============== WEBHOOK HANDLING ==============

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify incoming webhook signature from describe.net.

        Args:
            payload: Raw request body
            signature: X-Signature header value

        Returns:
            True if signature is valid
        """
        if not self.config.api_secret:
            logger.warning("No API secret configured, cannot verify webhook")
            return False

        try:
            timestamp, provided_sig = signature.split(".", 1)
            message = f"{timestamp}.POST./webhook.{payload.decode()}"

            expected_sig = hmac.new(
                self.config.api_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(provided_sig, expected_sig)

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False
