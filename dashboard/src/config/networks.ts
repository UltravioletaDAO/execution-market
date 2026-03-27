/**
 * Network configuration — single source of truth for the dashboard.
 *
 * When adding a new chain:
 *   1. Add an entry to NETWORKS below
 *   2. Add the chain to wagmi.ts (import + chains + transports)
 *   3. Place the logo PNG in /public/{key}.png
 *
 * Backend source of truth: mcp_server/integrations/x402/sdk_client.py
 */

export interface NetworkInfo {
  /** Network key (matches backend NETWORK_CONFIG key) */
  key: string
  /** Display name */
  name: string
  /** Chain ID */
  chainId: number | null
  /** Logo path (relative to /public) */
  logo: string
  /** Whether this network is currently live for payments */
  live: boolean
  /** Network type */
  networkType?: 'evm' | 'svm'
}

/**
 * All enabled payment networks.
 * Order determines display order in the UI.
 */
export const NETWORKS: NetworkInfo[] = [
  { key: 'base', name: 'Base', chainId: 8453, logo: '/base.png', live: true },
  { key: 'ethereum', name: 'Ethereum', chainId: 1, logo: '/ethereum.png', live: true },
  { key: 'polygon', name: 'Polygon', chainId: 137, logo: '/polygon.png', live: true },
  { key: 'arbitrum', name: 'Arbitrum', chainId: 42161, logo: '/arbitrum.png', live: true },
  { key: 'celo', name: 'Celo', chainId: 42220, logo: '/celo.png', live: true },
  { key: 'monad', name: 'Monad', chainId: 143, logo: '/monad.png', live: true },
  { key: 'avalanche', name: 'Avalanche', chainId: 43114, logo: '/avalanche.png', live: true },
  { key: 'optimism', name: 'Optimism', chainId: 10, logo: '/optimism.png', live: true },
  { key: 'skale', name: 'SKALE', chainId: 1187947933, logo: '/skale.png', live: true },
]

/** Quick lookup by network key */
export const NETWORK_BY_KEY = Object.fromEntries(
  NETWORKS.map((n) => [n.key, n])
) as Record<string, NetworkInfo>

/** Quick lookup by chain ID (excludes non-EVM networks with null chainId) */
export const NETWORK_BY_CHAIN_ID = Object.fromEntries(
  NETWORKS.filter((n) => n.chainId !== null).map((n) => [n.chainId, n])
) as Record<number, NetworkInfo>

/** Only live networks */
export const LIVE_NETWORKS = NETWORKS.filter((n) => n.live)

/**
 * Get the logo path for a network by its key.
 * 
 * @param networkKey - The network key (case-insensitive)
 * @returns Logo path or fallback for unknown networks
 */
export function getNetworkLogo(networkKey: string): string {
  const network = NETWORK_BY_KEY[networkKey] || NETWORK_BY_KEY[networkKey.toLowerCase()]
  return network?.logo || '/chain-default.png'
}
