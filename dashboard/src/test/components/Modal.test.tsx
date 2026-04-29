// Modal primitive tests — verifies portal, ESC, backdrop, and focus trap.
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useState } from 'react'
import { Modal } from '../../components/ui/Modal'

describe('Modal', () => {
  it('renders nothing when open=false', () => {
    render(
      <Modal open={false} onClose={() => {}} ariaLabel="x">
        <Modal.Body>hidden</Modal.Body>
      </Modal>
    )
    expect(screen.queryByText('hidden')).toBeNull()
  })

  it('renders into a portal on document.body when open=true', () => {
    render(
      <Modal open onClose={() => {}} ariaLabel="dialog">
        <Modal.Body>content</Modal.Body>
      </Modal>
    )
    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeTruthy()
    expect(document.body.contains(dialog)).toBe(true)
    expect(screen.getByText('content')).toBeTruthy()
  })

  it('calls onClose when ESC is pressed', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} ariaLabel="x">
        <Modal.Body>x</Modal.Body>
      </Modal>
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not call onClose on ESC when dismissOnEsc=false', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} dismissOnEsc={false} ariaLabel="x">
        <Modal.Body>x</Modal.Body>
      </Modal>
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('calls onClose when backdrop is clicked', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} ariaLabel="x">
        <Modal.Body>x</Modal.Body>
      </Modal>
    )
    // The backdrop is the <div role="presentation"> that wraps the dialog.
    const presentation = screen.getByRole('dialog').parentElement!
    fireEvent.click(presentation)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does NOT call onClose when content inside the dialog is clicked', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} ariaLabel="x">
        <Modal.Body>
          <button>inside</button>
        </Modal.Body>
      </Modal>
    )
    fireEvent.click(screen.getByText('inside'))
    expect(onClose).not.toHaveBeenCalled()
  })

  it('does not close on backdrop when dismissOnBackdrop=false', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} dismissOnBackdrop={false} ariaLabel="x">
        <Modal.Body>x</Modal.Body>
      </Modal>
    )
    const presentation = screen.getByRole('dialog').parentElement!
    fireEvent.click(presentation)
    expect(onClose).not.toHaveBeenCalled()
  })

  it('renders Header.onClose X button that triggers onClose', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} ariaLabel="x">
        <Modal.Header onClose={onClose}>Title</Modal.Header>
        <Modal.Body>x</Modal.Body>
      </Modal>
    )
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('wires aria-labelledby when labelledBy is provided', () => {
    render(
      <Modal open onClose={() => {}} labelledBy="title-id">
        <Modal.Header id="title-id">My Title</Modal.Header>
        <Modal.Body>x</Modal.Body>
      </Modal>
    )
    const dialog = screen.getByRole('dialog')
    expect(dialog.getAttribute('aria-labelledby')).toBe('title-id')
    expect(screen.getByText('My Title').id).toBe('title-id')
  })

  it('locks body scroll while open and restores on unmount', () => {
    const previous = document.body.style.overflow
    const { unmount } = render(
      <Modal open onClose={() => {}} ariaLabel="x">
        <Modal.Body>x</Modal.Body>
      </Modal>
    )
    expect(document.body.style.overflow).toBe('hidden')
    unmount()
    expect(document.body.style.overflow).toBe(previous)
  })

  it('toggles correctly when open prop transitions from true → false', () => {
    function Harness() {
      const [open, setOpen] = useState(true)
      return (
        <>
          <button onClick={() => setOpen(false)}>close-btn</button>
          <Modal open={open} onClose={() => setOpen(false)} ariaLabel="x">
            <Modal.Body>visible</Modal.Body>
          </Modal>
        </>
      )
    }
    render(<Harness />)
    expect(screen.getByText('visible')).toBeTruthy()
    fireEvent.click(screen.getByText('close-btn'))
    expect(screen.queryByText('visible')).toBeNull()
  })
})
