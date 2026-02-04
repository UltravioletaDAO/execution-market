/**
 * AuthModal - Login/Signup modal with unified wallet connection (NOW-041 to NOW-044)
 *
 * Supports:
 * - Wagmi wallets (MetaMask, WalletConnect)
 * - Crossmint email wallets
 * - Magic.link email auth (fallback)
 * - Legacy email/password auth
 */

import { useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { WalletSelector } from './WalletSelector'
import { useWallet } from '../hooks/useWallet'
import { supabase } from '../lib/supabase'

// =============================================================================
// Types
// =============================================================================

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

type AuthMode = 'wallet' | 'wallet-manual' | 'email-login' | 'email-signup'

// =============================================================================
// Component
// =============================================================================

export function AuthModal({ isOpen, onClose, onSuccess }: AuthModalProps) {
  const { t } = useTranslation()
  const { signing = false, ...walletRest } = useWallet()
  const wallet = { signing, ...walletRest }

  // Auth mode state
  const [mode, setMode] = useState<AuthMode>('wallet')

  // Form state for email auth
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [manualWalletAddress, setManualWalletAddress] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset form when modal closes
  const resetForm = useCallback(() => {
    setEmail('')
    setPassword('')
    setDisplayName('')
    setManualWalletAddress('')
    setError(null)
    setMode('wallet')
  }, [])

  const handleClose = useCallback(() => {
    resetForm()
    onClose()
  }, [resetForm, onClose])

  // Handle successful wallet connection
  const handleWalletSuccess = useCallback(() => {
    onSuccess()
    handleClose()
  }, [onSuccess, handleClose])

  // Handle wallet connection error
  const handleWalletError = useCallback((err: Error) => {
    setError(err.message)
  }, [])

  // Sync wallet authentication state
  useEffect(() => {
    if (wallet.isAuthenticated) {
      handleWalletSuccess()
    }
  }, [wallet.isAuthenticated, handleWalletSuccess])

  // Auth with manual wallet address
  const handleManualWalletAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    // Validate wallet address format
    if (!manualWalletAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
      setError(t('auth.errors.invalidWallet'))
      setLoading(false)
      return
    }

    try {
      const normalizedWallet = manualWalletAddress.toLowerCase()

      // Check if wallet already exists
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
      const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

      const checkResponse = await fetch(
        `${supabaseUrl}/rest/v1/executors?wallet_address=eq.${normalizedWallet}&select=id,display_name`,
        { headers: { 'apikey': supabaseKey } }
      )
      const existingExecutors = await checkResponse.json()
      const isReturningUser = existingExecutors && existingExecutors.length > 0

      // Sign in anonymously to create session
      const { data: authData, error: authError } = await supabase.auth.signInAnonymously()
      if (authError) throw authError
      if (!authData.user) throw new Error('Failed to create session')

      if (isReturningUser) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: linkError } = await (supabase.rpc as any)(
          'link_wallet_to_session',
          {
            p_user_id: authData.user.id,
            p_wallet_address: normalizedWallet,
          }
        )
        if (linkError) throw new Error('Failed to link wallet to session')
      } else {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const { error: rpcError } = await (supabase.rpc as any)(
          'get_or_create_executor',
          {
            p_wallet_address: normalizedWallet,
            p_display_name: displayName || null,
          }
        )
        if (rpcError) throw rpcError
      }

      onSuccess()
      handleClose()
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError(t('auth.errors.walletConnectionFailed'))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) throw error

      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('auth.errors.loginFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleEmailSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    // Validate wallet address format
    if (!manualWalletAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
      setError(t('auth.errors.invalidWallet'))
      setLoading(false)
      return
    }

    try {
      // 1. Create auth user
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password,
      })

      if (authError) throw authError
      if (!authData.user) throw new Error(t('auth.errors.signupFailed'))

      // 2. Create executor profile via RPC function
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { error: rpcError } = await (supabase.rpc as any)('create_executor_profile', {
        p_user_id: authData.user.id,
        p_wallet_address: manualWalletAddress.toLowerCase(),
        p_display_name: displayName || email.split('@')[0],
      })

      if (rpcError) {
        if (rpcError.code === '23505' || rpcError.message?.includes('already')) {
          throw new Error(t('auth.errors.walletInUse'))
        }
        throw rpcError
      }

      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('auth.errors.signupFailed'))
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 sticky top-0 bg-white z-10">
          <h2 className="text-xl font-semibold text-gray-900">
            {mode === 'wallet' && t('auth.connectWallet')}
            {mode === 'wallet-manual' && t('auth.manualWallet', 'Enter Wallet')}
            {mode === 'email-login' && t('auth.login')}
            {mode === 'email-signup' && t('auth.signup')}
          </h2>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors rounded-full hover:bg-gray-100"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <span>{error}</span>
                {error.includes('signature required') && (
                  <button
                    onClick={() => {
                      setError(null)
                      wallet.clearError()
                    }}
                    className="mt-2 block w-full py-2 px-3 bg-red-100 hover:bg-red-200 text-red-800 font-medium text-sm rounded-lg transition-colors text-center"
                  >
                    {t('wallet.tryAgain', 'Try Again')}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Signing indicator */}
          {wallet.signing && mode === 'wallet' && (
            <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-3">
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
              <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* ================================================================ */}
          {/* Wallet Connection Mode (Primary) - Uses WalletSelector */}
          {/* ================================================================ */}
          {mode === 'wallet' && (
            <div className="space-y-4">
              <WalletSelector
                onSuccess={handleWalletSuccess}
                onError={handleWalletError}
                showTitle={true}
              />

              {/* Manual wallet entry option */}
              <div className="pt-2">
                <button
                  onClick={() => setMode('wallet-manual')}
                  className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
                >
                  {t('auth.enterManually', 'Or enter your wallet manually')}
                </button>
              </div>

              {/* Divider */}
              <div className="relative pt-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-3 bg-white text-gray-500">{t('auth.orContinueWith')}</span>
                </div>
              </div>

              {/* Email/password option (legacy) */}
              <button
                type="button"
                onClick={() => setMode('email-login')}
                className="w-full py-2.5 text-emerald-600 hover:text-emerald-700 text-sm font-medium transition-colors"
              >
                {t('auth.emailPassword', 'Email & Password')}
              </button>
            </div>
          )}

          {/* ================================================================ */}
          {/* Manual Wallet Entry Mode */}
          {/* ================================================================ */}
          {mode === 'wallet-manual' && (
            <form onSubmit={handleManualWalletAuth} className="space-y-4">
              <div className="text-center mb-4">
                <div className="w-14 h-14 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-7 h-7 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>
                <p className="text-sm text-gray-500">
                  {t('auth.manualWalletDesc', 'Enter your wallet address to continue')}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.walletAddress')} *
                </label>
                <input
                  type="text"
                  value={manualWalletAddress}
                  onChange={(e) => setManualWalletAddress(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none font-mono text-sm transition-all"
                  placeholder="0x..."
                />
                <p className="mt-1.5 text-xs text-gray-500">{t('auth.walletAddressHint')}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.nameForNewUsers', 'Display name (for new users)')}
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                  placeholder={t('auth.namePlaceholder', 'Your name')}
                />
              </div>

              <button
                type="submit"
                disabled={loading || !manualWalletAddress}
                className="w-full py-3 bg-emerald-600 text-white font-medium rounded-xl hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    {t('auth.processing')}
                  </>
                ) : (
                  t('auth.connect', 'Connect')
                )}
              </button>

              <button
                type="button"
                onClick={() => setMode('wallet')}
                className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                {t('auth.backToWalletConnect', 'Back to wallet options')}
              </button>
            </form>
          )}

          {/* ================================================================ */}
          {/* Email Login */}
          {/* ================================================================ */}
          {mode === 'email-login' && (
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div className="text-center mb-4">
                <div className="w-14 h-14 bg-emerald-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-7 h-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.email')}
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
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.password')}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                  placeholder="........"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-emerald-600 text-white font-medium rounded-xl hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    {t('auth.processing')}
                  </>
                ) : (
                  t('auth.login')
                )}
              </button>
            </form>
          )}

          {/* ================================================================ */}
          {/* Email Signup */}
          {/* ================================================================ */}
          {mode === 'email-signup' && (
            <form onSubmit={handleEmailSignup} className="space-y-4">
              <div className="text-center mb-4">
                <div className="w-14 h-14 bg-emerald-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-7 h-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.walletAddress')} *
                </label>
                <input
                  type="text"
                  value={manualWalletAddress}
                  onChange={(e) => setManualWalletAddress(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none font-mono text-sm transition-all"
                  placeholder="0x..."
                />
                <p className="mt-1.5 text-xs text-gray-500">{t('auth.walletAddressHint')}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.email')} *
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.password')} *
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                  placeholder="........"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('auth.nameOptional')}
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                  placeholder="Your name"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-emerald-600 text-white font-medium rounded-xl hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    {t('auth.processing')}
                  </>
                ) : (
                  t('auth.signup')
                )}
              </button>
            </form>
          )}
        </div>

        {/* Footer - Mode switcher */}
        <div className="px-6 py-4 bg-gray-50 text-center space-y-2 border-t border-gray-100">
          {mode === 'wallet' && null}
          {mode === 'wallet-manual' && null}
          {mode === 'email-login' && (
            <>
              <button
                onClick={() => setMode('wallet')}
                className="block w-full text-sm text-emerald-600 hover:text-emerald-700 font-medium"
              >
                {t('auth.connectWallet')}
              </button>
              <p className="text-sm text-gray-600">
                {t('auth.noAccount')}{' '}
                <button
                  onClick={() => setMode('email-signup')}
                  className="text-emerald-600 hover:text-emerald-700 font-medium"
                >
                  {t('auth.registerNow')}
                </button>
              </p>
            </>
          )}
          {mode === 'email-signup' && (
            <>
              <button
                onClick={() => setMode('wallet')}
                className="block w-full text-sm text-emerald-600 hover:text-emerald-700 font-medium"
              >
                {t('auth.connectWallet')}
              </button>
              <p className="text-sm text-gray-600">
                {t('auth.hasAccount')}{' '}
                <button
                  onClick={() => setMode('email-login')}
                  className="text-emerald-600 hover:text-emerald-700 font-medium"
                >
                  {t('auth.loginNow')}
                </button>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default AuthModal
