"""
Minimal A2A Test Server for Execution Market
Run with: python test_a2a_server.py

WARNING: Development/testing only. Do NOT deploy to production.
"""

import os
import sys

if os.environ.get("ENVIRONMENT") == "production":
    print("ERROR: test_a2a_server.py must not run in production. Exiting.")
    sys.exit(1)

sys.path.insert(0, ".")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from a2a.agent_card import router as a2a_router

app = FastAPI(title="Execution Market A2A Test Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(a2a_router)


@app.get("/health")
async def health():
    return {"status": "ok", "server": "test-a2a"}


@app.get("/")
async def root():
    return {
        "message": "Execution Market A2A Test Server",
        "endpoints": ["/.well-known/agent.json", "/v1/card", "/discovery/agents"],
    }


if __name__ == "__main__":
    import uvicorn

    print("Starting Execution Market A2A Test Server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
