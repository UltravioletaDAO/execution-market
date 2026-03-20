"""Submissions resource — client.submissions.approve(), .reject(), etc."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..models import (
    ApproveParams,
    RejectParams,
    Submission,
    SubmissionList,
    SubmitEvidenceParams,
)

if TYPE_CHECKING:
    from ..client import EMClient


class SubmissionsResource:
    """Operations on submissions.

    Usage::

        subs = await client.submissions.list(task_id="...")
        await client.submissions.approve("sub-uuid")
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def list(self, task_id: str) -> SubmissionList:
        """List all submissions for a task."""
        data = await self._client._request("GET", f"/tasks/{task_id}/submissions")
        return SubmissionList.model_validate(data)

    async def submit(self, task_id: str, params: SubmitEvidenceParams) -> Submission:
        """Submit evidence for a task (worker operation)."""
        data = await self._client._request(
            "POST", f"/tasks/{task_id}/submit",
            json=params.model_dump(exclude_none=True),
        )
        return Submission.model_validate(data)

    async def approve(
        self,
        submission_id: str,
        params: ApproveParams | None = None,
    ) -> dict[str, Any]:
        """Approve a submission (releases payment to worker)."""
        body = params.model_dump(exclude_none=True) if params else {}
        return await self._client._request(
            "POST", f"/submissions/{submission_id}/approve",
            json=body,
        )

    async def reject(
        self,
        submission_id: str,
        params: RejectParams,
    ) -> dict[str, Any]:
        """Reject a submission."""
        return await self._client._request(
            "POST", f"/submissions/{submission_id}/reject",
            json=params.model_dump(exclude_none=True),
        )

    async def request_more_info(
        self,
        submission_id: str,
        notes: str,
    ) -> dict[str, Any]:
        """Request additional information from the worker."""
        return await self._client._request(
            "POST", f"/submissions/{submission_id}/request-more-info",
            json={"notes": notes},
        )
