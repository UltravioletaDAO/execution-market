"""
A2A JSON-RPC Router for Execution Market

Implements the A2A Protocol JSON-RPC 2.0 endpoint.
Handles message/send, message/stream, tasks/get, tasks/cancel, tasks/list.

Mount this router at /a2a/v1 in the main FastAPI app.
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .models import (
    JSONRPCError,
    A2ATaskState,
    Message,
    parse_part,
    now_iso,
)
from .task_manager import A2ATaskManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/a2a/v1", tags=["A2A Protocol"])

# ============== AUTH HELPER ==============


async def _extract_agent_id(request: Request) -> Optional[str]:
    """
    Extract agent identity from request via verified auth.

    Phase 1 GR-1.5 / API-019: Uses verify_agent_auth_write to
    cryptographically verify the caller's identity instead of trusting
    client-supplied headers like X-ERC8004-Agent-Id.
    """
    try:
        from api.auth import verify_agent_auth_write

        auth = await verify_agent_auth_write(request)
        # Prefer wallet address for cross-chain consistency
        if auth.wallet_address:
            return f"erc8004:{auth.wallet_address}"
        return f"agent:{auth.agent_id}"
    except Exception as _auth_err:
        # Auth failed — return None so the caller gets 401
        logger.debug(
            "A2A auth extraction failed: %s: %s", type(_auth_err).__name__, _auth_err
        )
        return None


# ============== METHOD HANDLERS ==============


async def _handle_message_send(
    params: Dict[str, Any],
    agent_id: Optional[str],
) -> Dict[str, Any]:
    """
    Handle message/send — create or update a task.

    If params contains an existing task 'id', this is a follow-up message.
    Otherwise, creates a new task.
    """
    task_id = params.get("id")
    raw_message = params.get("message")

    if not raw_message:
        return JSONRPCError.make(
            JSONRPCError.INVALID_PARAMS,
            "Missing 'message' in params",
        )

    # Parse message
    try:
        parts = [parse_part(p) for p in raw_message.get("parts", [])]
        message = Message(
            role=raw_message.get("role", "user"),
            parts=parts,
            metadata=raw_message.get("metadata"),
        )
    except Exception as e:
        return JSONRPCError.make(
            JSONRPCError.INVALID_PARAMS,
            f"Invalid message format: {str(e)}",
        )

    manager = A2ATaskManager(agent_id=agent_id)
    metadata = params.get("metadata")

    if task_id:
        # Follow-up message to existing task
        result = await manager.send_message(task_id, message)
        if not result:
            return JSONRPCError.make(
                JSONRPCError.TASK_NOT_FOUND,
                f"Task '{task_id}' not found or not accessible",
            )
    else:
        # New task creation
        result = await manager.create_task(
            message=message,
            task_id=task_id,
            metadata=metadata,
        )

    return result.model_dump(exclude_none=True)


async def _handle_tasks_get(
    params: Dict[str, Any],
    agent_id: Optional[str],
) -> Dict[str, Any]:
    """Handle tasks/get — retrieve task by ID."""
    task_id = params.get("id")
    if not task_id:
        return JSONRPCError.make(
            JSONRPCError.INVALID_PARAMS,
            "Missing 'id' in params",
        )

    include_history = params.get("historyLength", 0) > 0

    manager = A2ATaskManager(agent_id=agent_id)
    result = await manager.get_task(task_id, include_history=include_history)

    if not result:
        return JSONRPCError.make(
            JSONRPCError.TASK_NOT_FOUND,
            f"Task '{task_id}' not found",
        )

    return result.model_dump(exclude_none=True)


async def _handle_tasks_cancel(
    params: Dict[str, Any],
    agent_id: Optional[str],
) -> Dict[str, Any]:
    """Handle tasks/cancel — cancel a task."""
    task_id = params.get("id")
    if not task_id:
        return JSONRPCError.make(
            JSONRPCError.INVALID_PARAMS,
            "Missing 'id' in params",
        )

    manager = A2ATaskManager(agent_id=agent_id)
    result = await manager.cancel_task(task_id)

    if not result:
        return JSONRPCError.make(
            JSONRPCError.TASK_NOT_CANCELABLE,
            f"Task '{task_id}' not found or not in a cancellable state",
        )

    return result.model_dump(exclude_none=True)


async def _handle_tasks_list(
    params: Dict[str, Any],
    agent_id: Optional[str],
) -> Dict[str, Any]:
    """Handle tasks/list — list tasks for the agent (custom extension)."""
    limit = min(params.get("limit", 20), 100)
    state_str = params.get("state")
    state_filter = None
    if state_str:
        try:
            state_filter = A2ATaskState(state_str)
        except ValueError:
            pass

    manager = A2ATaskManager(agent_id=agent_id)
    tasks = await manager.list_tasks(limit=limit, state_filter=state_filter)

    return {
        "tasks": [t.model_dump(exclude_none=True) for t in tasks],
        "total": len(tasks),
    }


# ============== METHOD DISPATCH ==============


# Supported A2A methods
METHOD_HANDLERS = {
    "message/send": _handle_message_send,
    "tasks/get": _handle_tasks_get,
    "tasks/cancel": _handle_tasks_cancel,
    # Extensions (not in A2A spec but useful)
    "tasks/list": _handle_tasks_list,
}


async def _dispatch(
    request_data: Dict[str, Any],
    agent_id: Optional[str],
) -> Dict[str, Any]:
    """
    Dispatch a single JSON-RPC request to the appropriate handler.

    Returns a JSON-RPC response dict.
    """
    req_id = request_data.get("id")

    # Validate JSON-RPC version
    if request_data.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": JSONRPCError.make(
                JSONRPCError.INVALID_REQUEST,
                "Invalid JSON-RPC version (must be '2.0')",
            ),
        }

    method = request_data.get("method")
    if not method:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": JSONRPCError.make(
                JSONRPCError.INVALID_REQUEST,
                "Missing 'method' field",
            ),
        }

    handler = METHOD_HANDLERS.get(method)
    if not handler:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": JSONRPCError.make(
                JSONRPCError.METHOD_NOT_FOUND,
                f"Method '{method}' not supported. "
                f"Available: {', '.join(METHOD_HANDLERS.keys())}",
            ),
        }

    params = request_data.get("params", {})

    try:
        result = await handler(params, agent_id)

        # Check if result is an error dict
        if isinstance(result, dict) and "code" in result and "message" in result:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": result,
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("A2A validation error: %s", str(e)[:100])
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": f"Invalid params: {str(e)[:200]}"},
        }
    except Exception as e:
        logger.error("A2A error: %s: %s", type(e).__name__, str(e)[:100])
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": "Internal error"},
        }


# ============== STREAMING ==============


async def _stream_task_updates(
    task_id: str,
    agent_id: Optional[str],
    req_id: Any,
    poll_interval: float = 2.0,
    max_polls: int = 150,  # 5 min at 2s intervals
):
    """
    Server-Sent Events stream for task updates.

    Polls EM task status and yields A2A-formatted SSE events.
    """
    manager = A2ATaskManager(agent_id=agent_id)
    last_state = None

    for _ in range(max_polls):
        task = await manager.get_task(task_id)
        if not task:
            # Task deleted or inaccessible
            yield _sse_event(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": JSONRPCError.make(
                        JSONRPCError.TASK_NOT_FOUND,
                        f"Task '{task_id}' not found",
                    ),
                }
            )
            return

        current_state = task.status.state

        # Emit on state change
        if current_state != last_state:
            yield _sse_event(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": task.model_dump(exclude_none=True),
                }
            )
            last_state = current_state

            # Terminal states end the stream
            if current_state in {
                A2ATaskState.COMPLETED,
                A2ATaskState.FAILED,
                A2ATaskState.CANCELED,
                A2ATaskState.REJECTED,
            }:
                return

        await asyncio.sleep(poll_interval)

    # Timeout
    yield _sse_event(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": JSONRPCError.make(
                JSONRPCError.INTERNAL_ERROR,
                "Stream timeout — task still in progress",
            ),
        }
    )


def _sse_event(data: Dict[str, Any]) -> str:
    """Format a dict as an SSE event."""
    return f"data: {json.dumps(data)}\n\n"


# ============== ROUTES ==============


@router.post(
    "",
    summary="A2A JSON-RPC Endpoint",
    description=(
        "A2A Protocol JSON-RPC 2.0 endpoint. Supports: "
        "message/send, tasks/get, tasks/cancel, tasks/list"
    ),
    response_class=JSONResponse,
)
async def a2a_jsonrpc_endpoint(request: Request):
    """
    Main A2A JSON-RPC endpoint.

    Accepts single requests or batches.
    Dispatches to the appropriate handler based on the method field.
    """
    agent_id = await _extract_agent_id(request)

    if not agent_id:
        return JSONResponse(
            status_code=401,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Authentication required. Provide X-ERC8004-Agent-Id or X-API-Key header.",
                },
                "id": None,
            },
        )

    _client_ip = request.headers.get(  # noqa: F841
        "X-Forwarded-For", request.client.host if request.client else "unknown"
    )
    request_id = None  # noqa: F841

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": JSONRPCError.make(
                    JSONRPCError.PARSE_ERROR,
                    "Invalid JSON in request body",
                ),
            },
            status_code=200,  # JSON-RPC errors are always 200
        )

    if isinstance(body, dict):
        request_id = body.get("id")  # noqa: F841

    # Batch support
    if isinstance(body, list):
        if not body:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": JSONRPCError.make(
                        JSONRPCError.INVALID_REQUEST,
                        "Empty batch request",
                    ),
                },
                status_code=200,
            )
        results = await asyncio.gather(*[_dispatch(req, agent_id) for req in body])
        return JSONResponse(content=results, status_code=200)

    # Single request
    if not isinstance(body, dict):
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": JSONRPCError.make(
                    JSONRPCError.INVALID_REQUEST,
                    "Request must be a JSON object or array",
                ),
            },
            status_code=200,
        )

    result = await _dispatch(body, agent_id)
    return JSONResponse(content=result, status_code=200)


@router.post(
    "/stream",
    summary="A2A Streaming Endpoint (SSE)",
    description=(
        "A2A Protocol streaming endpoint. Creates a task and streams "
        "status updates as Server-Sent Events until completion."
    ),
)
async def a2a_stream_endpoint(request: Request):
    """
    A2A streaming endpoint (message/stream equivalent).

    Creates a task (or monitors existing) and returns SSE updates.
    """
    agent_id = await _extract_agent_id(request)

    if not agent_id:
        return JSONResponse(
            status_code=401,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Authentication required. Provide X-ERC8004-Agent-Id or X-API-Key header.",
                },
                "id": None,
            },
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": JSONRPCError.make(
                    JSONRPCError.PARSE_ERROR,
                    "Invalid JSON",
                ),
            },
            status_code=400,
        )

    req_id = body.get("id")
    params = body.get("params", {})
    task_id = params.get("id")

    # If no existing task, create one first
    if not task_id:
        result = await _handle_message_send(params, agent_id)
        if isinstance(result, dict) and "code" in result:
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": req_id, "error": result},
                status_code=200,
            )
        task_id = result.get("id")

    if not task_id:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": req_id,
                "error": JSONRPCError.make(
                    JSONRPCError.INTERNAL_ERROR,
                    "Failed to create or identify task for streaming",
                ),
            },
            status_code=200,
        )

    return StreamingResponse(
        _stream_task_updates(task_id, agent_id, req_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-A2A-Protocol-Version": "0.3.0",
        },
    )


@router.get(
    "/health",
    summary="A2A Endpoint Health",
)
async def a2a_health():
    """Health check for the A2A endpoint."""
    return {
        "status": "ok",
        "protocol": "A2A",
        "version": "0.3.0",
        "methods": list(METHOD_HANDLERS.keys()),
        "timestamp": now_iso(),
    }
