/**
 * PaymentStatusBadge - Color-coded badge for payment/escrow status
 *
 * Displays the current payment status with:
 * - Color-coded badge (green/blue/yellow/red/gray)
 * - Optional link to BaseScan when txHash is provided
 * - Consistent styling with the existing Badge/StatusBadge components
 *
 * Status colors:
 * - released/completed: green (payment sent)
 * - authorized/escrowed: blue (funds locked)
 * - pending: yellow (awaiting action)
 * - cancelled/refunded: red (returned/voided)
 * - expired/failed: gray (terminal state)
 */

import { cn } from '../lib/utils';
import { getExplorerUrl } from '../utils/blockchain';

export interface PaymentStatusBadgeProps {
  /** Payment/escrow status string */
  status: string;
  /** Optional transaction hash for explorer link */
  txHash?: string | null;
  /** Network for explorer URL (default: "base") */
  network?: string;
  /** Additional CSS classes */
  className?: string;
}

/** Status color configuration */
interface StatusConfig {
  bg: string;
  text: string;
  border: string;
  darkBg: string;
  darkText: string;
  label: string;
  icon: JSX.Element;
}

/**
 * Get configuration for a payment status.
 *
 * Returns color classes, label, and icon for the given status string.
 * Falls back to gray/unknown for unrecognized statuses.
 */
function getStatusConfig(status: string): StatusConfig {
  const normalized = status.toLowerCase().replace(/[\s-]/g, '_');

  const configs: Record<string, StatusConfig> = {
    released: {
      bg: 'bg-emerald-100',
      text: 'text-emerald-800',
      border: 'border-emerald-200',
      darkBg: 'dark:bg-emerald-900/30',
      darkText: 'dark:text-emerald-400',
      label: 'Released',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    completed: {
      bg: 'bg-emerald-100',
      text: 'text-emerald-800',
      border: 'border-emerald-200',
      darkBg: 'dark:bg-emerald-900/30',
      darkText: 'dark:text-emerald-400',
      label: 'Completed',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    authorized: {
      bg: 'bg-blue-100',
      text: 'text-blue-800',
      border: 'border-blue-200',
      darkBg: 'dark:bg-blue-900/30',
      darkText: 'dark:text-blue-400',
      label: 'Authorized',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      ),
    },
    escrowed: {
      bg: 'bg-blue-100',
      text: 'text-blue-800',
      border: 'border-blue-200',
      darkBg: 'dark:bg-blue-900/30',
      darkText: 'dark:text-blue-400',
      label: 'Escrowed',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      ),
    },
    pending: {
      bg: 'bg-amber-100',
      text: 'text-amber-800',
      border: 'border-amber-200',
      darkBg: 'dark:bg-amber-900/30',
      darkText: 'dark:text-amber-400',
      label: 'Pending',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    cancelled: {
      bg: 'bg-red-100',
      text: 'text-red-800',
      border: 'border-red-200',
      darkBg: 'dark:bg-red-900/30',
      darkText: 'dark:text-red-400',
      label: 'Cancelled',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      ),
    },
    refunded: {
      bg: 'bg-red-100',
      text: 'text-red-800',
      border: 'border-red-200',
      darkBg: 'dark:bg-red-900/30',
      darkText: 'dark:text-red-400',
      label: 'Refunded',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
        </svg>
      ),
    },
    disputed: {
      bg: 'bg-orange-100',
      text: 'text-orange-800',
      border: 'border-orange-200',
      darkBg: 'dark:bg-orange-900/30',
      darkText: 'dark:text-orange-400',
      label: 'Disputed',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
    expired: {
      bg: 'bg-slate-100',
      text: 'text-slate-600',
      border: 'border-slate-200',
      darkBg: 'dark:bg-slate-800',
      darkText: 'dark:text-slate-400',
      label: 'Expired',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    failed: {
      bg: 'bg-slate-100',
      text: 'text-slate-600',
      border: 'border-slate-200',
      darkBg: 'dark:bg-slate-800',
      darkText: 'dark:text-slate-400',
      label: 'Failed',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
    charged: {
      bg: 'bg-emerald-100',
      text: 'text-emerald-800',
      border: 'border-emerald-200',
      darkBg: 'dark:bg-emerald-900/30',
      darkText: 'dark:text-emerald-400',
      label: 'Charged',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
    },
    partial_released: {
      bg: 'bg-purple-100',
      text: 'text-purple-800',
      border: 'border-purple-200',
      darkBg: 'dark:bg-purple-900/30',
      darkText: 'dark:text-purple-400',
      label: 'Partial',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      ),
    },
  };

  // Fallback for unknown statuses
  const fallback: StatusConfig = {
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    border: 'border-slate-200',
    darkBg: 'dark:bg-slate-800',
    darkText: 'dark:text-slate-400',
    label: status.charAt(0).toUpperCase() + status.slice(1).toLowerCase(),
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  return configs[normalized] || fallback;
}

export function PaymentStatusBadge({
  status,
  txHash,
  network = 'base',
  className,
}: PaymentStatusBadgeProps) {
  const config = getStatusConfig(status);

  const badgeContent = (
    <span
      className={cn(
        'inline-flex items-center gap-1.5',
        'px-2.5 py-1 text-xs font-medium',
        'rounded-full border',
        config.bg,
        config.text,
        config.border,
        config.darkBg,
        config.darkText,
        txHash && 'cursor-pointer hover:opacity-80 transition-opacity',
        className
      )}
    >
      {config.icon}
      {config.label}
      {/* Small external link indicator when clickable */}
      {txHash && (
        <svg
          className="w-3 h-3 opacity-60"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
          />
        </svg>
      )}
    </span>
  );

  // Wrap in anchor if txHash is provided
  if (txHash) {
    return (
      <a
        href={getExplorerUrl(txHash, network)}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 rounded-full"
        title={`View transaction on explorer: ${txHash}`}
        aria-label={`Payment status: ${config.label}. Click to view transaction on block explorer.`}
      >
        {badgeContent}
      </a>
    );
  }

  return badgeContent;
}

export default PaymentStatusBadge;
