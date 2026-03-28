import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Settings from '../pages/Settings'

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

const MOCK_CONFIG = {
  fees: {
    platform_fee_pct: 0.13,
    partial_release_pct: 0.30,
    min_fee_usd: 0.01,
    instant_payment_max_usd: 5,
    instant_payment_min_reputation: 90,
  },
  limits: {
    min_usd: 0.01,
    max_usd: 10000,
    max_resubmissions: 3,
    max_active_tasks_per_agent: 100,
    max_applications_per_task: 50,
  },
  timing: {
    approval_hours: 48,
    task_default_hours: 24,
    auto_release_on_timeout: true,
  },
  features: {
    disputes_enabled: true,
    reputation_enabled: true,
    auto_matching_enabled: false,
    partial_release_enabled: true,
  },
  payments: {
    supported_networks: ['base', 'ethereum', 'polygon'],
    supported_tokens: ['USDC'],
    preferred_network: 'base',
  },
}

function renderSettings(adminKey = 'test-key') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <Settings adminKey={adminKey} />
    </QueryClientProvider>,
  )
}

// ---------- setup ----------

beforeEach(() => {
  mockFetch.mockReset()
})

// ---------- tests ----------

describe('Settings — Loading & Display', () => {
  it('shows loading state initially', () => {
    // Never resolve fetch so it stays loading
    mockFetch.mockReturnValue(new Promise(() => {}))
    renderSettings()
    expect(screen.getByText('Loading configuration...')).toBeInTheDocument()
  })

  it('displays config values after loading', async () => {
    mockFetch.mockResolvedValue(jsonResponse(MOCK_CONFIG))

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument()
    })

    // Check fee section shows platform fee as percentage (13%)
    expect(screen.getByText('Platform Fee')).toBeInTheDocument()
    // Check payment networks are displayed (use getAllByText since "base" appears in both networks list and preferred network)
    expect(screen.getAllByText('base').length).toBeGreaterThan(0)
    expect(screen.getByText('ethereum')).toBeInTheDocument()
    expect(screen.getByText('polygon')).toBeInTheDocument()
    // Check tokens
    expect(screen.getByText('USDC')).toBeInTheDocument()
  })

  it('shows error on load failure', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: 'Unauthorized' }, 401))

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText(/Failed to load configuration/)).toBeInTheDocument()
    })
  })
})

describe('Settings — Edit Flow', () => {
  it('clicking Edit shows input field and Save/Cancel buttons', async () => {
    mockFetch.mockResolvedValue(jsonResponse(MOCK_CONFIG))

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument()
    })

    // Find any Edit button and click it
    const editButtons = screen.getAllByText('Edit')
    fireEvent.click(editButtons[0])

    // Should show Save and Cancel buttons
    expect(screen.getByText('Save')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Reason for change (optional)')).toBeInTheDocument()
  })

  it('Cancel reverts to display mode', async () => {
    mockFetch.mockResolvedValue(jsonResponse(MOCK_CONFIG))

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Edit')
    fireEvent.click(editButtons[0])

    expect(screen.getByText('Save')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Cancel'))

    // Save should be gone, Edit should be back
    expect(screen.queryByText('Save')).not.toBeInTheDocument()
  })

  it('Save triggers PUT API call with value and reason', async () => {
    // First call: load config. Subsequent calls: save.
    mockFetch
      .mockResolvedValueOnce(jsonResponse(MOCK_CONFIG)) // GET config
      .mockResolvedValueOnce(jsonResponse({ ok: true })) // PUT save
      .mockResolvedValueOnce(jsonResponse(MOCK_CONFIG)) // refetch after invalidate

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument()
    })

    // Click first Edit button
    const editButtons = screen.getAllByText('Edit')
    fireEvent.click(editButtons[0])

    // Fill in reason
    const reasonInput = screen.getByPlaceholderText('Reason for change (optional)')
    fireEvent.change(reasonInput, { target: { value: 'test reason' } })

    // Click Save
    fireEvent.click(screen.getByText('Save'))

    await waitFor(() => {
      // The PUT call should be the second fetch call
      expect(mockFetch.mock.calls.length).toBeGreaterThanOrEqual(2)
      const putCall = mockFetch.mock.calls[1]
      const [url, init] = putCall
      expect(url).toContain('/api/v1/admin/config/')
      expect(init.method).toBe('PUT')
      const body = JSON.parse(init.body)
      expect(body.reason).toBe('test reason')
    })
  })
})

describe('Settings — Config Sections', () => {
  it('renders all config section headings', async () => {
    mockFetch.mockResolvedValue(jsonResponse(MOCK_CONFIG))

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument()
    })

    // All section titles
    expect(screen.getByText('Fees')).toBeInTheDocument()
    expect(screen.getByText('Bounty Limits')).toBeInTheDocument()
    expect(screen.getByText('Tier-Based Fees')).toBeInTheDocument()
    expect(screen.getByText('Timeouts')).toBeInTheDocument()
    expect(screen.getByText('Limits')).toBeInTheDocument()
    expect(screen.getByText('Feature Flags')).toBeInTheDocument()
    expect(screen.getByText('Payment Networks')).toBeInTheDocument()
  })

  it('displays boolean config values as Yes/No', async () => {
    mockFetch.mockResolvedValue(jsonResponse(MOCK_CONFIG))

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument()
    })

    // auto_release_on_timeout is true -> should show "Yes"
    const yesElements = screen.getAllByText('Yes')
    expect(yesElements.length).toBeGreaterThan(0)

    // auto_matching_enabled is false -> should show "No"
    const noElements = screen.getAllByText('No')
    expect(noElements.length).toBeGreaterThan(0)
  })
})

describe('Settings — Toolbar', () => {
  it('renders Export and Import buttons', async () => {
    mockFetch.mockResolvedValue(jsonResponse(MOCK_CONFIG))

    renderSettings()

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument()
    })

    expect(screen.getByText('Export Config')).toBeInTheDocument()
    expect(screen.getByText('Import Config')).toBeInTheDocument()
  })
})
