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
 *
 * Solana entry (Phase 2.5.5) is gated by VITE_EM_SOLANA_SESSIONS_ENABLED.
 * When the flag is off it falls back to live=false so the UI shows it as
 * "coming soon" rather than offering a network the backend will reject.
 */
const SOLANA_LIVE = import.meta.env.VITE_EM_SOLANA_SESSIONS_ENABLED === 'true'

export const NETWORKS: NetworkInfo[] = [
  { key: 'base', name: 'Base', chainId: 8453, logo: '/base.png', live: true, networkType: 'evm' },
  { key: 'ethereum', name: 'Ethereum', chainId: 1, logo: '/ethereum.png', live: true, networkType: 'evm' },
  { key: 'polygon', name: 'Polygon', chainId: 137, logo: '/polygon.png', live: true, networkType: 'evm' },
  { key: 'arbitrum', name: 'Arbitrum', chainId: 42161, logo: '/arbitrum.png', live: true, networkType: 'evm' },
  { key: 'celo', name: 'Celo', chainId: 42220, logo: '/celo.png', live: true, networkType: 'evm' },
  { key: 'monad', name: 'Monad', chainId: 143, logo: '/monad.png', live: true, networkType: 'evm' },
  { key: 'avalanche', name: 'Avalanche', chainId: 43114, logo: '/avalanche.png', live: true, networkType: 'evm' },
  { key: 'optimism', name: 'Optimism', chainId: 10, logo: '/optimism.png', live: true, networkType: 'evm' },
  { key: 'skale', name: 'SKALE', chainId: 1187947933, logo: '/skale.png', live: true, networkType: 'evm' },
  { key: 'solana', name: 'Solana', chainId: null, logo: '/solana.png', live: SOLANA_LIVE, networkType: 'svm' },
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
