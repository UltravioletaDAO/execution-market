/**
 * Badge Component
 *
 * A flexible badge component for displaying labels, counts, and status indicators.
 * Supports various colors, sizes, and styles.
 */

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /** Color variant */
  variant?:
    | 'default'
    | 'primary'
    | 'secondary'
    | 'success'
    | 'warning'
    | 'danger'
    | 'info'
    | 'outline';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether the badge has a dot indicator */
  dot?: boolean;
  /** Dot color (overrides variant) */
  dotColor?: string;
  /** Whether the badge is rounded (pill shape) */
  rounded?: boolean;
  /** Icon before the content */
  icon?: ReactNode;
  /** Make the badge removable */
  removable?: boolean;
  /** Called when remove button is clicked */
  onRemove?: () => void;
}

const variantClasses = {
  default: [
    'bg-slate-100 text-slate-800',
    'dark:bg-slate-800 dark:text-slate-300',
  ].join(' '),
  primary: [
    'bg-em-100 text-em-800',
    'dark:bg-em-900/30 dark:text-em-400',
  ].join(' '),
  secondary: [
    'bg-violet-100 text-violet-800',
    'dark:bg-violet-900/30 dark:text-violet-400',
  ].join(' '),
  success: [
    'bg-emerald-100 text-emerald-800',
    'dark:bg-emerald-900/30 dark:text-emerald-400',
  ].join(' '),
  warning: [
    'bg-amber-100 text-amber-800',
    'dark:bg-amber-900/30 dark:text-amber-400',
  ].join(' '),
  danger: [
    'bg-red-100 text-red-800',
    'dark:bg-red-900/30 dark:text-red-400',
  ].join(' '),
  info: [
    'bg-blue-100 text-blue-800',
    'dark:bg-blue-900/30 dark:text-blue-400',
  ].join(' '),
  outline: [
    'bg-transparent border border-slate-300 text-slate-700',
    'dark:border-slate-600 dark:text-slate-300',
  ].join(' '),
};

const dotColorClasses = {
  default: 'bg-slate-400 dark:bg-slate-500',
  primary: 'bg-em-500',
  secondary: 'bg-violet-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500',
  outline: 'bg-slate-400 dark:bg-slate-500',
};

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

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      variant = 'default',
      size = 'md',
      dot = false,
      dotColor,
      rounded = true,
      icon,
      removable = false,
      onRemove,
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1.5 font-medium',
          rounded ? 'rounded-full' : 'rounded-md',
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {dot && (
          <span
            className={cn(
              'rounded-full flex-shrink-0',
              dotSizeClasses[size],
              !dotColor && dotColorClasses[variant]
            )}
            style={dotColor ? { backgroundColor: dotColor } : undefined}
            aria-hidden="true"
          />
        )}
        {icon && <span className="flex-shrink-0 -ml-0.5">{icon}</span>}
        {children}
        {removable && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove?.();
            }}
            className={cn(
              'flex-shrink-0 -mr-1 ml-0.5',
              'rounded-full p-0.5',
              'hover:bg-black/10 dark:hover:bg-white/10',
              'transition-colors'
            )}
            aria-label="Remove"
          >
            <svg
              className={cn(size === 'lg' ? 'w-3.5 h-3.5' : 'w-3 h-3')}
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
      </span>
    );
  }
);

Badge.displayName = 'Badge';

/**
 * CountBadge - A badge specifically for displaying counts
 */
export interface CountBadgeProps extends Omit<BadgeProps, 'children'> {
  /** The count to display */
  count: number;
  /** Maximum count to display (shows "99+" if exceeded) */
  max?: number;
  /** Whether to show zero */
  showZero?: boolean;
}

export function CountBadge({
  count,
  max = 99,
  showZero = false,
  size = 'sm',
  variant = 'danger',
  className,
  ...props
}: CountBadgeProps) {
  if (count === 0 && !showZero) {
    return null;
  }

  const displayCount = count > max ? `${max}+` : count.toString();

  return (
    <Badge
      size={size}
      variant={variant}
      className={cn(
        // Make it more compact for counts
        'min-w-[1.25rem] justify-center',
        size === 'sm' && 'px-1.5',
        className
      )}
      {...props}
    >
      {displayCount}
    </Badge>
  );
}

/**
 * NotificationBadge - Positioned badge for notification indicators
 */
export interface NotificationBadgeProps extends CountBadgeProps {
  /** Position relative to parent */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

const positionClasses = {
  'top-right': '-top-1 -right-1',
  'top-left': '-top-1 -left-1',
  'bottom-right': '-bottom-1 -right-1',
  'bottom-left': '-bottom-1 -left-1',
};

export function NotificationBadge({
  position = 'top-right',
  className,
  ...props
}: NotificationBadgeProps) {
  return (
    <CountBadge
      className={cn('absolute', positionClasses[position], className)}
      {...props}
    />
  );
}

/**
 * TagBadge - A badge for displaying tags with optional color
 */
export interface TagBadgeProps extends Omit<BadgeProps, 'variant'> {
  /** Custom color (hex or CSS color) */
  color?: string;
}

export function TagBadge({
  color,
  className,
  style,
  ...props
}: TagBadgeProps) {
  if (!color) {
    return <Badge variant="outline" className={className} {...props} />;
  }

  return (
    <Badge
      variant="outline"
      className={className}
      style={{
        ...style,
        borderColor: color,
        color: color,
        backgroundColor: `${color}10`, // 10% opacity
      }}
      {...props}
    />
  );
}

/**
 * CategoryBadge - Pre-styled badges for task categories
 */
export interface CategoryBadgeProps extends Omit<BadgeProps, 'variant' | 'icon'> {
  /** Task category */
  category:
    | 'physical_presence'
    | 'knowledge_access'
    | 'human_authority'
    | 'simple_action'
    | 'digital_physical';
}

const categoryConfig = {
  physical_presence: {
    label: 'Physical Presence',
    icon: 'M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  },
  knowledge_access: {
    label: 'Knowledge Access',
    icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
    color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  },
  human_authority: {
    label: 'Human Authority',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  },
  simple_action: {
    label: 'Simple Action',
    icon: 'M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11',
    color: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
  },
  digital_physical: {
    label: 'Digital-Physical',
    icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1',
    color: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
  },
};

export function CategoryBadge({ category, className, ...props }: CategoryBadgeProps) {
  const config = categoryConfig[category];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full',
        'text-xs font-medium',
        config.color,
        className
      )}
      {...props}
    >
      <svg
        className="w-3.5 h-3.5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={config.icon} />
      </svg>
      {config.label}
    </span>
  );
}

/**
 * Badge Group - Display multiple badges with overflow handling
 */
export interface BadgeGroupProps {
  children: ReactNode;
  /** Maximum number of badges to show */
  max?: number;
  /** Size for the overflow badge */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

export function BadgeGroup({
  children,
  max,
  size = 'sm',
  className,
}: BadgeGroupProps) {
  const childArray = Array.isArray(children) ? children : [children];
  const visibleChildren = max ? childArray.slice(0, max) : childArray;
  const overflowCount = max ? childArray.length - max : 0;

  return (
    <div className={cn('flex flex-wrap gap-1.5', className)}>
      {visibleChildren}
      {overflowCount > 0 && (
        <Badge variant="default" size={size}>
          +{overflowCount}
        </Badge>
      )}
    </div>
  );
}

export default Badge;
