"""
Root conftest.py — sets TESTING env var before any test collection.

This is critical because some modules (e.g., integrations/x402/sdk_client.py)
check for EM_TREASURY_ADDRESS at import time and raise RuntimeError if not set.
The TESTING=1 flag bypasses this check.
"""
import os

# Must be set before ANY test module imports happen
os.environ.setdefault("TESTING", "1")
