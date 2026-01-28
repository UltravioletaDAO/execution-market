// ReputationCard component tests
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ReputationCard } from '../../components/profile/ReputationCard'
import type { ReputationData } from '../../hooks/useProfile'

describe('ReputationCard', () => {
  const mockReputation: ReputationData = {
    current_score: 85,
    total_tasks: 50,
    approved_tasks: 45,
    rejected_tasks: 3,
    disputed_tasks: 2,
    approval_rate: 90,
    history: [],
  }

  it('renders loading state', () => {
    render(
      <ReputationCard
        reputation={null}
        loading={true}
      />
    )

    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('renders reputation score correctly', () => {
    render(
      <ReputationCard
        reputation={mockReputation}
        loading={false}
      />
    )

    expect(screen.getByText('85')).toBeTruthy()
    expect(screen.getByText('/ 100')).toBeTruthy()
  })

  it('shows correct tier for high score', () => {
    const highScoreRep: ReputationData = {
      ...mockReputation,
      current_score: 92,
    }

    render(
      <ReputationCard
        reputation={highScoreRep}
        loading={false}
      />
    )

    expect(screen.getByText('Expert')).toBeTruthy()
  })

  it('shows correct tier for trusted score', () => {
    render(
      <ReputationCard
        reputation={mockReputation}
        loading={false}
      />
    )

    expect(screen.getByText('Trusted')).toBeTruthy()
  })

  it('displays task statistics', () => {
    render(
      <ReputationCard
        reputation={mockReputation}
        loading={false}
      />
    )

    expect(screen.getByText('50')).toBeTruthy() // total
    expect(screen.getByText('45')).toBeTruthy() // approved
    expect(screen.getByText('3')).toBeTruthy()  // rejected
  })

  it('shows approval rate', () => {
    render(
      <ReputationCard
        reputation={mockReputation}
        loading={false}
      />
    )

    expect(screen.getByText('90.0%')).toBeTruthy()
  })

  it('shows dispute warning when disputes exist', () => {
    render(
      <ReputationCard
        reputation={mockReputation}
        loading={false}
      />
    )

    expect(screen.getByText(/2.*disputed task/)).toBeTruthy()
  })

  it('does not show dispute warning when no disputes', () => {
    const noDisputesRep: ReputationData = {
      ...mockReputation,
      disputed_tasks: 0,
    }

    render(
      <ReputationCard
        reputation={noDisputesRep}
        loading={false}
      />
    )

    expect(screen.queryByText(/disputed task/)).toBeNull()
  })
})
