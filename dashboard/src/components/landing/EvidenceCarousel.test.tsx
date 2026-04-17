/**
 * EvidenceCarousel unit tests.
 *
 * We mock useShowcaseData + useReducedMotion at the module boundary so the
 * tests stay focused on rendering contract:
 *   - loading        → skeleton
 *   - error          → null (section hidden)
 *   - < 5 items      → null (honest empty state)
 *   - ≥ 5 items      → rendered header + slides + live region
 *   - click slide    → opens modal
 *   - reduced motion → autoplay disabled on Embla init
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import type { ShowcaseEvidence, ShowcaseResponse } from '../../services/showcase'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseShowcaseData = vi.fn()
const mockUseReducedMotion = vi.fn()

vi.mock('../../hooks/useShowcaseData', () => ({
  useShowcaseData: (opts: unknown) => mockUseShowcaseData(opts),
}))

vi.mock('../../hooks/useReducedMotion', () => ({
  useReducedMotion: () => mockUseReducedMotion(),
}))

// Embla leans on viewport math that jsdom does not implement. A tiny stub
// keeps the tree renderable without actually scrolling.
const emblaApiStub = {
  on: vi.fn(),
  off: vi.fn(),
  selectedScrollSnap: vi.fn(() => 0),
  scrollPrev: vi.fn(),
  scrollNext: vi.fn(),
}
vi.mock('embla-carousel-react', () => ({
  default: () => [vi.fn(), emblaApiStub],
}))

// Autoplay is a factory that returns a plugin object with play/stop. We only
// need identity — EvidenceCarousel never inspects the plugin's internals.
vi.mock('embla-carousel-autoplay', () => ({
  default: vi.fn(() => ({ play: vi.fn(), stop: vi.fn(), reset: vi.fn() })),
}))

// Blurhash requires canvas, which jsdom fakes poorly. Stub decode.
vi.mock('blurhash', () => ({
  decode: vi.fn(() => new Uint8ClampedArray(32 * 40 * 4)),
}))

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeEvidence(id: string, overrides: Partial<ShowcaseEvidence> = {}): ShowcaseEvidence {
  return {
    id,
    taskTitle: `Task ${id}`,
    taskDescription: `Description for ${id}`,
    category: 'physical_presence',
    bountyUsd: 0.25,
    paymentToken: 'USDC',
    paymentNetwork: 'base',
    paidAt: '2026-04-16T12:00:00Z',
    completedAt: '2026-04-16T12:00:30Z',
    executor: {
      displayName: `worker-${id}`,
      avatarUrl: null,
      rating: 4.8,
    },
    evidence: {
      primaryImageUrl: `https://cdn.example.com/${id}.jpg`,
      imageCount: 1,
      blurhash: null,
      verification: {
        gpsVerified: true,
        exifVerified: true,
        timestampVerified: true,
        worldIdVerified: false,
      },
    },
    ...overrides,
  }
}

function makeResponse(n: number): ShowcaseResponse {
  return {
    items: Array.from({ length: n }, (_, i) => makeEvidence(`sub-${i}`)),
    nextCursor: null,
    generatedAt: '2026-04-16T12:01:00Z',
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

async function importComponent() {
  return (await import('./EvidenceCarousel')).default
}

describe('EvidenceCarousel', () => {
  beforeEach(() => {
    mockUseShowcaseData.mockReset()
    mockUseReducedMotion.mockReset()
    mockUseReducedMotion.mockReturnValue(false)
    emblaApiStub.on.mockClear()
    emblaApiStub.off.mockClear()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the skeleton while loading', async () => {
    mockUseShowcaseData.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    const EvidenceCarousel = await importComponent()
    const { container } = render(<EvidenceCarousel />)
    expect(screen.getByTestId('carousel-skeleton')).toBeTruthy()
    expect(container.querySelector('[data-testid="evidence-carousel"]')).toBeNull()
  })

  it('renders nothing when the query errors', async () => {
    mockUseShowcaseData.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    const EvidenceCarousel = await importComponent()
    const { container } = render(<EvidenceCarousel />)
    expect(container.firstChild).toBeNull()
  })

  it('hides itself when fewer than 5 items are returned (empty-state gate)', async () => {
    mockUseShowcaseData.mockReturnValue({
      data: makeResponse(4),
      isLoading: false,
      isError: false,
    })
    const EvidenceCarousel = await importComponent()
    const { container } = render(<EvidenceCarousel />)
    expect(container.firstChild).toBeNull()
  })

  it('renders header, slides, and a live region when data is present', async () => {
    mockUseShowcaseData.mockReturnValue({
      data: makeResponse(6),
      isLoading: false,
      isError: false,
    })
    const EvidenceCarousel = await importComponent()
    render(<EvidenceCarousel />)

    expect(screen.getByRole('region', { name: /verified evidence showcase/i })).toBeTruthy()
    expect(screen.getByText(/proof of work/i)).toBeTruthy()
    expect(screen.getByText(/paid for/i)).toBeTruthy()
    expect(screen.getAllByTestId('evidence-slide')).toHaveLength(6)
    expect(screen.getByText(/Slide 1 of 6/)).toBeTruthy()
  })

  it('opens the modal when a slide is clicked', async () => {
    mockUseShowcaseData.mockReturnValue({
      data: makeResponse(5),
      isLoading: false,
      isError: false,
    })
    const EvidenceCarousel = await importComponent()
    render(<EvidenceCarousel />)

    const firstSlideButton = screen.getAllByRole('button', { name: /open evidence/i })[0]
    fireEvent.click(firstSlideButton)

    expect(screen.getByRole('dialog')).toBeTruthy()
  })

  it('passes playOnInit=false to Autoplay when reduced motion is on', async () => {
    const Autoplay = (await import('embla-carousel-autoplay')).default as unknown as ReturnType<typeof vi.fn>
    mockUseReducedMotion.mockReturnValue(true)
    mockUseShowcaseData.mockReturnValue({
      data: makeResponse(5),
      isLoading: false,
      isError: false,
    })

    const EvidenceCarousel = await importComponent()
    render(<EvidenceCarousel />)

    const calls = Autoplay.mock.calls
    const lastCall = calls[calls.length - 1]?.[0] as { playOnInit?: boolean } | undefined
    expect(lastCall?.playOnInit).toBe(false)
  })
})
