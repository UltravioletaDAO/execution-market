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
import { DYNAMIC_ENVIRONMENT_ID, isDynamicConfigured, dynamicCssOverrides } from '../lib/dynamic'

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
    return <>{children}</>
  }

  return (
    <DynamicContextProvider
      settings={{
        environmentId: DYNAMIC_ENVIRONMENT_ID,
        walletConnectors: [EthereumWalletConnectors],
        cssOverrides: dynamicCssOverrides,
        // connect-and-sign: Requires wallet signature to create persistent JWT.
        // This ensures sessions persist across tab switches and page reloads,
        // especially critical for mobile browsers. The signature step proves
        // wallet ownership and enables Dynamic's built-in session management.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        initialAuthenticationMode: 'connect-and-sign' as any,
        // Enable visit tracking for connect-and-sign mode (not needed but good practice)
        enableVisitTrackingOnConnectOnly: false,
        // Ensure shadow DOM is enabled for proper modal behavior
        shadowDOMEnabled: true,
        events: {
          onAuthSuccess: ({ user }) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            console.log('[Dynamic] Auth success:', (user as any)?.walletPublicKey || 'unknown wallet')
            console.log('[Dynamic] JWT session created - should persist across tab switches')
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
      {children}
    </DynamicContextProvider>
  )
}

