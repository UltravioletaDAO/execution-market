/**
 * PWA Install Prompt Component
 *
 * Mobile-focused install prompt for PWA installation.
 * - Only shows on mobile devices by default
 * - Persistent dismissal using localStorage
 * - Update notification support
 */

import React, { useState, useEffect } from 'react'
import { usePWA } from '../hooks/usePWA'

const DISMISS_KEY = 'chamba-install-dismissed'
const DISMISS_DURATION = 7 * 24 * 60 * 60 * 1000 // 7 days

interface InstallPromptProps {
  onInstalled?: () => void
  onDismissed?: () => void
  showOnDesktop?: boolean
}

export function InstallPrompt({
  onInstalled,
  onDismissed,
  showOnDesktop = false,
}: InstallPromptProps) {
  const {
    canInstall,
    installApp,
    isOnline,
    isInstalled,
    isMobile,
    swUpdateAvailable,
    updateServiceWorker,
  } = usePWA()

  const [dismissed, setDismissed] = useState(false)
  const [showUpdateBanner, setShowUpdateBanner] = useState(false)

  // Check localStorage for previous dismissal
  useEffect(() => {
    const dismissedAt = localStorage.getItem(DISMISS_KEY)
    if (dismissedAt) {
      const elapsed = Date.now() - parseInt(dismissedAt, 10)
      if (elapsed < DISMISS_DURATION) {
        setDismissed(true)
      } else {
        localStorage.removeItem(DISMISS_KEY)
      }
    }
  }, [])

  // Show update banner when available
  useEffect(() => {
    if (swUpdateAvailable) {
      setShowUpdateBanner(true)
    }
  }, [swUpdateAvailable])

  const handleInstall = async () => {
    const success = await installApp()
    if (success) {
      onInstalled?.()
    }
  }

  const handleDismiss = () => {
    localStorage.setItem(DISMISS_KEY, Date.now().toString())
    setDismissed(true)
    onDismissed?.()
  }

  const handleUpdate = () => {
    updateServiceWorker()
    setShowUpdateBanner(false)
  }

  // Update banner takes priority
  if (showUpdateBanner) {
    return (
      <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 bg-blue-600 rounded-xl shadow-2xl p-4 z-50 animate-slide-up">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <svg
              className="w-5 h-5 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-white text-base">Update Available</h3>
            <p className="text-sm text-blue-100 mt-0.5">
              A new version of Chamba is ready to install.
            </p>
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleUpdate}
                className="px-4 py-2 bg-white text-blue-600 text-sm font-semibold rounded-lg hover:bg-blue-50 transition-colors"
              >
                Update Now
              </button>
              <button
                onClick={() => setShowUpdateBanner(false)}
                className="px-4 py-2 text-blue-100 hover:text-white text-sm transition-colors"
              >
                Later
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Don't show install prompt if:
  // - Already installed
  // - Can't install (no beforeinstallprompt event)
  // - Previously dismissed
  // - On desktop and showOnDesktop is false
  if (isInstalled || !canInstall || dismissed || (!isMobile && !showOnDesktop)) {
    return null
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 bg-slate-800 rounded-xl shadow-2xl p-4 border border-slate-700 z-50 animate-slide-up">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center">
          <svg
            className="w-6 h-6 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-white text-base">Install Chamba</h3>
          <p className="text-sm text-slate-400 mt-0.5 leading-relaxed">
            Add to your home screen for quick access and offline support.
          </p>
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleInstall}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-blue-600/25"
            >
              Install App
            </button>
            <button
              onClick={handleDismiss}
              className="px-4 py-2.5 text-slate-400 hover:text-white text-sm transition-colors"
            >
              Not now
            </button>
          </div>
        </div>
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Dismiss"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {!isOnline && (
        <div className="mt-3 pt-3 border-t border-slate-700 flex items-center gap-2 text-amber-400 text-sm">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span>You're currently offline</span>
        </div>
      )}

      <style>{`
        @keyframes slide-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}

/**
 * iOS Install Instructions
 *
 * Shows manual install instructions for iOS devices (no beforeinstallprompt support)
 */
export function IOSInstallPrompt() {
  const [show, setShow] = useState(false)
  const { isInstalled, isMobile } = usePWA()

  useEffect(() => {
    // Check if iOS Safari
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
    const isInStandaloneMode =
      (navigator as { standalone?: boolean }).standalone === true ||
      window.matchMedia('(display-mode: standalone)').matches

    // Show on iOS Safari when not installed
    if (isIOS && isMobile && !isInStandaloneMode && !isInstalled) {
      const dismissed = localStorage.getItem('chamba-ios-install-dismissed')
      if (!dismissed) {
        setShow(true)
      }
    }
  }, [isInstalled, isMobile])

  const handleDismiss = () => {
    localStorage.setItem('chamba-ios-install-dismissed', 'true')
    setShow(false)
  }

  if (!show) return null

  return (
    <div className="fixed bottom-4 left-4 right-4 bg-slate-800 rounded-xl shadow-2xl p-4 border border-slate-700 z-50 animate-slide-up">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center">
          <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-4H8l4-7v4h3l-4 7z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-white text-base">Install Chamba</h3>
          <p className="text-sm text-slate-400 mt-1">
            Tap{' '}
            <span className="inline-flex items-center px-1.5 py-0.5 bg-slate-700 rounded text-white">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M16 5l-1.42 1.42-1.59-1.59V16h-2V4.83L9.41 6.41 8 5l4-4 4 4zm4 5v11c0 1.1-.9 2-2 2H6c-1.11 0-2-.9-2-2V10c0-1.11.89-2 2-2h3v2H6v11h12V10h-3V8h3c1.1 0 2 .89 2 2z" />
              </svg>
            </span>{' '}
            then "Add to Home Screen"
          </p>
        </div>
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <style>{`
        @keyframes slide-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}

export default InstallPrompt
