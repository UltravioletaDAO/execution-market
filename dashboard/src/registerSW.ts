/**
 * Service Worker Registration
 *
 * Handles service worker registration, updates, and user prompts.
 */

interface ServiceWorkerConfig {
  onUpdate?: (registration: ServiceWorkerRegistration) => void
  onSuccess?: (registration: ServiceWorkerRegistration) => void
  onError?: (error: Error) => void
}

let refreshing = false

/**
 * Register the service worker on page load
 */
export function register(config?: ServiceWorkerConfig): void {
  if (!('serviceWorker' in navigator)) {
    console.log('[SW] Service workers are not supported')
    return
  }

  // Only register SW on the dashboard hostname, not api.* or mcp.*
  const hostname = window.location.hostname
  if (hostname !== 'execution.market' && hostname !== 'localhost') {
    console.log('[SW] Skipping registration on non-dashboard hostname:', hostname)
    return
  }

  window.addEventListener('load', () => {
    registerServiceWorker('/sw.js', config)
  })
}

/**
 * Register a service worker at the given URL
 */
async function registerServiceWorker(
  swUrl: string,
  config?: ServiceWorkerConfig
): Promise<void> {
  try {
    const registration = await navigator.serviceWorker.register(swUrl)

    console.log('[SW] Registered:', registration.scope)

    // Check for updates on registration
    registration.addEventListener('updatefound', () => {
      const installingWorker = registration.installing

      if (!installingWorker) return

      installingWorker.addEventListener('statechange', () => {
        if (installingWorker.state === 'installed') {
          if (navigator.serviceWorker.controller) {
            // New update available
            console.log('[SW] New content available; please refresh.')
            config?.onUpdate?.(registration)
          } else {
            // First install
            console.log('[SW] Content cached for offline use.')
            config?.onSuccess?.(registration)
          }
        }
      })
    })

    // Handle controller change (new SW activated)
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!refreshing) {
        refreshing = true
        window.location.reload()
      }
    })

    // Check for updates periodically (every hour)
    setInterval(() => {
      registration.update().catch((err) => {
        console.error('[SW] Update check failed:', err)
      })
    }, 60 * 60 * 1000)

  } catch (error) {
    console.error('[SW] Registration failed:', error)
    config?.onError?.(error as Error)
  }
}

/**
 * Unregister the service worker
 */
export async function unregister(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) return false

  try {
    const registration = await navigator.serviceWorker.ready
    const success = await registration.unregister()

    if (success) {
      console.log('[SW] Unregistered successfully')
    }

    return success
  } catch (error) {
    console.error('[SW] Unregister failed:', error)
    return false
  }
}

/**
 * Skip waiting and activate the new service worker
 */
export function skipWaiting(registration: ServiceWorkerRegistration): void {
  if (registration.waiting) {
    registration.waiting.postMessage({ type: 'SKIP_WAITING' })
  }
}

/**
 * Check if there's a service worker update available
 */
export async function checkForUpdate(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) return false

  try {
    const registration = await navigator.serviceWorker.ready
    await registration.update()

    return !!registration.waiting
  } catch (error) {
    console.error('[SW] Update check failed:', error)
    return false
  }
}

/**
 * Get the current service worker registration
 */
export async function getRegistration(): Promise<ServiceWorkerRegistration | undefined> {
  if (!('serviceWorker' in navigator)) return undefined

  return navigator.serviceWorker.getRegistration()
}

/**
 * Clear all caches managed by the service worker
 */
export async function clearCaches(): Promise<boolean> {
  try {
    const cacheNames = await caches.keys()
    await Promise.all(cacheNames.map((name) => caches.delete(name)))
    console.log('[SW] Caches cleared')
    return true
  } catch (error) {
    console.error('[SW] Cache clear failed:', error)
    return false
  }
}

export default { register, unregister, skipWaiting, checkForUpdate, getRegistration, clearCaches }
