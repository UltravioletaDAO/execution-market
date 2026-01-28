/**
 * Skeleton Component
 *
 * Loading placeholder components for various UI elements.
 * Provides visual feedback while content is loading.
 */

import { type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';

// ============================================================================
// Base Skeleton
// ============================================================================

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /** Animation variant */
  animation?: 'pulse' | 'shimmer' | 'none';
  /** Whether the skeleton is circular */
  circle?: boolean;
  /** Width (can be a number for px or string for any CSS unit) */
  width?: number | string;
  /** Height (can be a number for px or string for any CSS unit) */
  height?: number | string;
}

export function Skeleton({
  animation = 'pulse',
  circle = false,
  width,
  height,
  className,
  style,
  ...props
}: SkeletonProps) {
  return (
    <div
      className={cn(
        'bg-slate-200 dark:bg-slate-700',
        circle ? 'rounded-full' : 'rounded',
        animation === 'pulse' && 'animate-pulse',
        animation === 'shimmer' && 'animate-shimmer bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 dark:from-slate-700 dark:via-slate-600 dark:to-slate-700 bg-[length:200%_100%]',
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        ...style,
      }}
      aria-hidden="true"
      {...props}
    />
  );
}

// ============================================================================
// Skeleton Text
// ============================================================================

export interface SkeletonTextProps extends Omit<SkeletonProps, 'circle'> {
  /** Number of lines */
  lines?: number;
  /** Width for the last line (percentage) */
  lastLineWidth?: string;
  /** Gap between lines */
  gap?: 'sm' | 'md' | 'lg';
}

const gapClasses = {
  sm: 'gap-1.5',
  md: 'gap-2',
  lg: 'gap-3',
};

export function SkeletonText({
  lines = 1,
  lastLineWidth = '75%',
  gap = 'md',
  height = 16,
  className,
  ...props
}: SkeletonTextProps) {
  return (
    <div className={cn('flex flex-col', gapClasses[gap], className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height={height}
          width={index === lines - 1 && lines > 1 ? lastLineWidth : '100%'}
          {...props}
        />
      ))}
    </div>
  );
}

// ============================================================================
// Skeleton Avatar
// ============================================================================

export interface SkeletonAvatarProps extends Omit<SkeletonProps, 'circle'> {
  /** Size variant */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

const avatarSizes = {
  xs: 24,
  sm: 32,
  md: 40,
  lg: 48,
  xl: 64,
};

export function SkeletonAvatar({
  size = 'md',
  className,
  ...props
}: SkeletonAvatarProps) {
  const dimension = avatarSizes[size];
  return (
    <Skeleton
      circle
      width={dimension}
      height={dimension}
      className={className}
      {...props}
    />
  );
}

// ============================================================================
// Skeleton Button
// ============================================================================

export interface SkeletonButtonProps extends Omit<SkeletonProps, 'circle'> {
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Full width */
  fullWidth?: boolean;
}

const buttonSizes = {
  sm: { width: 80, height: 32 },
  md: { width: 100, height: 40 },
  lg: { width: 120, height: 48 },
};

export function SkeletonButton({
  size = 'md',
  fullWidth = false,
  className,
  ...props
}: SkeletonButtonProps) {
  const dimensions = buttonSizes[size];
  return (
    <Skeleton
      width={fullWidth ? '100%' : dimensions.width}
      height={dimensions.height}
      className={cn('rounded-lg', className)}
      {...props}
    />
  );
}

// ============================================================================
// Skeleton Card
// ============================================================================

export interface SkeletonCardProps extends Omit<SkeletonProps, 'children'> {
  /** Show header section */
  header?: boolean;
  /** Show footer section */
  footer?: boolean;
  /** Number of content lines */
  lines?: number;
  /** Show avatar in header */
  avatar?: boolean;
}

export function SkeletonCard({
  header = true,
  footer = false,
  lines = 3,
  avatar = false,
  className,
  ...props
}: SkeletonCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 dark:border-slate-700',
        'bg-white dark:bg-slate-800',
        'overflow-hidden',
        className
      )}
      {...props}
    >
      {header && (
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            {avatar && <SkeletonAvatar size="md" />}
            <div className="flex-1">
              <Skeleton height={20} width="60%" />
              <Skeleton height={16} width="40%" className="mt-2" />
            </div>
          </div>
        </div>
      )}
      <div className="p-4">
        <SkeletonText lines={lines} />
      </div>
      {footer && (
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <div className="flex justify-end gap-2">
            <SkeletonButton size="sm" />
            <SkeletonButton size="sm" />
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Skeleton Task Card
// ============================================================================

export interface SkeletonTaskCardProps extends Omit<SkeletonProps, 'children'> {
  /** Show location badge */
  showLocation?: boolean;
  /** Show reputation requirement */
  showReputation?: boolean;
}

export function SkeletonTaskCard({
  showLocation = true,
  showReputation = false,
  className,
  ...props
}: SkeletonTaskCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 dark:border-slate-700',
        'bg-white dark:bg-slate-800',
        'p-4',
        className
      )}
      {...props}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <Skeleton width={24} height={24} />
          <Skeleton width={100} height={14} />
        </div>
        <Skeleton width={80} height={22} className="rounded-full" />
      </div>

      {/* Title */}
      <Skeleton width="90%" height={20} className="mb-2" />

      {/* Description */}
      <SkeletonText lines={2} height={14} className="mb-3" />

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-700">
        <Skeleton width={80} height={24} />
        <div className="flex items-center gap-1">
          <Skeleton width={16} height={16} />
          <Skeleton width={60} height={14} />
        </div>
      </div>

      {/* Location */}
      {showLocation && (
        <div className="mt-3 flex items-center gap-1">
          <Skeleton width={12} height={12} />
          <Skeleton width={120} height={12} />
        </div>
      )}

      {/* Reputation */}
      {showReputation && (
        <div className="mt-2 flex items-center gap-1">
          <Skeleton width={12} height={12} />
          <Skeleton width={140} height={12} />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Skeleton Stat Card
// ============================================================================

export function SkeletonStatCard({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 dark:border-slate-700',
        'bg-white dark:bg-slate-800',
        'p-6',
        className
      )}
      {...props}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Skeleton width={120} height={32} className="mb-2" />
          <Skeleton width={80} height={16} />
          <Skeleton width={100} height={16} className="mt-3" />
        </div>
        <Skeleton width={48} height={48} className="rounded-lg" />
      </div>
    </div>
  );
}

// ============================================================================
// Skeleton Table
// ============================================================================

export interface SkeletonTableProps extends Omit<SkeletonProps, 'children'> {
  /** Number of columns */
  columns?: number;
  /** Number of rows */
  rows?: number;
  /** Show table header */
  header?: boolean;
}

export function SkeletonTable({
  columns = 4,
  rows = 5,
  header = true,
  className,
  ...props
}: SkeletonTableProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-slate-200 dark:border-slate-700',
        'overflow-hidden',
        className
      )}
      {...props}
    >
      <table className="w-full">
        {header && (
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-800/50">
              {Array.from({ length: columns }).map((_, index) => (
                <th key={index} className="px-4 py-3">
                  <Skeleton width={index === 0 ? '70%' : '50%'} height={14} />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr
              key={rowIndex}
              className="border-t border-slate-200 dark:border-slate-700"
            >
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-4 py-3">
                  <Skeleton
                    width={colIndex === 0 ? '80%' : `${50 + Math.random() * 30}%`}
                    height={16}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================================
// Skeleton List
// ============================================================================

export interface SkeletonListProps extends Omit<SkeletonProps, 'children'> {
  /** Number of items */
  items?: number;
  /** Show avatars */
  avatar?: boolean;
  /** Item variant */
  variant?: 'simple' | 'detailed';
}

export function SkeletonList({
  items = 3,
  avatar = false,
  variant = 'simple',
  className,
  ...props
}: SkeletonListProps) {
  return (
    <div className={cn('space-y-4', className)} {...props}>
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} className="flex items-start gap-3">
          {avatar && <SkeletonAvatar size="md" />}
          <div className="flex-1">
            <Skeleton
              width={variant === 'detailed' ? '70%' : '100%'}
              height={variant === 'detailed' ? 18 : 16}
            />
            {variant === 'detailed' && (
              <>
                <Skeleton width="90%" height={14} className="mt-2" />
                <Skeleton width="60%" height={14} className="mt-1" />
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Skeleton Profile
// ============================================================================

export function SkeletonProfile({ className, ...props }: SkeletonProps) {
  return (
    <div className={cn('flex flex-col items-center text-center', className)} {...props}>
      <SkeletonAvatar size="xl" />
      <Skeleton width={150} height={24} className="mt-4" />
      <Skeleton width={200} height={16} className="mt-2" />
      <div className="flex gap-6 mt-4">
        <div className="text-center">
          <Skeleton width={50} height={24} />
          <Skeleton width={70} height={14} className="mt-1" />
        </div>
        <div className="text-center">
          <Skeleton width={50} height={24} />
          <Skeleton width={70} height={14} className="mt-1" />
        </div>
        <div className="text-center">
          <Skeleton width={50} height={24} />
          <Skeleton width={70} height={14} className="mt-1" />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Skeleton Wrapper (for custom content)
// ============================================================================

export interface SkeletonWrapperProps {
  /** Whether to show skeleton or children */
  loading: boolean;
  /** Skeleton to show when loading */
  skeleton: ReactNode;
  /** Content to show when not loading */
  children: ReactNode;
}

export function SkeletonWrapper({
  loading,
  skeleton,
  children,
}: SkeletonWrapperProps) {
  if (loading) {
    return <>{skeleton}</>;
  }
  return <>{children}</>;
}

export default Skeleton;
