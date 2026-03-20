"""
Integration validation scripts — NOT pytest test modules.

These are standalone import/syntax validators that happen to have test_ prefix.
Mark the entire directory as not collected by pytest.
"""
import os

os.environ.setdefault("TESTING", "1")

collect_ignore_glob = ["test_*.py"]
