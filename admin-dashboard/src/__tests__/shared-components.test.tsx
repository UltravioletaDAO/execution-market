import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { StatusBadge, ToggleSwitch, ConfirmModal } from '../components/shared'

// ---------- StatusBadge ----------

describe('StatusBadge', () => {
  it('renders the status text', () => {
    const { container } = render(<StatusBadge status="published" />)
    expect(container.textContent).toContain('published')
  })

  it('renders with task variant', () => {
    const { container } = render(<StatusBadge status="completed" variant="task" />)
    expect(container.textContent).toContain('completed')
  })

  it('renders with payment variant', () => {
    const { container } = render(<StatusBadge status="release" variant="payment" />)
    expect(container.textContent).toContain('release')
  })

  it('falls back to default for unknown status', () => {
    const { container } = render(<StatusBadge status="unknown_thing" />)
    expect(container.textContent).toContain('unknown')
  })
})

// ---------- ToggleSwitch ----------

describe('ToggleSwitch', () => {
  it('renders with correct aria-checked when off', () => {
    render(<ToggleSwitch enabled={false} onChange={() => {}} />)
    const toggle = screen.getByRole('switch')
    expect(toggle).toHaveAttribute('aria-checked', 'false')
  })

  it('renders with correct aria-checked when on', () => {
    render(<ToggleSwitch enabled={true} onChange={() => {}} />)
    const toggle = screen.getByRole('switch')
    expect(toggle).toHaveAttribute('aria-checked', 'true')
  })

  it('calls onChange with toggled value on click', () => {
    const onChange = vi.fn()
    render(<ToggleSwitch enabled={false} onChange={onChange} />)

    fireEvent.click(screen.getByRole('switch'))
    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('calls onChange with false when currently enabled', () => {
    const onChange = vi.fn()
    render(<ToggleSwitch enabled={true} onChange={onChange} />)

    fireEvent.click(screen.getByRole('switch'))
    expect(onChange).toHaveBeenCalledWith(false)
  })

  it('does not call onChange when disabled', () => {
    const onChange = vi.fn()
    render(<ToggleSwitch enabled={false} onChange={onChange} disabled />)

    fireEvent.click(screen.getByRole('switch'))
    expect(onChange).not.toHaveBeenCalled()
  })

  it('applies aria-label', () => {
    render(<ToggleSwitch enabled={false} onChange={() => {}} label="Enable feature" />)
    expect(screen.getByRole('switch')).toHaveAttribute('aria-label', 'Enable feature')
  })
})

// ---------- ConfirmModal ----------

describe('ConfirmModal', () => {
  const defaultProps = {
    isOpen: true,
    title: 'Delete Task',
    message: 'Are you sure?',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  }

  it('renders nothing when closed', () => {
    render(<ConfirmModal {...defaultProps} isOpen={false} />)
    expect(screen.queryByText('Delete Task')).not.toBeInTheDocument()
  })

  it('renders title and message when open', () => {
    render(<ConfirmModal {...defaultProps} />)
    expect(screen.getByText('Delete Task')).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
  })

  it('shows default button labels', () => {
    render(<ConfirmModal {...defaultProps} />)
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('shows custom button labels', () => {
    render(<ConfirmModal {...defaultProps} confirmLabel="Yes, delete" cancelLabel="No, keep" />)
    expect(screen.getByText('Yes, delete')).toBeInTheDocument()
    expect(screen.getByText('No, keep')).toBeInTheDocument()
  })

  it('calls onConfirm when confirm button is clicked', () => {
    const onConfirm = vi.fn()
    render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByText('Confirm'))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn()
    render(<ConfirmModal {...defaultProps} onCancel={onCancel} />)

    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledOnce()
  })
})
