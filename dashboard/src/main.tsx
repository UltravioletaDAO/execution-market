import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Initialize i18n (must be imported before App)
import './i18n'

// Dynamic.xyz provider for wallet auth
import { DynamicProvider } from './providers/DynamicProvider'

import App from './App'
import './index.css'

// Emergency cache reset to recover users stuck on stale service worker builds.
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  const swResetKey = 'em_sw_reset_version'
  const swResetVersion = '2026-02-05-cache-hotfix-1'

  if (window.localStorage.getItem(swResetKey) !== swResetVersion) {
    Promise.resolve()
      .then(async () => {
        const registrations = await navigator.serviceWorker.getRegistrations()
        const hadRegistrations = registrations.length > 0
        await Promise.all(registrations.map((reg) => reg.unregister()))
        let hadCaches = false
        if ('caches' in window) {
          const cacheNames = await caches.keys()
          hadCaches = cacheNames.some((name) => name.startsWith('em-'))
          await Promise.all(
            cacheNames
              .filter((name) => name.startsWith('em-'))
              .map((name) => caches.delete(name))
          )
        }
        return hadRegistrations || hadCaches
      })
      .then((shouldReload) => {
        window.localStorage.setItem(swResetKey, swResetVersion)
        if (shouldReload) {
          window.location.reload()
        }
      })
      .catch(() => {
        window.localStorage.setItem(swResetKey, swResetVersion)
      })
  }
}

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <DynamicProvider>
        <App />
      </DynamicProvider>
    </QueryClientProvider>
  </StrictMode>,
)
