#!/usr/bin/env python
"""
Rotate the xmtp-bot enterprise API key.

Generates a fresh ``em_enterprise_*`` key, inserts it into the Supabase
``api_keys`` table (hash + prefix only — the plaintext key is NEVER written to
disk or logged), and updates the ``EM_API_KEY`` field of the AWS Secrets
Manager secret ``em/xmtp`` while preserving the other fields
(XMTP_WALLET_KEY, XMTP_DB_ENCRYPTION_KEY).

The previous key(s) are left ACTIVE so the bot keeps working during the deploy
transition. Revoke them with ``--revoke-hash <hash>`` only AFTER the new key is
verified working post-deploy.

DB access goes through the Supabase Management API SQL endpoint (the direct
Postgres host is IPv6-only and does not resolve here). It authenticates with
the ``SUPABASE_TOKEN`` PAT and runs as ``postgres`` (bypasses RLS). A browser
User-Agent is required — Supabase's edge (Cloudflare) returns 1010 otherwise.

Context: INC-2026-04-04 — the bot's key leaked into WAF/ALB logs because it was
passed in the ``?api_key=`` query string. The bot now sends it in the WS auth
message body instead; this rotation invalidates the leaked key. See
docs/reports/aws-alarms-audit-2026-05-21/.

Usage:
    python scripts/rotate_bot_api_key.py                  # --check (read-only, default)
    python scripts/rotate_bot_api_key.py --rotate         # generate + insert + update secret
    python scripts/rotate_bot_api_key.py --revoke-hash H  # deactivate a key by its SHA256 hash

Reads SUPABASE_URL + SUPABASE_TOKEN from .env.local.
Requires AWS credentials (default profile) for Secrets Manager in us-east-2.
"""

import os
import sys
import json
import hashlib
import secrets as pysecrets
import argparse
import urllib.request
import urllib.error

import boto3

AGENT_ID = "xmtp-bot"
TIER = "enterprise"
KEY_NAME = "XMTP Bot - Task Notifications"
SECRET_ID = "em/xmtp"
REGION = "us-east-2"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _load_env() -> None:
    """Load .env.local from repo root without external deps."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root, ".env.local")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _project_ref() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    if not url:
        sys.exit("ERROR: SUPABASE_URL not set (.env.local)")
    return url.split("//", 1)[1].split(".", 1)[0]


def _run_sql(sql: str) -> list:
    """Execute SQL via the Supabase Management API (runs as postgres)."""
    token = os.environ.get("SUPABASE_TOKEN")
    if not token:
        sys.exit("ERROR: SUPABASE_TOKEN not set (.env.local)")
    url = f"https://api.supabase.com/v1/projects/{_project_ref()}/database/query"
    req = urllib.request.Request(
        url,
        data=json.dumps({"query": sql}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": _UA,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: Management API HTTP {e.code}: {e.read().decode()[:300]}")


def _sql_str(value: str) -> str:
    """Escape a string literal for inline SQL (Management API has no params)."""
    return "'" + value.replace("'", "''") + "'"


def check() -> None:
    """Read-only: list keys for the bot (metadata only, never the key)."""
    rows = _run_sql(
        "SELECT key_prefix, key_hash, is_active, created_at, last_used_at "
        f"FROM api_keys WHERE agent_id = {_sql_str(AGENT_ID)} ORDER BY created_at"
    )
    print(f"[CHECK] api_keys rows for agent_id={AGENT_ID}: {len(rows)}")
    for r in rows:
        flag = "ACTIVE" if r["is_active"] else "revoked"
        print(
            f"  - {flag:7s} prefix={r['key_prefix']} hash={r['key_hash'][:16]}... "
            f"last_used={r['last_used_at']}"
        )


def rotate() -> None:
    """Generate a new key, insert it, update Secrets Manager."""
    # Generate in memory — never written to disk or logged.
    new_key = f"em_{TIER}_{pysecrets.token_hex(16)}"  # em_enterprise_ + 32 hex
    key_hash = hashlib.sha256(new_key.encode()).hexdigest()
    key_prefix = new_key[:32]

    # Capture currently-active keys to revoke later (after verify).
    old = _run_sql(
        "SELECT key_hash, key_prefix FROM api_keys "
        f"WHERE agent_id = {_sql_str(AGENT_ID)} AND is_active = TRUE"
    )

    desc = "Rotated 2026-05-26 - INC-2026-04-04 header/User-Agent fix"
    result = _run_sql(
        "INSERT INTO api_keys "
        "(key_hash, key_prefix, agent_id, tier, is_active, name, description) VALUES ("
        f"{_sql_str(key_hash)}, {_sql_str(key_prefix)}, {_sql_str(AGENT_ID)}, "
        f"{_sql_str(TIER)}, TRUE, {_sql_str(KEY_NAME)}, {_sql_str(desc)}) RETURNING id"
    )
    new_id = result[0]["id"]

    # Update Secrets Manager — preserve the other fields.
    sm = boto3.client("secretsmanager", region_name=REGION)
    current = json.loads(sm.get_secret_value(SecretId=SECRET_ID)["SecretString"])
    current["EM_API_KEY"] = new_key
    sm.put_secret_value(SecretId=SECRET_ID, SecretString=json.dumps(current))

    # Print ONLY safe metadata — never the key itself.
    print(f"[OK] New key inserted: id={new_id} prefix={key_prefix}")
    print(f"[OK] new key_hash={key_hash}")
    print(
        f"[OK] Secrets Manager {SECRET_ID}.EM_API_KEY updated (other fields preserved)"
    )
    if old:
        print("[NEXT] After verifying the bot reconnects, revoke the old key(s):")
        for row in old:
            print(
                f"       python scripts/rotate_bot_api_key.py --revoke-hash {row['key_hash']}"
            )
            print(f"         (old prefix={row['key_prefix']})")
    else:
        print("[INFO] No previously-active keys found for this agent.")


def revoke(old_hash: str) -> None:
    """Deactivate a key by its hash."""
    result = _run_sql(
        f"UPDATE api_keys SET is_active = FALSE WHERE key_hash = {_sql_str(old_hash)} "
        "RETURNING id, key_prefix"
    )
    if result:
        print(f"[OK] Revoked key id={result[0]['id']} prefix={result[0]['key_prefix']}")
        print(
            "[NEXT] Clear the server API-key cache (5-min TTL) or wait for it to expire."
        )
    else:
        print(f"[WARN] No key found with hash {old_hash[:16]}...")


if __name__ == "__main__":
    _load_env()
    parser = argparse.ArgumentParser(description="Rotate the xmtp-bot API key")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--rotate", action="store_true", help="generate + insert + update secret"
    )
    group.add_argument("--revoke-hash", help="deactivate an old key by its SHA256 hash")
    args = parser.parse_args()

    if args.rotate:
        rotate()
    elif args.revoke_hash:
        revoke(args.revoke_hash)
    else:
        check()
