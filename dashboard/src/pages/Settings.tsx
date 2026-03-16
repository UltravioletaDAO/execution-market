import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import { LanguageSwitcherMenu } from '../components/LanguageSwitcher'

const PAYMENT_NETWORKS = [
  { key: 'base', name: 'Base' },
  { key: 'ethereum', name: 'Ethereum' },
  { key: 'polygon', name: 'Polygon' },
  { key: 'arbitrum', name: 'Arbitrum' },
  { key: 'avalanche', name: 'Avalanche' },
  { key: 'optimism', name: 'Optimism' },
  { key: 'celo', name: 'Celo' },
  { key: 'monad', name: 'Monad' },
] as const

function getStoredNetwork(): string {
  return localStorage.getItem('em_preferred_network') || 'base'
}

function getStoredNotifications(): boolean {
  return localStorage.getItem('em_notifications_email') !== 'false'
}

export function Settings() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { executor, logout } = useAuth()

  const [preferredNetwork, setPreferredNetwork] = useState(getStoredNetwork)
  const [emailNotifications, setEmailNotifications] = useState(getStoredNotifications)

  function handleNetworkChange(network: string) {
    setPreferredNetwork(network)
    localStorage.setItem('em_preferred_network', network)
  }

  function handleNotificationsChange(enabled: boolean) {
    setEmailNotifications(enabled)
    localStorage.setItem('em_notifications_email', String(enabled))
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="text-2xl font-bold text-gray-900">{t('settings.title')}</h1>
      </div>

      {/* Language Section */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          {t('settings.language')}
        </h2>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <LanguageSwitcherMenu />
        </div>
      </section>

      {/* Preferred Payment Network */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          {t('settings.preferredNetwork', 'Preferred Payment Network')}
        </h2>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <p className="text-sm text-gray-500 mb-3">
            {t('settings.preferredNetworkDesc', 'Default network for receiving payments')}
          </p>
          <div className="flex flex-wrap gap-2">
            {PAYMENT_NETWORKS.map((net) => (
              <button
                key={net.key}
                onClick={() => handleNetworkChange(net.key)}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                  preferredNetwork === net.key
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {net.name}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Notifications */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          {t('settings.notifications')}
        </h2>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <p className="text-sm font-medium text-gray-900">
                {t('settings.emailNotifications', 'Email Notifications')}
              </p>
              <p className="text-sm text-gray-500">
                {t('settings.emailNotificationsDesc', 'Receive updates about tasks, payments, and submissions')}
              </p>
            </div>
            <button
              role="switch"
              aria-checked={emailNotifications}
              onClick={() => handleNotificationsChange(!emailNotifications)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                emailNotifications ? 'bg-emerald-500' : 'bg-gray-200'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  emailNotifications ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </label>
        </div>
      </section>

      {/* Account Section */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          {t('settings.account')}
        </h2>
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden divide-y divide-gray-100">
          {executor?.wallet_address && (
            <div className="px-4 py-3">
              <p className="text-sm text-gray-500">{t('settings.wallet')}</p>
              <p className="text-sm font-mono text-gray-900 truncate">
                {executor.wallet_address}
              </p>
            </div>
          )}
          <button
            onClick={() => {
              logout()
              navigate('/')
            }}
            className="w-full text-left px-4 py-3 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            {t('settings.logout')}
          </button>
        </div>
      </section>

      {/* App Info */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          {t('settings.app', 'App')}
        </h2>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">{t('settings.version', 'Version')}</span>
            <span className="text-sm font-mono text-gray-900">1.0.0</span>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Settings
