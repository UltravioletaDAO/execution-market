/**
 * Single source of truth for task status semantics.
 *
 * Replaces the 4+ duplicated STATUS_COLORS / STATUS_STYLES / STATUS_CONFIG
 * Records that lived in TaskCard.tsx, TaskDetailModal.tsx, AgentDashboard.tsx,
 * agent/TaskManagement.tsx, and AuditGrid.tsx.
 *
 * Phase 2 will wrap these into a <StatusBadge status={...} /> primitive.
 */

import type { TaskStatus } from '../types/database';

/**
 * Tailwind classes for a task-status pill.
 * Monochromatic shade-weight progression: lifecycle moves "darker" toward completion.
 * Disputed = ring-2 (visual loud without color). Animations carry semantic load.
 */
export const STATUS_BADGE: Record<TaskStatus, string> = {
  published:   'bg-zinc-100 text-zinc-900 ring-1 ring-zinc-300 dark:bg-zinc-900 dark:text-zinc-100 dark:ring-zinc-700',
  accepted:    'bg-zinc-200 text-zinc-900 ring-1 ring-zinc-400 dark:bg-zinc-800 dark:text-zinc-100 dark:ring-zinc-600',
  in_progress: 'bg-zinc-300 text-zinc-900 ring-1 ring-zinc-500 dark:bg-zinc-700 dark:text-zinc-100',
  submitted:   'bg-zinc-800 text-zinc-100 ring-1 ring-zinc-600 dark:bg-zinc-200 dark:text-zinc-900',
  verifying:   'bg-zinc-800 text-zinc-100 ring-1 ring-zinc-600 animate-pulse dark:bg-zinc-200 dark:text-zinc-900',
  completed:   'bg-zinc-900 text-white ring-1 ring-zinc-900 dark:bg-zinc-100 dark:text-zinc-900',
  disputed:    'bg-white text-red-700 ring-2 ring-red-600 dark:bg-zinc-900 dark:text-red-300 dark:ring-red-500',
  expired:     'bg-zinc-100 text-amber-800 line-through ring-1 ring-amber-600/40 dark:bg-zinc-900 dark:text-amber-300 dark:ring-amber-700/50',
  cancelled:   'bg-zinc-100 text-zinc-400 line-through ring-1 ring-zinc-200 dark:bg-zinc-900 dark:text-zinc-500 dark:ring-zinc-800',
};

/**
 * Status-dot classes (for the small circle next to a status label).
 * Uses animation, not hue, to communicate "verifying" / "disputed".
 */
export const STATUS_DOT: Record<TaskStatus, string> = {
  published:   'bg-zinc-900 dark:bg-zinc-100',
  accepted:    'bg-zinc-900 dark:bg-zinc-100',
  in_progress: 'bg-zinc-900 dark:bg-zinc-100',
  submitted:   'bg-zinc-900 dark:bg-zinc-100',
  verifying:   'bg-zinc-900 dark:bg-zinc-100 animate-pulse',
  completed:   'bg-zinc-900 dark:bg-zinc-100',
  disputed:    'bg-red-600 ring-2 ring-red-600 ring-offset-2 ring-offset-white animate-pulse dark:ring-offset-black',
  expired:     'bg-amber-600 dark:bg-amber-500',
  cancelled:   'bg-zinc-400 dark:bg-zinc-600',
};

/**
 * Border-left accent for task cards. Width is the affordance for "active" states.
 */
export const STATUS_BORDER_L: Record<TaskStatus, string> = {
  published:   'border-l-zinc-300 dark:border-l-zinc-700',
  accepted:    'border-l-zinc-300 dark:border-l-zinc-700',
  in_progress: 'border-l-zinc-300 dark:border-l-zinc-700',
  submitted:   'border-l-zinc-900 dark:border-l-zinc-100',
  verifying:   'border-l-zinc-900 dark:border-l-zinc-100',
  completed:   'border-l-zinc-900 dark:border-l-zinc-100',
  disputed:    'border-l-red-600 border-l-[6px] dark:border-l-red-500',
  expired:     'border-l-amber-600 dark:border-l-amber-500',
  cancelled:   'border-l-zinc-200 dark:border-l-zinc-800',
};

export function getStatusBadgeClass(status: TaskStatus | string): string {
  const key = String(status).replace('-', '_') as TaskStatus;
  return STATUS_BADGE[key] ?? STATUS_BADGE.cancelled;
}

export function getStatusDotClass(status: TaskStatus | string): string {
  const key = String(status).replace('-', '_') as TaskStatus;
  return STATUS_DOT[key] ?? STATUS_DOT.cancelled;
}

export function getStatusBorderLeftClass(status: TaskStatus | string): string {
  const key = String(status).replace('-', '_') as TaskStatus;
  return STATUS_BORDER_L[key] ?? STATUS_BORDER_L.cancelled;
}

/** Human-friendly label, kept here so consumers don't reimplement a switch each time. */
export function formatStatus(status: TaskStatus | string): string {
  return String(status).replace(/[_-]+/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}

export function isActiveStatus(status: TaskStatus | string): boolean {
  return ['accepted', 'in_progress', 'submitted', 'verifying'].includes(String(status).replace('-', '_'));
}

export function isTerminalStatus(status: TaskStatus | string): boolean {
  return ['completed', 'expired', 'cancelled'].includes(String(status).replace('-', '_'));
}
