"""Apply migration 100 (show_in_showcase) via Supabase Management API.

Idempotent: ALTER TABLE ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")

TOKEN = os.environ.get("SUPABASE_TOKEN") or os.environ.get("SUPABASE_ACCESS_TOKEN")
PROJECT_REF = "puyhpytmtkyevnxffksl"

if not TOKEN:
    raise SystemExit("ERROR: SUPABASE_TOKEN missing")

sql = (ROOT / "supabase" / "migrations" / "100_showcase_opt_out.sql").read_text()

url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

r = httpx.post(url, json={"query": sql}, headers=headers, timeout=30.0)
print(f"Migration POST status: {r.status_code}")
if r.status_code >= 400:
    print(f"  body: {r.text[:800]}")
    raise SystemExit(1)
print(f"  body: {r.text[:400]}")

verify_sql = """
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name='submissions' AND column_name='show_in_showcase'
"""
r = httpx.post(url, json={"query": verify_sql}, headers=headers, timeout=30.0)
print(f"Verify column status: {r.status_code}")
print(f"  result: {r.text}")

verify_idx = """
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename='submissions' AND indexname='idx_submissions_showcase_feed'
"""
r = httpx.post(url, json={"query": verify_idx}, headers=headers, timeout=30.0)
print(f"Verify index status: {r.status_code}")
print(f"  result: {r.text}")
