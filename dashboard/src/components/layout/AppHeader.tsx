import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { LanguageSwitcher } from '../LanguageSwitcher'

interface AppHeaderProps {
  onConnectWallet: () => void
}

export function AppHeader({ onConnectWallet }: AppHeaderProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { isAuthenticated, userType } = useAuth()

  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <span className="text-2xl">&#128188;</span>
            <span className="font-bold text-lg text-gray-900">Chamba</span>
          </button>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            {isAuthenticated ? (
              <button
                onClick={() => navigate(userType === 'agent' ? '/agent/dashboard' : '/tasks')}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('nav.dashboard')}
              </button>
            ) : (
              <button
                onClick={onConnectWallet}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('auth.connectWallet')}
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
