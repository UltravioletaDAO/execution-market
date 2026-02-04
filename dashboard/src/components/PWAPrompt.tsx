/**
 * PWAPrompt - Install prompt and offline indicator
 *
 * Features:
 * - Install app banner
 * - Offline indicator
 * - Update available notification
 * - iOS install instructions
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { usePWA } from '../hooks/usePWA'

interface PWAPromptProps {
  onInstall?: () => void
  onDismiss?: () => void
}

export function PWAPrompt({ onInstall, onDismiss }: PWAPromptProps) {
  const { t } = useTranslation()
  const {
    canInstall,
    isInstalled,
    installApp,
    isOnline,
    swUpdateAvailable,
    updateServiceWorker,
  } = usePWA()

  const [showInstallBanner, setShowInstallBanner] = useState(false)
  const [showIOSPrompt, setShowIOSPrompt] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  // Check if iOS Safari
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
  const isIOSSafari = isIOS && /Safari/.test(navigator.userAgent) && !/CriOS|FxiOS/.test(navigator.userAgent)

  // Show install banner after delay
  useEffect(() => {
    if (isInstalled || dismissed) return

    const timer = setTimeout(() => {
      if (canInstall) {
        setShowInstallBanner(true)
      } else if (isIOSSafari) {
        // Check if already dismissed this session
        const iosDismissed = sessionStorage.getItem('em-ios-prompt-dismissed')
        if (!iosDismissed) {
          setShowIOSPrompt(true)
        }
      }
    }, 30000) // 30 seconds

    return () => clearTimeout(timer)
  }, [canInstall, isInstalled, isIOSSafari, dismissed])

  // Handle install click
  const handleInstall = async () => {
    const success = await installApp()
    if (success) {
      setShowInstallBanner(false)
      onInstall?.()
    }
  }

  // Handle dismiss
  const handleDismiss = () => {
    setShowInstallBanner(false)
    setShowIOSPrompt(false)
    setDismissed(true)
    sessionStorage.setItem('em-ios-prompt-dismissed', 'true')
    onDismiss?.()
  }

  // Handle update
  const handleUpdate = () => {
    updateServiceWorker()
  }

  return (
    <>
      {/* Offline indicator */}
      {!isOnline && (
        <div className="fixed top-0 left-0 right-0 bg-yellow-500 text-yellow-900 text-center py-2 px-4 z-50">
          <div className="flex items-center justify-center gap-2">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
            </svg>
            <span className="text-sm font-medium">
              {t('pwa.offline', 'Sin conexion - Los cambios se sincronizaran cuando vuelvas a estar en linea')}
            </span>
          </div>
        </div>
      )}

      {/* Update available banner */}
      {swUpdateAvailable && (
        <div className="fixed bottom-20 left-4 right-4 md:left-auto md:right-4 md:w-96 bg-blue-600 text-white rounded-lg shadow-lg p-4 z-50">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-medium">
                {t('pwa.updateAvailable', 'Actualizacion disponible')}
              </p>
              <p className="text-sm text-blue-100 mt-1">
                {t('pwa.updateMessage', 'Una nueva version de Execution Market esta lista')}
              </p>
              <button
                onClick={handleUpdate}
                className="mt-3 px-4 py-2 bg-white text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition-colors"
              >
                {t('pwa.updateNow', 'Actualizar ahora')}
              </button>
            </div>
            <button
              onClick={() => {/* Could add dismiss logic */}}
              className="text-blue-200 hover:text-white"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Install banner (Android/Desktop) */}
      {showInstallBanner && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg p-4 z-50 safe-area-bottom">
          <div className="max-w-lg mx-auto flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xl font-bold">EM</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900">
                {t('pwa.installTitle', 'Instalar Execution Market')}
              </p>
              <p className="text-sm text-gray-500 truncate">
                {t('pwa.installSubtitle', 'Accede mas rapido desde tu pantalla de inicio')}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDismiss}
                className="px-3 py-2 text-gray-500 text-sm hover:text-gray-700"
              >
                {t('common.notNow', 'Ahora no')}
              </button>
              <button
                onClick={handleInstall}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('pwa.install', 'Instalar')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* iOS install instructions */}
      {showIOSPrompt && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center">
          <div className="bg-white rounded-t-2xl w-full max-w-lg p-6 safe-area-bottom animate-slide-up">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center">
                  <span className="text-white text-xl font-bold">EM</span>
                </div>
                <div>
                  <p className="font-semibold text-gray-900">
                    {t('pwa.installTitle', 'Instalar Execution Market')}
                  </p>
                  <p className="text-sm text-gray-500">
                    {t('pwa.addToHome', 'Agregar a pantalla de inicio')}
                  </p>
                </div>
              </div>
              <button
                onClick={handleDismiss}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium">
                  1
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900">
                    {t('pwa.iosStep1', 'Toca el boton de compartir')}
                  </p>
                </div>
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>

              <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium">
                  2
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900">
                    {t('pwa.iosStep2', 'Selecciona "Agregar a pantalla de inicio"')}
                  </p>
                </div>
                <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>

              <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium">
                  3
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900">
                    {t('pwa.iosStep3', 'Toca "Agregar"')}
                  </p>
                </div>
                <svg className="w-6 h-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>

            <button
              onClick={handleDismiss}
              className="w-full mt-6 py-3 text-gray-500 text-sm"
            >
              {t('common.maybeLater', 'Quiza mas tarde')}
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export default PWAPrompt
