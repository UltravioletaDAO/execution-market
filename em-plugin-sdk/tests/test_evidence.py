"""Tests for the evidence resource."""

import pytest
import httpx
import respx

from em_plugin_sdk import EMClient

BASE = "https://api.execution.market/api/v1"


@pytest.fixture
def mock_router():
    with respx.mock(base_url=BASE) as router:
        yield router


@pytest.fixture
async def client(mock_router):
    async with EMClient(api_key="em_test") as c:
        yield c


class TestEvidence:
    async def test_presign_upload(self, mock_router, client):
        mock_router.get("/evidence/presign-upload").mock(return_value=httpx.Response(200, json={
            "upload_url": "https://s3.amazonaws.com/bucket/key?X-Amz-Signature=abc",
            "key": "evidence/task-1/photo.jpg",
            "public_url": "https://cdn.example.com/evidence/task-1/photo.jpg",
            "content_type": "image/jpeg",
            "expires_in": 900,
        }))
        info = await client.evidence.presign_upload("task-1", "photo.jpg")
        assert info.key == "evidence/task-1/photo.jpg"
        assert info.public_url.startswith("https://cdn")
        assert info.expires_in == 900

    async def test_presign_download(self, mock_router, client):
        mock_router.get("/evidence/presign-download").mock(return_value=httpx.Response(200, json={
            "download_url": "https://s3.amazonaws.com/bucket/key?signed",
            "expires_in": 3600,
        }))
        result = await client.evidence.presign_download("evidence/task-1/photo.jpg")
        assert "download_url" in result

    async def test_verify(self, mock_router, client):
        mock_router.post("/evidence/verify").mock(return_value=httpx.Response(200, json={
            "verified": True,
            "confidence": 0.95,
            "decision": "approved",
            "explanation": "Photo matches task requirements",
            "issues": [],
        }))
        result = await client.evidence.verify("task-1", "https://cdn.example.com/photo.jpg")
        assert result.verified is True
        assert result.confidence == 0.95
        assert result.decision == "approved"

    async def test_verify_with_issues(self, mock_router, client):
        mock_router.post("/evidence/verify").mock(return_value=httpx.Response(200, json={
            "verified": False,
            "confidence": 0.3,
            "decision": "rejected",
            "explanation": "Photo is blurry",
            "issues": ["Low resolution", "No GPS metadata"],
        }))
        result = await client.evidence.verify("task-1", "https://cdn.example.com/blurry.jpg")
        assert result.verified is False
        assert len(result.issues) == 2
