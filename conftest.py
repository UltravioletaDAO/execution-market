"""
Root conftest.py — project-wide pytest configuration.

Sets TESTING env var and excludes integration test directories
that require optional dependencies (crewai, langchain).
"""
import os

os.environ.setdefault("TESTING", "1")

# Exclude integration dirs that need optional deps (crewai_tools, langchain)
collect_ignore = [
    "integrations/crewai",
    "integrations/langchain",
    "integrations",
]
