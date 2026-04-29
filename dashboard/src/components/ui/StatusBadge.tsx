import type { TaskStatus } from '../../types/database';
import { getStatusBadgeClass, getStatusDotClass, formatStatus } from '../../lib/taskStatus';
import { cn } from '../../lib/utils';

export type StatusBadgeSize = 'sm' | 'md';

export interface StatusBadgeProps {
  status: TaskStatus | string;
  size?: StatusBadgeSize;
  /** Optional override label. Defaults to formatStatus(status). */
  label?: string;
  /** Render the small leading dot — useful for active-list rows. */
  withDot?: boolean;
  className?: string;
}

const sizeClasses: Record<StatusBadgeSize, string> = {
  sm: 'px-2 py-0.5 text-xs gap-1.5',
  md: 'px-2.5 py-1 text-sm gap-2',
};

export function StatusBadge({ status, size = 'sm', label, withDot, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full whitespace-nowrap',
        sizeClasses[size],
        getStatusBadgeClass(status),
        className,
      )}
    >
      {withDot && (
        <span
          aria-hidden="true"
          className={cn('w-1.5 h-1.5 rounded-full', getStatusDotClass(status))}
        />
      )}
      {label ?? formatStatus(status)}
    </span>
  );
}

export default StatusBadge;
