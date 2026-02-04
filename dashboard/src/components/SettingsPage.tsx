/**
 * SettingsPage - User settings and preferences
 *
 * Features:
 * - Profile editing
 * - Notification preferences
 * - Language selection
 * - Location settings
 * - Privacy controls
 * - Account management
 */

import { useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { supabase } from '../lib/supabase'
import { usePWA } from '../hooks/usePWA'

// Types
interface Executor {
  id: string
  wallet_address: string
  display_name: string | null
  skills: string[]
  reputation_score: number
  created_at: string
}

interface NotificationSettings {
  newTasks: boolean
  taskAssigned: boolean
  submissionReviewed: boolean
  paymentReceived: boolean
  disputes: boolean
  marketing: boolean
}

interface PrivacySettings {
  showEarnings: boolean
  showLocation: boolean
  showActivity: boolean
}

interface SettingsPageProps {
  executor: Executor
  onBack: () => void
  onLogout: () => void
}

export function SettingsPage({ executor, onBack, onLogout }: SettingsPageProps) {
  const { t, i18n } = useTranslation()
  const { canInstall, installApp, notificationPermission, requestNotificationPermission } = usePWA()

  const [displayName, setDisplayName] = useState(executor.display_name || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    newTasks: true,
    taskAssigned: true,
    submissionReviewed: true,
    paymentReceived: true,
    disputes: true,
    marketing: false,
  })

  const [privacySettings, setPrivacySettings] = useState<PrivacySettings>({
    showEarnings: true,
    showLocation: true,
    showActivity: true,
  })

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // Load settings from storage
  useEffect(() => {
    const savedNotifications = localStorage.getItem('em_notification_settings')
    if (savedNotifications) {
      setNotificationSettings(JSON.parse(savedNotifications))
    }

    const savedPrivacy = localStorage.getItem('em_privacy_settings')
    if (savedPrivacy) {
      setPrivacySettings(JSON.parse(savedPrivacy))
    }
  }, [])

  // Save profile
  const saveProfile = useCallback(async () => {
    try {
      setSaving(true)

      const { error } = await supabase
        .from('executors')
        .update({ display_name: displayName.trim() || null })
        .eq('id', executor.id)

      if (error) throw error

      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Failed to save profile:', err)
    } finally {
      setSaving(false)
    }
  }, [displayName, executor.id])

  // Update notification setting
  const updateNotificationSetting = useCallback((key: keyof NotificationSettings, value: boolean) => {
    setNotificationSettings((prev) => {
      const updated = { ...prev, [key]: value }
      localStorage.setItem('em_notification_settings', JSON.stringify(updated))
      return updated
    })
  }, [])

  // Update privacy setting
  const updatePrivacySetting = useCallback((key: keyof PrivacySettings, value: boolean) => {
    setPrivacySettings((prev) => {
      const updated = { ...prev, [key]: value }
      localStorage.setItem('em_privacy_settings', JSON.stringify(updated))
      return updated
    })
  }, [])

  // Change language
  const changeLanguage = useCallback((lang: string) => {
    i18n.changeLanguage(lang)
    localStorage.setItem('em_language', lang)
  }, [i18n])

  // Delete account
  const deleteAccount = useCallback(async () => {
    // In production, this would call a backend endpoint
    // that handles proper account deletion
    console.log('Account deletion requested')
    setShowDeleteConfirm(false)
    onLogout()
  }, [onLogout])

  // Toggle component
  const Toggle = ({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) => (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? 'bg-blue-600' : 'bg-gray-200'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-4 py-4 flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold text-gray-900">
            {t('settings.title', 'Configuracion')}
          </h1>
        </div>
      </div>

      <div className="p-4 space-y-6 pb-20">
        {/* Profile section */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">
              {t('settings.profile', 'Perfil')}
            </h2>
          </div>

          <div className="p-4 space-y-4">
            {/* Display name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('settings.displayName', 'Nombre visible')}
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t('settings.namePlaceholder', 'Tu nombre o apodo')}
              />
            </div>

            {/* Wallet address (read-only) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('settings.wallet', 'Billetera')}
              </label>
              <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 rounded-lg">
                <span className="font-mono text-sm text-gray-600 truncate">
                  {executor.wallet_address}
                </span>
                <button
                  onClick={() => navigator.clipboard.writeText(executor.wallet_address)}
                  className="text-gray-400 hover:text-gray-600 flex-shrink-0"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Save button */}
            <button
              onClick={saveProfile}
              disabled={saving || displayName === (executor.display_name || '')}
              className="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {t('common.saving', 'Guardando...')}
                </>
              ) : saved ? (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {t('common.saved', 'Guardado')}
                </>
              ) : (
                t('common.save', 'Guardar cambios')
              )}
            </button>
          </div>
        </section>

        {/* Language section */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">
              {t('settings.language', 'Idioma')}
            </h2>
          </div>

          <div className="p-4">
            <div className="grid grid-cols-3 gap-2">
              {[
                { code: 'es', label: 'Espanol', flag: '🇪🇸' },
                { code: 'en', label: 'English', flag: '🇺🇸' },
                { code: 'pt', label: 'Portugues', flag: '🇧🇷' },
              ].map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => changeLanguage(lang.code)}
                  className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-colors ${
                    i18n.language === lang.code
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span>{lang.flag}</span>
                  <span className="text-sm font-medium">{lang.label}</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Notifications section */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-medium text-gray-900">
              {t('settings.notifications', 'Notificaciones')}
            </h2>
            {notificationPermission !== 'granted' && (
              <button
                onClick={requestNotificationPermission}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                {t('settings.enableNotifications', 'Habilitar')}
              </button>
            )}
          </div>

          <div className="divide-y divide-gray-100">
            {[
              { key: 'newTasks', label: t('settings.notif.newTasks', 'Nuevas tareas disponibles') },
              { key: 'taskAssigned', label: t('settings.notif.taskAssigned', 'Tarea asignada') },
              { key: 'submissionReviewed', label: t('settings.notif.submissionReviewed', 'Envio revisado') },
              { key: 'paymentReceived', label: t('settings.notif.paymentReceived', 'Pago recibido') },
              { key: 'disputes', label: t('settings.notif.disputes', 'Actualizaciones de disputas') },
              { key: 'marketing', label: t('settings.notif.marketing', 'Novedades y promociones') },
            ].map((item) => (
              <div key={item.key} className="px-4 py-3 flex items-center justify-between">
                <span className="text-gray-700">{item.label}</span>
                <Toggle
                  checked={notificationSettings[item.key as keyof NotificationSettings]}
                  onChange={(v) => updateNotificationSetting(item.key as keyof NotificationSettings, v)}
                />
              </div>
            ))}
          </div>
        </section>

        {/* Privacy section */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">
              {t('settings.privacy', 'Privacidad')}
            </h2>
          </div>

          <div className="divide-y divide-gray-100">
            {[
              { key: 'showEarnings', label: t('settings.privacy.showEarnings', 'Mostrar ganancias en perfil') },
              { key: 'showLocation', label: t('settings.privacy.showLocation', 'Mostrar ubicacion aproximada') },
              { key: 'showActivity', label: t('settings.privacy.showActivity', 'Mostrar actividad reciente') },
            ].map((item) => (
              <div key={item.key} className="px-4 py-3 flex items-center justify-between">
                <span className="text-gray-700">{item.label}</span>
                <Toggle
                  checked={privacySettings[item.key as keyof PrivacySettings]}
                  onChange={(v) => updatePrivacySetting(item.key as keyof PrivacySettings, v)}
                />
              </div>
            ))}
          </div>
        </section>

        {/* App section */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">
              {t('settings.app', 'Aplicacion')}
            </h2>
          </div>

          <div className="divide-y divide-gray-100">
            {/* Install app */}
            {canInstall && (
              <button
                onClick={installApp}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium text-gray-900">
                    {t('settings.installApp', 'Instalar app')}
                  </p>
                  <p className="text-sm text-gray-500">
                    {t('settings.installAppDesc', 'Accede mas rapido desde tu pantalla de inicio')}
                  </p>
                </div>
                <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}

            {/* Version info */}
            <div className="px-4 py-3 flex items-center justify-between">
              <span className="text-gray-700">{t('settings.version', 'Version')}</span>
              <span className="text-gray-500">1.0.0</span>
            </div>
          </div>
        </section>

        {/* Account actions */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">
              {t('settings.account', 'Cuenta')}
            </h2>
          </div>

          <div className="divide-y divide-gray-100">
            {/* Logout */}
            <button
              onClick={onLogout}
              className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors"
            >
              <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </div>
              <span className="text-gray-900">{t('settings.logout', 'Cerrar sesion')}</span>
            </button>

            {/* Delete account */}
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="w-full px-4 py-3 flex items-center gap-3 hover:bg-red-50 transition-colors"
            >
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <span className="text-red-600">{t('settings.deleteAccount', 'Eliminar cuenta')}</span>
            </button>
          </div>
        </section>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg w-full max-w-sm overflow-hidden animate-scale-in">
            <div className="p-6 text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {t('settings.deleteConfirmTitle', 'Eliminar cuenta?')}
              </h3>
              <p className="text-gray-600 mb-6">
                {t('settings.deleteConfirmMessage', 'Esta accion es permanente y no se puede deshacer. Se perderan todos tus datos y ganancias pendientes.')}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {t('common.cancel', 'Cancelar')}
                </button>
                <button
                  onClick={deleteAccount}
                  className="flex-1 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors"
                >
                  {t('settings.deleteConfirm', 'Si, eliminar')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SettingsPage
