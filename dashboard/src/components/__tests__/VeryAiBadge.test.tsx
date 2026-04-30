/**
 * VeryAiBadge tests (Phase 3 Task 3.2 — VeryAI Integration).
 *
 * Render-state matrix: level x size x showLabel.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VeryAiBadge } from '../VeryAiBadge'

describe('VeryAiBadge', () => {
  it('renders muted gray when level is null', () => {
    render(<VeryAiBadge level={null} />)
    const badge = screen.getByTestId('veryai-badge')
    expect(badge.className).toContain('text-gray-500')
    expect(badge.getAttribute('data-level')).toBe('none')
    expect(badge.getAttribute('title')).toBe('VeryAI Unverified')
  })

  it('renders black when level is palm_single', () => {
    render(<VeryAiBadge level="palm_single" />)
    const badge = screen.getByTestId('veryai-badge')
    expect(badge.className).toContain('text-black')
    expect(badge.getAttribute('data-level')).toBe('palm_single')
    expect(badge.getAttribute('title')).toBe('VeryAI Palm Verified')
  })

  it('renders filled (palm_dual) with stroke=0', () => {
    const { container } = render(<VeryAiBadge level="palm_dual" />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('fill')).toBe('currentColor')
    expect(svg.getAttribute('stroke-width')).toBe('0')
    expect(screen.getByTestId('veryai-badge').getAttribute('title')).toBe(
      'VeryAI Palm Dual Verified'
    )
  })

  it('renders outlined (palm_single) with fill=none', () => {
    const { container } = render(<VeryAiBadge level="palm_single" />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('fill')).toBe('none')
    expect(svg.getAttribute('stroke-width')).toBe('1.5')
  })

  it('honors size variants (sm/md/lg)', () => {
    const { rerender, container } = render(<VeryAiBadge level="palm_single" size="sm" />)
    expect(container.querySelector('svg')!.getAttribute('class')).toContain('w-4 h-4')
    rerender(<VeryAiBadge level="palm_single" size="md" />)
    expect(container.querySelector('svg')!.getAttribute('class')).toContain('w-5 h-5')
    rerender(<VeryAiBadge level="palm_single" size="lg" />)
    expect(container.querySelector('svg')!.getAttribute('class')).toContain('w-6 h-6')
  })

  it('shows label text when showLabel=true', () => {
    const { rerender } = render(<VeryAiBadge level="palm_dual" showLabel />)
    expect(screen.getByText('Palm 2×')).toBeInTheDocument()
    rerender(<VeryAiBadge level="palm_single" showLabel />)
    expect(screen.getByText('Palm')).toBeInTheDocument()
    rerender(<VeryAiBadge level={null} showLabel />)
    expect(screen.getByText('Unverified')).toBeInTheDocument()
  })

  it('hides label by default', () => {
    render(<VeryAiBadge level="palm_dual" />)
    expect(screen.queryByText('Palm 2×')).toBeNull()
  })
})
