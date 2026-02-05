/**
 * Modal Component
 *
 * A flexible modal/dialog component with backdrop, animations, and accessibility features.
 * Supports different sizes and can be closed via backdrop click, escape key, or close button.
 */

import {
  forwardRef,
  type HTMLAttributes,
  type ReactNode,
  useEffect,
  useRef,
  useCallback,
} from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../lib/utils';

export interface ModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Called when the modal should close */
  onClose: () => void;
  /** Modal content */
  children: ReactNode;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** Whether clicking the backdrop closes the modal */
  closeOnBackdropClick?: boolean;
  /** Whether pressing escape closes the modal */
  closeOnEscape?: boolean;
  /** Whether to show the close button */
  showCloseButton?: boolean;
  /** Additional class for the modal container */
  className?: string;
  /** Additional class for the backdrop */
  backdropClassName?: string;
  /** Whether to center the modal vertically */
  centered?: boolean;
  /** Initial focus element ref */
  initialFocus?: React.RefObject<HTMLElement>;
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]',
};

export function Modal({
  open,
  onClose,
  children,
  size = 'md',
  closeOnBackdropClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  className,
  backdropClassName,
  centered = true,
  initialFocus,
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<Element | null>(null);

  // Handle escape key
  useEffect(() => {
    if (!open || !closeOnEscape) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, closeOnEscape, onClose]);

  // Handle focus trap and restoration
  useEffect(() => {
    if (!open) return;

    // Store the currently focused element
    previousActiveElement.current = document.activeElement;

    // Focus the modal or initial focus element
    const focusElement = initialFocus?.current ?? modalRef.current;
    if (focusElement) {
      focusElement.focus();
    }

    // Prevent body scroll
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      // Restore body scroll
      document.body.style.overflow = originalOverflow;

      // Restore focus
      if (previousActiveElement.current instanceof HTMLElement) {
        previousActiveElement.current.focus();
      }
    };
  }, [open, initialFocus]);

  // Handle backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (closeOnBackdropClick && e.target === e.currentTarget) {
        onClose();
      }
    },
    [closeOnBackdropClick, onClose]
  );

  // Handle tab key for focus trap
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== 'Tab' || !modalRef.current) return;

    const focusableElements = modalRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    if (e.shiftKey) {
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      }
    } else {
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    }
  }, []);

  if (!open) return null;

  return createPortal(
    <div
      className={cn(
        'fixed inset-0 z-50',
        'flex',
        centered ? 'items-center' : 'items-start pt-16',
        'justify-center',
        'p-4',
        'overflow-y-auto'
      )}
      aria-modal="true"
      role="dialog"
    >
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/50 backdrop-blur-sm',
          'animate-fade-in',
          backdropClassName
        )}
        onClick={handleBackdropClick}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={cn(
          'relative w-full',
          'bg-white dark:bg-slate-800',
          'rounded-2xl shadow-2xl',
          'animate-scale-in',
          'focus:outline-none',
          sizeClasses[size],
          className
        )}
      >
        {showCloseButton && (
          <button
            type="button"
            onClick={onClose}
            className={cn(
              'absolute top-4 right-4 z-10',
              'p-2 rounded-lg',
              'text-slate-400 dark:text-slate-500',
              'hover:text-slate-600 dark:hover:text-slate-300',
              'hover:bg-slate-100 dark:hover:bg-slate-700',
              'transition-colors'
            )}
            aria-label="Close modal"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
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
        {children}
      </div>
    </div>,
    document.body
  );
}

/**
 * ModalHeader Component
 */
export interface ModalHeaderProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Title text */
  title?: ReactNode;
  /** Subtitle/description */
  subtitle?: ReactNode;
  /** Whether to show a border */
  bordered?: boolean;
}

export const ModalHeader = forwardRef<HTMLDivElement, ModalHeaderProps>(
  ({ title, subtitle, bordered = false, className, children, ...props }, ref) => {
    if (children) {
      return (
        <div
          ref={ref}
          className={cn(
            'px-6 py-4',
            bordered && 'border-b border-slate-200 dark:border-slate-700',
            className
          )}
          {...props}
        >
          {children}
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          'px-6 py-4 pr-12', // Extra padding for close button
          bordered && 'border-b border-slate-200 dark:border-slate-700',
          className
        )}
        {...props}
      >
        {title && (
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h2>
        )}
        {subtitle && (
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {subtitle}
          </p>
        )}
      </div>
    );
  }
);

ModalHeader.displayName = 'ModalHeader';

/**
 * ModalBody Component
 */
export interface ModalBodyProps extends HTMLAttributes<HTMLDivElement> {
  /** Padding size */
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const bodyPaddingClasses = {
  none: '',
  sm: 'px-4 py-3',
  md: 'px-6 py-4',
  lg: 'px-8 py-6',
};

export const ModalBody = forwardRef<HTMLDivElement, ModalBodyProps>(
  ({ padding = 'md', className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(bodyPaddingClasses[padding], className)}
        {...props}
      />
    );
  }
);

ModalBody.displayName = 'ModalBody';

/**
 * ModalFooter Component
 */
export interface ModalFooterProps extends HTMLAttributes<HTMLDivElement> {
  /** Whether to show a border */
  bordered?: boolean;
  /** Alignment of footer content */
  align?: 'left' | 'center' | 'right' | 'between';
}

const alignClasses = {
  left: 'justify-start',
  center: 'justify-center',
  right: 'justify-end',
  between: 'justify-between',
};

export const ModalFooter = forwardRef<HTMLDivElement, ModalFooterProps>(
  ({ bordered = true, align = 'right', className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'px-6 py-4',
          'flex items-center gap-3',
          alignClasses[align],
          bordered && 'border-t border-slate-200 dark:border-slate-700',
          'bg-slate-50 dark:bg-slate-800/50',
          'rounded-b-2xl',
          className
        )}
        {...props}
      />
    );
  }
);

ModalFooter.displayName = 'ModalFooter';

/**
 * ConfirmModal - Pre-built confirmation dialog
 */
export interface ConfirmModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Called when the modal should close */
  onClose: () => void;
  /** Called when confirmed */
  onConfirm: () => void;
  /** Title text */
  title?: string;
  /** Description text */
  description?: string;
  /** Confirm button text */
  confirmText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** Visual variant for the confirm button */
  variant?: 'primary' | 'danger';
  /** Whether the action is loading */
  loading?: boolean;
}

export function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  description = 'Are you sure you want to proceed?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'primary',
  loading = false,
}: ConfirmModalProps) {
  return (
    <Modal open={open} onClose={onClose} size="sm" showCloseButton={false}>
      <ModalHeader title={title} />
      <ModalBody>
        <p className="text-slate-600 dark:text-slate-400">{description}</p>
      </ModalBody>
      <ModalFooter>
        <button
          type="button"
          onClick={onClose}
          disabled={loading}
          className={cn(
            'btn btn-secondary',
            loading && 'opacity-50 cursor-not-allowed'
          )}
        >
          {cancelText}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={loading}
          className={cn(
            'btn',
            variant === 'danger' ? 'btn-danger' : 'btn-primary',
            loading && 'opacity-50'
          )}
        >
          {loading && (
            <svg
              className="w-4 h-4 animate-spin mr-2"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          )}
          {confirmText}
        </button>
      </ModalFooter>
    </Modal>
  );
}

/**
 * AlertModal - Pre-built alert dialog
 */
export interface AlertModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Called when the modal should close */
  onClose: () => void;
  /** Title text */
  title?: string;
  /** Description text */
  description?: string;
  /** Button text */
  buttonText?: string;
  /** Visual variant */
  variant?: 'info' | 'success' | 'warning' | 'error';
}

const alertIconPaths = {
  info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  error: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
};

const alertIconColors = {
  info: 'text-blue-500',
  success: 'text-emerald-500',
  warning: 'text-amber-500',
  error: 'text-red-500',
};

export function AlertModal({
  open,
  onClose,
  title = 'Alert',
  description,
  buttonText = 'OK',
  variant = 'info',
}: AlertModalProps) {
  return (
    <Modal open={open} onClose={onClose} size="sm" showCloseButton={false}>
      <ModalBody padding="lg">
        <div className="text-center">
          <div
            className={cn(
              'mx-auto w-12 h-12 rounded-full flex items-center justify-center',
              'bg-slate-100 dark:bg-slate-800',
              'mb-4'
            )}
          >
            <svg
              className={cn('w-6 h-6', alertIconColors[variant])}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={alertIconPaths[variant]}
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            {title}
          </h3>
          {description && (
            <p className="text-slate-600 dark:text-slate-400">{description}</p>
          )}
          <button
            type="button"
            onClick={onClose}
            className="btn btn-primary mt-6 w-full"
          >
            {buttonText}
          </button>
        </div>
      </ModalBody>
    </Modal>
  );
}

export default Modal;
