/**
 * Chamba E2E Test Mocks
 *
 * API mocks and test data for E2E testing.
 * Uses Playwright's route interception for API mocking.
 */

import type { Page, Route } from '@playwright/test'

// ============================================================================
// Type Definitions (matching dashboard/src/types/database.ts)
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

export interface Location {
  lat: number
  lng: number
}

export interface Task {
  id: string
  agent_id: string
  category: TaskCategory
  title: string
  instructions: string
  location: Location | null
  location_radius_km: number | null
  location_hint: string | null
  evidence_schema: {
    required: string[]
    optional?: string[]
  }
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

export interface TaskApplication {
  id: string
  task_id: string
  executor_id: string
  message: string | null
  status: 'pending' | 'accepted' | 'rejected'
  created_at: string
}

// ============================================================================
// Mock Data
// ============================================================================

export const mockExecutor: Executor = {
  id: 'exec-001',
  user_id: 'user-001',
  wallet_address: '0x1234567890abcdef1234567890abcdef12345678',
  display_name: 'Test Executor',
  bio: 'Experienced executor for Chamba tasks',
  avatar_url: null,
  roles: ['general', 'photography'],
  reputation_score: 85,
  tasks_completed: 12,
  tasks_disputed: 1,
}

export const mockAgent: Executor = {
  id: 'agent-001',
  user_id: 'user-agent-001',
  wallet_address: '0xagent1234567890abcdef1234567890abcdef',
  display_name: 'Test Agent',
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
    evidence_schema: {
      required: ['photo_geo', 'photo'],
      optional: ['video'],
    },
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
      'Visitar el restaurante "El Buen Sabor" y transcribir el menu completo incluyendo precios. Tomar fotos del menu como respaldo.',
    location: { lat: -12.0464, lng: -77.0428 },
    location_radius_km: 1.0,
    location_hint: 'Miraflores, Lima',
    evidence_schema: {
      required: ['text_response', 'photo'],
    },
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
      'Comprar un paquete de cafe marca "X" en cualquier supermercado y subir foto del recibo mostrando precio y fecha.',
    location: null,
    location_radius_km: null,
    location_hint: 'Cualquier ubicacion',
    evidence_schema: {
      required: ['receipt', 'photo'],
    },
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
  {
    id: 'task-004',
    agent_id: 'agent-001',
    category: 'human_authority',
    title: 'Firmar documento de conformidad',
    instructions:
      'Recibir paquete en direccion indicada, verificar contenido y firmar documento de conformidad. Subir foto de firma.',
    location: { lat: -12.0897, lng: -77.0251 },
    location_radius_km: 0.1,
    location_hint: 'San Isidro, Lima',
    evidence_schema: {
      required: ['signature', 'photo'],
    },
    bounty_usd: 20.0,
    payment_token: 'USDC',
    deadline: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    min_reputation: 70,
    required_roles: ['verified'],
    max_executors: 1,
    status: 'published',
    executor_id: null,
  },
  {
    id: 'task-005',
    agent_id: 'agent-001',
    category: 'digital_physical',
    title: 'Escanear codigo QR en evento',
    instructions:
      'Asistir al evento Tech Summit, encontrar el stand de Chamba y escanear el codigo QR. Subir screenshot del resultado.',
    location: { lat: -12.1191, lng: -77.0313 },
    location_radius_km: 0.2,
    location_hint: 'Centro de Convenciones, Lima',
    evidence_schema: {
      required: ['screenshot', 'photo_geo'],
    },
    bounty_usd: 10.0,
    payment_token: 'USDC',
    deadline: new Date(Date.now() + 12 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    min_reputation: 40,
    required_roles: [],
    max_executors: 10,
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

export const mockApplications: TaskApplication[] = [
  {
    id: 'app-001',
    task_id: 'task-002',
    executor_id: 'exec-001',
    message: 'Estoy cerca del restaurante y puedo hacerlo hoy',
    status: 'pending',
    created_at: new Date().toISOString(),
  },
]

// ============================================================================
// API Mock Handlers
// ============================================================================

export interface MockOptions {
  delay?: number
  errorRate?: number
}

/**
 * Set up all API mocks for the Chamba application
 */
export async function setupMocks(
  page: Page,
  options: MockOptions = {}
): Promise<void> {
  const { delay = 100, errorRate = 0 } = options

  // Helper to potentially throw errors for testing error states
  const maybeError = (route: Route): boolean => {
    if (errorRate > 0 && Math.random() < errorRate) {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' }),
      })
      return true
    }
    return false
  }

  // Mock Supabase REST API - Tasks
  await page.route('**/rest/v1/tasks*', async (route) => {
    if (maybeError(route)) return

    const method = route.request().method()
    const url = route.request().url()

    await new Promise((r) => setTimeout(r, delay))

    if (method === 'GET') {
      // Parse query params for filtering
      const urlObj = new URL(url)
      const status = urlObj.searchParams.get('status')
      const category = urlObj.searchParams.get('category')

      let tasks = [...mockTasks]

      if (status) {
        tasks = tasks.filter((t) => t.status === status)
      }
      if (category) {
        tasks = tasks.filter((t) => t.category === category)
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(tasks),
      })
    } else if (method === 'POST') {
      const body = await route.request().postDataJSON()
      const newTask: Task = {
        id: `task-${Date.now()}`,
        ...body,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: 'published',
        executor_id: null,
      }
      mockTasks.push(newTask)
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newTask),
      })
    } else if (method === 'PATCH') {
      const body = await route.request().postDataJSON()
      const taskId = url.match(/id=eq\.([^&]+)/)?.[1]
      const taskIndex = mockTasks.findIndex((t) => t.id === taskId)
      if (taskIndex >= 0) {
        mockTasks[taskIndex] = { ...mockTasks[taskIndex], ...body }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockTasks[taskIndex]),
        })
      } else {
        await route.fulfill({ status: 404 })
      }
    } else {
      await route.continue()
    }
  })

  // Mock Supabase REST API - Submissions
  await page.route('**/rest/v1/submissions*', async (route) => {
    if (maybeError(route)) return

    const method = route.request().method()

    await new Promise((r) => setTimeout(r, delay))

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSubmissions),
      })
    } else if (method === 'POST') {
      const body = await route.request().postDataJSON()
      const newSubmission: Submission = {
        id: `sub-${Date.now()}`,
        ...body,
        submitted_at: new Date().toISOString(),
        agent_verdict: null,
        agent_notes: null,
      }
      mockSubmissions.push(newSubmission)
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newSubmission),
      })
    } else if (method === 'PATCH') {
      const body = await route.request().postDataJSON()
      const subId = route.request().url().match(/id=eq\.([^&]+)/)?.[1]
      const subIndex = mockSubmissions.findIndex((s) => s.id === subId)
      if (subIndex >= 0) {
        mockSubmissions[subIndex] = { ...mockSubmissions[subIndex], ...body }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockSubmissions[subIndex]),
        })
      } else {
        await route.fulfill({ status: 404 })
      }
    } else {
      await route.continue()
    }
  })

  // Mock Supabase REST API - Task Applications
  await page.route('**/rest/v1/task_applications*', async (route) => {
    if (maybeError(route)) return

    const method = route.request().method()

    await new Promise((r) => setTimeout(r, delay))

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockApplications),
      })
    } else if (method === 'POST') {
      const body = await route.request().postDataJSON()
      const newApp: TaskApplication = {
        id: `app-${Date.now()}`,
        ...body,
        status: 'pending',
        created_at: new Date().toISOString(),
      }
      mockApplications.push(newApp)
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newApp),
      })
    } else {
      await route.continue()
    }
  })

  // Mock Supabase REST API - Executors
  await page.route('**/rest/v1/executors*', async (route) => {
    if (maybeError(route)) return

    await new Promise((r) => setTimeout(r, delay))

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([mockExecutor]),
    })
  })

  // Mock Supabase Auth
  await page.route('**/auth/v1/**', async (route) => {
    if (maybeError(route)) return

    const url = route.request().url()

    await new Promise((r) => setTimeout(r, delay))

    if (url.includes('/token')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-access-token',
          token_type: 'bearer',
          expires_in: 3600,
          refresh_token: 'mock-refresh-token',
          user: {
            id: 'user-001',
            email: 'test@chamba.work',
            role: 'authenticated',
          },
        }),
      })
    } else if (url.includes('/user')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-001',
          email: 'test@chamba.work',
          role: 'authenticated',
        }),
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
 * Mock wallet connection (MetaMask, WalletConnect, etc.)
 */
export async function mockWalletConnection(page: Page): Promise<void> {
  // Inject mock ethereum provider
  await page.addInitScript(() => {
    const mockEthereum = {
      isMetaMask: true,
      isConnected: () => true,
      selectedAddress: '0x1234567890abcdef1234567890abcdef12345678',
      chainId: '0x1', // Ethereum mainnet
      networkVersion: '1',

      request: async ({ method, params }: { method: string; params?: unknown[] }) => {
        switch (method) {
          case 'eth_requestAccounts':
          case 'eth_accounts':
            return ['0x1234567890abcdef1234567890abcdef12345678']

          case 'eth_chainId':
            return '0x1'

          case 'wallet_switchEthereumChain':
            return null

          case 'personal_sign':
            // Return mock signature
            return '0x' + '00'.repeat(65)

          case 'eth_sendTransaction':
            // Return mock transaction hash
            return '0x' + '00'.repeat(32)

          default:
            console.log('[Mock Wallet] Unhandled method:', method, params)
            return null
        }
      },

      on: (event: string, callback: (...args: unknown[]) => void) => {
        console.log('[Mock Wallet] Event listener added:', event)
        if (event === 'accountsChanged') {
          // Immediately fire with mock account
          setTimeout(
            () => callback(['0x1234567890abcdef1234567890abcdef12345678']),
            100
          )
        }
      },

      removeListener: () => {},
    }

    // @ts-expect-error - Injecting mock provider
    window.ethereum = mockEthereum
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
    // Mock MediaDevices API
    const mockMediaDevices = {
      getUserMedia: async (constraints: MediaStreamConstraints) => {
        console.log('[Mock Camera] getUserMedia called:', constraints)

        // Create a mock MediaStream
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

        // @ts-expect-error - captureStream is not in TypeScript types
        const stream = canvas.captureStream(30)
        return stream
      },

      enumerateDevices: async () => [
        {
          deviceId: 'mock-camera-1',
          kind: 'videoinput',
          label: 'Mock Camera',
          groupId: 'mock-group',
        },
        {
          deviceId: 'mock-mic-1',
          kind: 'audioinput',
          label: 'Mock Microphone',
          groupId: 'mock-group',
        },
      ],
    }

    Object.defineProperty(navigator, 'mediaDevices', {
      value: mockMediaDevices,
      writable: true,
    })
  })
}

/**
 * Mock file upload dialog
 */
export async function mockFileUpload(
  page: Page,
  filePath: string,
  fileName: string
): Promise<void> {
  // Create a test file
  const fileContent = Buffer.from('mock file content')

  await page.setInputFiles('input[type="file"]', {
    name: fileName,
    mimeType: 'image/jpeg',
    buffer: fileContent,
  })
}
