import json
import mimetypes
import os
import re
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

    try:
        key = _build_object_key(params)
        requested_content_type = params.get("contentType")
        content_type = _content_type(key, requested_content_type)
    except ValueError as err:
        return _json_response(400, {"error": str(err)}, origin)

    if mode == "post":
        post = s3.generate_presigned_post(
            Bucket=BUCKET,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                ["content-length-range", 1, MAX_UPLOAD_BYTES],
                {"Content-Type": content_type},
            ],
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
                "public_url": f"{PUBLIC_BASE_URL}/{key}" if PUBLIC_BASE_URL else None,
            },
            origin,
        )

    signed_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": BUCKET, "Key": key, "ContentType": content_type},
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
            "public_url": f"{PUBLIC_BASE_URL}/{key}" if PUBLIC_BASE_URL else None,
            "max_upload_mb": MAX_UPLOAD_MB,
        },
        origin,
    )
