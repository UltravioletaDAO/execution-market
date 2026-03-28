import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from '../App'

// ---------- mocks ----------

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock the WebSocket module so App doesn't try to connect
vi.mock('../lib/ws', () => ({
  useWebSocketInvalidation: () => {},
  adminWS: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    onStatus: vi.fn(),
    offStatus: vi.fn(),
    onAny: vi.fn(),
    offAny: vi.fn(),
    status: 'disconnected',
    lastEvent: null,
    lastEventTime: null,
  },
  useWebSocket: () => ({
    isConnected: false,
    status: 'disconnected' as const,
    lastEvent: null,
    lastEventTime: null,
  }),
}))

// Mock ConnectionStatus to avoid WebSocket hookups
vi.mock('../components/ConnectionStatus', () => ({
  default: () => <span data-testid="connection-status">Offline</span>,
}))

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ---------- setup / teardown ----------

beforeEach(() => {
  mockFetch.mockReset()
  sessionStorage.clear()
})

afterEach(() => {
  sessionStorage.clear()
})

// ---------- tests ----------

describe('Auth — Login flow', () => {
  it('shows login form when not authenticated', () => {
    renderApp()
    expect(screen.getByPlaceholderText('Enter admin key...')).toBeInTheDocument()
    expect(screen.getByText('Login')).toBeInTheDocument()
  })

  it('shows error when submitting empty key', async () => {
    renderApp()
    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(screen.getByText('Please enter an admin key')).toBeInTheDocument()
    })
  })

  it('authenticates with valid key and shows dashboard', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

    renderApp()
    const input = screen.getByPlaceholderText('Enter admin key...')
    fireEvent.change(input, { target: { value: 'test-admin-key' } })
    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(screen.getByText('Logout')).toBeInTheDocument()
    })

    // Verify the verify API was called with X-Admin-Key header
    const verifyCalls = mockFetch.mock.calls.filter(([url]: [string]) => url.includes('/admin/verify'))
    expect(verifyCalls.length).toBe(1)
    const [url, init] = verifyCalls[0]
    expect(url).toContain('/api/v1/admin/verify')
    expect(init.headers['X-Admin-Key']).toBe('test-admin-key')
  })

  it('shows error on invalid key (401)', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 })

    renderApp()
    const input = screen.getByPlaceholderText('Enter admin key...')
    fireEvent.change(input, { target: { value: 'bad-key' } })
    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(screen.getByText('Invalid admin key')).toBeInTheDocument()
    })
  })

  it('shows error on network failure', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    renderApp()
    const input = screen.getByPlaceholderText('Enter admin key...')
    fireEvent.change(input, { target: { value: 'some-key' } })
    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(screen.getByText('Cannot reach the server. Please try again.')).toBeInTheDocument()
    })
  })
})

describe('Auth — Session persistence', () => {
  it('restores auth from sessionStorage on mount', () => {
    sessionStorage.setItem('adminKey', 'stored-key')

    renderApp()

    // Should skip login, show dashboard (sidebar with Logout)
    expect(screen.getByText('Logout')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Enter admin key...')).not.toBeInTheDocument()
  })

  it('stores key in sessionStorage on login', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

    renderApp()
    const input = screen.getByPlaceholderText('Enter admin key...')
    fireEvent.change(input, { target: { value: 'persist-me' } })
    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(sessionStorage.getItem('adminKey')).toBe('persist-me')
    })
  })
})

describe('Auth — Logout', () => {
  it('clears session and returns to login', async () => {
    sessionStorage.setItem('adminKey', 'stored-key')

    renderApp()
    expect(screen.getByText('Logout')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Logout'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Enter admin key...')).toBeInTheDocument()
    })
    expect(sessionStorage.getItem('adminKey')).toBeNull()
  })
})
