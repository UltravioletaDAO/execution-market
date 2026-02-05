/**
 * Dynamic.xyz SDK Configuration
 *
 * Dynamic provides wallet authentication with built-in UI and multi-wallet support.
 * https://docs.dynamic.xyz/
 */

import { EthereumWalletConnectors } from '@dynamic-labs/ethereum'

// Environment ID from Dynamic dashboard
export const DYNAMIC_ENVIRONMENT_ID = import.meta.env.VITE_DYNAMIC_ENVIRONMENT_ID || ''

// Check if Dynamic is properly configured
export const isDynamicConfigured = (): boolean => {
  return Boolean(DYNAMIC_ENVIRONMENT_ID)
}

// Wallet connectors to enable
export const walletConnectors = [EthereumWalletConnectors]

// CSS overrides for Dynamic widget (optional)
export const dynamicCssOverrides = `
  .dynamic-widget-inline-controls {
    background: transparent;
  }
  .dynamic-widget-card {
    border-radius: 1rem;
  }
`
