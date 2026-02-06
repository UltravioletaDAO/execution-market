/**
 * Unified Wallet Selector Component (NOW-041 to NOW-044)
 *
 * Provides a unified interface for selecting and connecting wallets:
 * - Email wallet (Crossmint/Magic.link)
 * - MetaMask (browser extension)
 * - WalletConnect (mobile/QR)
 */

import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useWallet,
  WalletType,
  isCrossmintAvailable,
  isMagicAvailable,
} from '../hooks/useWallet'

// =============================================================================
// Types
// =============================================================================

interface WalletSelectorProps {
  onSuccess?: () => void
  onError?: (error: Error) => void
  showTitle?: boolean
  className?: string
}

type WalletOption = {
  id: WalletType
  name: string
  description: string
  icon: React.ReactNode
  requiresEmail: boolean
  available: boolean
}

// =============================================================================
// Icons
// =============================================================================

const MetaMaskIcon = () => (
  <svg className="w-6 h-6" viewBox="0 0 318.6 318.6">
    <path fill="#6b7280" d="M274.1,35.5l-99.5,73.9l18.4-43.6L274.1,35.5z"/>
    <path fill="#71717a" d="M44.4,35.5l98.7,74.6l-17.5-44.3L44.4,35.5z"/>
    <path fill="#71717a" d="M238.3,206.8l-26.5,40.6l56.7,15.6l16.3-55.3L238.3,206.8z"/>
    <path fill="#71717a" d="M33.9,207.8l16.2,55.3l56.7-15.6l-26.5-40.6L33.9,207.8z"/>
    <path fill="#71717a" d="M103.6,138.2l-15.8,23.9l56.3,2.5l-2-60.5L103.6,138.2z"/>
    <path fill="#71717a" d="M214.9,138.2l-39-34.8l-1.3,61.2l56.2-2.5L214.9,138.2z"/>
    <path fill="#71717a" d="M106.8,247.4l33.8-16.5l-29.2-22.8L106.8,247.4z"/>
    <path fill="#71717a" d="M177.9,230.9l33.9,16.5l-4.7-39.3L177.9,230.9z"/>
  </svg>
)

const WalletConnectIcon = () => (
  <svg className="w-6 h-6" viewBox="0 0 480 480">
    <circle cx="240" cy="240" r="240" fill="#52525b"/>
    <path fill="white" d="M126.6,168c62.6-61.3,164.1-61.3,226.8,0l7.5,7.4c3.1,3.1,3.1,8.1,0,11.2l-25.8,25.2c-1.6,1.5-4.1,1.5-5.7,0l-10.4-10.1c-43.7-42.8-114.5-42.8-158.2,0l-11.1,10.9c-1.6,1.5-4.1,1.5-5.7,0l-25.8-25.2c-3.1-3.1-3.1-8.1,0-11.2L126.6,168z M391,205.4l22.9,22.4c3.1,3.1,3.1,8.1,0,11.2l-103.5,101.3c-3.1,3.1-8.2,3.1-11.3,0l-73.4-71.9c-0.8-0.8-2.1-0.8-2.8,0l-73.4,71.9c-3.1,3.1-8.2,3.1-11.3,0L34.7,239c-3.1-3.1-3.1-8.1,0-11.2l22.9-22.4c3.1-3.1,8.2-3.1,11.3,0l73.4,71.9c0.8,0.8,2.1,0.8,2.8,0l73.4-71.9c3.1-3.1,8.2-3.1,11.3,0l73.4,71.9c0.8,0.8,2.1,0.8,2.8,0l73.4-71.9C382.8,202.4,387.9,202.4,391,205.4z"/>
  </svg>
)

const EmailIcon = () => (
  <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
)

const SpinnerIcon = () => (
  <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
)

// =============================================================================
// Component
// =============================================================================

export function WalletSelector({
  onSuccess,
  onError,
  showTitle = true,
  className = '',
}: WalletSelectorProps) {
  const { t } = useTranslation()
  const { signing = false, ...walletRest } = useWallet()
  const wallet = { signing, ...walletRest }

  // Local state
  const [selectedWallet, setSelectedWallet] = useState<WalletType | null>(null)
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showEmailInput, setShowEmailInput] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  // Determine which email wallet provider to use
  const emailWalletProvider: WalletType | null = isCrossmintAvailable()
    ? 'crossmint'
    : isMagicAvailable()
    ? 'magic'
    : null

  // Build wallet options
  const walletOptions: WalletOption[] = [
    {
      id: emailWalletProvider || 'crossmint',
      name: t('wallet.emailWallet', 'Email Wallet'),
      description: t('wallet.emailWalletDesc', 'Sign in with email - no extension needed'),
      icon: <EmailIcon />,
      requiresEmail: true,
      available: Boolean(emailWalletProvider),
    },
    {
      id: 'metamask',
      name: 'MetaMask',
      description: t('wallet.metamaskDesc', 'Browser extension'),
      icon: <MetaMaskIcon />,
      requiresEmail: false,
      available: true,
    },
    {
      id: 'walletconnect',
      name: 'WalletConnect',
      description: t('wallet.walletConnectDesc', 'Scan QR code'),
      icon: <WalletConnectIcon />,
      requiresEmail: false,
      available: true,
    },
  ]

  // Filter to available options
  const availableOptions = walletOptions.filter(opt => opt.available)

  // ==========================================================================
  // Handlers
  // ==========================================================================

  const handleWalletSelect = useCallback(async (option: WalletOption) => {
    setLocalError(null)

    if (option.requiresEmail) {
      setSelectedWallet(option.id)
      setShowEmailInput(true)
      return
    }

    // Direct connection (MetaMask/WalletConnect)
    setSelectedWallet(option.id)

    try {
      await wallet.connect(option.id, { displayName: displayName || undefined })
      // Don't call onSuccess here for MetaMask/WalletConnect — wagmiConnect() is non-blocking,
      // so connect() returns before auth completes. AuthModal's useEffect on wallet.isAuthenticated
      // handles success once the full auth flow (signature + Supabase) finishes.
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Connection failed')
      setLocalError(error.message)
      onError?.(error)
      setSelectedWallet(null)
    }
  }, [wallet, displayName, onError])

  const handleEmailSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (!email || !selectedWallet) {
      setLocalError(t('wallet.emailRequired', 'Email is required'))
      return
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      setLocalError(t('wallet.invalidEmail', 'Please enter a valid email address'))
      return
    }

    try {
      await wallet.connect(selectedWallet, {
        email,
        displayName: displayName || email.split('@')[0],
      })
      onSuccess?.()
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Connection failed')
      setLocalError(error.message)
      onError?.(error)
    }
  }, [email, selectedWallet, displayName, wallet, t, onSuccess, onError])

  const handleBack = useCallback(() => {
    setShowEmailInput(false)
    setSelectedWallet(null)
    setEmail('')
    setLocalError(null)
  }, [])

  // Combined error from hook and local state
  const displayError = localError || wallet.error?.message

  // ==========================================================================
  // Render
  // ==========================================================================

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Title */}
      {showTitle && (
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-gradient-to-br from-emerald-100 to-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">
            {t('wallet.connectTitle', 'Connect your wallet')}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {t('wallet.connectSubtitle', 'Choose how you want to connect')}
          </p>
        </div>
      )}

      {/* Error display */}
      {displayError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
          <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p>{displayError}</p>
            <button
              onClick={() => {
                setLocalError(null)
                wallet.clearError()
              }}
              className="text-red-800 underline text-xs mt-1"
            >
              {t('common.dismiss', 'Dismiss')}
            </button>
          </div>
        </div>
      )}

      {/* Email input form */}
      {showEmailInput && selectedWallet ? (
        <form onSubmit={handleEmailSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('wallet.email', 'Email')} *
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
              placeholder="you@example.com"
            />
            <p className="mt-1.5 text-xs text-gray-500">
              {t('wallet.emailHint', "We'll create a wallet linked to your email")}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('wallet.displayName', 'Display name')}
              <span className="text-gray-400 font-normal ml-1">
                ({t('common.optional', 'optional')})
              </span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
              placeholder={t('wallet.displayNamePlaceholder', 'Your name')}
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleBack}
              className="flex-1 py-3 px-4 border border-gray-300 text-gray-700 font-medium rounded-xl hover:bg-gray-50 transition-colors"
            >
              {t('common.back', 'Back')}
            </button>
            <button
              type="submit"
              disabled={wallet.isConnecting || !email}
              className="flex-1 py-3 px-4 bg-emerald-600 text-white font-medium rounded-xl hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {wallet.signing ? (
                <>
                  <SpinnerIcon />
                  {t('wallet.signing', 'Sign the message in your wallet...')}
                </>
              ) : wallet.isConnecting ? (
                <>
                  <SpinnerIcon />
                  {t('wallet.connecting', 'Connecting...')}
                </>
              ) : (
                t('wallet.continue', 'Continue')
              )}
            </button>
          </div>
        </form>
      ) : (
        <>
          {/* Wallet options */}
          <div className="space-y-2">
            {availableOptions.map((option) => (
              <button
                key={option.id}
                onClick={() => handleWalletSelect(option)}
                disabled={wallet.isConnecting}
                className={`
                  w-full flex items-center gap-4 px-4 py-4 border rounded-xl transition-all
                  ${selectedWallet === option.id && wallet.isConnecting
                    ? 'border-emerald-300 bg-emerald-50'
                    : 'border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/50'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                <div className="flex-shrink-0 w-10 h-10 bg-gray-50 rounded-xl flex items-center justify-center">
                  {option.icon}
                </div>
                <div className="flex-1 text-left">
                  <div className="font-medium text-gray-900">{option.name}</div>
                  <div className="text-xs text-gray-500">{option.description}</div>
                </div>
                {selectedWallet === option.id && wallet.isConnecting && !wallet.signing && (
                  <SpinnerIcon />
                )}
                {selectedWallet === option.id && wallet.signing && (
                  <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                )}
                {option.requiresEmail && !wallet.isConnecting && (
                  <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                )}
              </button>
            ))}
          </div>

          {/* No email wallet available notice */}
          {!emailWalletProvider && (
            <p className="text-xs text-gray-400 text-center">
              {t('wallet.emailNotAvailable', 'Email wallet is not available. Please use MetaMask or WalletConnect.')}
            </p>
          )}
        </>
      )}

      {/* Signing indicator */}
      {wallet.signing && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-amber-800">
              {t('wallet.signing', 'Sign the message in your wallet...')}
            </p>
            <p className="text-xs text-amber-600 mt-0.5">
              {t('wallet.signingDesc', 'Confirm your identity by signing the request in your wallet')}
            </p>
          </div>
          <SpinnerIcon />
        </div>
      )}

      {/* Security note */}
      <p className="text-xs text-gray-400 text-center pt-2">
        {t('wallet.securityNote', 'Your wallet is used for identity and payments. We never store your private keys.')}
      </p>
    </div>
  )
}

export default WalletSelector
