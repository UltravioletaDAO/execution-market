/**
 * LevelBadge Component
 *
 * A badge component for displaying worker experience levels.
 */

import type { CSSProperties } from 'react';
import {
  getLevelBadgeClass,
  getLevelColor,
  getLevelIconClass,
  type WorkerLevel,
} from '../../styles/theme';
import { cn } from '../../lib/utils';

export interface LevelBadgeProps {
  /** Worker level */
  level: WorkerLevel | string;
  /** Badge size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show level icon */
  showIcon?: boolean;
  /** Custom label override */
  label?: string;
  /** Additional CSS classes */
  className?: string;
}

const sizeClasses = {
  sm: 'px-2 py-0.5 text-2xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
};

const iconSizeClasses = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

/**
 * Star icon for level display
 */
function StarIcon({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      style={style}
    >
      <path
        fillRule="evenodd"
        d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/**
 * Shield icon for master level
 */
function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
    >
      <path
        fillRule="evenodd"
        d="M12.516 2.17a.75.75 0 0 0-1.032 0 11.209 11.209 0 0 1-7.877 3.08.75.75 0 0 0-.722.515A12.74 12.74 0 0 0 2.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 0 0 .374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.39-.223-2.73-.635-3.985a.75.75 0 0 0-.722-.516 11.209 11.209 0 0 1-7.877-3.08Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/**
 * Get the appropriate icon for a level
 */
function LevelIcon({ level, className }: { level: string; className?: string }) {
  const normalizedLevel = level.toLowerCase();

  if (normalizedLevel === 'master') {
    return <ShieldIcon className={className} />;
  }

  return <StarIcon className={className} />;
}

/**
 * Format level name for display
 */
function formatLevel(level: string): string {
  return level.charAt(0).toUpperCase() + level.slice(1).toLowerCase();
}

/**
 * Get number of stars for a level
 */
function getLevelStars(level: string): number {
  const normalizedLevel = level.toLowerCase();
  switch (normalizedLevel) {
    case 'novice': return 1;
    case 'apprentice': return 2;
    case 'journeyman': return 3;
    case 'expert': return 4;
    case 'master': return 5;
    default: return 1;
  }
}

export function LevelBadge({
  level,
  size = 'md',
  showIcon = true,
  label,
  className,
}: LevelBadgeProps) {
  const normalizedLevel = level.toLowerCase();
  const displayLabel = label || formatLevel(level);
  const badgeClasses = getLevelBadgeClass(normalizedLevel);
  const iconClasses = getLevelIconClass(normalizedLevel);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium',
        sizeClasses[size],
        badgeClasses,
        className
      )}
    >
      {showIcon && (
        <LevelIcon
          level={normalizedLevel}
          className={cn(iconSizeClasses[size], iconClasses)}
        />
      )}
      <span>{displayLabel}</span>
    </span>
  );
}

/**
 * LevelStars Component
 *
 * Display level as a row of stars.
 */
export interface LevelStarsProps {
  /** Worker level */
  level: WorkerLevel | string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Maximum stars to show */
  maxStars?: number;
  /** Show level label */
  showLabel?: boolean;
  /** Additional CSS classes */
  className?: string;
}

const starSizeClasses = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

export function LevelStars({
  level,
  size = 'md',
  maxStars = 5,
  showLabel = false,
  className,
}: LevelStarsProps) {
  const normalizedLevel = level.toLowerCase();
  const filledStars = getLevelStars(normalizedLevel);
  const color = getLevelColor(normalizedLevel);

  return (
    <div className={cn('inline-flex items-center gap-1', className)}>
      <div className="flex gap-0.5">
        {Array.from({ length: maxStars }, (_, i) => (
          <StarIcon
            key={i}
            className={cn(
              starSizeClasses[size],
              i < filledStars
                ? '' // Color will be set via style
                : 'text-slate-300 dark:text-slate-600'
            )}
            style={i < filledStars ? { color } : undefined}
          />
        ))}
      </div>
      {showLabel && (
        <span className="text-sm text-slate-600 dark:text-slate-400 ml-1">
          {formatLevel(level)}
        </span>
      )}
    </div>
  );
}

/**
 * LevelProgress Component
 *
 * Show progress to next level.
 */
export interface LevelProgressProps {
  /** Current level */
  level: WorkerLevel | string;
  /** Current XP or progress value */
  current: number;
  /** Required XP or value for next level */
  required: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show numeric values */
  showValues?: boolean;
  /** Additional CSS classes */
  className?: string;
}

const progressSizeClasses = {
  sm: 'h-1.5',
  md: 'h-2',
  lg: 'h-3',
};

export function LevelProgress({
  level,
  current,
  required,
  size = 'md',
  showValues = false,
  className,
}: LevelProgressProps) {
  const normalizedLevel = level.toLowerCase();
  const color = getLevelColor(normalizedLevel);
  const percentage = Math.min((current / required) * 100, 100);

  return (
    <div className={cn('w-full', className)}>
      {showValues && (
        <div className="flex items-center justify-between mb-1 text-sm">
          <LevelBadge level={level} size="sm" />
          <span className="text-slate-500 dark:text-slate-400">
            {current.toLocaleString()} / {required.toLocaleString()}
          </span>
        </div>
      )}
      <div
        className={cn(
          'w-full rounded-full overflow-hidden',
          'bg-slate-200 dark:bg-slate-700',
          progressSizeClasses[size]
        )}
        role="progressbar"
        aria-valuenow={current}
        aria-valuemin={0}
        aria-valuemax={required}
        aria-label={`Level progress: ${Math.round(percentage)}%`}
      >
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

export default LevelBadge;
