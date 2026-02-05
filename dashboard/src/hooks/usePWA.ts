/**
 * usePWA - Progressive Web App installation and features
 *
 * Features:
 * - Service worker registration
 * - Install prompt handling
 * - Online/offline status
 * - Push notification subscription
 * - Background sync registration
 */

import { useState, useEffect, useCallback } from 'react'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

interface UsePWAReturn {
  // Installation
  canInstall: boolean
  isInstalled: boolean
  installApp: () => Promise<boolean>
  isMobile: boolean

  // Online status
  isOnline: boolean

  // Push notifications
  notificationPermission: NotificationPermission | 'unsupported'
  requestNotificationPermission: () => Promise<boolean>
  subscribeToPush: (vapidPublicKey: string) => Promise<PushSubscription | null>

  // Service worker
  swRegistration: ServiceWorkerRegistration | null
  swUpdateAvailable: boolean
  updateServiceWorker: () => void
  checkForUpdate: () => Promise<boolean>
}

export function usePWA(): UsePWAReturn {
  // Installation state
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [isInstalled, setIsInstalled] = useState(false)

  // Online status
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  // Notifications
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission | 'unsupported'>(
    'Notification' in window ? Notification.permission : 'unsupported'
  )

  // Service worker
  const [swRegistration, setSwRegistration] = useState<ServiceWorkerRegistration | null>(null)
  const [swUpdateAvailable, setSwUpdateAvailable] = useState(false)

  // Check if app is installed
  useEffect(() => {
    // Check display mode
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    const isIOSStandalone = (navigator as { standalone?: boolean }).standalone === true

    setIsInstalled(isStandalone || isIOSStandalone)
  }, [])

  // Listen for install prompt
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault()
      setInstallPrompt(e as BeforeInstallPromptEvent)
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    }
  }, [])

  // Listen for app installed
  useEffect(() => {
    const handleAppInstalled = () => {
      setIsInstalled(true)
      setInstallPrompt(null)
    }

    window.addEventListener('appinstalled', handleAppInstalled)

    return () => {
      window.removeEventListener('appinstalled', handleAppInstalled)
    }
  }, [])

  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Register service worker
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          setSwRegistration(registration)

          // Check for updates
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  setSwUpdateAvailable(true)
                }
              })
            }
          })
        })
        .catch((error) => {
          console.error('Service worker registration failed:', error)
        })

      // Listen for controller change (new SW activated)
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        window.location.reload()
      })
    }
  }, [])

  // Install app
  const installApp = useCallback(async (): Promise<boolean> => {
    if (!installPrompt) return false

    try {
      await installPrompt.prompt()
      const { outcome } = await installPrompt.userChoice

      if (outcome === 'accepted') {
        setInstallPrompt(null)
        return true
      }
      return false
    } catch (error) {
      console.error('Install failed:', error)
      return false
    }
  }, [installPrompt])

  // Request notification permission
  const requestNotificationPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) {
      return false
    }

    try {
      const permission = await Notification.requestPermission()
      setNotificationPermission(permission)
      return permission === 'granted'
    } catch (error) {
      console.error('Notification permission request failed:', error)
      return false
    }
  }, [])

  // Subscribe to push notifications
  const subscribeToPush = useCallback(
    async (vapidPublicKey: string): Promise<PushSubscription | null> => {
      if (!swRegistration) {
        console.error('No service worker registration')
        return null
      }

      try {
        const subscription = await swRegistration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as BufferSource,
        })

        return subscription
      } catch (error) {
        console.error('Push subscription failed:', error)
        return null
      }
    },
    [swRegistration]
  )

  // Update service worker
  const updateServiceWorker = useCallback(() => {
    if (swRegistration?.waiting) {
      swRegistration.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
  }, [swRegistration])

  // Check for updates manually
  const checkForUpdate = useCallback(async (): Promise<boolean> => {
    if (!swRegistration) return false

    try {
      await swRegistration.update()
      return !!swRegistration.waiting
    } catch (error) {
      console.error('[SW] Update check failed:', error)
      return false
    }
  }, [swRegistration])

  // Detect mobile device
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  )

  return {
    canInstall: !!installPrompt,
    isInstalled,
    installApp,
    isMobile,
    isOnline,
    notificationPermission,
    requestNotificationPermission,
    subscribeToPush,
    swRegistration,
    swUpdateAvailable,
    updateServiceWorker,
    checkForUpdate,
  }
}

// Helper to convert VAPID key
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }

  return outputArray
}

/**
 * Push Notification Permission Hook
 *
 * Standalone hook for managing push notification permissions and subscriptions.
 */
export function usePushNotifications() {
  const [permission, setPermission] = useState<NotificationPermission>(
    'Notification' in window ? Notification.permission : 'denied'
  )
  const [subscription, setSubscription] = useState<PushSubscription | null>(null)

  useEffect(() => {
    // Check existing subscription
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      navigator.serviceWorker.ready.then((registration) => {
        registration.pushManager.getSubscription().then(setSubscription)
      })
    }
  }, [])

  const requestPermission = useCallback(async () => {
    if (!('Notification' in window)) return false

    const result = await Notification.requestPermission()
    setPermission(result)
    return result === 'granted'
  }, [])

  const subscribe = useCallback(async (vapidPublicKey: string) => {
    if (!('serviceWorker' in navigator)) return null

    const registration = await navigator.serviceWorker.ready

    const sub = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as BufferSource,
    })

    setSubscription(sub)
    return sub
  }, [])

  return {
    permission,
    subscription,
    isSupported: 'Notification' in window && 'PushManager' in window,
    requestPermission,
    subscribe,
  }
}

export default usePWA
