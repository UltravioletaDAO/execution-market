import { StrictMode, lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'

// Initialize i18n (must be imported before App)
import './i18n'

// Prime platform config cache early so services have it available
import { ensurePlatformConfig } from './hooks/usePlatformConfig'
ensurePlatformConfig()

// Lazy-load Dynamic.xyz provider — the SDK is ~4MB and should not block initial render
const DynamicProvider = lazy(() =>
  import('./providers/DynamicProvider').then(m => ({ default: m.DynamicProvider }))
)

import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import './index.css'

// --------------------------------------------------------------------------
// Sentry — Task 1.6 (SaaS Production Hardening)
// --------------------------------------------------------------------------
// Initializes only when VITE_SENTRY_DSN is set. Without a DSN, the SDK is
// inert and `captureException` is a safe no-op, so the app (and the
// ErrorBoundary) keep working.
//
// PII scrubber: wallet addresses (0x + 40 hex) are truncated to 0xabcd...ef01
// in every string field before the event leaves the browser.
// --------------------------------------------------------------------------

const SENTRY_DSN = (import.meta.env.VITE_SENTRY_DSN ?? '').trim()

if (SENTRY_DSN) {
  const WALLET_RE = /0x[a-fA-F0-9]{40}/g

  const scrubWallets = (value: unknown, seen: WeakSet<object> = new WeakSet()): unknown => {
    if (typeof value === 'string') {
      return value.replace(WALLET_RE, (m) => `${m.slice(0, 6)}...${m.slice(-4)}`)
    }
    if (Array.isArray(value)) {
      return value.map((v) => scrubWallets(v, seen))
    }
    if (value && typeof value === 'object') {
      if (seen.has(value as object)) return value
      seen.add(value as object)
      const out: Record<string, unknown> = {}
      for (const key of Object.keys(value as Record<string, unknown>)) {
        out[key] = scrubWallets((value as Record<string, unknown>)[key], seen)
      }
      return out
    }
    return value
  }

  Sentry.init({
    dsn: SENTRY_DSN,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.0,
    replaysOnErrorSampleRate: 1.0,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_GIT_SHA || 'unknown',
    beforeSend(event) {
      return scrubWallets(event) as typeof event
    },
  })
}

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
      staleTime: 1000 * 30, // 30 seconds — financial data must stay fresh
      refetchOnWindowFocus: true,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Suspense fallback={
          <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: '#6b7280' }}>Loading...</div>
          </div>
        }>
          <DynamicProvider>
            <App />
          </DynamicProvider>
        </Suspense>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
)
