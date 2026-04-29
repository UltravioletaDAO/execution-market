import { useState, useCallback, useEffect, Suspense, lazy } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDynamicContext } from '@dynamic-labs/sdk-react-core'
import { useAuth } from '../context/AuthContext'
import { useTranslation } from 'react-i18next'

import { Spinner } from '../components/ui/Spinner'

const ProfilePage = lazy(() => import('../components/profile').then(m => ({ default: m.ProfilePage })))
const ProfileEditModal = lazy(() => import('../components/profile/ProfileEditModal').then(m => ({ default: m.ProfileEditModal })))

// After this much time without a wallet, we consider the Dynamic SDK unavailable
// (likely blocked by a browser extension or network failure).
const WALLET_UNAVAILABLE_TIMEOUT_MS = 8_000

function LoadingFallback({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="flex items-center gap-3">
        <Spinner size="md" className="text-zinc-700" label={message} />
        <p className="text-zinc-500">{message}</p>
      </div>
    </div>
  )
}

export function ProfilePageWrapper() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { executor, loading, walletAddress, isAuthenticated, refreshExecutor, logout } = useAuth()
  const { primaryWallet, sdkHasLoaded } = useDynamicContext()
  const [showEditModal, setShowEditModal] = useState(false)
  // Tracks whether enough time has passed to consider the wallet "unavailable"
  // (vs. still initializing). Distinguishes a cold SDK boot from a hard failure.
  const [walletWaitElapsed, setWalletWaitElapsed] = useState(false)

  useEffect(() => {
    if (walletAddress) {
      setWalletWaitElapsed(false)
      return
    }
    const timer = setTimeout(() => setWalletWaitElapsed(true), WALLET_UNAVAILABLE_TIMEOUT_MS)
    return () => clearTimeout(timer)
  }, [walletAddress])

  const handleEditSaved = useCallback(() => {
    setShowEditModal(false)
    refreshExecutor()
  }, [refreshExecutor])

  // --------------------------------------------------------------------------
  // State machine — distinguishes wallet loading, wallet failure, missing
  // executor, and authenticated-without-wallet. Each surface has its own UX
  // so users get actionable feedback instead of a generic "An error occurred".
  // --------------------------------------------------------------------------

  // Case 1: Dynamic SDK still booting OR auth context still resolving.
  if (!sdkHasLoaded || loading) {
    return <LoadingFallback message={t('errors.walletConnecting')} />
  }

  // Case 2: User authenticated but embedded wallet not yet provisioned
  // (email-only Dynamic sessions can create the wallet a few seconds after login).
  if (isAuthenticated && !walletAddress) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center max-w-md">
          <p className="text-gray-600 mb-4">{t('errors.walletStillConnecting')}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('errors.reload')}
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              {t('common.back')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Case 3: SDK loaded, no primary wallet after grace period → likely blocked
  // by a browser extension or SDK failed to initialize properly.
  if (!primaryWallet && walletWaitElapsed) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center max-w-md">
          <p className="text-gray-700 mb-4">{t('errors.walletConnectFailed')}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('errors.reload')}
            </button>
            <button
              onClick={() => refreshExecutor()}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              {t('common.retry')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Case 4: Wallet OK but executor fetch failed.
  if (!executor) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center max-w-md">
          <p className="text-gray-600 mb-4">{t('errors.profileLoadFailed')}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => refreshExecutor()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('common.retry')}
            </button>
            <a
              href="mailto:support@execution.market"
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              {t('errors.contactSupport')}
            </a>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <ProfilePage
        executor={executor}
        onBack={() => navigate('/tasks')}
        onEditProfile={() => setShowEditModal(true)}
        onLogout={() => { logout(); navigate('/') }}
      />
      {showEditModal && (
        <Suspense fallback={null}>
          <ProfileEditModal
            executor={executor}
            onClose={() => setShowEditModal(false)}
            onSaved={handleEditSaved}
          />
        </Suspense>
      )}
    </>
  )
}

export default ProfilePageWrapper
