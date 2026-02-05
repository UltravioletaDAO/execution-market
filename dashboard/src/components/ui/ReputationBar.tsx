/**
 * ReputationBar Component
 *
 * A visual indicator for reputation scores with color gradients.
 * Supports multiple sizes, variants, and display options.
 */

import { useMemo } from 'react';
import {
  getReputationColor,
  getReputationLabel,
  getReputationColorClass,
  getReputationBgClass,
} from '../../styles/theme';
import { cn } from '../../lib/utils';

export interface ReputationBarProps {
  /** Reputation score (0-100) */
  score: number;
  /** Maximum score (default 100) */
  maxScore?: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show the numeric score */
  showScore?: boolean;
  /** Show the reputation label (Poor, Fair, Good, etc.) */
  showLabel?: boolean;
  /** Show percentage instead of raw score */
  showPercentage?: boolean;
  /** Animate the bar fill */
  animate?: boolean;
  /** Additional CSS classes for the container */
  className?: string;
  /** Additional CSS classes for the bar */
  barClassName?: string;
}

const sizeClasses = {
  sm: 'h-1.5',
  md: 'h-2',
  lg: 'h-3',
};

function getReputationBand(score: number): string {
  if (score >= 90) return 'elite';
  if (score >= 70) return 'excellent';
  if (score >= 50) return 'good';
  if (score >= 30) return 'fair';
  return 'poor';
}

export function ReputationBar({
  score,
  maxScore = 100,
  size = 'md',
  showScore = false,
  showLabel = false,
  showPercentage = false,
  animate = true,
  className,
  barClassName,
}: ReputationBarProps) {
  const normalizedScore = Math.min(Math.max(score, 0), maxScore);
  const percentage = (normalizedScore / maxScore) * 100;
  const band = getReputationBand(normalizedScore);
  const label = getReputationLabel(normalizedScore);
  const color = getReputationColor(normalizedScore);

  return (
    <div className={cn('w-full', className)}>
      {/* Header with score and label */}
      {(showScore || showLabel) && (
        <div className="flex items-center justify-between mb-1.5">
          {showLabel && (
            <span className={cn('text-sm font-medium', getReputationColorClass(normalizedScore))}>
              {label}
            </span>
          )}
          {showScore && (
            <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              {showPercentage ? `${Math.round(percentage)}%` : `${normalizedScore}/${maxScore}`}
            </span>
          )}
        </div>
      )}

      {/* Progress bar */}
      <div
        className={cn(
          'w-full rounded-full overflow-hidden',
          'bg-slate-200 dark:bg-slate-700',
          sizeClasses[size],
          barClassName
        )}
        role="progressbar"
        aria-valuenow={normalizedScore}
        aria-valuemin={0}
        aria-valuemax={maxScore}
        aria-label={`Reputation: ${label} (${normalizedScore}/${maxScore})`}
      >
        <div
          className={cn(
            'h-full rounded-full',
            animate && 'transition-all duration-500 ease-out'
          )}
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
          data-level={band}
        />
      </div>
    </div>
  );
}

/**
 * ReputationScore Component
 *
 * A compact score display with optional badge styling.
 */
export interface ReputationScoreProps {
  /** Reputation score (0-100) */
  score: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show as badge with background */
  badge?: boolean;
  /** Show the label */
  showLabel?: boolean;
  /** Additional CSS classes */
  className?: string;
}

const scoreSizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
};

const badgeSizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export function ReputationScore({
  score,
  size = 'md',
  badge = false,
  showLabel = false,
  className,
}: ReputationScoreProps) {
  const normalizedScore = Math.min(Math.max(score, 0), 100);
  const label = getReputationLabel(normalizedScore);

  if (badge) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full font-semibold',
          badgeSizeClasses[size],
          getReputationBgClass(normalizedScore),
          'text-white',
          className
        )}
      >
        <span>{normalizedScore}</span>
        {showLabel && <span className="font-medium opacity-90">{label}</span>}
      </span>
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1',
        scoreSizeClasses[size],
        'font-semibold',
        getReputationColorClass(normalizedScore),
        className
      )}
    >
      <span>{normalizedScore}</span>
      {showLabel && <span className="font-medium opacity-80">({label})</span>}
    </span>
  );
}

/**
 * ReputationGauge Component
 *
 * A circular gauge for reputation display.
 */
export interface ReputationGaugeProps {
  /** Reputation score (0-100) */
  score: number;
  /** Size in pixels */
  size?: number;
  /** Stroke width */
  strokeWidth?: number;
  /** Show score in center */
  showScore?: boolean;
  /** Show label below score */
  showLabel?: boolean;
  /** Animate the gauge */
  animate?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function ReputationGauge({
  score,
  size = 80,
  strokeWidth = 6,
  showScore = true,
  showLabel = false,
  animate = true,
  className,
}: ReputationGaugeProps) {
  const normalizedScore = Math.min(Math.max(score, 0), 100);
  const label = getReputationLabel(normalizedScore);
  const color = getReputationColor(normalizedScore);

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
        role="img"
        aria-label={`Reputation: ${label} (${normalizedScore}%)`}
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className="stroke-slate-200 dark:stroke-slate-700"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className={cn(animate && 'transition-all duration-700 ease-out')}
        />
      </svg>

      {/* Center content */}
      {(showScore || showLabel) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {showScore && (
            <span
              className={cn(
                'font-bold',
                size >= 100 ? 'text-2xl' : size >= 60 ? 'text-lg' : 'text-sm'
              )}
              style={{ color }}
            >
              {normalizedScore}
            </span>
          )}
          {showLabel && (
            <span
              className={cn(
                'text-slate-500 dark:text-slate-400',
                size >= 100 ? 'text-xs' : 'text-2xs'
              )}
            >
              {label}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * ReputationTrend Component
 *
 * Shows reputation change with trend indicator.
 */
export interface ReputationTrendProps {
  /** Current score */
  current: number;
  /** Previous score (for calculating change) */
  previous?: number;
  /** Direct change value (if previous not provided) */
  change?: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show the current score */
  showScore?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function ReputationTrend({
  current,
  previous,
  change: directChange,
  size = 'md',
  showScore = true,
  className,
}: ReputationTrendProps) {
  const change = useMemo(() => {
    if (directChange !== undefined) return directChange;
    if (previous !== undefined) return current - previous;
    return 0;
  }, [current, previous, directChange]);

  const isPositive = change > 0;
  const isNeutral = change === 0;

  const trendColors = {
    positive: 'text-emerald-500 dark:text-emerald-400',
    negative: 'text-red-500 dark:text-red-400',
    neutral: 'text-slate-400 dark:text-slate-500',
  };

  const trendColor = isNeutral
    ? trendColors.neutral
    : isPositive
    ? trendColors.positive
    : trendColors.negative;

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      {showScore && (
        <ReputationScore score={current} size={size} />
      )}

      <span className={cn('inline-flex items-center gap-0.5', trendColor)}>
        {!isNeutral && (
          <svg
            className={cn(
              'w-4 h-4',
              !isPositive && 'rotate-180'
            )}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
              clipRule="evenodd"
            />
          </svg>
        )}
        <span className={cn(scoreSizeClasses[size], 'font-medium')}>
          {isPositive && '+'}
          {change}
        </span>
      </span>
    </div>
  );
}

export default ReputationBar;
