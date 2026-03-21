"""
Webhook CRUD REST Endpoints

Allows agents and partners to register, manage, and test webhook endpoints.
Fixes BUG-4: TS SDK calls 6 endpoints that all returned 404.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator

from ..auth import verify_api_key, APIKeyData
from webhooks.events import WebhookEventType, WebhookEvent
from webhooks.registry import get_webhook_registry, WebhookStatus
from webhooks.sender import send_webhook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class WebhookCreateRequest(BaseModel):
    url: str = Field(..., description="HTTPS endpoint URL")
    events: List[str] = Field(
        ..., description="Event types to subscribe to", min_length=1
    )
    description: str = Field("", description="Human-readable description")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: List[str]) -> List[str]:
        valid = {e.value for e in WebhookEventType}
        for event in v:
            if event not in valid:
                raise ValueError(f"Invalid event type: {event}. Valid: {sorted(valid)}")
        return v


class WebhookUpdateRequest(BaseModel):
    url: Optional[str] = None
    events: Optional[List[str]] = None
    description: Optional[str] = None
    status: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "paused"):
            raise ValueError("Status must be 'active' or 'paused'")
        return v


class WebhookResponse(BaseModel):
    webhook_id: str
    owner_id: str
    url: str
    events: List[str]
    description: str
    status: str
    created_at: str
    updated_at: str
    last_triggered_at: Optional[str] = None
    failure_count: int = 0
    total_deliveries: int = 0
    successful_deliveries: int = 0


class WebhookCreateResponse(WebhookResponse):
    secret: str = Field(..., description="HMAC signing secret (shown only once)")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=WebhookCreateResponse, status_code=201)
async def register_webhook(
    req: WebhookCreateRequest,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """Register a new webhook endpoint."""
    registry = get_webhook_registry()
    event_types = [WebhookEventType(e) for e in req.events]

    try:
        registration = registry.register(
            owner_id=api_key.agent_id,
            url=req.url,
            events=event_types,
            description=req.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    wh = registration.webhook
    return WebhookCreateResponse(
        webhook_id=wh.webhook_id,
        owner_id=wh.owner_id,
        url=wh.url,
        events=[e.value for e in wh.events],
        description=wh.description,
        status=wh.status.value,
        created_at=wh.created_at,
        updated_at=wh.updated_at,
        secret=registration.secret,
    )


@router.get("/", response_model=List[WebhookResponse])
async def list_webhooks(
    api_key: APIKeyData = Depends(verify_api_key),
):
    """List all webhooks for the authenticated agent."""
    registry = get_webhook_registry()
    webhooks = registry.get_by_owner(api_key.agent_id)
    return [
        WebhookResponse(
            webhook_id=wh.webhook_id,
            owner_id=wh.owner_id,
            url=wh.url,
            events=[e.value for e in wh.events],
            description=wh.description,
            status=wh.status.value,
            created_at=wh.created_at,
            updated_at=wh.updated_at,
            last_triggered_at=wh.last_triggered_at,
            failure_count=wh.failure_count,
            total_deliveries=wh.total_deliveries,
            successful_deliveries=wh.successful_deliveries,
        )
        for wh in webhooks
    ]


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """Get a single webhook by ID."""
    registry = get_webhook_registry()
    wh = registry.get(webhook_id)
    if not wh or wh.owner_id != api_key.agent_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookResponse(
        webhook_id=wh.webhook_id,
        owner_id=wh.owner_id,
        url=wh.url,
        events=[e.value for e in wh.events],
        description=wh.description,
        status=wh.status.value,
        created_at=wh.created_at,
        updated_at=wh.updated_at,
        last_triggered_at=wh.last_triggered_at,
        failure_count=wh.failure_count,
        total_deliveries=wh.total_deliveries,
        successful_deliveries=wh.successful_deliveries,
    )


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    req: WebhookUpdateRequest,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """Update a webhook endpoint."""
    registry = get_webhook_registry()

    event_types = [WebhookEventType(e) for e in req.events] if req.events else None
    status = WebhookStatus(req.status) if req.status else None

    try:
        wh = registry.update(
            webhook_id=webhook_id,
            owner_id=api_key.agent_id,
            url=req.url,
            events=event_types,
            description=req.description,
            status=status,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookResponse(
        webhook_id=wh.webhook_id,
        owner_id=wh.owner_id,
        url=wh.url,
        events=[e.value for e in wh.events],
        description=wh.description,
        status=wh.status.value,
        created_at=wh.created_at,
        updated_at=wh.updated_at,
        last_triggered_at=wh.last_triggered_at,
        failure_count=wh.failure_count,
        total_deliveries=wh.total_deliveries,
        successful_deliveries=wh.successful_deliveries,
    )


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """Delete a webhook endpoint."""
    registry = get_webhook_registry()
    deleted = registry.delete(webhook_id, api_key.agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/{webhook_id}/rotate-secret")
async def rotate_webhook_secret(
    webhook_id: str,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """Rotate the webhook signing secret. Returns new secret (shown only once)."""
    registry = get_webhook_registry()
    new_secret = registry.rotate_secret(webhook_id, api_key.agent_id)
    if not new_secret:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"webhook_id": webhook_id, "secret": new_secret}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    api_key: APIKeyData = Depends(verify_api_key),
):
    """Send a test ping event to the webhook."""
    registry = get_webhook_registry()
    wh = registry.get(webhook_id)
    if not wh or wh.owner_id != api_key.agent_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    secret = registry.get_secret(webhook_id) or ""
    event = WebhookEvent.test_event()

    try:
        await send_webhook(
            url=wh.url,
            event=event,
            secret=secret,
            webhook_id=webhook_id,
        )
        return {
            "webhook_id": webhook_id,
            "test_event_id": event.metadata.event_id,
            "delivered": True,
        }
    except Exception as e:
        return {
            "webhook_id": webhook_id,
            "delivered": False,
            "error": str(e),
        }
