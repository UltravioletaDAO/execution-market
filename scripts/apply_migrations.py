#!/usr/bin/env python3
"""Apply pending database migrations for A2A/H2A integration."""

import psycopg2
import os
import json
import subprocess
import sys

def get_db_password():
    """Get DB password from AWS Secrets Manager."""
    result = subprocess.run(
        ["aws", "secretsmanager", "get-secret-value",
         "--secret-id", "em/supabase-db",
         "--region", "us-east-2",
         "--query", "SecretString",
         "--output", "text"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)["DB_PASSWORD"]

def get_connection():
    """Connect to Supabase via session mode pooler."""
    db_host = os.environ.get("SUPABASE_DB_HOST", "localhost")
    db_user = os.environ.get("SUPABASE_DB_USER", "postgres")
    return psycopg2.connect(
        host=db_host,
        port=int(os.environ.get("SUPABASE_DB_PORT", "5432")),
        dbname=os.environ.get("SUPABASE_DB_NAME", "postgres"),
        user=db_user,
        password=get_db_password(),
        connect_timeout=15,
        sslmode='require'
    )

def apply_migration_031(conn):
    """Migration 031: Agent Executor Support."""
    print("\n=== Applying Migration 031: Agent Executor Support ===")
    cur = conn.cursor()
    
    # Add executor columns
    statements = [
        """ALTER TABLE executors
           ADD COLUMN IF NOT EXISTS executor_type VARCHAR(10) DEFAULT 'human'""",
        """ALTER TABLE executors
           ADD COLUMN IF NOT EXISTS agent_card_url TEXT""",
        """ALTER TABLE executors
           ADD COLUMN IF NOT EXISTS mcp_endpoint_url TEXT""",
        """ALTER TABLE executors
           ADD COLUMN IF NOT EXISTS capabilities TEXT[]""",
        """ALTER TABLE executors
           ADD COLUMN IF NOT EXISTS a2a_protocol_version VARCHAR(10)""",
        
        # Task columns
        """ALTER TABLE tasks
           ADD COLUMN IF NOT EXISTS target_executor_type VARCHAR(10) DEFAULT 'any'""",
        """ALTER TABLE tasks
           ADD COLUMN IF NOT EXISTS verification_mode VARCHAR(20) DEFAULT 'manual'""",
        """ALTER TABLE tasks
           ADD COLUMN IF NOT EXISTS verification_criteria JSONB""",
        """ALTER TABLE tasks
           ADD COLUMN IF NOT EXISTS required_capabilities TEXT[]""",
        
        # Indexes
        """CREATE INDEX IF NOT EXISTS idx_tasks_target_executor 
           ON tasks(target_executor_type) WHERE status = 'published'""",
        """CREATE INDEX IF NOT EXISTS idx_executors_type 
           ON executors(executor_type)""",
        """CREATE INDEX IF NOT EXISTS idx_executors_capabilities 
           ON executors USING GIN(capabilities) WHERE executor_type = 'agent'""",
        """CREATE INDEX IF NOT EXISTS idx_tasks_required_capabilities 
           ON tasks USING GIN(required_capabilities) WHERE target_executor_type IN ('agent', 'any')""",
        
        # API keys columns
        """ALTER TABLE api_keys 
           ADD COLUMN IF NOT EXISTS key_type VARCHAR(20) DEFAULT 'publisher'""",
        """ALTER TABLE api_keys 
           ADD COLUMN IF NOT EXISTS executor_id UUID REFERENCES executors(id)""",
    ]
    
    for stmt in statements:
        try:
            cur.execute(stmt)
            conn.commit()
            print(f"  ✅ {stmt.strip()[:80]}...")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  {stmt.strip()[:60]}... → {e}")
    
    # Add enum values (each needs its own transaction)
    enum_values = [
        'data_processing', 'api_integration', 'content_generation',
        'code_execution', 'research', 'multi_step_workflow'
    ]
    for val in enum_values:
        try:
            cur.execute(f"ALTER TYPE task_category ADD VALUE IF NOT EXISTS '{val}'")
            conn.commit()
            print(f"  ✅ Added enum value: {val}")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  Enum {val} → {e}")
    
    # Add CHECK constraints separately (might conflict with existing)
    checks = [
        ("executors", "executor_type", "executor_type IN ('human', 'agent')"),
        ("tasks", "target_executor_type", "target_executor_type IN ('human', 'agent', 'any')"),
        ("tasks", "verification_mode", "verification_mode IN ('manual', 'auto', 'oracle')"),
        ("api_keys", "key_type", "key_type IN ('publisher', 'executor', 'admin')"),
    ]
    for table, col, check_expr in checks:
        constraint_name = f"chk_{table}_{col}"
        try:
            cur.execute(f"""
                DO $$ BEGIN
                    ALTER TABLE {table} ADD CONSTRAINT {constraint_name} CHECK ({check_expr});
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$
            """)
            conn.commit()
            print(f"  ✅ CHECK constraint on {table}.{col}")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  CHECK {table}.{col} → {e}")

def apply_migration_033_h2a(conn):
    """Migration 033: H2A Marketplace columns."""
    print("\n=== Applying Migration 033: H2A Marketplace ===")
    cur = conn.cursor()
    
    statements = [
        # H2A task columns
        """ALTER TABLE tasks
           ADD COLUMN IF NOT EXISTS publisher_type VARCHAR(10) DEFAULT 'agent'""",
        """ALTER TABLE tasks
           ADD COLUMN IF NOT EXISTS human_wallet TEXT""",
        """ALTER TABLE tasks
           ADD COLUMN IF NOT EXISTS human_user_id TEXT""",
        
        # Indexes for H2A queries
        """CREATE INDEX IF NOT EXISTS idx_tasks_publisher_type 
           ON tasks(publisher_type) WHERE publisher_type = 'human'""",
        """CREATE INDEX IF NOT EXISTS idx_tasks_human_wallet 
           ON tasks(human_wallet) WHERE human_wallet IS NOT NULL""",
    ]
    
    for stmt in statements:
        try:
            cur.execute(stmt)
            conn.commit()
            print(f"  ✅ {stmt.strip()[:80]}...")
        except Exception as e:
            conn.rollback()
            print(f"  ⚠️  {stmt.strip()[:60]}... → {e}")
    
    # Add CHECK constraint for publisher_type
    try:
        cur.execute("""
            DO $$ BEGIN
                ALTER TABLE tasks ADD CONSTRAINT chk_tasks_publisher_type 
                CHECK (publisher_type IN ('agent', 'human'));
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        conn.commit()
        print("  ✅ CHECK constraint on tasks.publisher_type")
    except Exception as e:
        conn.rollback()
        print(f"  ⚠️  CHECK publisher_type → {e}")

def add_h2a_config(conn):
    """Add H2A feature flags to platform_config."""
    print("\n=== Adding H2A Configuration ===")
    cur = conn.cursor()
    
    configs = [
        ("feature.h2a_enabled", "true", "H2A marketplace enabled"),
        ("feature.h2a_min_bounty", "0.50", "Minimum H2A bounty in USD"),
        ("feature.h2a_max_bounty", "500.00", "Maximum H2A bounty in USD"),
    ]
    
    for key, value, desc in configs:
        try:
            cur.execute("""
                INSERT INTO platform_config (key, value, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, value, desc))
            conn.commit()
            print(f"  ✅ {key} = {value}")
        except Exception as e:
            conn.rollback()
            # Try without description if column doesn't exist
            try:
                cur.execute("""
                    INSERT INTO platform_config (key, value)
                    VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, (key, value))
                conn.commit()
                print(f"  ✅ {key} = {value} (no desc)")
            except Exception as e2:
                conn.rollback()
                print(f"  ⚠️  {key} → {e2}")

def verify_schema(conn):
    """Verify all expected columns exist."""
    print("\n=== Verifying Schema ===")
    cur = conn.cursor()
    
    # Check tasks columns
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='tasks' 
        AND column_name IN ('publisher_type','human_wallet','human_user_id',
                            'target_executor_type','verification_mode',
                            'required_capabilities','verification_criteria')
    """)
    tasks_cols = [r[0] for r in cur.fetchall()]
    print(f"  Tasks H2A columns: {tasks_cols}")
    
    # Check executors columns
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='executors' 
        AND column_name IN ('executor_type','capabilities','agent_card_url',
                            'mcp_endpoint_url','a2a_protocol_version')
    """)
    exec_cols = [r[0] for r in cur.fetchall()]
    print(f"  Executors A2A columns: {exec_cols}")
    
    # Check platform_config
    cur.execute("SELECT key, value FROM platform_config WHERE key LIKE 'feature.h2a%'")
    configs = {r[0]: r[1] for r in cur.fetchall()}
    print(f"  H2A config: {configs}")
    
    expected_tasks = {'publisher_type','human_wallet','human_user_id',
                      'target_executor_type','verification_mode',
                      'required_capabilities','verification_criteria'}
    expected_exec = {'executor_type','capabilities','agent_card_url',
                     'mcp_endpoint_url','a2a_protocol_version'}
    
    missing_tasks = expected_tasks - set(tasks_cols)
    missing_exec = expected_exec - set(exec_cols)
    
    if missing_tasks:
        print(f"\n  ❌ Missing tasks columns: {missing_tasks}")
    if missing_exec:
        print(f"\n  ❌ Missing executors columns: {missing_exec}")
    if not missing_tasks and not missing_exec:
        print(f"\n  ✅ All schema changes applied successfully!")
    
    return not missing_tasks and not missing_exec

if __name__ == "__main__":
    print("Connecting to Supabase (session mode)...")
    conn = get_connection()
    print("Connected!")
    
    apply_migration_031(conn)
    apply_migration_033_h2a(conn)
    add_h2a_config(conn)
    
    success = verify_schema(conn)
    conn.close()
    
    sys.exit(0 if success else 1)
