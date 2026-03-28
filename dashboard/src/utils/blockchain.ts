/**
 * Blockchain Utility Functions
 *
 * Shared utilities for blockchain-related display across the dashboard:
 * - Explorer URL generation (BaseScan, Etherscan, etc.)
 * - Transaction hash and address truncation
 * - Validation helpers
 *
 * These utilities consolidate duplicated logic from PaymentStatus.tsx,
 * PaymentHistory.tsx, and other components that display on-chain data.
 */

/** Supported network identifiers */
export type NetworkId =
  | 'base'
  | 'base-mainnet'
  | 'base-sepolia'
  | 'ethereum'
  | 'sepolia'
  | 'polygon'
  | 'arbitrum'
  | 'celo'
  | 'monad'
  | 'avalanche'
  | 'optimism'
  | 'skale'
  | 'solana';

/** Explorer base URLs for transactions */
export const TX_EXPLORER_URLS: Record<string, string> = {
  base: 'https://basescan.org/tx/',
  'base-mainnet': 'https://basescan.org/tx/',
  'base-sepolia': 'https://sepolia.basescan.org/tx/',
  ethereum: 'https://etherscan.io/tx/',
  sepolia: 'https://sepolia.etherscan.io/tx/',
  polygon: 'https://polygonscan.com/tx/',
  arbitrum: 'https://arbiscan.io/tx/',
  celo: 'https://celoscan.io/tx/',
  monad: 'https://explorer.monad.xyz/tx/',
  avalanche: 'https://snowtrace.io/tx/',
  optimism: 'https://optimistic.etherscan.io/tx/',
  skale: 'https://skale-base-explorer.skalenodes.com/tx/',
  solana: 'https://solscan.io/tx/',
};

/** Explorer base URLs for addresses */
export const ADDRESS_EXPLORER_URLS: Record<string, string> = {
  base: 'https://basescan.org/address/',
  'base-mainnet': 'https://basescan.org/address/',
  'base-sepolia': 'https://sepolia.basescan.org/address/',
  ethereum: 'https://etherscan.io/address/',
  sepolia: 'https://sepolia.etherscan.io/address/',
  polygon: 'https://polygonscan.com/address/',
  arbitrum: 'https://arbiscan.io/address/',
  celo: 'https://celoscan.io/address/',
  monad: 'https://explorer.monad.xyz/address/',
  avalanche: 'https://snowtrace.io/address/',
  optimism: 'https://optimistic.etherscan.io/address/',
  skale: 'https://skale-base-explorer.skalenodes.com/address/',
  solana: 'https://solscan.io/account/',
};

/**
 * Get the block explorer URL for a transaction hash.
 *
 * @param txHash - The transaction hash (0x-prefixed)
 * @param network - The network identifier (default: "base")
 * @returns Full explorer URL for the transaction
 *
 * @example
 * getExplorerUrl('0xabc123...')
 * // "https://basescan.org/tx/0xabc123..."
 *
 * getExplorerUrl('0xabc123...', 'base-sepolia')
 * // "https://sepolia.basescan.org/tx/0xabc123..."
 */
export function getExplorerUrl(txHash: string, network: string = 'base'): string {
  const baseUrl = TX_EXPLORER_URLS[network] || TX_EXPLORER_URLS.base;
  return baseUrl + txHash;
}

/**
 * Get the block explorer URL for an address.
 *
 * @param address - The wallet or contract address (0x-prefixed)
 * @param network - The network identifier (default: "base")
 * @returns Full explorer URL for the address
 *
 * @example
 * getAddressUrl('YOUR_DEV_WALLET')
 * // "https://basescan.org/address/0x857fe6..."
 */
export function getAddressUrl(address: string, network: string = 'base'): string {
  const baseUrl = ADDRESS_EXPLORER_URLS[network] || ADDRESS_EXPLORER_URLS.base;
  return baseUrl + address;
}

/**
 * Truncate a hex hash for display.
 *
 * @param hash - The full hash string
 * @param startChars - Number of characters to keep at the start (default: 6, includes "0x")
 * @param endChars - Number of characters to keep at the end (default: 4)
 * @returns Truncated hash like "0x1234...abcd"
 *
 * @example
 * truncateHash('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')
 * // "0x1234...cdef"
 *
 * truncateHash('0xabcdef1234567890', 8, 6)
 * // "0xabcdef...567890"
 */
export function truncateHash(hash: string, startChars: number = 6, endChars: number = 4): string {
  if (!hash || hash.length <= startChars + endChars + 3) return hash;
  return `${hash.slice(0, startChars)}...${hash.slice(-endChars)}`;
}

/**
 * Validate whether a string is a valid transaction hash.
 *
 * A valid tx hash is a 0x-prefixed, 66-character hex string (32 bytes).
 *
 * @param hash - The string to validate
 * @returns true if the string is a valid transaction hash
 *
 * @example
 * isValidTxHash('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')
 * // true
 *
 * isValidTxHash('0xinvalid')
 * // false
 */
export function isValidTxHash(hash: string): boolean {
  // EVM: 0x-prefixed 64 hex chars
  if (/^0x[0-9a-fA-F]{64}$/.test(hash)) return true;
  // Solana: Base58 signature (~88 chars)
  if (/^[1-9A-HJ-NP-Za-km-z]{80,90}$/.test(hash)) return true;
  return false;
}

/**
 * Validate whether a string is a valid Ethereum address.
 *
 * A valid address is a 0x-prefixed, 42-character hex string (20 bytes).
 *
 * @param address - The string to validate
 * @returns true if the string is a valid address
 */
export function isValidAddress(address: string): boolean {
  // EVM: 0x-prefixed 40 hex chars
  if (/^0x[0-9a-fA-F]{40}$/.test(address)) return true;
  // Solana: Base58 address (32-44 chars)
  if (/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address)) return true;
  return false;
}

/**
 * Get a human-readable network display name.
 *
 * @param network - The network identifier
 * @returns Display name for the network
 */
export function getNetworkDisplayName(network: string): string {
  const names: Record<string, string> = {
    base: 'Base',
    'base-mainnet': 'Base',
    'base-sepolia': 'Base Sepolia',
    ethereum: 'Ethereum',
    sepolia: 'Sepolia',
    polygon: 'Polygon',
    arbitrum: 'Arbitrum',
    celo: 'Celo',
    monad: 'Monad',
    avalanche: 'Avalanche',
    optimism: 'Optimism',
    solana: 'Solana',
  };
  return names[network] || network;
}
