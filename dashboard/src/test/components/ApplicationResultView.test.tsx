import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ApplicationResultView } from '../../components/ApplicationResultView'
import type { ApplicationResultState } from '../../components/ApplicationResultView'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderResult(state: ApplicationResultState, props: Partial<Parameters<typeof ApplicationResultView>[0]> = {}) {
  const onClose = vi.fn()
  const onRetry = vi.fn()
  const result = render(
    <MemoryRouter>
      <ApplicationResultView
        state={state}
        worldIdThreshold={5}
        onClose={onClose}
        onRetry={onRetry}
        {...props}
      />
    </MemoryRouter>
  )
  return { ...result, onClose, onRetry }
}

describe('ApplicationResultView', () => {
  describe('success state', () => {
    it('renders success title and message', () => {
      renderResult('success')
      expect(screen.getByText('Application submitted!')).toBeTruthy()
      expect(screen.getByText(/Your application has been sent/)).toBeTruthy()
    })

    it('does not show World ID suggestion', () => {
      renderResult('success')
      expect(screen.queryByText(/Unlock higher-value/)).toBeNull()
    })

    it('has Close and View my tasks buttons', () => {
      renderResult('success')
      expect(screen.getByText('Close')).toBeTruthy()
      expect(screen.getByText('View my tasks')).toBeTruthy()
    })

    it('calls onClose when Close button clicked', () => {
      const { onClose } = renderResult('success')
      fireEvent.click(screen.getByText('Close'))
      expect(onClose).toHaveBeenCalledOnce()
    })

    it('navigates to /tasks when View my tasks clicked', () => {
      const { onClose } = renderResult('success')
      fireEvent.click(screen.getByText('View my tasks'))
      expect(onClose).toHaveBeenCalledOnce()
      expect(mockNavigate).toHaveBeenCalledWith('/tasks', { state: { tab: 'mine' } })
    })
  })

  describe('success_suggest_worldid state', () => {
    it('renders success title AND World ID suggestion', () => {
      renderResult('success_suggest_worldid')
      expect(screen.getByText('Application submitted!')).toBeTruthy()
      expect(screen.getByText('Unlock higher-value tasks')).toBeTruthy()
    })

    it('shows suggestion message with threshold', () => {
      renderResult('success_suggest_worldid', { worldIdThreshold: 5 })
      // i18next fallback may render interpolation placeholder or actual value
      expect(screen.getByText(/or more/)).toBeTruthy()
    })

    it('has Verify now link', () => {
      renderResult('success_suggest_worldid')
      expect(screen.getByText('Verify now')).toBeTruthy()
    })

    it('navigates to /profile when Verify now clicked', () => {
      renderResult('success_suggest_worldid')
      fireEvent.click(screen.getByText('Verify now'))
      expect(mockNavigate).toHaveBeenCalledWith('/profile')
    })
  })

  describe('blocked_worldid state', () => {
    it('renders blocked title', () => {
      renderResult('blocked_worldid')
      expect(screen.getByText('Identity verification required')).toBeTruthy()
    })

    it('shows blocked message with threshold', () => {
      renderResult('blocked_worldid', { worldIdThreshold: 5 })
      expect(screen.getByText(/or more require World ID/)).toBeTruthy()
    })

    it('shows explainer text', () => {
      renderResult('blocked_worldid')
      expect(screen.getByText(/World ID verifies you are a unique person/)).toBeTruthy()
    })

    it('shows threshold badge', () => {
      renderResult('blocked_worldid', { worldIdThreshold: 5 })
      expect(screen.getByText(/Required for tasks/)).toBeTruthy()
    })

    it('has Cancel and Verify with World ID buttons', () => {
      renderResult('blocked_worldid')
      expect(screen.getByText('Cancel')).toBeTruthy()
      expect(screen.getByText('Verify with World ID')).toBeTruthy()
    })

    it('navigates to /profile when Verify clicked', () => {
      const { onClose } = renderResult('blocked_worldid')
      fireEvent.click(screen.getByText('Verify with World ID'))
      expect(onClose).toHaveBeenCalledOnce()
      expect(mockNavigate).toHaveBeenCalledWith('/profile')
    })

    it('renders World ID logo', () => {
      renderResult('blocked_worldid')
      const logos = screen.getAllByAltText('World ID')
      expect(logos.length).toBeGreaterThanOrEqual(1)
    })
  })

  describe('already_applied state', () => {
    it('renders already applied title and message', () => {
      renderResult('already_applied')
      expect(screen.getByText('Already applied')).toBeTruthy()
      expect(screen.getByText(/already applied to this task/)).toBeTruthy()
    })

    it('has Close and View my tasks buttons', () => {
      renderResult('already_applied')
      expect(screen.getByText('Close')).toBeTruthy()
      expect(screen.getByText('View my tasks')).toBeTruthy()
    })
  })

  describe('error state', () => {
    it('renders error title and default message', () => {
      renderResult('error')
      expect(screen.getByText('Something went wrong')).toBeTruthy()
      expect(screen.getByText(/Could not submit your application/)).toBeTruthy()
    })

    it('renders custom error message when provided', () => {
      renderResult('error', { errorMessage: 'Server is down' })
      expect(screen.getByText('Server is down')).toBeTruthy()
    })

    it('has Retry button that calls onRetry', () => {
      const { onRetry } = renderResult('error')
      fireEvent.click(screen.getByText('Retry'))
      expect(onRetry).toHaveBeenCalledOnce()
    })

    it('has Close button', () => {
      const { onClose } = renderResult('error')
      fireEvent.click(screen.getByText('Close'))
      expect(onClose).toHaveBeenCalledOnce()
    })
  })
})
