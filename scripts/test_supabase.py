#!/usr/bin/env python3
"""
Test Supabase connection for Execution Market
Run: python scripts/test_supabase.py
"""
import os
import sys
from pathlib import Path

# Load environment variables
env_file = Path(__file__).parent.parent / ".env.local"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

# Check for required environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("Missing SUPABASE_URL or SUPABASE_ANON_KEY")
    sys.exit(1)

print(f"Supabase URL: {SUPABASE_URL}")
print(f"Anon Key: {SUPABASE_ANON_KEY[:20]}...")

# Test with supabase-py if available
try:
    from supabase import create_client

    print("\nTesting Supabase client connection...")
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    # Try to query tasks table
    print("Attempting to query tasks table...")
    response = client.table("tasks").select("*").limit(1).execute()
    print(f"Query successful! Found {len(response.data)} tasks")

except ImportError:
    print("\nsupabase-py not installed. Install with: pip install supabase")
    print("Skipping client test...")

# Test direct PostgreSQL connection if psycopg2 is available
try:
    import psycopg2

    if DATABASE_URL:
        print("\nTesting direct PostgreSQL connection...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"PostgreSQL version: {version[0][:50]}...")

        # Check if tables exist
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()

        if tables:
            print(f"\nFound {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\nNo tables found. Run migrations first:")
            print("  1. Go to Supabase SQL Editor")
            print("  2. Run supabase/migrations/001_initial_schema.sql")
            print("  3. Run supabase/migrations/002_storage_bucket.sql")

        cur.close()
        conn.close()
        print("\nConnection test successful!")

except ImportError:
    print("\npsycopg2 not installed. Install with: pip install psycopg2-binary")
    print("Skipping direct PostgreSQL test...")
except Exception as e:
    print(f"\nPostgreSQL connection error: {e}")

print("\nDone!")
