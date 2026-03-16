/**
 * TxLink - Transaction hash link to block explorer
 *
 * Maps network to the appropriate block explorer URL and shows
 * a truncated hash with an external link icon.
 */

import { getExplorerUrl, truncateHash, getNetworkDisplayName } from '../utils/blockchain'

interface TxLinkProps {
  txHash: string
  network: string
  /** Show the network name next to the hash (default: false) */
  showNetwork?: boolean
  /** Additional CSS classes */
  className?: string
}

export function TxLink({ txHash, network, showNetwork = false, className = '' }: TxLinkProps) {
  if (!txHash) return null

  const url = getExplorerUrl(txHash, network)
  const truncated = truncateHash(txHash)

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 transition-colors ${className}`}
    >
      <span className="font-mono">{truncated}</span>
      {showNetwork && (
        <span className="text-gray-400 font-normal">({getNetworkDisplayName(network)})</span>
      )}
      <svg
        className="w-3 h-3 flex-shrink-0"
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
  )
}

export default TxLink
