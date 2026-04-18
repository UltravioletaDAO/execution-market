/**
 * ErrorBoundary tests (Task 1.3 — SaaS Production Hardening).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ErrorBoundary } from '../ErrorBoundary'

// Silence React's `componentDidCatch` console.error during the "boom" test so
// test output stays clean. We restore the original afterEach.
const originalConsoleError = console.error

beforeEach(() => {
  console.error = vi.fn()
})

afterEach(() => {
  console.error = originalConsoleError
})

function Boom(): JSX.Element {
  throw new Error('boom')
}

function Ok(): JSX.Element {
  return <p>all good</p>
}

describe('ErrorBoundary', () => {
  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary>
        <Ok />
      </ErrorBoundary>
    )

    expect(screen.getByText('all good')).toBeInTheDocument()
  })

  it('renders fallback UI when a child throws', () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/algo salió mal/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /recargar la página/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ir al inicio/i })).toBeInTheDocument()
  })

  it('supports a custom fallback render prop', () => {
    render(
      <ErrorBoundary
        fallback={({ error }) => <div>custom: {error.message}</div>}
      >
        <Boom />
      </ErrorBoundary>
    )

    expect(screen.getByText('custom: boom')).toBeInTheDocument()
  })
})
