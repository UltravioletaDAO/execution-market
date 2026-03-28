import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Health from '../pages/Health'

// ---------- global fetch mock ----------

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock child components that need their own adminKey-based queries
vi.mock('../components/PhantomTasks', () => ({
  default: () => <div data-testid="phantom-tasks">PhantomTasks</div>,
}))
vi.mock('../components/OrphanedPayments', () => ({
  default: () => <div data-testid="orphaned-payments">OrphanedPayments</div>,
}))
vi.mock('../components/FinancialAudit', () => ({
  default: () => <div data-testid="financial-audit">FinancialAudit</div>,
}))

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    headers: new Headers(),
    redirected: false,
    statusText: 'OK',
    type: 'basic',
    url: '',
    clone: () => ({} as Response),
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response
}

const MOCK_HEALTH: Record<string, unknown> = {
  status: 'healthy',
  version: '1.0.0',
  uptime_seconds: 3661,
  timestamp: '2026-03-26T12:00:00Z',
  components: {
    database: {
      status: 'healthy',
      latency_ms: 12,
      message: 'Connected',
    },
    blockchain: {
      status: 'healthy',
      latency_ms: 45,
      message: 'Base L2 OK',
    },
    x402: {
      status: 'degraded',
      latency_ms: 1200,
      message: 'High latency',
    },
  },
}

const MOCK_VERSION = {
  name: 'Execution Market',
  version: '2.5.0',
  environment: 'production',
  build_date: '2026-03-25',
  git_commit: 'abc1234',
  uptime_seconds: 3661,
}

const MOCK_DETAILED = {
  status: 'healthy',
  version: '2.5.0',
  environment: 'production',
  uptime_seconds: 3661,
  timestamp: '2026-03-26T12:00:00Z',
  components: {
    database: { status: 'healthy', latency_ms: 12, message: 'Connected' },
    blockchain: { status: 'healthy', latency_ms: 45, message: 'Base L2 OK' },
    x402: { status: 'degraded', latency_ms: 1200, message: 'High latency' },
  },
  summary: {
    total_components: 3,
    healthy: 2,
    degraded: 1,
    unhealthy: 0,
  },
  critical_components: ['database', 'blockchain'],
}

const MOCK_SANITY = {
  status: 'ok',
  checks_passed: 5,
  checks_total: 5,
  warnings: [],
  summary: {
    task_status_distribution: { published: 3, completed: 10 },
    total_tasks: 13,
    total_bounty_usd: 1.50,
  },
  timestamp: '2026-03-26T12:00:00Z',
}

/**
 * Route mock fetch calls to the right response based on URL path.
 */
function setupHealthMocks() {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/health/version')) return Promise.resolve(jsonResponse(MOCK_VERSION))
    if (url.includes('/health/detailed')) return Promise.resolve(jsonResponse(MOCK_DETAILED))
    if (url.includes('/health/sanity')) return Promise.resolve(jsonResponse(MOCK_SANITY))
    if (url.includes('/health/metrics')) return Promise.resolve(jsonResponse(''))
    if (url.includes('/health/routes')) return Promise.resolve(jsonResponse({ total: 0, by_group: {} }))
    if (url.includes('/health')) return Promise.resolve(jsonResponse(MOCK_HEALTH))
    return Promise.resolve(jsonResponse({}, 404))
  })
}

function renderHealth(adminKey = 'test-key') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <Health adminKey={adminKey} />
    </QueryClientProvider>,
  )
}

// ---------- setup ----------

beforeEach(() => {
  mockFetch.mockReset()
})

// ---------- tests ----------

describe('Health — Loading state', () => {
  it('shows loading spinner while fetching', () => {
    // Never resolve so it stays loading
    mockFetch.mockReturnValue(new Promise(() => {}))
    renderHealth()
    expect(screen.getByText('Loading health data...')).toBeInTheDocument()
  })
})

describe('Health — Healthy system', () => {
  it('displays System Operational when all healthy', async () => {
    setupHealthMocks()
    renderHealth()

    await waitFor(() => {
      expect(screen.getByText('Health & Monitoring')).toBeInTheDocument()
    })

    expect(screen.getByText('System Operational')).toBeInTheDocument()
  })

  it('displays component cards', async () => {
    setupHealthMocks()
    renderHealth()

    await waitFor(() => {
      expect(screen.getByText('Database')).toBeInTheDocument()
    })

    expect(screen.getByText('Blockchain RPC')).toBeInTheDocument()
    expect(screen.getByText('x402 SDK')).toBeInTheDocument()
  })

  it('displays version info', async () => {
    setupHealthMocks()
    renderHealth()

    await waitFor(() => {
      expect(screen.getByText('2.5.0')).toBeInTheDocument()
    })

    expect(screen.getByText('abc1234')).toBeInTheDocument()
    expect(screen.getByText('production')).toBeInTheDocument()
  })

  it('shows component health summary counts', async () => {
    setupHealthMocks()
    renderHealth()

    await waitFor(() => {
      expect(screen.getByText(/2 healthy/)).toBeInTheDocument()
    })

    expect(screen.getByText(/1 degraded/)).toBeInTheDocument()
    expect(screen.getByText(/0 unhealthy/)).toBeInTheDocument()
  })
})

describe('Health — Degraded component', () => {
  it('shows degraded status text for x402', async () => {
    setupHealthMocks()
    renderHealth()

    await waitFor(() => {
      expect(screen.getByText('x402 SDK')).toBeInTheDocument()
    })

    // The x402 component should show "degraded"
    const degradedLabels = screen.getAllByText('degraded')
    expect(degradedLabels.length).toBeGreaterThan(0)
  })
})

describe('Health — API down', () => {
  it('shows error banner when health endpoint fails', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))
    renderHealth()

    await waitFor(() => {
      expect(screen.getByText(/Failed to reach health endpoint/)).toBeInTheDocument()
    })
  })
})

describe('Health — Sanity section', () => {
  it('displays sanity check results', async () => {
    setupHealthMocks()
    renderHealth()

    await waitFor(() => {
      expect(screen.getByText('Data Sanity Checks')).toBeInTheDocument()
    })

    // Should show total tasks from sanity summary
    await waitFor(() => {
      expect(screen.getByText('13')).toBeInTheDocument()
    })
    expect(screen.getByText('$1.50')).toBeInTheDocument()
  })
})

describe('Health — Financial auditors rendered', () => {
  it('renders PhantomTasks, OrphanedPayments, FinancialAudit', async () => {
    setupHealthMocks()
    renderHealth()

    await waitFor(() => {
      expect(screen.getByTestId('phantom-tasks')).toBeInTheDocument()
    })

    expect(screen.getByTestId('orphaned-payments')).toBeInTheDocument()
    expect(screen.getByTestId('financial-audit')).toBeInTheDocument()
  })
})
