/**
 * StatusBadge Component
 *
 * A reusable badge component for displaying task status with consistent styling.
 * Supports multiple variants and sizes.
 */

import { type ReactNode } from 'react';
import { type TaskStatus } from '../../types/database';
import {
  getStatusBadgeClass,
  getStatusBadgeWithDotClass,
  getStatusColor,
  formatStatus,
  getStatusDotAnimationClass,
} from '../../styles/theme';
import { cn } from '../../lib/utils';

export interface StatusBadgeProps {
  /** The task status to display */
  status: TaskStatus | string;
  /** Badge size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Badge style variant */
  variant?: 'default' | 'outline' | 'dot';
  /** Show status dot indicator */
  showDot?: boolean;
  /** Custom label override */
  label?: string;
  /** Additional CSS classes */
  className?: string;
  /** Icon to display before the label */
  icon?: ReactNode;
}

const sizeClasses = {
  sm: 'px-2 py-0.5 text-2xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
};

const dotSizeClasses = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-2.5 h-2.5',
};

export function StatusBadge({
  status,
  size = 'md',
  variant = 'default',
  showDot = false,
  label,
  className,
  icon,
}: StatusBadgeProps) {
  const displayLabel = label || formatStatus(status);
  const dotAnimation = getStatusDotAnimationClass(status);

  // Get the appropriate badge classes based on variant
  const badgeClasses =
    variant === 'outline'
      ? getStatusBadgeWithDotClass(status)
      : getStatusBadgeClass(status);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        sizeClasses[size],
        badgeClasses,
        className
      )}
    >
      {showDot && (
        <span
          className={cn(
            'rounded-full flex-shrink-0',
            dotSizeClasses[size],
            dotAnimation
          )}
          style={{ backgroundColor: getStatusColor(status) }}
          aria-hidden="true"
        />
      )}
      {icon && <span className="flex-shrink-0">{icon}</span>}
      <span>{displayLabel}</span>
    </span>
  );
}

/**
 * StatusDot Component
 *
 * A standalone dot indicator for task status.
 */
export interface StatusDotProps {
  /** The task status */
  status: TaskStatus | string;
  /** Dot size */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
  /** Show pulse animation for certain statuses */
  animate?: boolean;
}

const dotOnlySizeClasses = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-3 h-3',
};

export function StatusDot({
  status,
  size = 'md',
  className,
  animate = true,
}: StatusDotProps) {
  const dotAnimation = animate ? getStatusDotAnimationClass(status) : '';

  return (
    <span
      className={cn(
        'rounded-full flex-shrink-0',
        dotOnlySizeClasses[size],
        dotAnimation,
        className
      )}
      style={{ backgroundColor: getStatusColor(status) }}
      role="img"
      aria-label={`Status: ${formatStatus(status)}`}
    />
  );
}

/**
 * StatusIndicator Component
 *
 * A larger status indicator with ring styling.
 */
export interface StatusIndicatorProps {
  /** The task status */
  status: TaskStatus | string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

const indicatorSizeClasses = {
  sm: 'w-2.5 h-2.5',
  md: 'w-3 h-3',
  lg: 'w-4 h-4',
};

export function StatusIndicator({
  status,
  size = 'md',
  className,
}: StatusIndicatorProps) {
  const dotAnimation = getStatusDotAnimationClass(status);

  return (
    <span
      className={cn(
        'rounded-full flex-shrink-0',
        'ring-2 ring-offset-2 ring-offset-white dark:ring-offset-slate-900',
        indicatorSizeClasses[size],
        dotAnimation,
        className
      )}
      style={{
        backgroundColor: getStatusColor(status),
        // @ts-expect-error: CSS custom property for ring color
        '--tw-ring-color': getStatusColor(status),
      }}
      role="img"
      aria-label={`Status: ${formatStatus(status)}`}
    />
  );
}

export default StatusBadge;
