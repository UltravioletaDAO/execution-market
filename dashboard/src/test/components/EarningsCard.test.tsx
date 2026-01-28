// EarningsCard component tests
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
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
    render(
      <EarningsCard
        earnings={null}
        loading={true}
        onWithdraw={() => {}}
      />
    )

    // Should show skeleton/loading state
    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('renders earnings data correctly', () => {
    render(
      <EarningsCard
        earnings={mockEarnings}
        loading={false}
        onWithdraw={() => {}}
      />
    )

    // Should show balance
    expect(screen.getByText('$125.50')).toBeTruthy()

    // Should show pending
    expect(screen.getByText(/\+\$45\.00/)).toBeTruthy()

    // Should show total earned
    expect(screen.getByText('$1500.00')).toBeTruthy()

    // Should show this month
    expect(screen.getByText('$250.00')).toBeTruthy()
  })

  it('shows positive month-over-month change', () => {
    render(
      <EarningsCard
        earnings={mockEarnings}
        loading={false}
        onWithdraw={() => {}}
      />
    )

    // 250 vs 200 = +25%
    expect(screen.getByText('+25%')).toBeTruthy()
  })

  it('calls onWithdraw when button clicked', () => {
    const onWithdraw = vi.fn()

    render(
      <EarningsCard
        earnings={mockEarnings}
        loading={false}
        onWithdraw={onWithdraw}
      />
    )

    const withdrawButton = screen.getByText('Withdraw Funds')
    fireEvent.click(withdrawButton)

    expect(onWithdraw).toHaveBeenCalled()
  })

  it('disables withdraw button when balance is 0', () => {
    const zeroBalanceEarnings: EarningsData = {
      ...mockEarnings,
      balance_usdc: 0,
    }

    render(
      <EarningsCard
        earnings={zeroBalanceEarnings}
        loading={false}
        onWithdraw={() => {}}
      />
    )

    const withdrawButton = screen.getByText('Withdraw Funds')
    expect(withdrawButton).toBeDisabled()
  })
})
