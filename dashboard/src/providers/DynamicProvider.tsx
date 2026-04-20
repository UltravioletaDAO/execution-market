/**
 * Dynamic.xyz Provider
 *
 * Wraps the application with Dynamic's authentication context.
 * Handles wallet connection, authentication, and user management.
 */

import { ReactNode } from 'react'
import {
  DynamicContextProvider,
  DynamicWidget,
} from '@dynamic-labs/sdk-react-core'
import { EthereumWalletConnectors } from '@dynamic-labs/ethereum'
import { DYNAMIC_ENVIRONMENT_ID, isDynamicConfigured, isDynamicLive, dynamicCssOverrides } from '../lib/dynamic'

// Re-export for convenience
export { DynamicWidget }

interface DynamicProviderProps {
  children: ReactNode
}

/**
 * Dynamic Provider Component
 */
export function DynamicProvider({ children }: DynamicProviderProps) {
  if (!isDynamicConfigured()) {
    console.warn('[Dynamic] VITE_DYNAMIC_ENVIRONMENT_ID not set. Auth will not work.')
    return (
      <>
        <div className="fixed top-0 left-0 right-0 z-50 bg-gray-900 text-center py-2 px-4 text-sm">
          {import.meta.env.DEV ? (
            <span className="text-amber-400">
              Set VITE_DYNAMIC_ENVIRONMENT_ID in .env.local
            </span>
          ) : (
            <span className="text-red-400">
              Authentication unavailable. Please try again later.
            </span>
          )}
        </div>
        {children}
      </>
    )
  }

  const showSandboxBanner = import.meta.env.DEV && !isDynamicLive()

  return (
    <DynamicContextProvider
      settings={{
        environmentId: DYNAMIC_ENVIRONMENT_ID,
        walletConnectors: [EthereumWalletConnectors],
        cssOverrides: dynamicCssOverrides,
        // connect-and-sign: wallet connects + signs SIWE message → Dynamic creates
        // a persistent JWT session. This is the SDK default and is required for
        // session persistence across page reloads and mobile tab switches.
        // DO NOT change to 'connect-only' — it breaks session persistence.
        initialAuthenticationMode: 'connect-and-sign',
        // NOTE: siweStatement removed — it broke embedded wallet creation for email-only users.
        // Dynamic's embedded wallets do auto-SIWE internally; custom statements can conflict.
        events: {
          onAuthFlowOpen: () => {
            console.log('[Dynamic] Auth flow opened')
          },
          onAuthFlowClose: () => {
            console.log('[Dynamic] Auth flow closed')
          },
          onAuthSuccess: ({ user }) => {
            console.log('[Dynamic] Auth success:', (user as unknown as Record<string, unknown>)?.walletPublicKey || 'unknown wallet')
          },
          onAuthFailure: (_data, reason) => {
            console.error('[Dynamic] Auth failure:', reason)
          },
          onLogout: () => {
            console.log('[Dynamic] User logged out')
            // Clear persisted wallet on Dynamic logout
            if (typeof window !== 'undefined') {
              localStorage.removeItem('em_last_wallet_address')
              localStorage.removeItem('em_user_type')
            }
          },
        },
      }}
    >
      {showSandboxBanner && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-amber-900 text-center py-1 px-4 text-xs text-amber-200">
          Dynamic Sandbox Mode
        </div>
      )}
      {children}
    </DynamicContextProvider>
  )
}
