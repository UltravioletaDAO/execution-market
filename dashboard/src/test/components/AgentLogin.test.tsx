// AgentLogin component tests
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// Mock the API module
const mockPost = vi.fn()
vi.mock('../../services/api', () => ({
  api: {
    post: (...args: unknown[]) => mockPost(...args),
  },
  setAuthToken: vi.fn(),
  clearAuthToken: vi.fn(),
}))

// Mock react-router-dom navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock usePlatformConfig — simulate API key required mode for login form tests
vi.mock('../../hooks/usePlatformConfig', () => ({
  usePlatformConfig: () => ({
    config: { require_api_key: true },
    requireApiKey: true,
    loading: false,
    error: null,
  }),
}))

// Create a proper in-memory localStorage mock
const storageMap = new Map<string, string>()
const localStorageMock = {
  getItem: vi.fn((key: string) => storageMap.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => { storageMap.set(key, value) }),
  removeItem: vi.fn((key: string) => { storageMap.delete(key) }),
  clear: vi.fn(() => { storageMap.clear() }),
  get length() { return storageMap.size },
  key: vi.fn((i: number) => Array.from(storageMap.keys())[i] ?? null),
}

vi.stubGlobal('localStorage', localStorageMock)

// Import AFTER mocks are set up
import { AgentLogin } from '../../components/AgentLogin'
import { isAgentLoggedIn, clearAgentSession, setAgentSession } from '../../utils/agentAuth'

function renderAgentLogin() {
  return render(
    <MemoryRouter
      initialEntries={['/agent/login']}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AgentLogin />
    </MemoryRouter>
  )
}

describe('AgentLogin', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    storageMap.clear()
  })

  afterEach(() => {
    storageMap.clear()
  })

  it('renders the login form', () => {
    renderAgentLogin()

    expect(screen.getByText('Agent Login')).toBeTruthy()
    expect(screen.getByTestId('api-key-input')).toBeTruthy()
    expect(screen.getByTestId('login-button')).toBeTruthy()
  })

  it('disables submit button when input is empty', () => {
    renderAgentLogin()

    const button = screen.getByTestId('login-button')
    expect(button).toBeDisabled()
  })

  it('enables submit button when input has value', () => {
    renderAgentLogin()

    const input = screen.getByTestId('api-key-input')
    fireEvent.change(input, { target: { value: 'em_free_test123' } })

    const button = screen.getByTestId('login-button')
    expect(button).not.toBeDisabled()
  })

  it('calls API and navigates on successful login', async () => {
    mockPost.mockResolvedValueOnce({
      token: 'jwt-token-123',
      agent_id: 'agent-42',
      tier: 'starter',
      expires_at: '2026-12-31T23:59:59Z',
    })

    renderAgentLogin()

    const input = screen.getByTestId('api-key-input')
    fireEvent.change(input, { target: { value: 'em_starter_testkey123' } })

    const button = screen.getByTestId('login-button')
    fireEvent.click(button)

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/api/v1/agent/auth', {
        api_key: 'em_starter_testkey123',
      })
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/agent/dashboard', { replace: true })
    })

    // Verify localStorage was set
    expect(localStorage.getItem('em_agent_jwt')).toBe('jwt-token-123')
    expect(localStorage.getItem('em_agent_id')).toBe('agent-42')
    expect(localStorage.getItem('em_agent_tier')).toBe('starter')
  })

  it('shows error on 401 response', async () => {
    mockPost.mockRejectedValueOnce({
      status: 401,
      message: 'Invalid API key',
      detail: { message: 'Invalid API key' },
    })

    renderAgentLogin()

    const input = screen.getByTestId('api-key-input')
    fireEvent.change(input, { target: { value: 'em_free_invalidkey123' } })

    const button = screen.getByTestId('login-button')
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Invalid API key')).toBeTruthy()
    })

    // Should NOT navigate
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('shows generic error on network failure', async () => {
    mockPost.mockRejectedValueOnce({
      message: 'Network error',
    })

    renderAgentLogin()

    const input = screen.getByTestId('api-key-input')
    fireEvent.change(input, { target: { value: 'em_free_somekey12345678' } })

    const button = screen.getByTestId('login-button')
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeTruthy()
    })
  })

  it('shows worker login link', () => {
    renderAgentLogin()

    const workerLink = screen.getByTestId('worker-login-link')
    expect(workerLink).toBeTruthy()
  })

  it('navigates to home when worker link clicked', () => {
    renderAgentLogin()

    const workerLink = screen.getByTestId('worker-login-link')
    fireEvent.click(workerLink)

    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('clears error when user types', async () => {
    mockPost.mockRejectedValueOnce({
      status: 401,
      message: 'Invalid API key',
      detail: { message: 'Invalid API key' },
    })

    renderAgentLogin()

    const input = screen.getByTestId('api-key-input')
    fireEvent.change(input, { target: { value: 'em_free_bad' } })

    const button = screen.getByTestId('login-button')
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Invalid API key')).toBeTruthy()
    })

    // Type again — error should clear
    fireEvent.change(input, { target: { value: 'em_free_new' } })

    await waitFor(() => {
      expect(screen.queryByText('Invalid API key')).toBeNull()
    })
  })
})

// --------------------------------------------------------------------------
// Session helper tests
// --------------------------------------------------------------------------

describe('Agent session helpers', () => {
  beforeEach(() => {
    storageMap.clear()
  })

  afterEach(() => {
    storageMap.clear()
  })

  it('isAgentLoggedIn returns false when no token', () => {
    expect(isAgentLoggedIn()).toBe(false)
  })

  it('isAgentLoggedIn returns true for valid non-expired token', () => {
    // Create a simple JWT-like token with future expiration
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))
    const fakeJwt = `header.${payload}.signature`
    localStorage.setItem('em_agent_jwt', fakeJwt)

    expect(isAgentLoggedIn()).toBe(true)
  })

  it('isAgentLoggedIn returns false for expired token', () => {
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 }))
    const fakeJwt = `header.${payload}.signature`
    localStorage.setItem('em_agent_jwt', fakeJwt)

    expect(isAgentLoggedIn()).toBe(false)
    // Should also clear the storage
    expect(localStorage.getItem('em_agent_jwt')).toBeNull()
  })

  it('setAgentSession stores all values', () => {
    setAgentSession('token-123', 'agent-1', 'growth')

    expect(localStorage.getItem('em_agent_jwt')).toBe('token-123')
    expect(localStorage.getItem('em_agent_id')).toBe('agent-1')
    expect(localStorage.getItem('em_agent_tier')).toBe('growth')
  })

  it('clearAgentSession removes all values', () => {
    setAgentSession('token-123', 'agent-1', 'growth')
    clearAgentSession()

    expect(localStorage.getItem('em_agent_jwt')).toBeNull()
    expect(localStorage.getItem('em_agent_id')).toBeNull()
    expect(localStorage.getItem('em_agent_tier')).toBeNull()
  })
})
