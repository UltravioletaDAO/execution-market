-- Chamba MCP Server: Seed Data for Testing
-- Run after all migrations are applied
-- Contains bilingual (ES/EN) test data

-- ============================================
-- TEST AGENTS
-- ============================================

INSERT INTO agents (id, wallet_address, name, description, tier, verified, contact_email)
VALUES
    -- Colmena Agent (Task distribution)
    (
        'a1111111-1111-1111-1111-111111111111',
        '0xAgentColmena111111111111111111111111',
        'Colmena Forager',
        'Distributed task execution agent from the Colmena network. Specializes in physical verification tasks.',
        'professional',
        TRUE,
        'colmena@ultravioleta.io'
    ),
    -- Research Agent
    (
        'a2222222-2222-2222-2222-222222222222',
        '0xAgentResearch22222222222222222222222',
        'Council Research Agent',
        'Academic and research task agent. Handles document retrieval and knowledge access tasks.',
        'professional',
        TRUE,
        'research@ultravioleta.io'
    ),
    -- Market Research Agent
    (
        'a3333333-3333-3333-3333-333333333333',
        '0xAgentMarket333333333333333333333333',
        'Market Intel Agent',
        'Market research and competitive intelligence agent. Needs boots on the ground.',
        'starter',
        TRUE,
        'market@ultravioleta.io'
    ),
    -- Legal Services Agent
    (
        'a4444444-4444-4444-4444-444444444444',
        '0xAgentLegal4444444444444444444444444',
        'Legal Verification Agent',
        'Handles document notarization and legal verification tasks.',
        'enterprise',
        TRUE,
        'legal@ultravioleta.io'
    ),
    -- Inventory Agent
    (
        'a5555555-5555-5555-5555-555555555555',
        '0xAgentInventory55555555555555555555',
        'Inventory Checker',
        'Retail inventory and stock verification agent.',
        'starter',
        FALSE,
        'inventory@ultravioleta.io'
    )
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description;

-- ============================================
-- TEST EXECUTORS
-- ============================================

INSERT INTO executors (id, wallet_address, display_name, bio, email, roles, reputation_score, tasks_completed, location_city, location_country, default_location)
VALUES
    -- Ana - Mexico City (Spanish speaker, notary specialist)
    (
        'e1111111-1111-1111-1111-111111111111',
        '0xExecutor1111111111111111111111111111',
        'Ana Martinez',
        'Profesional verificadora en Ciudad de Mexico. Especialista en documentos legales y notarizacion.',
        'ana@example.com',
        ARRAY['notary', 'translator', 'document_verifier'],
        85,
        42,
        'Ciudad de Mexico',
        'Mexico',
        ST_MakePoint(-99.1332, 19.4326)::geography
    ),
    -- Carlos - Buenos Aires (Delivery specialist)
    (
        'e2222222-2222-2222-2222-222222222222',
        '0xExecutor2222222222222222222222222222',
        'Carlos Ruiz',
        'Freelancer en Buenos Aires. Hago entregas y verificaciones de presencia.',
        'carlos@example.com',
        ARRAY['delivery', 'presence_verification'],
        72,
        28,
        'Buenos Aires',
        'Argentina',
        ST_MakePoint(-58.3816, -34.6037)::geography
    ),
    -- Maria - Lima (Student, document scanner)
    (
        'e3333333-3333-3333-3333-333333333333',
        '0xExecutor3333333333333333333333333333',
        'Maria Garcia',
        'Estudiante en Lima. Disponible para escaneo de libros y documentos.',
        'maria@example.com',
        ARRAY['document_scanner', 'researcher'],
        45,
        15,
        'Lima',
        'Peru',
        ST_MakePoint(-77.0428, -12.0464)::geography
    ),
    -- David - San Francisco (Tech worker)
    (
        'e4444444-4444-4444-4444-444444444444',
        '0xExecutor4444444444444444444444444444',
        'David Chen',
        'Tech worker in San Francisco. Available for verification tasks and tech-related errands.',
        'david@example.com',
        ARRAY['tech_verification', 'presence_verification'],
        65,
        20,
        'San Francisco',
        'USA',
        ST_MakePoint(-122.4194, 37.7749)::geography
    ),
    -- Emma - London (Researcher)
    (
        'e5555555-5555-5555-5555-555555555555',
        '0xExecutor5555555555555555555555555555',
        'Emma Wilson',
        'Freelance researcher in London. Specialized in document retrieval and academic research.',
        'emma@example.com',
        ARRAY['researcher', 'document_scanner', 'translator'],
        78,
        35,
        'London',
        'UK',
        ST_MakePoint(-0.1276, 51.5074)::geography
    ),
    -- Roberto - Bogota (New user, low reputation)
    (
        'e6666666-6666-6666-6666-666666666666',
        '0xExecutor6666666666666666666666666666',
        'Roberto Gomez',
        'Nuevo en la plataforma. Estudiante universitario en Bogota.',
        'roberto@example.com',
        ARRAY['presence_verification'],
        30,
        3,
        'Bogota',
        'Colombia',
        ST_MakePoint(-74.0721, 4.7110)::geography
    ),
    -- Sakura - Tokyo (High reputation)
    (
        'e7777777-7777-7777-7777-777777777777',
        '0xExecutor7777777777777777777777777777',
        'Sakura Tanaka',
        'Professional verifier in Tokyo. Specialized in tech product verification and documentation.',
        'sakura@example.com',
        ARRAY['tech_verification', 'document_verifier', 'translator'],
        92,
        67,
        'Tokyo',
        'Japan',
        ST_MakePoint(139.6917, 35.6895)::geography
    )
ON CONFLICT (id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    reputation_score = EXCLUDED.reputation_score;

-- ============================================
-- SPANISH TASKS
-- ============================================

-- Physical presence task (ES) - Published
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location, location_radius_km, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't1111111-1111-1111-1111-111111111111',
    'a1111111-1111-1111-1111-111111111111',
    'Verificar que restaurante El Buen Sabor esta abierto',
    'Necesitamos confirmar que el restaurante esta operando normalmente.',
    E'Por favor verifica lo siguiente:\n1. El restaurante esta abierto y atendiendo clientes\n2. Toma una foto del frente mostrando horario visible\n3. Confirma si tienen mesas disponibles\n4. Toma foto del menu si esta visible',
    'physical_presence',
    5.00,
    NOW() + INTERVAL '24 hours',
    'published',
    ST_MakePoint(-99.1674, 19.4261)::geography,
    2.0,
    'Colonia Roma Norte, cerca del metro Insurgentes',
    '{"required": ["photo_geo", "text_response"], "optional": ["photo"]}',
    0,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Knowledge access task (ES) - Published
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't2222222-2222-2222-2222-222222222222',
    'a2222222-2222-2222-2222-222222222222',
    'Escanear paginas 45-52 del libro "Economia Digital"',
    'Necesito capitulo sobre micropagos de un libro academico.',
    E'Necesito las siguientes paginas escaneadas en alta calidad:\n\nLibro: "Economia Digital: Transformacion en America Latina"\nAutor: Juan Perez\nEditorial: Fondo de Cultura Economica\nISBN: 978-607-16-1234-5\n\nPaginas requeridas: 45-52 (Capitulo 3: Micropagos)\n\nRequisitos:\n- Minimo 300 DPI o foto muy clara\n- Todo el texto debe ser legible\n- Incluir foto de la portada del libro',
    'knowledge_access',
    12.50,
    NOW() + INTERVAL '72 hours',
    'published',
    'Cualquier biblioteca con el libro',
    '{"required": ["document", "photo"], "optional": ["text_response"]}',
    30,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Human authority task (ES) - Published, high reputation required
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location, location_radius_km, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't3333333-3333-3333-3333-333333333333',
    'a4444444-4444-4444-4444-444444444444',
    'Notarizar documento de poder legal',
    'Se requiere notarizacion de documento legal importante.',
    E'Se requiere notarizacion de documento de poder legal.\n\nDocumento adjunto en el sistema.\n\nProceso:\n1. Descargar documento del sistema\n2. Llevarlo a notaria publica autorizada\n3. Obtener firma y sello del notario\n4. Escanear documento notarizado\n5. Subir escaneo con foto del recibo de notaria\n\nNOTA: El gasto de notaria sera reembolsado adicionalmente.',
    'human_authority',
    150.00,
    NOW() + INTERVAL '168 hours',
    'published',
    ST_MakePoint(-100.3899, 20.5888)::geography,
    10.0,
    'Cualquier notaria publica en Queretaro',
    '{"required": ["notarized", "receipt", "document"], "optional": ["photo"]}',
    70,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Simple action task (ES) - Accepted by Carlos
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, executor_id, accepted_at,
    location, location_radius_km, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't4444444-4444-4444-4444-444444444444',
    'a5555555-5555-5555-5555-555555555555',
    'Comprar y fotografiar producto en tienda',
    'Verificacion de disponibilidad y precio de producto.',
    E'Comprar el siguiente producto:\n\nProducto: Cafe Organico Don Pablo (250g)\nTienda: Oxxo o 7-Eleven\n\nRequisitos:\n1. Comprar 1 unidad\n2. Fotografiar ticket de compra\n3. Fotografiar producto comprado\n4. Anotar precio y fecha de caducidad',
    'simple_action',
    8.00,
    NOW() + INTERVAL '48 hours',
    'accepted',
    'e2222222-2222-2222-2222-222222222222',
    NOW() - INTERVAL '2 hours',
    ST_MakePoint(-58.3816, -34.6037)::geography,
    5.0,
    'Cualquier tienda de conveniencia en Buenos Aires',
    '{"required": ["receipt", "photo"], "optional": ["text_response"]}',
    0,
    NOW() - INTERVAL '4 hours'
)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- ENGLISH TASKS
-- ============================================

-- Physical presence task (EN) - Published
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location, location_radius_km, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't5555555-5555-5555-5555-555555555555',
    'a1111111-1111-1111-1111-111111111111',
    'Verify property listing at 123 Main Street',
    'Real estate verification task for property listing.',
    E'Please verify the following for a real estate listing:\n\n1. Take a photo of the property exterior\n2. Confirm the "For Sale" sign is visible\n3. Note the condition of the exterior (1-5 rating)\n4. Check if anyone is currently occupying the property\n5. Take a photo of the neighborhood\n\nAddress: 123 Main Street, San Francisco, CA\n\nIMPORTANT: Do not trespass or enter the property.',
    'physical_presence',
    12.00,
    NOW() + INTERVAL '48 hours',
    'published',
    ST_MakePoint(-122.4194, 37.7749)::geography,
    1.0,
    'Near Mission District, San Francisco',
    '{"required": ["photo_geo", "text_response"], "optional": ["video"]}',
    50,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Knowledge access task (EN) - Published
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't6666666-6666-6666-6666-666666666666',
    'a2222222-2222-2222-2222-222222222222',
    'Retrieve article from university library',
    'Academic article retrieval requiring library access.',
    E'I need a specific academic article that requires library access:\n\nArticle: "Machine Learning in Financial Markets: A Survey"\nJournal: Journal of Finance, Vol. 78, Issue 3 (2023)\nDOI: 10.1234/jof.2023.12345\n\nRequirements:\n- Access via university library database\n- Download full PDF (not just abstract)\n- Include bibliography/references section\n- Screenshot of library access confirmation\n\nNote: Many universities provide alumni access. Public library access also acceptable.',
    'knowledge_access',
    20.00,
    NOW() + INTERVAL '96 hours',
    'published',
    'Any university library with journal access',
    '{"required": ["document", "screenshot"], "optional": ["text_response"]}',
    40,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Digital-physical task (EN) - Published
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location, location_radius_km, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't7777777-7777-7777-7777-777777777777',
    'a3333333-3333-3333-3333-333333333333',
    'Document cafe menu and prices for market research',
    'Market research on specialty coffee pricing in Seattle.',
    E'Conducting market research on specialty coffee pricing.\n\nTask: Visit a local specialty coffee shop and document:\n\n1. Full menu with prices (photo)\n2. Price of a medium latte\n3. Price of a small drip coffee\n4. Any seasonal specials\n5. Overall vibe/atmosphere (1-5 rating)\n6. Estimated customer count at time of visit\n\nPreferred cafes: Blue Bottle, Stumptown, or similar specialty shops.\n\nBonus: Note any non-dairy milk upcharge.',
    'digital_physical',
    8.00,
    NOW() + INTERVAL '48 hours',
    'published',
    ST_MakePoint(-122.3321, 47.6062)::geography,
    15.0,
    'Capitol Hill or Downtown Seattle',
    '{"required": ["photo", "text_response"], "optional": ["receipt"]}',
    20,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- High-value legal task (EN) - Published
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location, location_radius_km, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't8888888-8888-8888-8888-888888888888',
    'a4444444-4444-4444-4444-444444444444',
    'File small claims court paperwork',
    'Legal document filing assistance needed.',
    E'Need assistance filing small claims court paperwork.\n\nTask:\n1. Receive completed court forms (will be provided)\n2. Visit local courthouse clerk\n3. File the paperwork\n4. Pay filing fee (will be reimbursed)\n5. Obtain stamped/filed copies\n6. Upload all documentation\n\nLocation: San Francisco County Superior Court\n\nIMPORTANT:\n- Must be 18+ years old\n- All fees reimbursed + task bounty\n- Handle all documents confidentially',
    'human_authority',
    200.00,
    NOW() + INTERVAL '168 hours',
    'published',
    ST_MakePoint(-122.4194, 37.7749)::geography,
    5.0,
    'SF County Superior Court, 400 McAllister St',
    '{"required": ["document", "receipt", "photo"], "optional": ["text_response"]}',
    75,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Quick verification task (EN) - Published
INSERT INTO tasks (
    id, agent_id, title, description, instructions, category,
    bounty_usd, deadline, status, location, location_radius_km, location_hint,
    evidence_schema, min_reputation, published_at
)
VALUES (
    't9999999-9999-9999-9999-999999999999',
    'a5555555-5555-5555-5555-555555555555',
    'Verify business hours of local pharmacy',
    'Quick verification needed today.',
    E'Quick verification task:\n\nPlease verify the current operating hours of:\nWalgreens on Market Street, San Francisco\n\nRequired:\n1. Photo of posted business hours\n2. Confirm if pharmacy section has different hours\n3. Note if 24-hour or not\n\nThis is time-sensitive - need verification today.',
    'simple_action',
    3.00,
    NOW() + INTERVAL '6 hours',
    'published',
    ST_MakePoint(-122.4194, 37.7749)::geography,
    3.0,
    'Market Street area, San Francisco',
    '{"required": ["photo_geo"], "optional": ["text_response"]}',
    0,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- TEST APPLICATIONS
-- ============================================

-- Maria applied to the book scanning task
INSERT INTO applications (id, task_id, executor_id, message, status, created_at)
VALUES (
    'app11111-1111-1111-1111-111111111111',
    't2222222-2222-2222-2222-222222222222',
    'e3333333-3333-3333-3333-333333333333',
    'Tengo acceso a la biblioteca de la PUCP donde esta este libro. Puedo escanearlo manana.',
    'pending',
    NOW() - INTERVAL '1 hour'
)
ON CONFLICT (id) DO NOTHING;

-- David applied to the property verification task
INSERT INTO applications (id, task_id, executor_id, message, status, created_at)
VALUES (
    'app22222-2222-2222-2222-222222222222',
    't5555555-5555-5555-5555-555555555555',
    'e4444444-4444-4444-4444-444444444444',
    'I live near Mission District and can verify this property today after work.',
    'pending',
    NOW() - INTERVAL '30 minutes'
)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- TEST SUBMISSION
-- ============================================

-- Carlos submitted work for his accepted task
INSERT INTO submissions (
    id, task_id, executor_id,
    evidence, evidence_files, evidence_hash,
    status, submitted_at, auto_check_passed
)
VALUES (
    'sub11111-1111-1111-1111-111111111111',
    't4444444-4444-4444-4444-444444444444',
    'e2222222-2222-2222-2222-222222222222',
    '{
        "receipt": {
            "file": "evidence/t4444444/receipt.jpg",
            "amount": 850.00,
            "currency": "ARS"
        },
        "photo": {
            "file": "evidence/t4444444/product.jpg",
            "description": "Cafe Don Pablo 250g en empaque original"
        },
        "text_response": {
            "price": 850.00,
            "expiry_date": "2026-08-15",
            "notes": "Encontrado en Carrefour Express, Palermo"
        }
    }',
    ARRAY['evidence/t4444444/receipt.jpg', 'evidence/t4444444/product.jpg'],
    'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678',
    'pending',
    NOW(),
    TRUE
)
ON CONFLICT DO NOTHING;

-- Update task status to submitted
UPDATE tasks SET status = 'submitted' WHERE id = 't4444444-4444-4444-4444-444444444444';

-- ============================================
-- TEST ESCROWS
-- ============================================

-- Escrow for the submitted task
INSERT INTO escrows (
    id, task_id, amount_usd, status, deposited_at, expires_at
)
VALUES (
    'esc11111-1111-1111-1111-111111111111',
    't4444444-4444-4444-4444-444444444444',
    8.00,
    'active',
    NOW() - INTERVAL '4 hours',
    NOW() + INTERVAL '44 hours'
)
ON CONFLICT DO NOTHING;

-- Link escrow to task
UPDATE tasks SET escrow_id = 'esc11111-1111-1111-1111-111111111111' WHERE id = 't4444444-4444-4444-4444-444444444444';

-- ============================================
-- REPUTATION LOG SEED
-- ============================================

INSERT INTO reputation_log (executor_id, task_id, delta, new_score, reason, created_at)
SELECT
    e.id,
    NULL,
    e.reputation_score - 50,  -- Delta from starting score of 50
    e.reputation_score,
    'Initial seed reputation based on historical performance',
    e.created_at
FROM executors e
ON CONFLICT DO NOTHING;

-- ============================================
-- VERIFICATION
-- ============================================

-- Show summary of seeded data
DO $$
DECLARE
    v_agents INTEGER;
    v_executors INTEGER;
    v_tasks INTEGER;
    v_applications INTEGER;
    v_submissions INTEGER;
    v_escrows INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_agents FROM agents;
    SELECT COUNT(*) INTO v_executors FROM executors;
    SELECT COUNT(*) INTO v_tasks FROM tasks;
    SELECT COUNT(*) INTO v_applications FROM applications;
    SELECT COUNT(*) INTO v_submissions FROM submissions;
    SELECT COUNT(*) INTO v_escrows FROM escrows;

    RAISE NOTICE 'Seed data loaded successfully:';
    RAISE NOTICE '  - Agents: %', v_agents;
    RAISE NOTICE '  - Executors: %', v_executors;
    RAISE NOTICE '  - Tasks: %', v_tasks;
    RAISE NOTICE '  - Applications: %', v_applications;
    RAISE NOTICE '  - Submissions: %', v_submissions;
    RAISE NOTICE '  - Escrows: %', v_escrows;
END $$;
