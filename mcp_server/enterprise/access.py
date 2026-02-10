"""
Enterprise Access Control (NOW-161)

Role-based access control for enterprise organizations.
"""

import logging
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles within an organization."""

    OWNER = "owner"  # Full access, billing
    ADMIN = "admin"  # Manage users, settings
    MANAGER = "manager"  # Create tasks, approve
    OPERATOR = "operator"  # Create tasks
    VIEWER = "viewer"  # Read-only
    API_KEY = "api_key"  # Programmatic access


class Permission(str, Enum):
    """Granular permissions."""

    # Tasks
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_APPROVE = "task:approve"

    # Workers
    WORKER_VIEW = "worker:view"
    WORKER_MANAGE = "worker:manage"
    WORKER_BLOCK = "worker:block"

    # Payments
    PAYMENT_VIEW = "payment:view"
    PAYMENT_APPROVE = "payment:approve"
    PAYMENT_REFUND = "payment:refund"

    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"

    # Settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_UPDATE = "settings:update"

    # Users
    USER_INVITE = "user:invite"
    USER_MANAGE = "user:manage"
    USER_DELETE = "user:delete"

    # API
    API_KEY_CREATE = "api_key:create"
    API_KEY_REVOKE = "api_key:revoke"

    # Billing
    BILLING_VIEW = "billing:view"
    BILLING_MANAGE = "billing:manage"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OWNER: set(Permission),  # All permissions
    Role.ADMIN: {
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_DELETE,
        Permission.TASK_APPROVE,
        Permission.WORKER_VIEW,
        Permission.WORKER_MANAGE,
        Permission.WORKER_BLOCK,
        Permission.PAYMENT_VIEW,
        Permission.PAYMENT_APPROVE,
        Permission.PAYMENT_REFUND,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_UPDATE,
        Permission.USER_INVITE,
        Permission.USER_MANAGE,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_REVOKE,
        Permission.BILLING_VIEW,
    },
    Role.MANAGER: {
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_APPROVE,
        Permission.WORKER_VIEW,
        Permission.WORKER_MANAGE,
        Permission.PAYMENT_VIEW,
        Permission.PAYMENT_APPROVE,
        Permission.ANALYTICS_VIEW,
        Permission.SETTINGS_VIEW,
    },
    Role.OPERATOR: {
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.WORKER_VIEW,
        Permission.PAYMENT_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    Role.VIEWER: {
        Permission.TASK_READ,
        Permission.WORKER_VIEW,
        Permission.PAYMENT_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    Role.API_KEY: {
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.WORKER_VIEW,
        Permission.PAYMENT_VIEW,
    },
}


@dataclass
class OrgMember:
    """Organization member."""

    user_id: str
    org_id: str
    role: Role
    email: str
    name: Optional[str] = None
    custom_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    invited_by: Optional[str] = None
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    is_active: bool = True


@dataclass
class APIKey:
    """API key for programmatic access."""

    key_id: str
    org_id: str
    name: str
    key_hash: str  # Never store actual key
    prefix: str  # First 8 chars for identification
    permissions: Set[Permission] = field(default_factory=set)
    rate_limit_override: Optional[int] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True


class AccessControl:
    """
    Manages access control for organizations.

    Features:
    - Role-based access control
    - Custom permission grants/denials
    - API key management
    - Audit logging
    """

    def __init__(self):
        """Initialize access control."""
        self._members: Dict[
            str, Dict[str, OrgMember]
        ] = {}  # org_id -> user_id -> member
        self._api_keys: Dict[str, Dict[str, APIKey]] = {}  # org_id -> key_id -> key

    async def add_member(
        self,
        org_id: str,
        user_id: str,
        email: str,
        role: Role,
        invited_by: Optional[str] = None,
        **kwargs,
    ) -> OrgMember:
        """
        Add member to organization.

        Args:
            org_id: Organization ID
            user_id: User ID
            email: User email
            role: User role
            invited_by: Inviting user ID
            **kwargs: Additional member fields

        Returns:
            Created OrgMember
        """
        member = OrgMember(
            user_id=user_id,
            org_id=org_id,
            role=role,
            email=email,
            invited_by=invited_by,
            invited_at=datetime.now(timezone.utc),
            **kwargs,
        )

        if org_id not in self._members:
            self._members[org_id] = {}

        self._members[org_id][user_id] = member
        logger.info(f"Member added: {user_id} to {org_id} as {role.value}")
        return member

    async def update_role(
        self, org_id: str, user_id: str, new_role: Role, updated_by: str
    ) -> OrgMember:
        """Update member's role."""
        member = self._get_member(org_id, user_id)
        if not member:
            raise ValueError(f"Member not found: {user_id}")

        old_role = member.role
        member.role = new_role
        logger.info(
            f"Role updated: {user_id} from {old_role.value} to {new_role.value}"
        )
        return member

    async def remove_member(self, org_id: str, user_id: str, removed_by: str) -> bool:
        """Remove member from organization."""
        if org_id in self._members and user_id in self._members[org_id]:
            del self._members[org_id][user_id]
            logger.info(f"Member removed: {user_id} from {org_id}")
            return True
        return False

    def has_permission(self, org_id: str, user_id: str, permission: Permission) -> bool:
        """
        Check if user has a specific permission.

        Args:
            org_id: Organization ID
            user_id: User ID
            permission: Permission to check

        Returns:
            True if permitted
        """
        member = self._get_member(org_id, user_id)
        if not member or not member.is_active:
            return False

        # Check denied first
        if permission in member.denied_permissions:
            return False

        # Check custom grants
        if permission in member.custom_permissions:
            return True

        # Check role permissions
        role_perms = ROLE_PERMISSIONS.get(member.role, set())
        return permission in role_perms

    def get_permissions(self, org_id: str, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        member = self._get_member(org_id, user_id)
        if not member or not member.is_active:
            return set()

        # Start with role permissions
        perms = ROLE_PERMISSIONS.get(member.role, set()).copy()

        # Add custom grants
        perms |= member.custom_permissions

        # Remove denials
        perms -= member.denied_permissions

        return perms

    async def grant_permission(
        self, org_id: str, user_id: str, permission: Permission, granted_by: str
    ):
        """Grant additional permission to user."""
        member = self._get_member(org_id, user_id)
        if not member:
            raise ValueError(f"Member not found: {user_id}")

        member.custom_permissions.add(permission)
        logger.info(f"Permission granted: {permission.value} to {user_id}")

    async def deny_permission(
        self, org_id: str, user_id: str, permission: Permission, denied_by: str
    ):
        """Explicitly deny permission for user."""
        member = self._get_member(org_id, user_id)
        if not member:
            raise ValueError(f"Member not found: {user_id}")

        member.denied_permissions.add(permission)
        logger.info(f"Permission denied: {permission.value} for {user_id}")

    # API Key management

    async def create_api_key(
        self,
        org_id: str,
        name: str,
        created_by: str,
        permissions: Optional[Set[Permission]] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple[APIKey, str]:
        """
        Create new API key.

        Returns:
            Tuple of (APIKey metadata, actual key string)
        """
        import secrets
        import hashlib

        # Generate key
        key_bytes = secrets.token_bytes(32)
        key_string = f"em_{key_bytes.hex()}"
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        key = APIKey(
            key_id=secrets.token_hex(8),
            org_id=org_id,
            name=name,
            key_hash=key_hash,
            prefix=key_string[:12],
            permissions=permissions or ROLE_PERMISSIONS[Role.API_KEY].copy(),
            created_by=created_by,
            expires_at=expires_at,
        )

        if org_id not in self._api_keys:
            self._api_keys[org_id] = {}

        self._api_keys[org_id][key.key_id] = key
        logger.info(f"API key created: {key.key_id} for {org_id}")

        # Return metadata and actual key (key shown only once)
        return key, key_string

    async def verify_api_key(self, key_string: str) -> Optional[APIKey]:
        """Verify API key and return metadata."""
        import hashlib

        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        for org_keys in self._api_keys.values():
            for key in org_keys.values():
                if key.key_hash == key_hash:
                    if not key.is_active:
                        return None
                    if key.expires_at and key.expires_at < datetime.now(timezone.utc):
                        return None
                    key.last_used = datetime.now(timezone.utc)
                    return key

        return None

    async def revoke_api_key(self, org_id: str, key_id: str, revoked_by: str) -> bool:
        """Revoke API key."""
        if org_id in self._api_keys and key_id in self._api_keys[org_id]:
            self._api_keys[org_id][key_id].is_active = False
            logger.info(f"API key revoked: {key_id}")
            return True
        return False

    # Private methods

    def _get_member(self, org_id: str, user_id: str) -> Optional[OrgMember]:
        """Get member by org and user ID."""
        if org_id not in self._members:
            return None
        return self._members[org_id].get(user_id)

    def list_members(self, org_id: str) -> List[OrgMember]:
        """List all members of an organization."""
        if org_id not in self._members:
            return []
        return list(self._members[org_id].values())

    def list_api_keys(self, org_id: str) -> List[APIKey]:
        """List all API keys for an organization."""
        if org_id not in self._api_keys:
            return []
        return list(self._api_keys[org_id].values())
