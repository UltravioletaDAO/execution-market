/**
 * Execution Market E2E Test Mocks
 *
 * API mocks and test data for E2E testing.
 * Uses Playwright's route interception for Supabase API mocking.
 */

import type { Page } from '@playwright/test'

// ============================================================================
// Types
// ============================================================================

export type TaskCategory =
  | 'physical_presence'
  | 'knowledge_access'
  | 'human_authority'
  | 'simple_action'
  | 'digital_physical'

export type TaskStatus =
  | 'published'
  | 'accepted'
  | 'in_progress'
  | 'submitted'
  | 'verifying'
  | 'completed'
  | 'disputed'
  | 'expired'
  | 'cancelled'

export interface Task {
  id: string
  agent_id: string
  category: TaskCategory
  title: string
  instructions: string
  location: { lat: number; lng: number } | null
  location_radius_km: number | null
  location_hint: string | null
  evidence_schema: { required: string[]; optional?: string[] }
  bounty_usd: number
  payment_token: string
  deadline: string
  created_at: string
  updated_at: string
  min_reputation: number
  required_roles: string[]
  max_executors: number
  status: TaskStatus
  executor_id: string | null
}

export interface Executor {
  id: string
  user_id: string | null
  wallet_address: string
  display_name: string | null
  bio: string | null
  avatar_url: string | null
  roles: string[]
  reputation_score: number
  tasks_completed: number
  tasks_disputed: number
}

export interface Submission {
  id: string
  task_id: string
  executor_id: string
  evidence: Record<string, unknown>
  evidence_files: string[]
  submitted_at: string
  agent_verdict: string | null
  agent_notes: string | null
}

// ============================================================================
// Mock Data
// ============================================================================

export const mockExecutor: Executor = {
  id: 'exec-001',
  user_id: 'e2e-worker-001',
  wallet_address: '0xe2e0000000000000000000000000000000000001',
  display_name: 'E2E Worker',
  bio: 'Experienced executor for testing',
  avatar_url: null,
  roles: ['general', 'photography'],
  reputation_score: 85,
  tasks_completed: 12,
  tasks_disputed: 1,
}

export const mockAgent: Executor = {
  id: 'agent-001',
  user_id: 'e2e-agent-001',
  wallet_address: '0xe2e0000000000000000000000000000000000002',
  display_name: 'E2E Agent',
  bio: 'AI Agent for task coordination',
  avatar_url: null,
  roles: ['agent'],
  reputation_score: 100,
  tasks_completed: 0,
  tasks_disputed: 0,
}

export const mockTasks: Task[] = [
  {
    id: 'task-001',
    agent_id: 'agent-001',
    category: 'physical_presence',
    title: 'Verificar existencia de tienda en Plaza Norte',
    instructions:
      'Ir a Plaza Norte, Nivel 2, Local 245. Tomar foto del frente de la tienda mostrando el nombre y una foto del interior mostrando productos.',
    location: { lat: -12.0219, lng: -77.0593 },
    location_radius_km: 0.5,
    location_hint: 'Plaza Norte, Lima',
    evidence_schema: { required: ['photo_geo', 'photo'], optional: ['video'] },
    bounty_usd: 15.0,
    payment_token: 'USDC',
    deadline: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    min_reputation: 50,
    required_roles: [],
    max_executors: 1,
    status: 'published',
    executor_id: null,
  },
  {
    id: 'task-002',
    agent_id: 'agent-001',
    category: 'knowledge_access',
    title: 'Transcribir menu de restaurante local',
    instructions:
      'Visitar el restaurante "El Buen Sabor" y transcribir el menu completo incluyendo precios.',
    location: { lat: -12.0464, lng: -77.0428 },
    location_radius_km: 1.0,
    location_hint: 'Miraflores, Lima',
    evidence_schema: { required: ['text_response', 'photo'] },
    bounty_usd: 8.0,
    payment_token: 'USDC',
    deadline: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    min_reputation: 30,
    required_roles: [],
    max_executors: 1,
    status: 'published',
    executor_id: null,
  },
  {
    id: 'task-003',
    agent_id: 'agent-001',
    category: 'simple_action',
    title: 'Comprar y enviar recibo de producto',
    instructions:
      'Comprar un paquete de cafe marca "X" en cualquier supermercado y subir foto del recibo.',
    location: null,
    location_radius_km: null,
    location_hint: 'Cualquier ubicacion',
    evidence_schema: { required: ['receipt', 'photo'] },
    bounty_usd: 5.0,
    payment_token: 'USDC',
    deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    min_reputation: 0,
    required_roles: [],
    max_executors: 5,
    status: 'published',
    executor_id: null,
  },
]

export const mockSubmissions: Submission[] = [
  {
    id: 'sub-001',
    task_id: 'task-001',
    executor_id: 'exec-001',
    evidence: {
      photo_geo: 'https://example.com/photo1.jpg',
      photo: 'https://example.com/photo2.jpg',
      location: { lat: -12.0219, lng: -77.0593 },
    },
    evidence_files: ['photo1.jpg', 'photo2.jpg'],
    submitted_at: new Date().toISOString(),
    agent_verdict: null,
    agent_notes: null,
  },
]

// ============================================================================
// API Mock Setup
// ============================================================================

export interface MockOptions {
  delay?: number
}

/**
 * Set up Supabase API mocks for the dashboard.
 * Intercepts REST and RPC calls to return mock data.
 */
export async function setupMocks(
  page: Page,
  options: MockOptions = {}
): Promise<void> {
  const { delay = 50 } = options

  const wait = () => new Promise((r) => setTimeout(r, delay))

  // --------------------------------------------------------------------------
  // Supabase RPC calls (get_or_create_executor, link_wallet_to_session, etc.)
  // --------------------------------------------------------------------------
  await page.route('**/rest/v1/rpc/*', async (route) => {
    await wait()
    const url = route.request().url()

    if (url.includes('get_or_create_executor')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{
          id: mockExecutor.id,
          wallet_address: mockExecutor.wallet_address,
          display_name: mockExecutor.display_name,
          email: null,
          reputation_score: mockExecutor.reputation_score,
          tasks_completed: mockExecutor.tasks_completed,
          is_new: false,
          created_at: new Date().toISOString(),
        }]),
      })
    } else if (url.includes('link_wallet_to_session')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(null),
      })
    } else if (url.includes('apply_to_task')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(null),
      })
    }
  })

  // --------------------------------------------------------------------------
  // Tasks REST
  // --------------------------------------------------------------------------
  await page.route('**/rest/v1/tasks*', async (route) => {
    await wait()
    const method = route.request().method()

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockTasks),
      })
    } else if (method === 'POST') {
      const body = await route.request().postDataJSON()
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: `task-${Date.now()}`, ...body, status: 'published' }),
      })
    } else {
      await route.continue()
    }
  })

  // --------------------------------------------------------------------------
  // Submissions REST
  // --------------------------------------------------------------------------
  await page.route('**/rest/v1/submissions*', async (route) => {
    await wait()
    const method = route.request().method()

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSubmissions),
      })
    } else if (method === 'POST') {
      const body = await route.request().postDataJSON()
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `sub-${Date.now()}`,
          ...body,
          submitted_at: new Date().toISOString(),
        }),
      })
    } else {
      await route.continue()
    }
  })

  // --------------------------------------------------------------------------
  // Executors REST
  // --------------------------------------------------------------------------
  await page.route('**/rest/v1/executors*', async (route) => {
    await wait()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([mockExecutor]),
    })
  })

  // --------------------------------------------------------------------------
  // Task Applications REST
  // --------------------------------------------------------------------------
  await page.route('**/rest/v1/task_applications*', async (route) => {
    await wait()
    const method = route.request().method()

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    } else if (method === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `app-${Date.now()}`,
          status: 'pending',
          created_at: new Date().toISOString(),
        }),
      })
    } else {
      await route.continue()
    }
  })

  // --------------------------------------------------------------------------
  // Supabase Auth (anonymous sign-in, session)
  // --------------------------------------------------------------------------
  await page.route('**/auth/v1/**', async (route) => {
    await wait()
    const url = route.request().url()

    if (url.includes('/token') || url.includes('/signup')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'e2e-mock-token',
          token_type: 'bearer',
          expires_in: 3600,
          refresh_token: 'e2e-mock-refresh',
          user: { id: 'e2e-anon-user', role: 'anon' },
        }),
      })
    } else if (url.includes('/user')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'e2e-anon-user', role: 'anon' }),
      })
    } else if (url.includes('/logout')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    } else {
      await route.continue()
    }
  })
}

/**
 * Mock geolocation API
 */
export async function mockGeolocation(
  page: Page,
  coords: { latitude: number; longitude: number } = {
    latitude: -12.0464,
    longitude: -77.0428,
  }
): Promise<void> {
  await page.context().grantPermissions(['geolocation'])
  await page.context().setGeolocation(coords)
}

/**
 * Mock camera/media devices
 */
export async function mockCamera(page: Page): Promise<void> {
  await page.context().grantPermissions(['camera'])

  await page.addInitScript(() => {
    const mockMediaDevices = {
      getUserMedia: async () => {
        const canvas = document.createElement('canvas')
        canvas.width = 640
        canvas.height = 480
        const ctx = canvas.getContext('2d')
        if (ctx) {
          ctx.fillStyle = '#333'
          ctx.fillRect(0, 0, 640, 480)
          ctx.fillStyle = '#fff'
          ctx.font = '24px sans-serif'
          ctx.textAlign = 'center'
          ctx.fillText('Mock Camera Feed', 320, 240)
        }
        return (canvas as any).captureStream(30)
      },
      enumerateDevices: async () => [
        { deviceId: 'mock-cam', kind: 'videoinput', label: 'Mock Camera', groupId: 'g' },
      ],
    }

    Object.defineProperty(navigator, 'mediaDevices', {
      value: mockMediaDevices,
      writable: true,
    })
  })
}
