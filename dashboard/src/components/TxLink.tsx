/**
 * TxLink - Transaction hash link to block explorer
 *
 * Canonical component for displaying transaction hashes with:
 * - Truncated hash display (monospace font)
 * - Direct link to block explorer
 * - Copy-to-clipboard on hash text click
 * - Brief "Copied!" feedback tooltip
 * - External link icon
 * - Network name display option
 *
 * Used across PaymentStatus, PaymentHistory, TaskDetail, and agent dashboard.
 */

import { useState, useCallback } from 'react'
import { getExplorerUrl, truncateHash, getNetworkDisplayName, isValidTxHash } from '../utils/blockchain'
import { copyToClipboard } from '../lib/utils'

export interface TxLinkProps {
  /** The transaction hash to display */
  txHash: string | null | undefined
  /** Network for explorer URL (default: "base") */
  network?: string
  /** Show the network name next to the hash (default: false) */
  showNetwork?: boolean
  /** Optional label to display instead of the truncated hash */
  label?: string
  /** Show external link icon (default: true) */
  showIcon?: boolean
  /** Additional CSS classes */
  className?: string
}

// Keep old name as alias for backward compatibility during migration
export type TxHashLinkProps = TxLinkProps

export function TxLink({ txHash, network = 'base', showNetwork = false, label, showIcon = true, className = '' }: TxLinkProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (!txHash) return

      const success = await copyToClipboard(txHash)
      if (success) {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    },
    [txHash]
  )

  if (!txHash || txHash.trim() === '') return null

  const isTx = isValidTxHash(txHash)
  const url = isTx ? getExplorerUrl(txHash, network) : null
  const displayText = label || truncateHash(txHash)

  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      {/* Copyable hash text */}
      <button
        type="button"
        onClick={handleCopy}
        className={`relative inline-flex items-center gap-1 font-mono text-sm transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 rounded-sm ${
          isTx ? 'text-blue-600 hover:text-blue-700' : 'text-gray-600'
        }`}
        title={copied ? undefined : txHash}
        aria-label={`Copy reference ${txHash}`}
      >
        <span>{displayText}</span>
        {copied && (
          <span
            className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 text-xs font-medium bg-gray-900 text-white rounded-md shadow-sm whitespace-nowrap animate-fade-in"
            role="status"
            aria-live="polite"
          >
            Copied!
          </span>
        )}
      </button>

      {showNetwork && (
        <span className="text-gray-400 font-normal text-xs">({getNetworkDisplayName(network)})</span>
      )}

      {/* Explorer link — only for valid tx hashes */}
      {showIcon && url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0 text-blue-600 hover:text-blue-700 transition-colors"
          title="View on explorer"
          aria-label="View transaction on block explorer"
        >
          <svg
            className="w-3 h-3"
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
        </a>
      )}
    </span>
  )
}

// Alias for backward compatibility
export const TxHashLink = TxLink

export default TxLink
