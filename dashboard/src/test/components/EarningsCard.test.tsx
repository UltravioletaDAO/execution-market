// EarningsCard component tests — read-only lifetime earnings (ADR-001)
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EarningsCard } from '../../components/profile/EarningsCard'
import type { EarningsData } from '../../hooks/useProfile'

describe('EarningsCard', () => {
  const mockEarnings: EarningsData = {
    balance_usdc: 125.50,
    total_earned_usdc: 1500.00,
    total_withdrawn_usdc: 1374.50,
    pending_earnings_usdc: 45.00,
    this_month_usdc: 250.00,
    last_month_usdc: 200.00,
  }

  it('renders loading state', () => {
    render(<EarningsCard earnings={null} loading={true} />)
    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('renders lifetime earnings as hero number', () => {
    render(<EarningsCard earnings={mockEarnings} loading={false} />)

    expect(screen.getByText('$1500.00')).toBeTruthy()
    expect(screen.getByText(/\+\$45\.00/)).toBeTruthy()
    expect(screen.getByText('$250.00')).toBeTruthy()
    expect(screen.getByText('$200.00')).toBeTruthy()
  })

  it('shows positive month-over-month change', () => {
    render(<EarningsCard earnings={mockEarnings} loading={false} />)
    expect(screen.getByText('+25%')).toBeTruthy()
  })

  it('does not render a Withdraw button (funds flow direct on-chain per ADR-001)', () => {
    render(<EarningsCard earnings={mockEarnings} loading={false} />)
    expect(screen.queryByText(/withdraw/i)).toBeNull()
  })
})
