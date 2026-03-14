"""
Evidence presigned URL endpoints.

Generates S3 presigned URLs for evidence upload (PUT) and download (GET).
The ECS task role has s3:PutObject + s3:GetObject on the evidence bucket.
"""

import hashlib
import os
import re
import time
import uuid
from typing import Optional

import boto3
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ._helpers import logger

router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence"])

# Config from environment (set by ECS task definition / evidence.tf)
EVIDENCE_BUCKET = os.environ.get("EVIDENCE_BUCKET", "")
EVIDENCE_PUBLIC_BASE_URL = os.environ.get("EVIDENCE_PUBLIC_BASE_URL", "").rstrip("/")
PRESIGN_EXPIRES_UPLOAD = int(os.environ.get("PRESIGN_EXPIRES_SECONDS", "900"))
PRESIGN_EXPIRES_DOWNLOAD = 3600  # 1 hour for read access
MAX_UPLOAD_MB = int(os.environ.get("EVIDENCE_MAX_UPLOAD_MB", "25"))

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "pdf",
    "mp4",
    "mov",
    "heic",
    "txt",
    "json",
}

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
        )
    return _s3_client


def _safe_slug(value: str, fallback: str = "unknown") -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip()).strip("-")
    return text[:80] or fallback


def _safe_filename(filename: str) -> str:
    base = os.path.basename(str(filename or "")).strip()
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)
    if not base:
        return f"evidence-{uuid.uuid4().hex[:8]}.bin"
    return base[:160]


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


class PresignUploadResponse(BaseModel):
    upload_url: str
    key: str
    public_url: Optional[str] = None
    content_type: str
    expires_in: int
    nonce: str


class PresignDownloadResponse(BaseModel):
    download_url: str
    key: str
    public_url: Optional[str] = None
    expires_in: int


@router.get(
    "/presign-upload",
    response_model=PresignUploadResponse,
    responses={
        400: {"description": "Invalid parameters"},
        503: {"description": "Evidence storage not configured"},
    },
)
async def presign_upload(
    task_id: str = Query(..., description="Task UUID"),
    executor_id: str = Query(..., description="Executor UUID"),
    filename: str = Query(..., description="Original filename"),
    evidence_type: str = Query(
        "photo", description="Evidence type (photo, screenshot, etc)"
    ),
    content_type: str = Query("image/jpeg", description="MIME type"),
) -> PresignUploadResponse:
    """Generate a presigned S3 PUT URL for evidence upload."""
    if not EVIDENCE_BUCKET:
        raise HTTPException(503, "Evidence storage not configured")

    safe_filename = _safe_filename(filename)
    ext = _extension(safe_filename)
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File extension .{ext} not allowed")

    # Build S3 key: tasks/{task_id}/submissions/{executor_id}/{unique}-{filename}
    unique = uuid.uuid4().hex[:12]
    key = f"tasks/{_safe_slug(task_id)}/submissions/{_safe_slug(executor_id)}/{unique}-{safe_filename}"

    # Nonce for replay protection
    nonce = hashlib.sha256(f"{uuid.uuid4().hex}-{time.time_ns()}".encode()).hexdigest()[
        :32
    ]

    s3 = _get_s3()
    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": EVIDENCE_BUCKET,
            "Key": key,
            "ContentType": content_type,
            "Metadata": {
                "upload-nonce": nonce,
                "evidence-type": _safe_slug(evidence_type),
                "task-id": _safe_slug(task_id),
                "executor-id": _safe_slug(executor_id),
            },
        },
        ExpiresIn=PRESIGN_EXPIRES_UPLOAD,
    )

    public_url = (
        f"{EVIDENCE_PUBLIC_BASE_URL}/{key}" if EVIDENCE_PUBLIC_BASE_URL else None
    )

    logger.info(
        "[Evidence] Presigned upload URL generated",
        extra={
            "task_id": task_id,
            "key": key,
            "content_type": content_type,
        },
    )

    return PresignUploadResponse(
        upload_url=upload_url,
        key=key,
        public_url=public_url,
        content_type=content_type,
        expires_in=PRESIGN_EXPIRES_UPLOAD,
        nonce=nonce,
    )


@router.get(
    "/presign-download",
    response_model=PresignDownloadResponse,
    responses={
        400: {"description": "Invalid parameters"},
        503: {"description": "Evidence storage not configured"},
    },
)
async def presign_download(
    key: str = Query(..., description="S3 object key"),
) -> PresignDownloadResponse:
    """Generate a presigned S3 GET URL for evidence download."""
    if not EVIDENCE_BUCKET:
        raise HTTPException(503, "Evidence storage not configured")

    # Sanitize key
    key = key.strip().lstrip("/")
    if not key or ".." in key:
        raise HTTPException(400, "Invalid key")

    s3 = _get_s3()
    download_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": EVIDENCE_BUCKET, "Key": key},
        ExpiresIn=PRESIGN_EXPIRES_DOWNLOAD,
    )

    public_url = (
        f"{EVIDENCE_PUBLIC_BASE_URL}/{key}" if EVIDENCE_PUBLIC_BASE_URL else None
    )

    return PresignDownloadResponse(
        download_url=download_url,
        key=key,
        public_url=public_url,
        expires_in=PRESIGN_EXPIRES_DOWNLOAD,
    )
