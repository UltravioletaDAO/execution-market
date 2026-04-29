import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';

export type PillVariant = 'default' | 'selected' | 'removable';
export type PillSize = 'sm' | 'md';

export interface PillProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  /** Visual variant. `selected` = active filter / language; `removable` = chip with X. */
  variant?: PillVariant;
  /** Size variant. `sm` = filter rows; `md` = skill chips, tabs. */
  size?: PillSize;
  /** Render as <span> instead of <button> when non-interactive. Default false. */
  asSpan?: boolean;
  /** Optional icon left of label. */
  leftIcon?: ReactNode;
  /** Callback for the X button when variant='removable'. */
  onRemove?: () => void;
  /** Localized label for the X button. Default 'Remove'. */
  removeLabel?: string;
  /** Children = the pill label. */
  children: ReactNode;
}

const baseClasses =
  'inline-flex items-center gap-1.5 rounded-full font-medium ' +
  'transition-colors duration-150 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 dark:focus-visible:ring-zinc-100 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-black ' +
  'disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-400 disabled:pointer-events-none';

const sizeClasses: Record<PillSize, string> = {
  sm: 'px-2.5 py-0.5 text-xs',
  md: 'px-3 py-1.5 text-sm',
};

const variantClasses: Record<PillVariant, string> = {
  default:
    'bg-zinc-100 text-zinc-700 hover:bg-zinc-200 ' +
    'dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800',
  selected:
    'bg-zinc-900 text-white hover:bg-zinc-800 ' +
    'dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200',
  removable:
    'bg-zinc-900 text-white pr-1.5 ' +
    'dark:bg-zinc-100 dark:text-zinc-900',
};

export const Pill = forwardRef<HTMLButtonElement, PillProps>(function Pill(
  {
    variant = 'default',
    size = 'md',
    asSpan = false,
    leftIcon,
    onRemove,
    removeLabel = 'Remove',
    className,
    children,
    disabled,
    ...rest
  },
  ref,
) {
  const classes = cn(baseClasses, sizeClasses[size], variantClasses[variant], className);

  const content = (
    <>
      {leftIcon ? <span aria-hidden="true">{leftIcon}</span> : null}
      <span>{children}</span>
      {variant === 'removable' && onRemove ? (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          aria-label={removeLabel}
          className="ml-1 -mr-0.5 rounded-full p-0.5 hover:bg-white/20 dark:hover:bg-black/20"
        >
          <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M3 3l6 6M9 3l-6 6" strokeLinecap="round" />
          </svg>
        </button>
      ) : null}
    </>
  );

  if (asSpan) {
    return (
      <span className={classes} aria-pressed={variant === 'selected' || undefined}>
        {content}
      </span>
    );
  }

  return (
    <button
      ref={ref}
      type="button"
      className={classes}
      aria-pressed={variant === 'selected'}
      disabled={disabled}
      {...rest}
    >
      {content}
    </button>
  );
});

Pill.displayName = 'Pill';
