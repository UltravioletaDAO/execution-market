"""Evidence resource — client.evidence.presign_upload(), .upload(), .verify()."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..models import EvidenceUploadInfo, EvidenceVerifyResult

if TYPE_CHECKING:
    from ..client import EMClient


class EvidenceResource:
    """Evidence upload and verification operations.

    Usage::

        # Get presigned upload URL
        info = await client.evidence.presign_upload(
            task_id="...", filename="photo.jpg", content_type="image/jpeg"
        )

        # Upload file to S3 (convenience method)
        public_url = await client.evidence.upload(
            task_id="...", filename="photo.jpg",
            content_type="image/jpeg", data=file_bytes
        )

        # AI-powered verification
        result = await client.evidence.verify(task_id="...", evidence_url="https://...")
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def presign_upload(
        self,
        task_id: str,
        filename: str,
        content_type: str = "image/jpeg",
    ) -> EvidenceUploadInfo:
        """Get a presigned S3 URL for evidence upload."""
        data = await self._client._request(
            "GET", "/evidence/presign-upload",
            params={
                "task_id": task_id,
                "filename": filename,
                "content_type": content_type,
            },
        )
        return EvidenceUploadInfo.model_validate(data)

    async def presign_download(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Get a presigned S3 URL for evidence download."""
        return await self._client._request(
            "GET", "/evidence/presign-download",
            params={"key": key},
        )

    async def upload(
        self,
        task_id: str,
        filename: str,
        data: bytes,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload evidence to S3 via presigned URL (convenience method).

        Returns the public CDN URL for the uploaded file.
        """
        import httpx

        info = await self.presign_upload(task_id, filename, content_type)
        async with httpx.AsyncClient() as http:
            resp = await http.put(
                info.upload_url,
                content=data,
                headers={"Content-Type": content_type},
            )
            resp.raise_for_status()
        return info.public_url or info.upload_url.split("?")[0]

    async def verify(
        self,
        task_id: str,
        evidence_url: str,
        evidence_type: str = "photo",
    ) -> EvidenceVerifyResult:
        """Run AI-powered evidence verification against task requirements."""
        data = await self._client._request(
            "POST", "/evidence/verify",
            json={
                "task_id": task_id,
                "evidence_url": evidence_url,
                "evidence_type": evidence_type,
            },
        )
        return EvidenceVerifyResult.model_validate(data)
