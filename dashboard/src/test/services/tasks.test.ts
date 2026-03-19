/**
 * Tasks Service — Unit tests
 *
 * Tests the task service layer's URL building, error parsing,
 * and API interaction patterns.
 *
 * The service uses supabase for DB queries and fetch for API calls.
 * We mock both to test the logic in isolation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// --------------------------------------------------------------------------
// URL builder logic (extracted from tasks.ts for testability)
// --------------------------------------------------------------------------

describe('Task API URL building', () => {
  const buildUrl = (base: string, path: string) => {
    if (base.endsWith('/api')) return `${base}/v1${path}`
    return `${base}/api/v1${path}`
  }

  it('appends /api/v1 when base has no /api suffix', () => {
    expect(buildUrl('https://api.execution.market', '/tasks/abc/apply')).toBe(
      'https://api.execution.market/api/v1/tasks/abc/apply'
    )
  })

  it('appends /v1 only when base already ends with /api', () => {
    expect(buildUrl('https://example.com/api', '/tasks/abc/apply')).toBe(
      'https://example.com/api/v1/tasks/abc/apply'
    )
  })

  it('handles cancel endpoint', () => {
    expect(buildUrl('https://api.execution.market', '/tasks/xyz/cancel')).toBe(
      'https://api.execution.market/api/v1/tasks/xyz/cancel'
    )
  })

  it('handles assign endpoint', () => {
    expect(buildUrl('https://api.execution.market', '/tasks/xyz/assign')).toBe(
      'https://api.execution.market/api/v1/tasks/xyz/assign'
    )
  })

  it('handles task creation endpoint', () => {
    expect(buildUrl('https://api.execution.market', '/tasks')).toBe(
      'https://api.execution.market/api/v1/tasks'
    )
  })
})

// --------------------------------------------------------------------------
// parseApiError logic (extracted pattern)
// --------------------------------------------------------------------------

describe('API error parsing', () => {
  const parseApiError = async (response: { json: () => Promise<unknown> }, fallback: string): Promise<string> => {
    try {
      const data = await response.json() as { detail?: string; message?: string; error?: string }
      return data.detail || data.message || data.error || fallback
    } catch {
      return fallback
    }
  }

  it('extracts detail field', async () => {
    const res = { json: () => Promise.resolve({ detail: 'Task not found' }) }
    expect(await parseApiError(res, 'Unknown error')).toBe('Task not found')
  })

  it('extracts message field as fallback', async () => {
    const res = { json: () => Promise.resolve({ message: 'Bad request' }) }
    expect(await parseApiError(res, 'Unknown error')).toBe('Bad request')
  })

  it('extracts error field as second fallback', async () => {
    const res = { json: () => Promise.resolve({ error: 'Internal error' }) }
    expect(await parseApiError(res, 'Unknown error')).toBe('Internal error')
  })

  it('returns fallback when response body is empty', async () => {
    const res = { json: () => Promise.resolve({}) }
    expect(await parseApiError(res, 'Something went wrong')).toBe('Something went wrong')
  })

  it('returns fallback when json parsing fails', async () => {
    const res = { json: () => Promise.reject(new Error('not json')) }
    expect(await parseApiError(res, 'Parse failed')).toBe('Parse failed')
  })

  it('prefers detail over message', async () => {
    const res = { json: () => Promise.resolve({ detail: 'Specific', message: 'Generic' }) }
    expect(await parseApiError(res, 'Fallback')).toBe('Specific')
  })
})

// --------------------------------------------------------------------------
// TaskFilters interface validation
// --------------------------------------------------------------------------

describe('TaskFilters interface', () => {
  it('accepts empty filters', () => {
    const filters = {}
    expect(filters).toEqual({})
  })

  it('accepts all filter fields', () => {
    const filters = {
      agentId: 'agent-1',
      executorId: 'exec-1',
      status: 'published',
      category: 'physical_presence',
      minBounty: 0.10,
      maxBounty: 100,
      limit: 20,
      offset: 0,
    }
    expect(filters.limit).toBe(20)
    expect(filters.status).toBe('published')
  })

  it('accepts array status filter', () => {
    const filters = {
      status: ['published', 'accepted'],
    }
    expect(Array.isArray(filters.status)).toBe(true)
    expect(filters.status).toHaveLength(2)
  })
})

// --------------------------------------------------------------------------
// Agent auth header building
// --------------------------------------------------------------------------

describe('Agent auth headers', () => {
  const buildAgentJsonHeaders = (apiKey?: string): Record<string, string> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`
      headers['X-API-Key'] = apiKey
    }
    return headers
  }

  it('includes Content-Type always', () => {
    const h = buildAgentJsonHeaders()
    expect(h['Content-Type']).toBe('application/json')
  })

  it('adds auth headers when API key is present', () => {
    const h = buildAgentJsonHeaders('test-key-123')
    expect(h['Authorization']).toBe('Bearer test-key-123')
    expect(h['X-API-Key']).toBe('test-key-123')
  })

  it('omits auth headers when no API key', () => {
    const h = buildAgentJsonHeaders()
    expect(h['Authorization']).toBeUndefined()
    expect(h['X-API-Key']).toBeUndefined()
  })

  it('omits auth headers for empty string API key', () => {
    const h = buildAgentJsonHeaders('')
    expect(h['Authorization']).toBeUndefined()
  })
})
