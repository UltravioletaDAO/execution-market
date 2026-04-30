/**
 * VeryAiVerification — state machine tests (Phase 3 Task 3.1).
 *
 * Covers all six states: idle / loading_url / redirecting / polling /
 * success / error. Mocks useAuth, useTranslation, fetch, and
 * window.location so each transition can be driven deterministically.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'

// -----------------------------------------------------------------------------
// Mocks — installed BEFORE importing the component under test.
// -----------------------------------------------------------------------------

interface FakeExecutor {
  id: string
  veryai_verified?: boolean
  veryai_level?: string | null
}

let mockExecutor: FakeExecutor | null
let mockRefresh: ReturnType<typeof vi.fn>

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    executor: mockExecutor,
    refreshExecutor: mockRefresh,
    walletAddress: null,
    isAuthenticated: !!mockExecutor,
    loading: false,
    logout: vi.fn(),
  }),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

import { VeryAiVerification } from '../VeryAiVerification'

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

// Capture original Location BEFORE any test mutates it. Test 2 replaces
// window.location wholesale to spy on assign(); without restoring it the
// real Location getter (which makes replaceState reflect into .search)
// is permanently shadowed by a frozen object literal, breaking the
// callback-param tests.
const originalLocation = window.location

function setSearch(query: string) {
  window.history.replaceState({}, '', `/profile?${query}`)
}

function clearSearch() {
  window.history.replaceState({}, '', '/profile')
}

beforeEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    writable: true,
    value: originalLocation,
  })
  mockExecutor = { id: 'exec-1', veryai_verified: false, veryai_level: null }
  mockRefresh = vi.fn().mockResolvedValue(undefined)
  vi.useFakeTimers({ shouldAdvanceTime: true })
  clearSearch()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

describe('VeryAiVerification', () => {
  it('renders the start button when idle and executor present', () => {
    render(<VeryAiVerification />)
    expect(screen.getByTestId('veryai-start-button')).toBeInTheDocument()
    expect(screen.getByText(/Verify with VeryAI palm/i)).toBeInTheDocument()
  })

  it('click → fetches /oauth-url and redirects to authorize URL', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ url: 'https://api.very.org/oauth2/authorize?x=1', state: 'state-jwt' }), {
        status: 200,
      })
    )
    const assignSpy = vi.fn()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, assign: assignSpy, search: '', pathname: '/profile', hash: '' },
    })

    render(<VeryAiVerification />)
    fireEvent.click(screen.getByTestId('veryai-start-button'))

    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/very-id/oauth-url?executor_id=exec-1')
      )
    )
    await waitFor(() =>
      expect(assignSpy).toHaveBeenCalledWith('https://api.very.org/oauth2/authorize?x=1')
    )
    expect(screen.getByTestId('veryai-redirecting')).toBeInTheDocument()
  })

  it('oauth-url fetch failure → error state with retry', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('signing service unavailable', { status: 503 })
    )

    render(<VeryAiVerification />)
    fireEvent.click(screen.getByTestId('veryai-start-button'))

    await waitFor(() => expect(screen.getByTestId('veryai-error')).toBeInTheDocument())
    expect(screen.getByText(/signing service unavailable/i)).toBeInTheDocument()

    fireEvent.click(screen.getByText(/Try again/i))
    expect(screen.getByTestId('veryai-start-button')).toBeInTheDocument()
  })

  it('mount with ?veryai=success → polls /status until verified=true', async () => {
    setSearch('veryai=success')

    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    fetchSpy
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ verified: false, level: null, verified_at: null }), {
          status: 200,
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            verified: true,
            level: 'palm_single',
            verified_at: '2026-04-30T00:00:00Z',
          }),
          { status: 200 }
        )
      )

    render(<VeryAiVerification onVerified={vi.fn()} />)

    expect(screen.getByTestId('veryai-polling')).toBeInTheDocument()
    expect(window.location.search).toBe('') // params stripped on mount

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1))
    // Advance timers so the second tick fires.
    await vi.advanceTimersByTimeAsync(1500)
    await waitFor(() => expect(screen.getByTestId('veryai-success')).toBeInTheDocument())
    expect(mockRefresh).toHaveBeenCalled()
  })

  it('mount with ?veryai=error&reason=invalid_state → error UI shows reason', () => {
    setSearch('veryai=error&reason=invalid_state')
    render(<VeryAiVerification />)
    expect(screen.getByTestId('veryai-error')).toBeInTheDocument()
    expect(screen.getByText('invalid_state')).toBeInTheDocument()
  })

  it('mount with ?veryai=incomplete&reason=not_palm_verified → error UI', () => {
    setSearch('veryai=incomplete&reason=not_palm_verified')
    render(<VeryAiVerification />)
    expect(screen.getByTestId('veryai-error')).toBeInTheDocument()
    expect(screen.getByText('not_palm_verified')).toBeInTheDocument()
  })

  it('already-verified executor → renders badge + verified text, no button', () => {
    mockExecutor = { id: 'exec-1', veryai_verified: true, veryai_level: 'palm_dual' }
    render(<VeryAiVerification />)
    expect(screen.getByTestId('veryai-badge')).toBeInTheDocument()
    expect(screen.queryByTestId('veryai-start-button')).toBeNull()
    expect(screen.getByText(/Palm Dual Verified/i)).toBeInTheDocument()
  })

  it('strips ?veryai=success param from URL after consuming it', () => {
    setSearch('veryai=success')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ verified: false, level: null, verified_at: null }), {
        status: 200,
      })
    )
    render(<VeryAiVerification />)
    expect(window.location.search).toBe('')
  })
})
