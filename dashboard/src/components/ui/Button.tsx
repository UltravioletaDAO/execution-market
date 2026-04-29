/**
 * Button Component
 *
 * A flexible button component with multiple variants, sizes, and states.
 * Supports icons, loading states, and full-width options.
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { Spinner as SpinnerPrimitive, type SpinnerSize } from './Spinner';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual variant */
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'warning' | 'link';
  /** Size variant */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** Full width button */
  fullWidth?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Icon to display before children */
  leftIcon?: ReactNode;
  /** Icon to display after children */
  rightIcon?: ReactNode;
  /** Icon-only button (square with equal padding) */
  iconOnly?: boolean;
}

// Canonical B&W zinc palette — matches `.btn-*` classes in globals.css.
// Red/amber are reserved for semantic accents (disputed/expired badges, error toasts) — not buttons.
const variantClasses = {
  primary: [
    'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900',
    'hover:bg-zinc-800 dark:hover:bg-zinc-200',
    'focus:ring-zinc-900 dark:focus:ring-white',
    'active:bg-zinc-950 dark:active:bg-zinc-300',
  ].join(' '),
  secondary: [
    'bg-white border border-zinc-300 text-zinc-900',
    'dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-100',
    'hover:bg-zinc-100 dark:hover:bg-zinc-700',
    'focus:ring-zinc-500',
    'active:bg-zinc-200 dark:active:bg-zinc-600',
  ].join(' '),
  outline: [
    'border-2 border-zinc-700 dark:border-zinc-300',
    'text-zinc-700 dark:text-zinc-300',
    'hover:bg-zinc-900 hover:text-white hover:border-zinc-900',
    'dark:hover:bg-white dark:hover:text-zinc-900 dark:hover:border-white',
    'focus:ring-zinc-500',
  ].join(' '),
  ghost: [
    'bg-transparent',
    'text-zinc-700 dark:text-zinc-300',
    'hover:bg-zinc-100 dark:hover:bg-zinc-800',
    'hover:text-zinc-900 dark:hover:text-zinc-100',
    'focus:ring-zinc-500',
  ].join(' '),
  danger: [
    'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900',
    'hover:bg-zinc-700 dark:hover:bg-zinc-300',
    'focus:ring-zinc-700',
    'active:bg-zinc-950 dark:active:bg-white',
  ].join(' '),
  success: [
    'bg-zinc-800 text-white dark:bg-zinc-200 dark:text-zinc-900',
    'hover:bg-zinc-700 dark:hover:bg-zinc-300',
    'focus:ring-zinc-700',
    'active:bg-zinc-900 dark:active:bg-zinc-100',
  ].join(' '),
  warning: [
    'bg-zinc-700 text-white dark:bg-zinc-300 dark:text-zinc-900',
    'hover:bg-zinc-600 dark:hover:bg-zinc-400',
    'focus:ring-zinc-600',
    'active:bg-zinc-800 dark:active:bg-zinc-200',
  ].join(' '),
  link: [
    'bg-transparent',
    'text-zinc-900 dark:text-zinc-100',
    'hover:text-zinc-700 dark:hover:text-zinc-300',
    'hover:underline',
    'focus:ring-zinc-500',
    'p-0',
  ].join(' '),
};

const sizeClasses = {
  xs: 'px-2.5 py-1 text-xs gap-1',
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
  xl: 'px-8 py-4 text-lg gap-2.5',
};

const iconOnlySizeClasses = {
  xs: 'p-1',
  sm: 'p-1.5',
  md: 'p-2',
  lg: 'p-3',
  xl: 'p-4',
};

const iconSizeClasses = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
  xl: 'w-6 h-6',
};

const buttonSizeToSpinnerSize: Record<NonNullable<ButtonProps['size']>, SpinnerSize> = {
  xs: 'xs',
  sm: 'sm',
  md: 'sm',
  lg: 'md',
  xl: 'lg',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      loading = false,
      leftIcon,
      rightIcon,
      iconOnly = false,
      disabled,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center',
          'rounded-lg font-medium',
          'transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-offset-2',
          'focus:ring-offset-white dark:focus:ring-offset-zinc-900',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
          'active:scale-[0.98]',
          // Variant styles
          variantClasses[variant],
          // Size styles
          iconOnly ? iconOnlySizeClasses[size] : sizeClasses[size],
          // Full width
          fullWidth && 'w-full',
          // Custom classes
          className
        )}
        {...props}
      >
        {loading && (
          <SpinnerPrimitive
            size={buttonSizeToSpinnerSize[size]}
            className={children ? 'mr-2' : ''}
          />
        )}
        {!loading && leftIcon && (
          <span className={cn('flex-shrink-0', iconSizeClasses[size])}>{leftIcon}</span>
        )}
        {children}
        {!loading && rightIcon && (
          <span className={cn('flex-shrink-0', iconSizeClasses[size])}>{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

/**
 * IconButton - A square button optimized for icons
 */
export interface IconButtonProps extends Omit<ButtonProps, 'iconOnly' | 'leftIcon' | 'rightIcon'> {
  /** Accessible label for the button */
  'aria-label': string;
  /** The icon to display */
  icon: ReactNode;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, size = 'md', className, ...props }, ref) => {
    return (
      <Button
        ref={ref}
        iconOnly
        size={size}
        className={cn('aspect-square', className)}
        {...props}
      >
        <span className={iconSizeClasses[size]}>{icon}</span>
      </Button>
    );
  }
);

IconButton.displayName = 'IconButton';

/**
 * ButtonGroup - Group buttons together
 */
export interface ButtonGroupProps {
  /** Child buttons */
  children: ReactNode;
  /** Orientation */
  orientation?: 'horizontal' | 'vertical';
  /** Size for all buttons in the group */
  size?: ButtonProps['size'];
  /** Additional CSS classes */
  className?: string;
}

export function ButtonGroup({
  children,
  orientation = 'horizontal',
  className,
}: ButtonGroupProps) {
  return (
    <div
      role="group"
      className={cn(
        'inline-flex',
        orientation === 'vertical' ? 'flex-col' : 'flex-row',
        // Remove border radius from middle children
        '[&>*:not(:first-child):not(:last-child)]:rounded-none',
        orientation === 'horizontal' && [
          '[&>*:first-child]:rounded-r-none',
          '[&>*:last-child]:rounded-l-none',
          '[&>*:not(:first-child)]:-ml-px',
        ],
        orientation === 'vertical' && [
          '[&>*:first-child]:rounded-b-none',
          '[&>*:last-child]:rounded-t-none',
          '[&>*:not(:first-child)]:-mt-px',
        ],
        className
      )}
    >
      {children}
    </div>
  );
}

export default Button;
