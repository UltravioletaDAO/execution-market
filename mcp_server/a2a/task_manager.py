"""
A2A Task Manager for Execution Market

Maps A2A protocol operations to EM's database layer (supabase_client).
This is the bridge between the A2A wire format and EM's internal representations.

Design: thin adapter — does NOT duplicate business logic from routes.py.
Calls supabase_client directly for reads, delegates to EM API for writes.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from .models import (
    A2ATask,
    A2ATaskState,
    A2ATaskStatus,
    Message,
    Artifact,
    TextPart,
    FilePart,
    DataPart,
    Part,
    em_status_to_a2a,
    now_iso,
    parse_part,
)

# Import database client — lazy-safe for testing
try:
    import supabase_client as db
except ImportError:
    db = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ============== TASK PARSING ==============


def _extract_task_params(message: Message) -> Dict[str, Any]:
    """
    Extract EM task creation parameters from an A2A message.

    Supports two modes:
    1. Structured: DataPart with EM-specific fields (title, bounty, etc.)
    2. Natural language: TextPart that gets mapped to a simple task

    Returns dict suitable for passing to supabase create_task.
    """
    params: Dict[str, Any] = {}
    text_parts: List[str] = []

    for part in message.parts:
        if isinstance(part, DataPart):
            # Structured data — merge directly
            data = part.data
            if "title" in data:
                params["title"] = data["title"]
            if "description" in data:
                params["description"] = data["description"]
            if "bounty_usd" in data:
                params["bounty_usd"] = float(data["bounty_usd"])
            if "bounty" in data:
                params["bounty_usd"] = float(data["bounty"])
            if "category" in data:
                params["category"] = data["category"]
            if "evidence_required" in data:
                params["evidence_required"] = data["evidence_required"]
            if "deadline_hours" in data:
                params["deadline_hours"] = int(data["deadline_hours"])
            if "location" in data:
                params["location"] = data["location"]
            if "max_workers" in data:
                params["max_workers"] = int(data["max_workers"])
            if "tags" in data:
                params["tags"] = data["tags"]
            if "skill_id" in data:
                params["skill_id"] = data["skill_id"]
            # Pass through any extra fields as metadata
            extra_keys = set(data.keys()) - {
                "title", "description", "bounty_usd", "bounty",
                "category", "evidence_required", "deadline_hours",
                "location", "max_workers", "tags", "skill_id",
            }
            if extra_keys:
                params.setdefault("metadata", {})
                for k in extra_keys:
                    params["metadata"][k] = data[k]
        elif isinstance(part, TextPart):
            text_parts.append(part.text)

    # If no structured title, use text parts
    if "title" not in params and text_parts:
        combined = " ".join(text_parts)
        # First line → title, rest → description
        lines = combined.strip().split("\n", 1)
        params["title"] = lines[0][:200]  # Cap at 200 chars
        if len(lines) > 1:
            params["description"] = lines[1].strip()

    # Defaults
    params.setdefault("bounty_usd", 1.00)
    params.setdefault("category", "simple_action")
    params.setdefault("evidence_required", ["text_response"])
    params.setdefault("deadline_hours", 24)

    return params


def _em_task_to_a2a(
    em_task: Dict[str, Any],
    include_history: bool = False,
    include_artifacts: bool = True,
) -> A2ATask:
    """
    Convert an EM task dict (from Supabase) to an A2A Task.

    Maps all EM fields to their A2A equivalents.
    """
    task_id = em_task.get("id", "unknown")
    em_status = em_task.get("status", "published")
    a2a_state = em_status_to_a2a(em_status)

    # Build status message
    status_text = _build_status_text(em_task, a2a_state)
    status_msg = Message(
        role="agent",
        parts=[TextPart(text=status_text)],
    )

    # Build artifacts from submissions
    artifacts = []
    if include_artifacts:
        artifacts = _extract_artifacts(em_task)

    # Build history from task events
    history = None
    if include_history:
        history = _build_history(em_task)

    # Metadata — expose useful EM fields
    metadata = {
        "em_status": em_status,
        "em_task_id": task_id,
        "bounty_usd": em_task.get("bounty_usd"),
        "category": em_task.get("category"),
        "created_at": em_task.get("created_at"),
        "deadline": em_task.get("deadline"),
        "location": em_task.get("location"),
        "worker_id": em_task.get("worker_id"),
    }
    # Strip None values
    metadata = {k: v for k, v in metadata.items() if v is not None}

    return A2ATask(
        id=task_id,
        contextId=em_task.get("agent_id"),
        status=A2ATaskStatus(
            state=a2a_state,
            message=status_msg,
            timestamp=em_task.get("updated_at") or em_task.get("created_at") or now_iso(),
        ),
        artifacts=artifacts if artifacts else None,
        history=history,
        metadata=metadata,
    )


def _build_status_text(em_task: Dict[str, Any], state: A2ATaskState) -> str:
    """Generate human-readable status text for the A2A message."""
    title = em_task.get("title", "Untitled task")
    bounty = em_task.get("bounty_usd", 0)

    messages = {
        A2ATaskState.SUBMITTED: f"Task '{title}' published. Bounty: ${bounty}. Awaiting worker.",
        A2ATaskState.WORKING: f"Task '{title}' assigned to a worker. In progress.",
        A2ATaskState.INPUT_REQUIRED: f"Task '{title}' has a submission awaiting review.",
        A2ATaskState.COMPLETED: f"Task '{title}' completed successfully. Payment settled.",
        A2ATaskState.FAILED: f"Task '{title}' expired with no completion.",
        A2ATaskState.CANCELED: f"Task '{title}' was cancelled.",
    }
    return messages.get(state, f"Task '{title}' in state: {state.value}")


def _extract_artifacts(em_task: Dict[str, Any]) -> List[Artifact]:
    """
    Extract A2A artifacts from EM task submissions.

    Maps worker evidence (photos, text, GPS) to A2A Artifact format.
    """
    artifacts = []

    # Check for submission data
    submissions = em_task.get("submissions", [])
    if not isinstance(submissions, list):
        submissions = []

    for idx, sub in enumerate(submissions):
        parts: List[Part] = []

        # Evidence text
        evidence_text = sub.get("evidence_text") or sub.get("notes")
        if evidence_text:
            parts.append(TextPart(text=evidence_text))

        # Evidence photos/files
        evidence_files = sub.get("evidence_files") or sub.get("photos") or []
        if isinstance(evidence_files, list):
            for file_url in evidence_files:
                if isinstance(file_url, str):
                    parts.append(FilePart(
                        mimeType="image/jpeg",
                        uri=file_url,
                        name=f"evidence_{idx}",
                    ))

        # GPS data
        gps = sub.get("gps") or sub.get("location")
        if gps and isinstance(gps, dict):
            parts.append(DataPart(data={
                "type": "gps_verification",
                "latitude": gps.get("lat") or gps.get("latitude"),
                "longitude": gps.get("lng") or gps.get("longitude"),
                "accuracy_m": gps.get("accuracy"),
                "timestamp": sub.get("submitted_at"),
            }))

        if parts:
            artifacts.append(Artifact(
                name=f"submission_{idx}",
                description=f"Worker submission #{idx + 1}",
                parts=parts,
                index=idx,
                lastChunk=True,
            ))

    return artifacts


def _build_history(em_task: Dict[str, Any]) -> List[Message]:
    """Build A2A message history from EM task events."""
    history = []

    # Creation message
    created_at = em_task.get("created_at", "")
    history.append(Message(
        role="user",
        parts=[TextPart(text=f"Task created: {em_task.get('title', '')}. "
                        f"Description: {em_task.get('description', 'N/A')}")],
        metadata={"timestamp": created_at, "event": "created"},
    ))

    # Status change events (if available)
    events = em_task.get("status_history") or em_task.get("events") or []
    if isinstance(events, list):
        for event in events:
            if isinstance(event, dict):
                history.append(Message(
                    role="agent",
                    parts=[TextPart(text=event.get("message", str(event)))],
                    metadata={
                        "timestamp": event.get("timestamp", ""),
                        "event": event.get("type", "status_change"),
                    },
                ))

    return history


# ============== PUBLIC API ==============


class A2ATaskManager:
    """
    Manages A2A task operations over the EM database.

    Instantiate per-request with the authenticated agent context.
    """

    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id

    async def create_task(
        self,
        message: Message,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> A2ATask:
        """
        Create a new EM task from an A2A message/send request.

        Args:
            message: The A2A message containing task details
            task_id: Optional pre-assigned task ID
            metadata: Optional A2A metadata

        Returns:
            A2ATask with status=submitted
        """

        params = _extract_task_params(message)

        # Add agent context
        if self.agent_id:
            params["agent_id"] = self.agent_id

        # Calculate deadline
        deadline_hours = params.pop("deadline_hours", 24)
        deadline = datetime.now(timezone.utc) + timedelta(hours=deadline_hours)
        params["deadline"] = deadline.isoformat()

        # Set status
        params["status"] = "published"
        params["created_at"] = now_iso()
        params["updated_at"] = now_iso()

        # A2A metadata
        a2a_meta = params.pop("metadata", {})
        if metadata:
            a2a_meta.update(metadata)
        a2a_meta["a2a_protocol"] = True
        a2a_meta["a2a_version"] = "0.3.0"
        params["metadata"] = a2a_meta

        # Create in database
        try:
            result = db.create_task(params)
            if result and isinstance(result, dict):
                return _em_task_to_a2a(result)
            elif result and isinstance(result, list) and len(result) > 0:
                return _em_task_to_a2a(result[0])
        except Exception as e:
            logger.error(f"Failed to create task via A2A: {e}")
            raise

        # Fallback — construct response from params
        return A2ATask(
            id=task_id or str(uuid.uuid4()),
            contextId=self.agent_id,
            status=A2ATaskStatus(
                state=A2ATaskState.SUBMITTED,
                message=Message(
                    role="agent",
                    parts=[TextPart(text=f"Task '{params.get('title', '')}' created.")],
                ),
                timestamp=now_iso(),
            ),
            metadata=a2a_meta,
        )

    async def get_task(
        self,
        task_id: str,
        include_history: bool = False,
    ) -> Optional[A2ATask]:
        """
        Get an A2A task by ID.

        Args:
            task_id: The EM task ID
            include_history: Whether to include full message history

        Returns:
            A2ATask or None if not found
        """

        try:
            task = db.get_task(task_id)
            if not task:
                return None

            # Verify agent ownership if agent_id is set
            if self.agent_id and task.get("agent_id") != self.agent_id:
                # Allow read but strip sensitive data
                task.pop("agent_id", None)

            return _em_task_to_a2a(
                task,
                include_history=include_history,
                include_artifacts=True,
            )
        except Exception as e:
            logger.error(f"Failed to get A2A task {task_id}: {e}")
            return None

    async def cancel_task(self, task_id: str) -> Optional[A2ATask]:
        """
        Cancel an A2A task.

        Only tasks in cancellable states (published, accepted) can be cancelled.

        Args:
            task_id: The EM task ID

        Returns:
            Updated A2ATask or None if not found/not cancellable
        """

        try:
            task = db.get_task(task_id)
            if not task:
                return None

            # Check ownership
            if self.agent_id and task.get("agent_id") != self.agent_id:
                logger.warning(f"Agent {self.agent_id} tried to cancel task {task_id} they don't own")
                return None

            # Check if cancellable
            cancellable_states = {"published", "accepted"}
            if task.get("status") not in cancellable_states:
                logger.info(f"Task {task_id} in state {task.get('status')} not cancellable")
                return None

            # Cancel
            db.update_task(task_id, {
                "status": "cancelled",
                "updated_at": now_iso(),
            })

            task["status"] = "cancelled"
            task["updated_at"] = now_iso()
            return _em_task_to_a2a(task)
        except Exception as e:
            logger.error(f"Failed to cancel A2A task {task_id}: {e}")
            return None

    async def list_tasks(
        self,
        limit: int = 20,
        state_filter: Optional[A2ATaskState] = None,
    ) -> List[A2ATask]:
        """
        List tasks for the authenticated agent.

        Args:
            limit: Maximum number of tasks to return
            state_filter: Optional A2A state filter

        Returns:
            List of A2ATasks
        """

        try:
            # Map A2A state filter to EM status
            em_status = None
            if state_filter:
                # Reverse mapping
                for em_s, a2a_s in {
                    "published": A2ATaskState.SUBMITTED,
                    "accepted": A2ATaskState.WORKING,
                    "in_progress": A2ATaskState.WORKING,
                    "submitted": A2ATaskState.INPUT_REQUIRED,
                    "completed": A2ATaskState.COMPLETED,
                    "expired": A2ATaskState.FAILED,
                    "cancelled": A2ATaskState.CANCELED,
                }.items():
                    if a2a_s == state_filter:
                        em_status = em_s
                        break

            tasks = db.list_tasks(
                agent_id=self.agent_id,
                status=em_status,
                limit=limit,
            )

            return [_em_task_to_a2a(t) for t in (tasks or [])]
        except Exception as e:
            logger.error(f"Failed to list A2A tasks: {e}")
            return []

    async def send_message(
        self,
        task_id: str,
        message: Message,
    ) -> Optional[A2ATask]:
        """
        Send a follow-up message to an existing task.

        For EM, this maps to adding notes or approving/rejecting submissions.

        Args:
            task_id: The EM task ID
            message: The A2A message to send

        Returns:
            Updated A2ATask or None if not found
        """

        try:
            task = db.get_task(task_id)
            if not task:
                return None

            # Extract intent from message parts
            for part in message.parts:
                if isinstance(part, TextPart):
                    text_lower = part.text.lower().strip()
                    if text_lower.startswith("approve") or text_lower.startswith("accept"):
                        # This is an approval — delegate to the review flow
                        # For now, update status
                        db.update_task(task_id, {
                            "status": "completed",
                            "updated_at": now_iso(),
                        })
                        task["status"] = "completed"
                    elif text_lower.startswith("reject") or text_lower.startswith("dispute"):
                        db.update_task(task_id, {
                            "status": "disputed",
                            "updated_at": now_iso(),
                        })
                        task["status"] = "disputed"
                    elif text_lower.startswith("cancel"):
                        return await self.cancel_task(task_id)
                    else:
                        # Add as a note/comment
                        db.update_task(task_id, {
                            "updated_at": now_iso(),
                        })
                elif isinstance(part, DataPart):
                    action = part.data.get("action")
                    if action == "approve":
                        db.update_task(task_id, {
                            "status": "completed",
                            "updated_at": now_iso(),
                        })
                        task["status"] = "completed"
                    elif action == "reject":
                        db.update_task(task_id, {
                            "status": "disputed",
                            "updated_at": now_iso(),
                        })
                        task["status"] = "disputed"

            return _em_task_to_a2a(task, include_history=True)
        except Exception as e:
            logger.error(f"Failed to send message to A2A task {task_id}: {e}")
            return None
