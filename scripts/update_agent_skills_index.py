#!/usr/bin/env python3
"""Regenerate sha256 digests in dashboard/public/.well-known/agent-skills/index.json.

Run after editing skill.md, skill-lite.md, or workflows.md.
Fails with exit 1 if the file on disk doesn't match the digest in the index
(useful as a pre-commit check).

Usage:
    python scripts/update_agent_skills_index.py           # rewrite digests in place
    python scripts/update_agent_skills_index.py --check   # exit 1 if out of sync
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "dashboard" / "public" / ".well-known" / "agent-skills" / "index.json"
PUBLIC_DIR = REPO_ROOT / "dashboard" / "public"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def url_to_local_path(url: str) -> Path:
    if not url.startswith("https://execution.market/"):
        raise ValueError(f"Unsupported url (expected https://execution.market/…): {url}")
    rel = url.removeprefix("https://execution.market/")
    return PUBLIC_DIR / rel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit 1 if out of sync (no write)")
    args = parser.parse_args()

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    out_of_sync: list[str] = []

    for skill in index.get("skills", []):
        local = url_to_local_path(skill["url"])
        if not local.exists():
            print(f"[FAIL] referenced file missing: {local}")
            return 1
        actual = sha256_file(local)
        recorded = skill.get("sha256")
        if actual != recorded:
            out_of_sync.append(f"{skill['name']}: index={recorded} disk={actual}")
            skill["sha256"] = actual

    if args.check:
        if out_of_sync:
            print("[FAIL] agent-skills index out of sync:")
            for line in out_of_sync:
                print(f"  {line}")
            print("Run: python scripts/update_agent_skills_index.py")
            return 1
        print("[OK] agent-skills index is in sync")
        return 0

    if out_of_sync:
        INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] updated {len(out_of_sync)} digest(s) in {INDEX_PATH.relative_to(REPO_ROOT)}")
        for line in out_of_sync:
            print(f"  {line}")
    else:
        print("[OK] all digests already match — no changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
