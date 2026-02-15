/**
 * TxHashLink - Blockchain transaction hash display with explorer link
 *
 * A shared component for displaying transaction hashes with:
 * - Truncated hash display (monospace font)
 * - Direct link to BaseScan (or other explorers)
 * - Copy-to-clipboard on hash text click
 * - Brief "Copied!" feedback tooltip
 * - External link icon
 *
 * Used across PaymentStatus, PaymentHistory, TaskDetail, and agent dashboard.
 */

import { useState, useCallback } from 'react';
import { cn } from '../lib/utils';
import { copyToClipboard } from '../lib/utils';
import { getExplorerUrl, truncateHash, isValidTxHash } from '../utils/blockchain';

export interface TxHashLinkProps {
  /** The transaction hash to display */
  txHash: string | null | undefined;
  /** Network for explorer URL (default: "base") */
  network?: string;
  /** Optional label to display instead of the truncated hash */
  label?: string;
  /** Show external link icon (default: true) */
  showIcon?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * External link icon (inline SVG matching project conventions)
 */
function ExternalLinkIcon({ className }: { className?: string }) {
  return (
    <svg
      className={cn('w-3.5 h-3.5', className)}
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
  );
}

/**
 * Copy icon (inline SVG)
 */
function CopyIcon({ className }: { className?: string }) {
  return (
    <svg
      className={cn('w-3.5 h-3.5', className)}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
      />
    </svg>
  );
}

export function TxHashLink({
  txHash,
  network = 'base',
  label,
  showIcon = true,
  className,
}: TxHashLinkProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!txHash) return;

      const success = await copyToClipboard(txHash);
      if (success) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    },
    [txHash]
  );

  // Render nothing if no hash provided
  if (!txHash || txHash.trim() === '') {
    return null;
  }

  // Only link to explorer for valid tx hashes (0x-prefixed, 66 chars)
  // x402 references like "x402_auth_..." are not valid explorer links
  const isTxHash = isValidTxHash(txHash);
  const explorerUrl = isTxHash ? getExplorerUrl(txHash, network) : null;
  const displayText = label || truncateHash(txHash);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5',
        className
      )}
    >
      {/* Copyable hash text */}
      <button
        type="button"
        onClick={handleCopy}
        className={cn(
          'relative inline-flex items-center gap-1',
          'font-mono text-sm',
          isTxHash
            ? 'text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300'
            : 'text-gray-600 dark:text-gray-400',
          'transition-colors cursor-pointer',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 rounded-sm'
        )}
        title={copied ? undefined : txHash}
        aria-label={`Copy reference ${txHash}`}
      >
        <CopyIcon className="opacity-0 group-hover:opacity-100 transition-opacity" />
        <span>{displayText}</span>

        {/* Copied feedback tooltip */}
        {copied && (
          <span
            className={cn(
              'absolute -top-8 left-1/2 -translate-x-1/2',
              'px-2 py-1 text-xs font-medium',
              'bg-gray-900 text-white rounded-md shadow-sm',
              'dark:bg-gray-700',
              'whitespace-nowrap',
              'animate-fade-in'
            )}
            role="status"
            aria-live="polite"
          >
            Copied!
          </span>
        )}
      </button>

      {/* Explorer link — only for valid tx hashes */}
      {showIcon && explorerUrl && (
        <a
          href={explorerUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            'flex-shrink-0',
            'text-blue-600 hover:text-blue-700',
            'dark:text-blue-400 dark:hover:text-blue-300',
            'transition-colors'
          )}
          title="View on explorer"
          aria-label="View transaction on block explorer"
        >
          <ExternalLinkIcon />
        </a>
      )}
    </span>
  );
}

export default TxHashLink;
