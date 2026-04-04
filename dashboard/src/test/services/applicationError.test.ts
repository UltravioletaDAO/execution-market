/**
 * ApplicationError & applyToTask error handling tests
 *
 * Verifies that the service layer correctly parses structured API errors
 * and throws typed ApplicationError instances for 403/409 responses.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock supabase before importing the service
vi.mock('../../lib/supabase', () => ({
  supabase: {
    from: () => ({
      select: () => ({ eq: () => ({ single: () => Promise.resolve({ data: null, error: null }) }) }),
    }),
  },
}))

// Mock auth headers
vi.mock('../../lib/auth', () => ({
  buildAuthHeaders: vi.fn(async (extra: Record<string, string>) => ({
    ...extra,
    Authorization: 'Bearer test-token',
  })),
}))

// Mock usePlatformConfig
vi.mock('../../hooks/usePlatformConfig', () => ({
  getRequireApiKey: () => false,
}))

import { ApplicationError } from '../../services/tasks'

describe('ApplicationError', () => {
  it('is an instance of Error', () => {
    const err = new ApplicationError('world_id_required', 'Need World ID', 403)
    expect(err).toBeInstanceOf(Error)
    expect(err).toBeInstanceOf(ApplicationError)
  })

  it('has correct type, status, and message', () => {
    const err = new ApplicationError('already_applied', 'Already applied', 409)
    expect(err.type).toBe('already_applied')
    expect(err.status).toBe(409)
    expect(err.message).toBe('Already applied')
  })

  it('stores detail object', () => {
    const detail = { required_level: 'orb', current_level: null }
    const err = new ApplicationError('world_id_required', 'msg', 403, detail)
    expect(err.detail).toEqual(detail)
  })

  it('defaults detail to empty object', () => {
    const err = new ApplicationError('generic', 'msg', 500)
    expect(err.detail).toEqual({})
  })
})

// Import once — no resetModules needed
import { applyToTask, ApplicationError as AppErr } from '../../services/tasks'

/** Duck-type check: vi.resetModules breaks instanceof across module boundaries */
function assertApplicationError(err: unknown, expectedType: string, expectedStatus: number) {
  expect(err).toBeTruthy()
  const e = err as { name: string; type: string; status: number; message: string }
  expect(e.name).toBe('ApplicationError')
  expect(e.type).toBe(expectedType)
  expect(e.status).toBe(expectedStatus)
}

describe('applyToTask error parsing', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('throws ApplicationError with type world_id_required for 403 world_id_orb_required', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: {
            error: 'world_id_orb_required',
            message: 'World ID Orb verification required',
            required_level: 'orb',
            current_level: null,
          },
        }),
        { status: 403, headers: { 'Content-Type': 'application/json' } }
      )
    ))

    try {
      await applyToTask({ taskId: 'task-1', executorId: 'exec-1' })
      expect.unreachable('Should have thrown')
    } catch (err) {
      assertApplicationError(err, 'world_id_required', 403)
    }
  })

  it('throws ApplicationError with type already_applied for 409', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: 'Already applied to this task' }),
        { status: 409, headers: { 'Content-Type': 'application/json' } }
      )
    ))

    try {
      await applyToTask({ taskId: 'task-1', executorId: 'exec-1' })
      expect.unreachable('Should have thrown')
    } catch (err) {
      assertApplicationError(err, 'already_applied', 409)
    }
  })

  it('throws ApplicationError with type generic for other errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: 'Internal server error' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    ))

    try {
      await applyToTask({ taskId: 'task-1', executorId: 'exec-1' })
      expect.unreachable('Should have thrown')
    } catch (err) {
      assertApplicationError(err, 'generic', 500)
    }
  })
})
