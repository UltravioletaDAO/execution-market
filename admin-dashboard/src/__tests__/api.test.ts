import { describe, it, expect, vi, beforeEach } from 'vitest'
import { adminFetch, adminGet, adminPost, API_BASE } from '../lib/api'

// ---------- global fetch mock ----------

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
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
    text: () => Promise.resolve(JSON.stringify(body)),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response
}

// ---------- tests ----------

beforeEach(() => {
  mockFetch.mockReset()
})

describe('adminFetch', () => {
  it('adds X-Admin-Key header', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true }))

    await adminFetch('/api/v1/test', 'my-secret-key')

    expect(mockFetch).toHaveBeenCalledOnce()
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toBe(`${API_BASE}/api/v1/test`)
    const headers = init.headers as Headers
    expect(headers.get('X-Admin-Key')).toBe('my-secret-key')
  })

  it('sets Content-Type to application/json when body is present', async () => {
    mockFetch.mockResolvedValue(jsonResponse({}))

    await adminFetch('/api/v1/test', 'key', {
      method: 'POST',
      body: JSON.stringify({ foo: 1 }),
    })

    const headers = mockFetch.mock.calls[0][1].headers as Headers
    expect(headers.get('Content-Type')).toBe('application/json')
  })
})

describe('adminGet', () => {
  it('returns parsed JSON on success', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ tasks: [] }))

    const result = await adminGet('/api/v1/tasks', 'key123')

    expect(result).toEqual({ tasks: [] })
  })

  it('appends query params', async () => {
    mockFetch.mockResolvedValue(jsonResponse({}))

    await adminGet('/api/v1/tasks', 'key', { status: 'published', limit: '10' })

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain('status=published')
    expect(url).toContain('limit=10')
  })

  it('throws on 401 (auth error)', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: 'Unauthorized' }, 401))

    await expect(adminGet('/test', 'bad-key')).rejects.toThrow('Unauthorized')
  })

  it('throws on 403 (forbidden)', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: 'Forbidden' }, 403))

    await expect(adminGet('/test', 'bad-key')).rejects.toThrow('Forbidden')
  })

  it('throws on 503 (maintenance)', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ message: 'Service Unavailable' }, 503))

    await expect(adminGet('/test', 'key')).rejects.toThrow('Service Unavailable')
  })

  it('throws generic error when response body is not JSON', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
    } as unknown as Response)

    await expect(adminGet('/test', 'key')).rejects.toThrow('Request failed: 500')
  })

  it('throws on network failure', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(adminGet('/test', 'key')).rejects.toThrow('Failed to fetch')
  })
})

describe('adminPost', () => {
  it('sends JSON body and returns parsed response', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ id: 'abc' }))

    const result = await adminPost('/api/v1/tasks', 'key', { title: 'Test' })

    expect(result).toEqual({ id: 'abc' })
    const [, init] = mockFetch.mock.calls[0]
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ title: 'Test' }))
  })

  it('throws on error status', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: 'Bad Request' }, 400))

    await expect(adminPost('/test', 'key', {})).rejects.toThrow('Bad Request')
  })
})
