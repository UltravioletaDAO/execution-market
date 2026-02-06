"""Evidence presigned URL Lambda — generates S3 presigned upload/download URLs.

Enhancements over v1:
- MIME type ↔ extension cross-validation (P1-EVID-003)
- Client SHA-256 checksum forwarded as S3 metadata (P1-EVID-003)
- Upload nonce for replay protection (P1-EVID-004)
- File size enforced via content-length-range condition (P1-EVID-003)
"""

import hashlib
import json
import mimetypes
import os
import re
import time
import uuid

import boto3

s3 = boto3.client("s3")

BUCKET = os.environ["EVIDENCE_BUCKET"]
PUBLIC_BASE_URL = os.environ.get("EVIDENCE_PUBLIC_BASE_URL", "").rstrip("/")
DEFAULT_EXPIRES_SECONDS = int(os.environ.get("PRESIGN_EXPIRES_SECONDS", "900"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
DEFAULT_ALLOWED_EXTENSIONS = "jpg,jpeg,png,webp,pdf,mp4,mov,heic,txt,json"
ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.environ.get("ALLOWED_EXTENSIONS", DEFAULT_ALLOWED_EXTENSIONS).split(",")
    if ext.strip()
}

# MIME type ↔ extension mapping for cross-validation
MIME_TO_EXTENSIONS = {
    "image/jpeg": {"jpg", "jpeg"},
    "image/png": {"png"},
    "image/webp": {"webp"},
    "image/heic": {"heic"},
    "video/mp4": {"mp4"},
    "video/quicktime": {"mov"},
    "application/pdf": {"pdf"},
    "text/plain": {"txt"},
    "application/json": {"json"},
}

EXTENSION_TO_MIMES = {}
for mime, exts in MIME_TO_EXTENSIONS.items():
    for ext in exts:
        EXTENSION_TO_MIMES.setdefault(ext, set()).add(mime)


def _origin(event):
    headers = event.get("headers") or {}
    return headers.get("origin") or headers.get("Origin") or "*"


def _json_response(status_code, body, origin):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Headers": "content-type,authorization,x-evidence-token",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Vary": "Origin",
        },
        "body": json.dumps(body),
    }


def _safe_slug(value, fallback):
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip()).strip("-")
    return (text[:80] or fallback)


def _safe_filename(filename):
    base = os.path.basename(str(filename or "")).strip()
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)
    if not base:
        return f"evidence-{uuid.uuid4().hex}.bin"
    return base[:160]


def _extension(filename):
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def _validate_mime_extension(content_type, ext):
    """Cross-validate MIME type against file extension."""
    if not ext or not content_type:
        return
    ct_lower = content_type.lower().split(";")[0].strip()
    # Check if the extension is known and the MIME type doesn't match
    valid_mimes = EXTENSION_TO_MIMES.get(ext)
    if valid_mimes and ct_lower not in valid_mimes:
        # Allow generic types as fallback
        if ct_lower not in ("application/octet-stream", "binary/octet-stream"):
            raise ValueError(
                f"Content-Type '{ct_lower}' does not match extension '.{ext}'. "
                f"Expected one of: {', '.join(sorted(valid_mimes))}"
            )


def _build_object_key(params):
    task_id = _safe_slug(params.get("taskId"), "task")
    submission_id = _safe_slug(params.get("submissionId"), "submission")
    actor_id = _safe_slug(params.get("actorId"), "anonymous")
    filename = _safe_filename(params.get("filename"))
    ext = _extension(filename)
    if ext and ALLOWED_EXTENSIONS and ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension .{ext} is not allowed")
    return f"tasks/{task_id}/submissions/{submission_id}/{actor_id}/{uuid.uuid4().hex}-{filename}"


def _safe_existing_key(value):
    key = str(value or "").strip().lstrip("/")
    if not key:
        raise ValueError("Missing required key parameter")
    if ".." in key:
        raise ValueError("Invalid key parameter")
    return key[:1024]


def _content_type(filename, requested):
    if requested:
        return requested
    guess, _ = mimetypes.guess_type(filename)
    return guess or "application/octet-stream"


def _generate_nonce():
    """Generate a unique upload nonce for replay protection."""
    raw = f"{uuid.uuid4().hex}-{time.time_ns()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _validate_checksum(checksum):
    """Validate SHA-256 checksum format if provided."""
    if not checksum:
        return None
    checksum = checksum.strip().lower()
    if not re.match(r"^[a-f0-9]{64}$", checksum):
        raise ValueError("Invalid SHA-256 checksum format (expected 64 hex chars)")
    return checksum


def handler(event, _context):
    origin = _origin(event)

    method = (event.get("requestContext") or {}).get("http", {}).get("method", "GET")
    if method == "OPTIONS":
        return _json_response(200, {"ok": True}, origin)

    params = event.get("queryStringParameters") or {}
    route_key = str(event.get("routeKey", ""))
    mode = str(params.get("mode", "put")).lower()
    expires = int(params.get("expires", DEFAULT_EXPIRES_SECONDS))
    expires = max(60, min(expires, 3600))

    # Download URL
    if route_key.endswith("/download-url"):
        try:
            key = _safe_existing_key(params.get("key"))
        except ValueError as err:
            return _json_response(400, {"error": str(err)}, origin)

        signed_url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expires,
        )
        return _json_response(
            200,
            {
                "mode": "download",
                "key": key,
                "download_url": signed_url,
                "public_url": f"{PUBLIC_BASE_URL}/{key}" if PUBLIC_BASE_URL else None,
                "expires_in": expires,
            },
            origin,
        )

    # Upload URL
    try:
        key = _build_object_key(params)
        requested_content_type = params.get("contentType")
        content_type = _content_type(key, requested_content_type)

        # P1-EVID-003: Cross-validate MIME ↔ extension
        ext = _extension(key)
        _validate_mime_extension(content_type, ext)

        # P1-EVID-003: Validate client-provided checksum
        client_checksum = _validate_checksum(params.get("checksum"))

    except ValueError as err:
        return _json_response(400, {"error": str(err)}, origin)

    # P1-EVID-004: Generate upload nonce for replay protection
    nonce = _generate_nonce()

    # S3 metadata to attach to the uploaded object
    s3_metadata = {
        "upload-nonce": nonce,
        "evidence-type": _safe_slug(params.get("evidenceType"), "unknown"),
        "task-id": _safe_slug(params.get("taskId"), "unknown"),
        "actor-id": _safe_slug(params.get("actorId"), "unknown"),
    }
    if client_checksum:
        s3_metadata["client-sha256"] = client_checksum

    if mode == "post":
        fields = {"Content-Type": content_type}
        conditions = [
            ["content-length-range", 1, MAX_UPLOAD_BYTES],
            {"Content-Type": content_type},
        ]
        # Add metadata fields and conditions
        for mk, mv in s3_metadata.items():
            meta_key = f"x-amz-meta-{mk}"
            fields[meta_key] = mv
            conditions.append({meta_key: mv})

        post = s3.generate_presigned_post(
            Bucket=BUCKET,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires,
        )
        return _json_response(
            200,
            {
                "mode": "post",
                "key": key,
                "upload_url": post["url"],
                "fields": post["fields"],
                "content_type": content_type,
                "max_upload_mb": MAX_UPLOAD_MB,
                "expires_in": expires,
                "nonce": nonce,
                "public_url": f"{PUBLIC_BASE_URL}/{key}" if PUBLIC_BASE_URL else None,
            },
            origin,
        )

    # PUT mode
    put_params = {
        "Bucket": BUCKET,
        "Key": key,
        "ContentType": content_type,
        "Metadata": s3_metadata,
    }

    signed_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params=put_params,
        ExpiresIn=expires,
    )
    return _json_response(
        200,
        {
            "mode": "put",
            "key": key,
            "upload_url": signed_url,
            "content_type": content_type,
            "expires_in": expires,
            "nonce": nonce,
            "metadata": s3_metadata,
            "public_url": f"{PUBLIC_BASE_URL}/{key}" if PUBLIC_BASE_URL else None,
            "max_upload_mb": MAX_UPLOAD_MB,
        },
        origin,
    )
