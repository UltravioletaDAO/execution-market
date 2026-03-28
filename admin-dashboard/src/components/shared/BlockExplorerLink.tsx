interface BlockExplorerLinkProps {
  txHash: string
  network?: string
  label?: string
}

const EXPLORER_MAP: Record<string, string> = {
  base: 'https://basescan.org',
  ethereum: 'https://etherscan.io',
  polygon: 'https://polygonscan.com',
  arbitrum: 'https://arbiscan.io',
  optimism: 'https://optimistic.etherscan.io',
  avalanche: 'https://snowscan.xyz',
  celo: 'https://celoscan.io',
  monad: 'https://explorer.monad.xyz',
  skale: 'https://elated-tan-skat.explorer.mainnet.skalenodes.com',
  solana: 'https://solscan.io',
}

function getExplorerUrl(txHash: string, network: string): string {
  const baseUrl = EXPLORER_MAP[network] || EXPLORER_MAP.base

  if (network === 'solana') {
    return `${baseUrl}/tx/${txHash}`
  }

  return `${baseUrl}/tx/${txHash}`
}

function truncateHash(hash: string): string {
  if (hash.length <= 16) return hash
  return `${hash.slice(0, 8)}...${hash.slice(-4)}`
}

export default function BlockExplorerLink({
  txHash,
  network = 'base',
  label,
}: BlockExplorerLinkProps) {
  const url = getExplorerUrl(txHash, network)
  const displayText = label || truncateHash(txHash)

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-em-400 hover:text-em-300 font-mono text-sm transition-colors"
    >
      {displayText}
      <svg
        className="w-3.5 h-3.5 flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
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
