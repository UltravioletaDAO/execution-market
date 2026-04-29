/**
 * Modal — Compound primitive for dialog windows.
 *
 * API:
 *   <Modal open onClose size="md|lg|xl|2xl" labelledBy="title-id">
 *     <Modal.Header onClose={onClose}>Title</Modal.Header>
 *     <Modal.Body>...content...</Modal.Body>
 *     <Modal.Footer>...buttons...</Modal.Footer>
 *   </Modal>
 *
 * Behavior:
 *   - Renders into document.body via React portal.
 *   - Locks body scroll while open.
 *   - ESC closes (unless `dismissOnEsc={false}`).
 *   - Click on backdrop closes (unless `dismissOnBackdrop={false}`).
 *   - Focus is trapped inside the dialog — Tab cycles only within.
 *   - Returns focus to the previously-focused element on close.
 *
 * Replaces the duplicated focus-trap + backdrop + sticky-header copy across
 * 8 modals. See MASTER_PLAN_UI_UX_POLISH_2026-04-28.md Task 2.3.
 */

import {
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface ModalProps {
  /** Whether the modal is visible. When false, nothing is rendered. */
  open: boolean;
  /** Called when the modal requests to close (ESC, backdrop, X button). */
  onClose: () => void;
  /** Size variant — controls max-width of the dialog container. */
  size?: ModalSize;
  /** id of the element that labels the dialog (passed to aria-labelledby). */
  labelledBy?: string;
  /** Fallback aria-label when `labelledBy` is not provided. */
  ariaLabel?: string;
  /** Disable ESC-to-close. */
  dismissOnEsc?: boolean;
  /** Disable click-outside-to-close. */
  dismissOnBackdrop?: boolean;
  /** Optional class for the dialog container. */
  className?: string;
  /** Modal content — typically Header + Body + Footer subcomponents. */
  children: ReactNode;
}

// ---------------------------------------------------------------------------
// Size map
// ---------------------------------------------------------------------------

const sizeClasses: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  '2xl': 'max-w-6xl',
};

// ---------------------------------------------------------------------------
// Focus-trap helper
// ---------------------------------------------------------------------------

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function getFocusables(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute('disabled') && el.offsetParent !== null
  );
}

// ---------------------------------------------------------------------------
// Modal (root)
// ---------------------------------------------------------------------------

export function Modal({
  open,
  onClose,
  size = 'md',
  labelledBy,
  ariaLabel,
  dismissOnEsc = true,
  dismissOnBackdrop = true,
  className,
  children,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<Element | null>(null);

  // Keyboard handler (ESC + Tab focus trap)
  const handleKeyDown = useCallback(
    (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape' && dismissOnEsc) {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusables = getFocusables(dialogRef.current);
      if (focusables.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (event.shiftKey) {
        if (active === first || !dialogRef.current.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last) {
        event.preventDefault();
        first.focus();
      }
    },
    [onClose, dismissOnEsc]
  );

  // Mount effects: scroll lock + focus capture/restore + key listener
  useEffect(() => {
    if (!open) return;

    openerRef.current = document.activeElement;

    // Move focus into the dialog (first focusable, or the dialog itself).
    const focusInside = () => {
      if (!dialogRef.current) return;
      const focusables = getFocusables(dialogRef.current);
      if (focusables.length > 0) {
        focusables[0].focus();
      } else {
        dialogRef.current.focus();
      }
    };
    // Defer one frame so any portal/render is committed.
    const raf = requestAnimationFrame(focusInside);

    document.addEventListener('keydown', handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;

      const opener = openerRef.current as HTMLElement | null;
      if (opener && typeof opener.focus === 'function' && document.contains(opener)) {
        opener.focus();
      }
    };
  }, [open, handleKeyDown]);

  if (!open) return null;
  if (typeof document === 'undefined') return null;

  const handleBackdropClick = () => {
    if (dismissOnBackdrop) onClose();
  };

  // Stop bubbling so clicks inside the dialog don't trigger backdrop close.
  const stopPropagation = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
      role="presentation"
    >
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-hidden="true"
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-label={!labelledBy ? ariaLabel : undefined}
        tabIndex={-1}
        onClick={stopPropagation}
        className={cn(
          'relative bg-white dark:bg-zinc-900',
          'rounded-2xl shadow-2xl',
          'w-full max-h-[90vh] overflow-hidden flex flex-col',
          'focus:outline-none',
          sizeClasses[size],
          className
        )}
      >
        {children}
      </div>
    </div>,
    document.body
  );
}

// ---------------------------------------------------------------------------
// Modal.Header
// ---------------------------------------------------------------------------

export interface ModalHeaderProps {
  /** When provided, renders an X close button that calls this. */
  onClose?: () => void;
  /** id used for aria-labelledby on the parent Modal. */
  id?: string;
  /** Optional extra class for the header wrapper. */
  className?: string;
  /** Header content — typically a title string or `<h2>`. */
  children: ReactNode;
}

function ModalHeader({ onClose, id, className, children }: ModalHeaderProps) {
  return (
    <div
      className={cn(
        'sticky top-0 z-10',
        'bg-white dark:bg-zinc-900',
        'border-b border-zinc-200 dark:border-zinc-800',
        'px-6 py-4 flex items-center justify-between',
        'rounded-t-2xl',
        className
      )}
    >
      <h2
        id={id}
        className="text-lg font-semibold text-zinc-900 dark:text-zinc-100"
      >
        {children}
      </h2>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1 -mr-1 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800 transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
          aria-label="Close"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
ModalHeader.displayName = 'Modal.Header';

// ---------------------------------------------------------------------------
// Modal.Body
// ---------------------------------------------------------------------------

export interface ModalBodyProps {
  className?: string;
  children: ReactNode;
}

function ModalBody({ className, children }: ModalBodyProps) {
  return (
    <div className={cn('px-6 py-5 overflow-y-auto flex-1', className)}>
      {children}
    </div>
  );
}
ModalBody.displayName = 'Modal.Body';

// ---------------------------------------------------------------------------
// Modal.Footer
// ---------------------------------------------------------------------------

export interface ModalFooterProps {
  className?: string;
  children: ReactNode;
}

function ModalFooter({ className, children }: ModalFooterProps) {
  return (
    <div
      className={cn(
        'border-t border-zinc-200 dark:border-zinc-800',
        'px-6 py-4',
        'flex items-center justify-end gap-2',
        'rounded-b-2xl',
        'bg-white dark:bg-zinc-900',
        className
      )}
    >
      {children}
    </div>
  );
}
ModalFooter.displayName = 'Modal.Footer';

// ---------------------------------------------------------------------------
// Compose compound API
// ---------------------------------------------------------------------------

Modal.Header = ModalHeader;
Modal.Body = ModalBody;
Modal.Footer = ModalFooter;

export default Modal;
