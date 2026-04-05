/**
 * Dynamic Wallet Button
 *
 * A simple button that opens the Dynamic authentication modal.
 * Shows wallet address when connected, or "Connect Wallet" when not.
 */

import { DynamicWidget } from '@dynamic-labs/sdk-react-core'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'

interface DynamicWalletButtonProps {
  className?: string
  variant?: 'default' | 'compact'
}

export function DynamicWalletButton({
  className = '',
  variant = 'default',
}: DynamicWalletButtonProps) {
  return (
    <div className={className}>
      <DynamicWidget
        variant={variant === 'compact' ? 'dropdown' : 'modal'}
      />
    </div>
  )
}

/**
 * Simple connect button that triggers Dynamic modal
 */
interface ConnectButtonProps {
  className?: string
  children?: React.ReactNode
}

export function ConnectButton({ className = '', children }: ConnectButtonProps) {
  const { t } = useTranslation()
  const { isAuthenticated, walletAddress, openAuthModal, logout, loading } = useAuth()

  if (isAuthenticated && walletAddress) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-sm text-gray-600">
          {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
        </span>
        <button
          onClick={logout}
          className="text-sm text-red-600 hover:text-red-700"
        >
          Disconnect
        </button>
      </div>
    )
  }

  // Returning user: show restoring indicator instead of connect button
  if (loading && localStorage.getItem('em_last_wallet_address')) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500 animate-pulse">
          {t('auth.restoringSession', 'Restoring session...')}
        </span>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        onClick={openAuthModal}
        className={`px-4 py-2 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 transition-colors ${className}`}
      >
        {children || t('auth.connectWallet', 'Connect Wallet')}
      </button>
      <button
        onClick={openAuthModal}
        className="text-xs text-gray-500 hover:text-gray-700 underline underline-offset-2 transition-colors"
      >
        {t('auth.orSignInWithEmail', 'Or sign in with email')}
      </button>
    </div>
  )
}

export default DynamicWalletButton
