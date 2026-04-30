/**
 * ApplicationResultView — covers the tier-aware result states added by
 * Phase 3 Task 3.4 (VeryAI integration). The legacy states (success,
 * already_applied, error, blocked_worldid) are covered indirectly by
 * the application flow; these tests pin down the new T1 dual-CTA branch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    // Echo fallback so the assertions don't depend on a real i18n bundle.
    t: (_key: string, fallback?: string | object, vars?: Record<string, unknown>) => {
      if (typeof fallback === 'string') {
        if (!vars) return fallback
        return fallback.replace(/\{\{(\w+)\}\}/g, (_, k) => String(vars[k] ?? ''))
      }
      return _key
    },
  }),
}))

import { ApplicationResultView } from '../ApplicationResultView'

afterEach(() => {
  cleanup()
})

const renderView = (props: Partial<Parameters<typeof ApplicationResultView>[0]> = {}) =>
  render(
    <MemoryRouter>
      <ApplicationResultView
        state="blocked_t1_dual"
        veryAiFloor={50}
        worldIdThreshold={500}
        onClose={vi.fn()}
        {...props}
      />
    </MemoryRouter>,
  )

describe('ApplicationResultView — blocked_t1_dual', () => {
  beforeEach(() => {})

  it('renders both Orb and palm CTAs side-by-side', () => {
    renderView()
    expect(screen.getByText(/Verify with Orb/i)).toBeInTheDocument()
    expect(screen.getByText(/Verify with palm/i)).toBeInTheDocument()
  })

  it('shows the T1 band thresholds in the message', () => {
    renderView({ veryAiFloor: 50, worldIdThreshold: 500 })
    expect(screen.getByText(/\$50/)).toBeInTheDocument()
    expect(screen.getByText(/\$500/)).toBeInTheDocument()
  })

  it('clicking either CTA calls onClose', () => {
    const onClose = vi.fn()
    renderView({ onClose })
    fireEvent.click(screen.getByText(/Verify with Orb/i))
    expect(onClose).toHaveBeenCalledTimes(1)
    onClose.mockClear()
    // Second render to test palm independently (closing unmounts the modal).
    cleanup()
    renderView({ onClose })
    fireEvent.click(screen.getByText(/Verify with palm/i))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('cancel button at the bottom also closes', () => {
    const onClose = vi.fn()
    renderView({ onClose })
    fireEvent.click(screen.getByText(/^Cancel$/i))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

describe('ApplicationResultView — other states still render', () => {
  it('blocked_worldid renders single Orb CTA only (no palm)', () => {
    render(
      <MemoryRouter>
        <ApplicationResultView
          state="blocked_worldid"
          worldIdThreshold={500}
          onClose={vi.fn()}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Verify with World ID/i)).toBeInTheDocument()
    expect(screen.queryByText(/Verify with palm/i)).toBeNull()
  })

  it('error state renders the provided error message', () => {
    render(
      <MemoryRouter>
        <ApplicationResultView
          state="error"
          errorMessage="Custom failure"
          onClose={vi.fn()}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('Custom failure')).toBeInTheDocument()
  })
})
