-- ============================================================================
-- CHAMBA: Seed Data for Testing
-- Description: Creates test executor and sample tasks for development/testing
-- Safe to run multiple times (uses ON CONFLICT DO NOTHING)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- TEST EXECUTOR (Worker)
-- ---------------------------------------------------------------------------
INSERT INTO executors (
    id,
    wallet_address,
    display_name,
    reputation_score,
    status,
    tier,
    tasks_completed,
    skills,
    languages,
    location_city,
    location_country
)
VALUES (
    '11111111-1111-1111-1111-111111111111'::UUID,
    'YOUR_DEV_WALLET',
    'Test Worker',
    75,
    'active',
    'standard',
    5,
    ARRAY['photography', 'local-presence', 'verification'],
    ARRAY['en', 'es'],
    'Mexico City',
    'Mexico'
)
ON CONFLICT (wallet_address) DO NOTHING;

-- ---------------------------------------------------------------------------
-- SAMPLE TASKS
-- ---------------------------------------------------------------------------

-- Task 1: Physical Presence ($5)
INSERT INTO tasks (
    id,
    agent_id,
    agent_name,
    title,
    instructions,
    category,
    bounty_usd,
    deadline,
    evidence_schema,
    status,
    chain_id,
    published_at,
    tags
)
VALUES (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::UUID,
    'test-agent-001',
    'Test Agent',
    'Verify Store Hours',
    'Visit the store at 123 Main St and take a photo of the hours sign. Confirm if they match the online listing.',
    'physical_presence',
    5.00,
    NOW() + INTERVAL '24 hours',
    '{"required": ["photo_geo", "text_response"], "optional": []}'::JSONB,
    'published',
    43114,
    NOW(),
    ARRAY['verification', 'photo', 'local']
)
ON CONFLICT (id) DO NOTHING;

-- Task 2: Knowledge Access ($10)
INSERT INTO tasks (
    id,
    agent_id,
    agent_name,
    title,
    instructions,
    category,
    bounty_usd,
    deadline,
    evidence_schema,
    status,
    chain_id,
    published_at,
    tags
)
VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::UUID,
    'test-agent-001',
    'Test Agent',
    'Get Quote from Contractor',
    'Contact ABC Contractors at (555) 123-4567 and get a written quote for kitchen renovation.',
    'knowledge_access',
    10.00,
    NOW() + INTERVAL '48 hours',
    '{"required": ["document", "text_response"], "optional": ["photo"]}'::JSONB,
    'published',
    43114,
    NOW(),
    ARRAY['quote', 'contractor', 'document']
)
ON CONFLICT (id) DO NOTHING;

-- Task 3: Simple Action ($3)
INSERT INTO tasks (
    id,
    agent_id,
    agent_name,
    title,
    instructions,
    category,
    bounty_usd,
    deadline,
    evidence_schema,
    status,
    chain_id,
    published_at,
    tags
)
VALUES (
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::UUID,
    'test-agent-001',
    'Test Agent',
    'Check Package Delivery',
    'Check if package #12345 has been delivered to the mailroom at Building A. Take a photo of the package if found.',
    'simple_action',
    3.00,
    NOW() + INTERVAL '12 hours',
    '{"required": ["photo"], "optional": ["text_response"]}'::JSONB,
    'published',
    43114,
    NOW(),
    ARRAY['delivery', 'package', 'photo']
)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- VERIFICATION QUERY (Optional - run to verify seed data)
-- ---------------------------------------------------------------------------
-- SELECT 'Executors:' as table_name, COUNT(*) as count FROM executors
-- UNION ALL
-- SELECT 'Tasks:', COUNT(*) FROM tasks WHERE agent_id = 'test-agent-001';
