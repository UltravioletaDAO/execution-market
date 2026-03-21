"""
A2A Protocol Data Models for Execution Market

Pydantic models implementing the A2A Protocol specification (v0.3.0 / RC v1.0).
These are the wire-format types used in JSON-RPC messages.

See: https://a2a-protocol.org/latest/specification/
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone


# ============== ENUMS ==============


class A2ATaskState(str, Enum):
    """A2A task lifecycle states."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"
    AUTH_REQUIRED = "auth-required"
    UNKNOWN = "unknown"


class PartKind(str, Enum):
    """Part type discriminator."""

    TEXT = "text"
    FILE = "file"
    DATA = "data"


# ============== PARTS ==============


class TextPart(BaseModel):
    """A text content part."""

    kind: str = "text"
    text: str
    metadata: Optional[Dict[str, Any]] = None


class FilePart(BaseModel):
    """A file/binary content part (inline base64 or URI reference)."""

    kind: str = "file"
    mimeType: str
    data: Optional[str] = None  # base64-encoded content
    uri: Optional[str] = None  # URI reference (mutually exclusive with data)
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DataPart(BaseModel):
    """A structured data part (arbitrary JSON)."""

    kind: str = "data"
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


# Union type for parts
Part = Union[TextPart, FilePart, DataPart]


def parse_part(raw: Dict[str, Any]) -> Part:
    """Parse a raw dict into the appropriate Part type."""
    kind = raw.get("kind", "text")
    if kind == "file":
        return FilePart(**raw)
    elif kind == "data":
        return DataPart(**raw)
    else:
        return TextPart(**raw)


# ============== MESSAGES ==============


class Message(BaseModel):
    """A message in the A2A conversation."""

    role: str  # "user" or "agent"
    parts: List[Part]
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ============== ARTIFACTS ==============


class Artifact(BaseModel):
    """
    An artifact produced by task execution.

    In EM context: worker photos, GPS data, receipts, etc.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Part]
    index: int = 0
    append: Optional[bool] = None
    lastChunk: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ============== TASK STATUS ==============


class A2ATaskStatus(BaseModel):
    """Current status of an A2A task."""

    state: A2ATaskState
    message: Optional[Message] = None
    timestamp: str  # ISO-8601

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ============== TASK ==============


class A2ATask(BaseModel):
    """
    A complete A2A Task.

    This is the primary response object for message/send and tasks/get.
    """

    id: str
    contextId: Optional[str] = None
    status: A2ATaskStatus
    artifacts: Optional[List[Artifact]] = None
    history: Optional[List[Message]] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ============== JSON-RPC ==============


class JSONRPCRequest(BaseModel):
    """A2A JSON-RPC 2.0 request."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    """A2A JSON-RPC 2.0 response."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class JSONRPCError:
    """Standard JSON-RPC error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # A2A-specific error codes
    TASK_NOT_FOUND = -32001
    TASK_NOT_CANCELABLE = -32002
    AUTHENTICATION_REQUIRED = -32003
    INSUFFICIENT_FUNDS = -32004
    RATE_LIMITED = -32005

    @staticmethod
    def make(code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create a JSON-RPC error dict."""
        err: Dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return err


# ============== STATUS MAPPING ==============

# EM TaskStatus → A2A TaskState mapping
EM_TO_A2A_STATE: Dict[str, A2ATaskState] = {
    "published": A2ATaskState.SUBMITTED,
    "accepted": A2ATaskState.WORKING,
    "in_progress": A2ATaskState.WORKING,
    "submitted": A2ATaskState.INPUT_REQUIRED,
    "verifying": A2ATaskState.INPUT_REQUIRED,
    "completed": A2ATaskState.COMPLETED,
    "disputed": A2ATaskState.INPUT_REQUIRED,
    "expired": A2ATaskState.FAILED,
    "cancelled": A2ATaskState.CANCELED,
}


def em_status_to_a2a(em_status: str) -> A2ATaskState:
    """Convert an EM task status string to A2A TaskState."""
    return EM_TO_A2A_STATE.get(em_status.lower().strip(), A2ATaskState.UNKNOWN)


def now_iso() -> str:
    """Current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()
