/**
 * Execution Market Theme System
 *
 * Centralized theme configuration for consistent styling across the dashboard.
 * This file provides type-safe theme tokens and helper functions.
 */

import type { TaskStatus } from '../types/database';

// ============================================================================
// Color Definitions
// ============================================================================

export const colors = {
  // Brand colors
  brand: {
    primary: '#111111',
    primaryLight: '#3f3f46',
    primaryDark: '#000000',
    secondary: '#52525b',
    accent: '#71717a',
  },

  // Task status colors
  taskStatus: {
    published: '#3f3f46',
    accepted: '#52525b',
    in_progress: '#71717a',
    submitted: '#a1a1aa',
    verifying: '#d4d4d8',
    completed: '#111111',
    disputed: '#1f1f1f',
    expired: '#a1a1aa',
    cancelled: '#d4d4d8',
  } as const,

  // Worker level colors
  levelColors: {
    novice: '#d4d4d8',
    apprentice: '#a1a1aa',
    journeyman: '#71717a',
    expert: '#3f3f46',
    master: '#111111',
  } as const,

  // Reputation bands
  reputation: {
    poor: { color: '#d4d4d8', min: 0, max: 30, label: 'Poor' },
    fair: { color: '#a1a1aa', min: 30, max: 50, label: 'Fair' },
    good: { color: '#71717a', min: 50, max: 70, label: 'Good' },
    excellent: { color: '#3f3f46', min: 70, max: 90, label: 'Excellent' },
    elite: { color: '#111111', min: 90, max: 100, label: 'Elite' },
  } as const,

  // Semantic colors
  semantic: {
    success: '#3f3f46',
    warning: '#71717a',
    error: '#1f1f1f',
    info: '#52525b',
  },

  // Background colors
  background: {
    primary: {
      light: '#ffffff',
      dark: '#000000',
    },
    secondary: {
      light: '#f4f4f5',
      dark: '#09090b',
    },
    tertiary: {
      light: '#e4e4e7',
      dark: '#18181b',
    },
    elevated: {
      light: '#ffffff',
      dark: '#09090b',
    },
  },

  // Text colors
  text: {
    primary: {
      light: '#09090b',
      dark: '#fafafa',
    },
    secondary: {
      light: '#3f3f46',
      dark: '#d4d4d8',
    },
    muted: {
      light: '#71717a',
      dark: '#a1a1aa',
    },
    inverse: {
      light: '#fafafa',
      dark: '#09090b',
    },
  },

  // Border colors
  border: {
    default: {
      light: '#d4d4d8',
      dark: '#3f3f46',
    },
    light: {
      light: '#e4e4e7',
      dark: '#52525b',
    },
    focus: '#111111',
  },
} as const;

// ============================================================================
// Status Badge Styles (Tailwind classes)
// ============================================================================

export const statusBadge = {
  published:   'bg-zinc-100 text-zinc-900 ring-1 ring-zinc-300 dark:bg-zinc-900 dark:text-zinc-100 dark:ring-zinc-700',
  accepted:    'bg-zinc-200 text-zinc-900 ring-1 ring-zinc-400 dark:bg-zinc-800 dark:text-zinc-100 dark:ring-zinc-600',
  in_progress: 'bg-zinc-300 text-zinc-900 ring-1 ring-zinc-500 dark:bg-zinc-700 dark:text-zinc-100 dark:ring-zinc-500',
  submitted:   'bg-zinc-800 text-zinc-100 ring-1 ring-zinc-600 dark:bg-zinc-200 dark:text-zinc-900 dark:ring-zinc-400',
  verifying:   'bg-zinc-800 text-zinc-100 ring-1 ring-zinc-600 animate-pulse dark:bg-zinc-200 dark:text-zinc-900',
  completed:   'bg-zinc-900 text-white ring-1 ring-zinc-900 dark:bg-zinc-100 dark:text-zinc-900',
  disputed:    'bg-white text-red-700 ring-2 ring-red-600 dark:bg-zinc-900 dark:text-red-300 dark:ring-red-500',
  expired:     'bg-zinc-100 text-amber-800 line-through ring-1 ring-amber-600/40 dark:bg-zinc-900 dark:text-amber-300 dark:ring-amber-700/50',
  cancelled:   'bg-zinc-100 text-zinc-400 line-through ring-1 ring-zinc-200 dark:bg-zinc-900 dark:text-zinc-500 dark:ring-zinc-800',
} as const;

// statusBadgeWithDot - same map; the new design uses shade-weight progression so the
// "WithDot" variant is redundant. Keep the export for backward compat.
export const statusBadgeWithDot = statusBadge;

// ============================================================================
// Level Badge Styles
// ============================================================================

// Reputation tiers use metallic palette (bronze/silver/gold/platinum) by user choice.
// novice = unranked (zinc neutral); apprentice = bronze; journeyman = silver; expert = gold; master = platinum.
export const levelBadge = {
  novice:     'bg-zinc-100 text-zinc-700 ring-1 ring-zinc-300 dark:bg-zinc-900 dark:text-zinc-300 dark:ring-zinc-700',
  apprentice: 'bg-orange-50 text-orange-900 ring-1 ring-orange-700/40 dark:bg-orange-950/40 dark:text-orange-300 dark:ring-orange-700/50',
  journeyman: 'bg-slate-100 text-slate-800 ring-1 ring-slate-400/60 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-500/60',
  expert:     'bg-yellow-50 text-yellow-800 ring-1 ring-yellow-500/50 dark:bg-yellow-950/40 dark:text-yellow-300 dark:ring-yellow-600/50',
  master:     'bg-sky-50 text-sky-900 ring-1 ring-sky-400/60 dark:bg-sky-950/40 dark:text-sky-200 dark:ring-sky-500/60',
} as const;

// Level badge icon — slightly darker hue so the glyph reads on the soft tinted bg.
export const levelBadgeIcon = {
  novice:     'text-zinc-500 dark:text-zinc-400',
  apprentice: 'text-orange-700 dark:text-orange-400',
  journeyman: 'text-slate-500 dark:text-slate-300',
  expert:     'text-yellow-600 dark:text-yellow-400',
  master:     'text-sky-600 dark:text-sky-400',
} as const;

// ============================================================================
// Spacing Scale
// ============================================================================

export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
  '4xl': '5rem',   // 80px
  '5xl': '6rem',   // 96px
} as const;

// ============================================================================
// Border Radius
// ============================================================================

export const radius = {
  none: '0',
  sm: '0.25rem',   // 4px
  md: '0.375rem',  // 6px
  lg: '0.5rem',    // 8px
  xl: '0.75rem',   // 12px
  '2xl': '1rem',   // 16px
  '3xl': '1.5rem', // 24px
  full: '9999px',
} as const;

// ============================================================================
// Shadows
// ============================================================================

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  glow: '0 0 20px rgba(0, 0, 0, 0.2)',
  glowMd: '0 0 30px rgba(0, 0, 0, 0.25)',
  glowLg: '0 0 40px rgba(0, 0, 0, 0.3)',
  innerGlow: 'inset 0 0 20px rgba(0, 0, 0, 0.08)',
} as const;

// ============================================================================
// Transitions
// ============================================================================

export const transitions = {
  fast: '150ms ease-in-out',
  normal: '200ms ease-in-out',
  slow: '300ms ease-in-out',
  bounce: '300ms cubic-bezier(0.68, -0.55, 0.265, 1.55)',
} as const;

// ============================================================================
// Z-Index Scale
// ============================================================================

export const zIndex = {
  base: 0,
  dropdown: 1000,
  sticky: 1020,
  fixed: 1030,
  modalBackdrop: 1040,
  modal: 1050,
  popover: 1060,
  tooltip: 1070,
  toast: 1080,
} as const;

// ============================================================================
// Breakpoints
// ============================================================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the color for a task status
 */
export function getStatusColor(status: TaskStatus | string): string {
  const normalizedStatus = status.replace('-', '_') as keyof typeof colors.taskStatus;
  return colors.taskStatus[normalizedStatus] || colors.taskStatus.cancelled;
}

/**
 * Get the Tailwind classes for a status badge
 */
export function getStatusBadgeClass(status: TaskStatus | string): string {
  const normalizedStatus = status.replace('-', '_') as keyof typeof statusBadge;
  return statusBadge[normalizedStatus] || statusBadge.cancelled;
}

/**
 * Get the Tailwind classes for a status badge with ring styling
 */
export function getStatusBadgeWithDotClass(status: TaskStatus | string): string {
  const normalizedStatus = status.replace('-', '_') as keyof typeof statusBadgeWithDot;
  return statusBadgeWithDot[normalizedStatus] || statusBadgeWithDot.cancelled;
}

/**
 * Get the color for a worker level
 */
export function getLevelColor(level: string): string {
  const normalizedLevel = level.toLowerCase() as keyof typeof colors.levelColors;
  return colors.levelColors[normalizedLevel] || colors.levelColors.novice;
}

/**
 * Get the Tailwind classes for a level badge
 */
export function getLevelBadgeClass(level: string): string {
  const normalizedLevel = level.toLowerCase() as keyof typeof levelBadge;
  return levelBadge[normalizedLevel] || levelBadge.novice;
}

/**
 * Get the icon color class for a level
 */
export function getLevelIconClass(level: string): string {
  const normalizedLevel = level.toLowerCase() as keyof typeof levelBadgeIcon;
  return levelBadgeIcon[normalizedLevel] || levelBadgeIcon.novice;
}

/**
 * Get the color for a reputation score
 */
export function getReputationColor(score: number): string {
  if (score >= 90) return colors.reputation.elite.color;
  if (score >= 70) return colors.reputation.excellent.color;
  if (score >= 50) return colors.reputation.good.color;
  if (score >= 30) return colors.reputation.fair.color;
  return colors.reputation.poor.color;
}

/**
 * Get the label for a reputation score
 */
export function getReputationLabel(score: number): string {
  if (score >= 90) return colors.reputation.elite.label;
  if (score >= 70) return colors.reputation.excellent.label;
  if (score >= 50) return colors.reputation.good.label;
  if (score >= 30) return colors.reputation.fair.label;
  return colors.reputation.poor.label;
}

/**
 * Get the Tailwind color class for a reputation score.
 * Reputation bar/score is monochromatic; the tier label (levelBadge) carries the metallic accent.
 */
export function getReputationColorClass(_score: number): string {
  return 'text-zinc-900 dark:text-zinc-100';
}

/**
 * Get the Tailwind background class for a reputation score.
 */
export function getReputationBgClass(_score: number): string {
  return 'bg-zinc-900 dark:bg-zinc-100';
}

/**
 * Format a status for display
 */
export function formatStatus(status: TaskStatus | string): string {
  return status
    .replace(/_/g, ' ')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

/**
 * Check if a status is considered active/in-flight
 */
export function isActiveStatus(status: TaskStatus | string): boolean {
  const activeStatuses = ['accepted', 'in_progress', 'submitted', 'verifying'];
  return activeStatuses.includes(status.replace('-', '_'));
}

/**
 * Check if a status is terminal (no further changes expected)
 */
export function isTerminalStatus(status: TaskStatus | string): boolean {
  const terminalStatuses = ['completed', 'expired', 'cancelled'];
  return terminalStatuses.includes(status.replace('-', '_'));
}

/**
 * Get status dot animation class
 */
export function getStatusDotAnimationClass(status: TaskStatus | string): string {
  const animatedStatuses = ['verifying', 'disputed'];
  const normalizedStatus = status.replace('-', '_');
  return animatedStatuses.includes(normalizedStatus) ? 'animate-pulse' : '';
}

// ============================================================================
// Theme Object (for export)
// ============================================================================

export const theme = {
  colors,
  statusBadge,
  statusBadgeWithDot,
  levelBadge,
  levelBadgeIcon,
  spacing,
  radius,
  shadows,
  transitions,
  zIndex,
  breakpoints,
} as const;

// ============================================================================
// Type Exports
// ============================================================================

export type WorkerLevel = keyof typeof colors.levelColors;
export type ReputationBand = keyof typeof colors.reputation;
export type ThemeColors = typeof colors;
export type Theme = typeof theme;

export default theme;
