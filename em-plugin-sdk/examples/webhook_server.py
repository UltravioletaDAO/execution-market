"""FastAPI webhook receiver with HMAC signature verification."""

from fastapi import FastAPI, Request, HTTPException
from em_plugin_sdk.resources.webhooks import WebhooksResource

app = FastAPI()
WEBHOOK_SECRET = "whsec_your_secret_here"


@app.post("/em-webhook")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-EM-Signature", "")
    timestamp = request.headers.get("X-EM-Timestamp", "")

    if not WebhooksResource.verify_signature(body, signature, timestamp, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    import json
    event = json.loads(body)
    event_type = event.get("event", "unknown")

    if event_type == "task.completed":
        task_id = event["data"]["task_id"]
        print(f"Task {task_id} completed!")

    elif event_type == "submission.received":
        sub_id = event["data"]["submission_id"]
        print(f"New submission {sub_id}")

    elif event_type == "payment.released":
        tx = event["data"].get("tx_hash", "")
        print(f"Payment released: {tx}")

    return {"ok": True}


# Run: uvicorn examples.webhook_server:app --port 8080
