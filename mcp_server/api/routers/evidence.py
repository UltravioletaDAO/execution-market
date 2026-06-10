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
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..auth import (
    verify_worker_auth,
    WorkerAuth,
    _enforce_worker_identity,
    verify_agent_auth_read,
    AgentAuth,
    is_worker_auth_required,
)
from ..admin import verify_admin_key
from ._helpers import logger

router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence"])


def _agent_matches_task(agent_auth: Optional["AgentAuth"], task: dict) -> bool:
    """True iff agent_auth is a real (non-anonymous) ERC-8128 principal that owns the task.

    A task's publishing principal is stored in tasks.agent_id (wallet address OR
    numeric ERC-8004 id). We only trust a *signed* identity here — the anonymous
    Agent #2106 fallback (auth_method="anonymous") must NOT match anything.
    """
    if agent_auth is None or agent_auth.auth_method != "erc8128":
        return False
    task_agent = str(task.get("agent_id") or "").lower()
    if not task_agent:
        return False
    wallet = (agent_auth.wallet_address or "").lower()
    erc_id = str(agent_auth.erc8004_agent_id or "")
    if wallet and wallet == task_agent:
        return True
    if erc_id and erc_id == task_agent:
        return True
    return False


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
    # Phase 0 GR-0.4: short-lived JWT the client sends to the Lambda
    # presign authorizer (Track D1). Not used directly by the caller — it
    # is forwarded in the Authorization header.
    authorizer_jwt: Optional[str] = None


class PresignDownloadResponse(BaseModel):
    download_url: str
    key: str
    public_url: Optional[str] = None
    expires_in: int
    authorizer_jwt: Optional[str] = None


@router.get(
    "/presign-upload",
    response_model=PresignUploadResponse,
    responses={
        400: {"description": "Invalid parameters"},
        503: {"description": "Evidence storage not configured"},
    },
)
async def presign_upload(
    raw_request: Request,
    task_id: str = Query(..., description="Task UUID"),
    executor_id: str = Query(..., description="Executor UUID"),
    filename: str = Query(..., description="Original filename"),
    evidence_type: str = Query(
        "photo", description="Evidence type (photo, screenshot, etc)"
    ),
    content_type: str = Query("image/jpeg", description="MIME type"),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> PresignUploadResponse:
    """Generate a presigned S3 PUT URL for evidence upload."""
    if not is_worker_auth_required():
        # ---- LEGACY (EM_REQUIRE_WORKER_AUTH off) — byte-identical to main ----
        # Enforce: caller must be the executor they claim to be
        executor_id = _enforce_worker_identity(
            worker_auth, executor_id, raw_request.url.path
        )

        # Verify caller is the task's assigned executor
        try:
            import supabase_client as db

            task = await db.get_task(task_id)
            if task and task.get("executor_id") and task["executor_id"] != executor_id:
                logger.warning(
                    "SECURITY_AUDIT action=evidence.upload_denied "
                    "task=%s claimed_executor=%s actual_executor=%s",
                    task_id,
                    executor_id[:8],
                    str(task["executor_id"])[:8],
                )
                raise HTTPException(
                    status_code=403,
                    detail="You are not the assigned executor for this task",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Could not verify task executor for presign-upload: %s", e)
    else:
        # ---- FIX-P1-02 (enforcement on) — require an authenticated principal ----
        # (worker JWT for the executor, OR the publishing agent, OR admin) before
        # issuing an upload URL. Blocks unauthenticated upload-URL minting into a
        # victim's submission path.
        executor_id = _enforce_worker_identity(
            worker_auth, executor_id, raw_request.url.path
        )

        try:
            import supabase_client as db

            task = await db.get_task(task_id)
        except Exception as e:
            logger.error("evidence.upload: task lookup failed (deny): %s", e)
            raise HTTPException(503, "Could not verify upload access")
        if not task:
            raise HTTPException(404, "Task not found")

        # Probe agent + admin principals (defensive, non-fatal on bad creds).
        is_admin = False
        try:
            await verify_admin_key(
                authorization=raw_request.headers.get("authorization"),
                x_admin_key=raw_request.headers.get("x-admin-key"),
                x_admin_actor=raw_request.headers.get("x-admin-actor"),
            )
            is_admin = True
        except HTTPException:
            is_admin = False
        agent_auth: Optional[AgentAuth] = None
        try:
            agent_auth = await verify_agent_auth_read(raw_request)
        except HTTPException:
            agent_auth = None

        is_assigned_executor = bool(
            worker_auth
            and task.get("executor_id")
            and task["executor_id"] == worker_auth.executor_id
        )
        is_owner_agent = _agent_matches_task(agent_auth, task)

        if not (is_admin or is_assigned_executor or is_owner_agent):
            logger.warning(
                "SECURITY_AUDIT action=evidence.upload_denied task=%s claimed_executor=%s",
                task_id,
                str(executor_id)[:8],
            )
            raise HTTPException(403, "Not authorized to upload evidence for this task")

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
    # NOTE: Do NOT include Metadata in presign Params — any x-amz-meta-*
    # headers become part of the signature, and the mobile client would need
    # to send identical headers or S3 returns 403 SignatureDoesNotMatch.
    # Metadata (task_id, executor_id, nonce) is already tracked server-side.
    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": EVIDENCE_BUCKET,
            "Key": key,
            "ContentType": content_type,
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

    # Phase 0 GR-0.4: mint a short-lived JWT bound to this (task, executor).
    # The client forwards it to the Lambda presign authorizer owned by
    # Track D1. If the secret is not configured (local dev), we return
    # None and log at debug — the Lambda is optional until D1 ships.
    authorizer_jwt: Optional[str] = None
    try:
        from integrations.evidence.jwt_helper import mint_evidence_jwt

        # submission_id is pre-allocated from the nonce so the Lambda can
        # bind the upload to the eventual submission row.
        authorizer_jwt = mint_evidence_jwt(
            task_id=task_id,
            submission_id=nonce,
            actor_id=executor_id,
        )
    except RuntimeError as e:
        # EM_EVIDENCE_JWT_SECRET not set — OK in local dev.
        logger.debug("[Evidence] skipping authorizer JWT: %s", e)
    except Exception as e:
        # Don't fail the presign on JWT errors — log loudly and continue.
        logger.error("[Evidence] failed to mint authorizer JWT: %s", e)

    return PresignUploadResponse(
        upload_url=upload_url,
        key=key,
        public_url=public_url,
        content_type=content_type,
        expires_in=PRESIGN_EXPIRES_UPLOAD,
        nonce=nonce,
        authorizer_jwt=authorizer_jwt,
    )


@router.get(
    "/presign-download",
    response_model=PresignDownloadResponse,
    responses={
        400: {"description": "Invalid parameters"},
        401: {"description": "Authentication required"},
        403: {"description": "Not authorized for this evidence"},
        503: {"description": "Evidence storage not configured"},
    },
)
async def presign_download(
    raw_request: Request,
    key: str = Query(..., description="S3 object key"),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> PresignDownloadResponse:
    """Generate a presigned S3 GET URL for evidence download.

    Access control: assigned executor, task's publishing agent, or admin.
    When EM_REQUIRE_WORKER_AUTH is on, the check is DENY BY DEFAULT (FIX-P1-02).
    When off, behaviour is byte-identical to the legacy soft-auth path.
    """
    if not is_worker_auth_required():
        # ---- LEGACY (EM_REQUIRE_WORKER_AUTH off) — byte-identical to main ----
        # Extract task_id from key pattern: tasks/{task_id}/submissions/...
        _key_task_id = None
        _key_parts = key.strip().lstrip("/").split("/")
        if len(_key_parts) >= 2 and _key_parts[0] == "tasks":
            _key_task_id = _key_parts[1]

        if _key_task_id and worker_auth:
            try:
                import supabase_client as db

                task = await db.get_task(_key_task_id)
                if task:
                    is_executor = task.get("executor_id") == worker_auth.executor_id
                    if not is_executor:
                        logger.warning(
                            "SECURITY_AUDIT action=evidence.download_denied "
                            "task=%s executor=%s",
                            _key_task_id,
                            worker_auth.executor_id[:8],
                        )
                        raise HTTPException(
                            status_code=403,
                            detail="You do not have access to this evidence",
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("Could not verify evidence download access: %s", e)

        if not EVIDENCE_BUCKET:
            raise HTTPException(503, "Evidence storage not configured")

        # Sanitize key
        key = key.strip().lstrip("/")
        if not key or ".." in key:
            raise HTTPException(400, "Invalid key")

        actor_id = (
            worker_auth.executor_id if worker_auth else (_key_task_id or "unknown")
        )
        task_id_for_jwt = _key_task_id or "unknown"
    else:
        # ---- FIX-P1-02 (enforcement on) — DENY BY DEFAULT ----
        if not EVIDENCE_BUCKET:
            raise HTTPException(503, "Evidence storage not configured")

        # Sanitize + parse task_id from the key (fail closed on bad shape).
        key = key.strip().lstrip("/")
        if not key or ".." in key:
            raise HTTPException(400, "Invalid key")
        parts = key.split("/")
        if len(parts) < 2 or parts[0] != "tasks" or not parts[1]:
            logger.warning(
                "SECURITY_AUDIT action=evidence.download_denied reason=bad_key_shape"
            )
            raise HTTPException(403, "You do not have access to this evidence")
        task_id_for_jwt = parts[1]

        # Probe each principal source defensively (never sign on probe errors).
        is_admin = False
        try:
            await verify_admin_key(
                authorization=raw_request.headers.get("authorization"),
                x_admin_key=raw_request.headers.get("x-admin-key"),
                x_admin_actor=raw_request.headers.get("x-admin-actor"),
            )
            is_admin = True
        except HTTPException:
            is_admin = False

        agent_auth: Optional[AgentAuth] = None
        try:
            agent_auth = await verify_agent_auth_read(raw_request)
        except HTTPException:
            agent_auth = None

        has_principal = (
            is_admin
            or worker_auth is not None
            or (agent_auth is not None and agent_auth.auth_method == "erc8128")
        )
        if not has_principal:
            logger.warning(
                "SECURITY_AUDIT action=evidence.download_unauth task=%s",
                task_id_for_jwt,
            )
            raise HTTPException(
                status_code=401,
                detail="Authentication required to download evidence",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if is_admin:
            actor_id = "admin"
        else:
            try:
                import supabase_client as db

                task = await db.get_task(task_id_for_jwt)
            except Exception as e:
                logger.error(
                    "evidence.download: task lookup failed (deny) task=%s err=%s",
                    task_id_for_jwt,
                    e,
                )
                raise HTTPException(503, "Could not verify evidence access")
            if not task:
                raise HTTPException(403, "You do not have access to this evidence")

            is_executor = bool(
                worker_auth and task.get("executor_id") == worker_auth.executor_id
            )
            is_owner_agent = _agent_matches_task(agent_auth, task)
            actor_id = (
                worker_auth.executor_id
                if is_executor
                else (agent_auth.agent_id if is_owner_agent else "unknown")
            )
            if not (is_executor or is_owner_agent):
                logger.warning(
                    "SECURITY_AUDIT action=evidence.download_denied task=%s actor=%s",
                    task_id_for_jwt,
                    actor_id[:8],
                )
                raise HTTPException(403, "You do not have access to this evidence")

    s3 = _get_s3()
    download_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": EVIDENCE_BUCKET, "Key": key},
        ExpiresIn=PRESIGN_EXPIRES_DOWNLOAD,
    )

    public_url = (
        f"{EVIDENCE_PUBLIC_BASE_URL}/{key}" if EVIDENCE_PUBLIC_BASE_URL else None
    )

    # Phase 0 GR-0.4: mint authorizer JWT for the Lambda (Track D1).
    authorizer_jwt: Optional[str] = None
    try:
        from integrations.evidence.jwt_helper import mint_evidence_jwt

        authorizer_jwt = mint_evidence_jwt(
            task_id=task_id_for_jwt,
            submission_id=key,
            actor_id=actor_id,
        )
    except RuntimeError as e:
        logger.debug("[Evidence] skipping authorizer JWT (download): %s", e)
    except Exception as e:
        logger.error("[Evidence] failed to mint authorizer JWT (download): %s", e)

    return PresignDownloadResponse(
        download_url=download_url,
        key=key,
        public_url=public_url,
        expires_in=PRESIGN_EXPIRES_DOWNLOAD,
        authorizer_jwt=authorizer_jwt,
    )
