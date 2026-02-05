/**
 * Card Component
 *
 * A flexible card component for displaying content in a contained box.
 * Supports headers, footers, and different visual variants.
 */

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Visual variant */
  variant?: 'default' | 'elevated' | 'outline' | 'ghost' | 'interactive';
  /** Padding size */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** Whether the card is clickable */
  clickable?: boolean;
  /** Whether the card is selected */
  selected?: boolean;
}

const variantClasses = {
  default: [
    'bg-white dark:bg-slate-800',
    'border border-slate-200 dark:border-slate-700',
    'shadow-sm',
  ].join(' '),
  elevated: [
    'bg-white dark:bg-slate-800',
    'border border-slate-200/50 dark:border-slate-700/50',
    'shadow-lg',
  ].join(' '),
  outline: [
    'bg-transparent',
    'border-2 border-slate-200 dark:border-slate-700',
  ].join(' '),
  ghost: [
    'bg-slate-50 dark:bg-slate-800/50',
    'border border-transparent',
  ].join(' '),
  interactive: [
    'bg-white dark:bg-slate-800',
    'border border-slate-200 dark:border-slate-700',
    'shadow-sm',
    'cursor-pointer',
    'hover:shadow-md hover:scale-[1.01]',
    'hover:border-slate-300 dark:hover:border-slate-600',
    'active:scale-[0.99]',
  ].join(' '),
};

const paddingClasses = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      variant = 'default',
      padding = 'md',
      clickable = false,
      selected = false,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const isInteractive = variant === 'interactive' || clickable;

    return (
      <div
        ref={ref}
        className={cn(
          // Base styles
          'rounded-xl',
          'transition-all duration-200',
          // Variant styles
          variantClasses[variant],
          // Padding
          paddingClasses[padding],
          // Clickable state
          isInteractive && variant !== 'interactive' && [
            'cursor-pointer',
            'hover:shadow-md',
            'hover:border-slate-300 dark:hover:border-slate-600',
          ],
          // Selected state
          selected && [
            'ring-2 ring-em-500',
            'border-em-500 dark:border-em-500',
          ],
          // Custom classes
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

/**
 * CardHeader Component
 */
export interface CardHeaderProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Title element */
  title?: ReactNode;
  /** Subtitle/description */
  subtitle?: ReactNode;
  /** Action elements (buttons, etc.) */
  action?: ReactNode;
  /** Whether to show a border */
  bordered?: boolean;
}

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  (
    { title, subtitle, action, bordered = false, className, children, ...props },
    ref
  ) => {
    // If children are provided, use them directly
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
          'px-6 py-4',
          'flex items-start justify-between gap-4',
          bordered && 'border-b border-slate-200 dark:border-slate-700',
          className
        )}
        {...props}
      >
        <div className="flex-1 min-w-0">
          {title && (
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

/**
 * CardBody Component
 */
export interface CardBodyProps extends HTMLAttributes<HTMLDivElement> {
  /** Padding override */
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const bodyPaddingClasses = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const CardBody = forwardRef<HTMLDivElement, CardBodyProps>(
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

CardBody.displayName = 'CardBody';

/**
 * CardFooter Component
 */
export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
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

export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
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
          'rounded-b-xl',
          className
        )}
        {...props}
      />
    );
  }
);

CardFooter.displayName = 'CardFooter';

/**
 * StatCard - A specialized card for displaying statistics
 */
export interface StatCardProps extends Omit<CardProps, 'children'> {
  /** Stat value */
  value: ReactNode;
  /** Stat label */
  label: string;
  /** Icon to display */
  icon?: ReactNode;
  /** Change indicator (positive/negative percentage) */
  change?: {
    value: number;
    label?: string;
  };
  /** Loading state */
  loading?: boolean;
}

export function StatCard({
  value,
  label,
  icon,
  change,
  loading = false,
  className,
  ...props
}: StatCardProps) {
  return (
    <Card padding="lg" className={className} {...props}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {loading ? (
            <div className="h-8 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
          ) : (
            <div className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              {value}
            </div>
          )}
          <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {label}
          </div>
          {change && !loading && (
            <div
              className={cn(
                'mt-2 text-sm font-medium flex items-center gap-1',
                change.value > 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : change.value < 0
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-slate-500 dark:text-slate-400'
              )}
            >
              {change.value > 0 ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
              ) : change.value < 0 ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              ) : null}
              <span>
                {change.value > 0 ? '+' : ''}
                {change.value}%
              </span>
              {change.label && (
                <span className="text-slate-400 dark:text-slate-500">
                  {change.label}
                </span>
              )}
            </div>
          )}
        </div>
        {icon && (
          <div className="flex-shrink-0 p-3 rounded-lg bg-em-50 dark:bg-em-900/20 text-em-600 dark:text-em-400">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

/**
 * TaskCard - A specialized card for displaying tasks (styled version)
 */
export interface TaskCardStyledProps extends CardProps {
  /** Border color status */
  status?: 'published' | 'accepted' | 'in_progress' | 'submitted' | 'verifying' | 'completed' | 'disputed' | 'expired' | 'cancelled';
}

const statusBorderClasses = {
  published: 'border-l-4 border-l-blue-500',
  accepted: 'border-l-4 border-l-violet-500',
  in_progress: 'border-l-4 border-l-amber-500',
  submitted: 'border-l-4 border-l-indigo-500',
  verifying: 'border-l-4 border-l-purple-500',
  completed: 'border-l-4 border-l-emerald-500',
  disputed: 'border-l-4 border-l-red-500',
  expired: 'border-l-4 border-l-gray-500',
  cancelled: 'border-l-4 border-l-gray-400',
};

export const TaskCardStyled = forwardRef<HTMLDivElement, TaskCardStyledProps>(
  ({ status, className, ...props }, ref) => {
    return (
      <Card
        ref={ref}
        variant="interactive"
        className={cn(status && statusBorderClasses[status], className)}
        {...props}
      />
    );
  }
);

TaskCardStyled.displayName = 'TaskCardStyled';

export default Card;
