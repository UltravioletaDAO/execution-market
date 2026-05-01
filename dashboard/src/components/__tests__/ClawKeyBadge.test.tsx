/**
 * ClawKeyBadge tests (Phase 4 Task 4.4 — VeryAI/ClawKey Integration).
 *
 * Render-state matrix: verified flag x humanId presence x size x showLabel.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ClawKeyBadge } from '../ClawKeyBadge'

describe('ClawKeyBadge', () => {
  it('renders muted gray when verified is null', () => {
    render(<ClawKeyBadge verified={null} />)
    const badge = screen.getByTestId('clawkey-badge')
    expect(badge.className).toContain('text-gray-500')
    expect(badge.getAttribute('data-verified')).toBe('false')
    expect(badge.getAttribute('title')).toBe('ClawKey KYA — not verified')
  })

  it('renders muted gray when verified is false', () => {
    render(<ClawKeyBadge verified={false} />)
    const badge = screen.getByTestId('clawkey-badge')
    expect(badge.className).toContain('text-gray-500')
    expect(badge.getAttribute('data-verified')).toBe('false')
  })

  it('renders solid black when verified is true', () => {
    const { container } = render(<ClawKeyBadge verified={true} />)
    const badge = screen.getByTestId('clawkey-badge')
    expect(badge.className).toContain('text-black')
    expect(badge.getAttribute('data-verified')).toBe('true')
    expect(badge.getAttribute('title')).toBe('ClawKey KYA Verified')

    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('fill')).toBe('currentColor')
    expect(svg.getAttribute('stroke-width')).toBe('0')
  })

  it('renders outlined (verified=false) with fill=none and stroke=1.5', () => {
    const { container } = render(<ClawKeyBadge verified={false} />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('fill')).toBe('none')
    expect(svg.getAttribute('stroke-width')).toBe('1.5')
  })

  it('truncates long humanIds in the tooltip', () => {
    render(
      <ClawKeyBadge
        verified={true}
        humanId="hum-abcdef-very-long-binding-id"
      />
    )
    const badge = screen.getByTestId('clawkey-badge')
    // Truncated to first 10 chars + ellipsis
    expect(badge.getAttribute('title')).toBe('ClawKey KYA Verified — hum-abcdef…')
  })

  it('shows full humanId when shorter than truncation threshold', () => {
    render(<ClawKeyBadge verified={true} humanId="hum-short" />)
    const badge = screen.getByTestId('clawkey-badge')
    expect(badge.getAttribute('title')).toBe('ClawKey KYA Verified — hum-short')
  })

  it('omits humanId from tooltip when not provided', () => {
    render(<ClawKeyBadge verified={true} />)
    const badge = screen.getByTestId('clawkey-badge')
    expect(badge.getAttribute('title')).toBe('ClawKey KYA Verified')
  })

  it('honors size variants (sm/md/lg)', () => {
    const { rerender, container } = render(
      <ClawKeyBadge verified={true} size="sm" />
    )
    expect(container.querySelector('svg')!.getAttribute('class')).toContain('w-4 h-4')
    rerender(<ClawKeyBadge verified={true} size="md" />)
    expect(container.querySelector('svg')!.getAttribute('class')).toContain('w-5 h-5')
    rerender(<ClawKeyBadge verified={true} size="lg" />)
    expect(container.querySelector('svg')!.getAttribute('class')).toContain('w-6 h-6')
  })

  it('shows label text when showLabel=true', () => {
    const { rerender } = render(<ClawKeyBadge verified={true} showLabel />)
    expect(screen.getByText('KYA')).toBeInTheDocument()
    rerender(<ClawKeyBadge verified={false} showLabel />)
    expect(screen.getByText('Unverified')).toBeInTheDocument()
  })

  it('hides label by default', () => {
    render(<ClawKeyBadge verified={true} />)
    expect(screen.queryByText('KYA')).toBeNull()
  })
})
