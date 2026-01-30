# api.py - Entry point for uvicorn
# Re-exports the FastAPI app from main.py

from main import app

__all__ = ["app"]
