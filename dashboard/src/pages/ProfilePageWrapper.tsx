import { useState, useCallback, Suspense, lazy } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTranslation } from 'react-i18next'

const ProfilePage = lazy(() => import('../components/profile').then(m => ({ default: m.ProfilePage })))
const ProfileEditModal = lazy(() => import('../components/profile/ProfileEditModal').then(m => ({ default: m.ProfileEditModal })))

export function ProfilePageWrapper() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { executor, loading, refreshExecutor, logout } = useAuth()
  const [showEditModal, setShowEditModal] = useState(false)

  const handleEditSaved = useCallback(() => {
    setShowEditModal(false)
    refreshExecutor()
  }, [refreshExecutor])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3">
          <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-gray-500">{t('common.loading')}</p>
        </div>
      </div>
    )
  }

  if (!executor) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <p className="text-gray-500 mb-4">{t('errors.generic')}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => refreshExecutor()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('common.retry')}
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
