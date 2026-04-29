import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export type EmptyStateVariant = 'default' | 'warning' | 'danger';
export type EmptyStateSize = 'sm' | 'md' | 'lg';

export interface EmptyStateProps {
  /** SVG path 'd' attribute. Auto-wrapped in a colored circle. */
  iconPath?: string;
  /** Custom icon node. Takes precedence over `iconPath`. Caller controls wrapper. */
  icon?: ReactNode;
  /** Heading text. */
  title?: ReactNode;
  /** Subtext below title. */
  description?: ReactNode;
  /** Optional CTA (button, link, etc). */
  action?: ReactNode;
  /** Color of the auto-rendered icon circle. */
  variant?: EmptyStateVariant;
  /** Vertical padding. */
  size?: EmptyStateSize;
  className?: string;
}

const sizePaddingClasses: Record<EmptyStateSize, string> = {
  sm: 'py-8',
  md: 'py-12',
  lg: 'py-16',
};

const sizeCircleClasses: Record<EmptyStateSize, string> = {
  sm: 'w-12 h-12 mb-3',
  md: 'w-16 h-16 mb-4',
  lg: 'w-20 h-20 mb-4',
};

const sizeIconClasses: Record<EmptyStateSize, string> = {
  sm: 'w-6 h-6',
  md: 'w-8 h-8',
  lg: 'w-10 h-10',
};

const sizeTitleClasses: Record<EmptyStateSize, string> = {
  sm: 'text-base',
  md: 'text-lg',
  lg: 'text-lg',
};

const variantCircleClasses: Record<EmptyStateVariant, string> = {
  default: 'bg-zinc-100 text-zinc-400',
  warning: 'bg-amber-50 text-amber-700',
  danger: 'bg-red-50 text-red-500',
};

export function EmptyState({
  iconPath,
  icon,
  title,
  description,
  action,
  variant = 'default',
  size = 'md',
  className,
}: EmptyStateProps) {
  const renderedIcon = icon ?? (iconPath ? (
    <div
      className={cn(
        'rounded-full flex items-center justify-center mx-auto',
        sizeCircleClasses[size],
        variantCircleClasses[variant],
      )}
      aria-hidden="true"
    >
      <svg
        className={sizeIconClasses[size]}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d={iconPath}
        />
      </svg>
    </div>
  ) : null);

  return (
    <div className={cn('text-center', sizePaddingClasses[size], className)}>
      {renderedIcon}
      {title && (
        <h3 className={cn('font-medium text-zinc-900 mb-1', sizeTitleClasses[size])}>
          {title}
        </h3>
      )}
      {description && (
        <p className="text-sm text-zinc-500 mb-4">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
