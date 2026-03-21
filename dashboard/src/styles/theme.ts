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
  published: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  accepted: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-400',
  in_progress: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  submitted: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  verifying: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  completed: 'bg-green-600 text-white dark:bg-green-700 dark:text-white',
  disputed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  expired: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-800/30 dark:text-gray-500',
} as const;

// Status badge with dot indicator
export const statusBadgeWithDot = {
  published: 'bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20',
  accepted: 'bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-600/20 dark:bg-violet-500/10 dark:text-violet-400 dark:ring-violet-500/20',
  in_progress: 'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20',
  submitted: 'bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/20',
  verifying: 'bg-purple-50 text-purple-700 ring-1 ring-inset ring-purple-600/20 dark:bg-purple-500/10 dark:text-purple-400 dark:ring-purple-500/20',
  completed: 'bg-green-100 text-green-700 ring-1 ring-inset ring-green-600/20 dark:bg-green-500/10 dark:text-green-400 dark:ring-green-500/20',
  disputed: 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20',
  expired: 'bg-gray-50 text-gray-700 ring-1 ring-inset ring-gray-600/20 dark:bg-gray-500/10 dark:text-gray-400 dark:ring-gray-500/20',
  cancelled: 'bg-gray-50 text-gray-600 ring-1 ring-inset ring-gray-500/20 dark:bg-gray-500/10 dark:text-gray-500 dark:ring-gray-500/20',
} as const;

// ============================================================================
// Level Badge Styles
// ============================================================================

export const levelBadge = {
  novice: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
  apprentice: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  journeyman: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-400',
  expert: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  master: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
} as const;

// Level badge with icon styling
export const levelBadgeIcon = {
  novice: 'text-gray-400 dark:text-gray-500',
  apprentice: 'text-blue-500 dark:text-blue-400',
  journeyman: 'text-violet-500 dark:text-violet-400',
  expert: 'text-amber-500 dark:text-amber-400',
  master: 'text-red-500 dark:text-red-400',
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
 * Get the Tailwind color class for a reputation score
 */
export function getReputationColorClass(score: number): string {
  if (score >= 90) return 'text-violet-500 dark:text-violet-400';
  if (score >= 70) return 'text-blue-500 dark:text-blue-400';
  if (score >= 50) return 'text-emerald-500 dark:text-emerald-400';
  if (score >= 30) return 'text-amber-500 dark:text-amber-400';
  return 'text-red-500 dark:text-red-400';
}

/**
 * Get the Tailwind background class for a reputation score
 */
export function getReputationBgClass(score: number): string {
  if (score >= 90) return 'bg-violet-500';
  if (score >= 70) return 'bg-blue-500';
  if (score >= 50) return 'bg-emerald-500';
  if (score >= 30) return 'bg-amber-500';
  return 'bg-red-500';
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
