"""Phase 1.6 — Minimal upstream backend that pay.sh proxies to.

Exists only to validate the proxy flow end-to-end with a real HTTP response.
Phase 2 swaps this out for mcp_server/ when pay.sh deploys in front of it.

Run: uvicorn services.em_stub.main:app --host 127.0.0.1 --port 8090
"""
from __future__ import annotations

from fastapi import FastAPI, Request

app = FastAPI(title="em-stub", version="0.1.0")


@app.get("/hello")
async def hello(request: Request) -> dict[str, object]:
    return {
        "ok": True,
        "msg": "execution market",
        "payshell_channel_id": request.headers.get("x-payshell-channel-id"),
        "payshell_cumulative_usdc": request.headers.get("x-payshell-cumulative-usdc"),
        "payshell_payer": request.headers.get("x-payshell-payer"),
    }


@app.get("/_health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
