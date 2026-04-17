import { useEffect, useCallback, useRef } from 'react'
import { safeSrc } from '../lib/safeHref'

interface EvidenceModalProps {
  imageUrl: string
  alt: string
  onClose: () => void
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export function EvidenceModal({ imageUrl, alt, onClose }: EvidenceModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const openerRef = useRef<Element | null>(null)

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !dialogRef.current) return

      // Focus trap — cycle Tab/Shift-Tab inside the dialog.
      const focusables = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      ).filter((el) => !el.hasAttribute('disabled') && el.offsetParent !== null)

      if (focusables.length === 0) {
        event.preventDefault()
        return
      }

      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      const active = document.activeElement as HTMLElement | null

      if (event.shiftKey) {
        if (active === first || !dialogRef.current.contains(active)) {
          event.preventDefault()
          last.focus()
        }
      } else if (active === last) {
        event.preventDefault()
        first.focus()
      }
    },
    [onClose]
  )

  useEffect(() => {
    openerRef.current = document.activeElement
    closeButtonRef.current?.focus()

    document.addEventListener('keydown', handleKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow

      // Return focus to the element that opened the modal.
      const opener = openerRef.current as HTMLElement | null
      if (opener && typeof opener.focus === 'function' && document.contains(opener)) {
        opener.focus()
      }
    }
  }, [handleKeyDown])

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={alt}
    >
      {/* Close button */}
      <button
        ref={closeButtonRef}
        onClick={onClose}
        className="absolute top-4 right-4 z-10 p-2 text-white/80 hover:text-white transition-colors"
        aria-label="Close"
      >
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      {/* Image — stop propagation so clicking the image does not close the modal */}
      <img
        src={safeSrc(imageUrl)}
        alt={alt}
        className="max-h-[90vh] max-w-[90vw] object-contain"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  )
}
