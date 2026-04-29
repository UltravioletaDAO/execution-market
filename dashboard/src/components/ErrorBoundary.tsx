/**
 * ErrorBoundary — Global React error boundary.
 *
 * Catches render-time and lifecycle errors anywhere beneath it and shows a
 * recoverable fallback UI instead of a blank page. Errors are reported to
 * Sentry when it's initialized (Task 1.6). When Sentry is not initialized,
 * `captureException` is a safe no-op, so the boundary still works.
 *
 * Must be a class component — React Error Boundaries require class lifecycle
 * hooks (`getDerivedStateFromError` + `componentDidCatch`).
 *
 * Scope: wrap the outermost tree in `main.tsx` (see Task 1.3 of the SaaS
 * Production Hardening master plan).
 */

import { Component, type ErrorInfo, type ReactNode } from 'react'
import * as Sentry from '@sentry/react'

interface ErrorBoundaryProps {
  children: ReactNode
  /** Optional custom fallback. When omitted, the default UI is rendered. */
  fallback?: (args: { error: Error; reset: () => void; eventId?: string }) => ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  eventId?: string
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Report to Sentry. When Sentry isn't initialized (no DSN) this is a no-op
    // and returns an empty event id — we still log to the console for devs.
    let eventId: string | undefined
    try {
      eventId = Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      })
    } catch {
      // Never let Sentry bring down the fallback UI.
      eventId = undefined
    }

    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary] Uncaught error:', error, errorInfo)
    }

    this.setState({ eventId })
  }

  private handleReload = (): void => {
    window.location.reload()
  }

  private handleGoHome = (): void => {
    window.location.href = '/'
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: undefined, eventId: undefined })
  }

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children
    }

    const { error, eventId } = this.state

    if (this.props.fallback) {
      return this.props.fallback({
        error: error ?? new Error('Unknown error'),
        reset: this.handleReset,
        eventId,
      })
    }

    return (
      <div
        role="alert"
        aria-live="assertive"
        className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-12"
      >
        <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-gray-200 p-6 sm:p-8">
          <div className="flex items-start gap-3 mb-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5 text-red-600"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-lg font-semibold text-gray-900">
                Algo salió mal
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Un error inesperado ocurrió. Nuestro equipo fue notificado.
              </p>
              {eventId ? (
                <p className="mt-2 text-xs text-gray-400 font-mono break-all">
                  Ref: {eventId}
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 mt-6">
            <button
              type="button"
              onClick={this.handleReload}
              className="inline-flex items-center justify-center rounded-lg font-medium px-4 py-2 text-sm bg-zinc-900 text-white hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-zinc-700 transition-colors"
            >
              Recargar la página
            </button>
            <button
              type="button"
              onClick={this.handleGoHome}
              className="inline-flex items-center justify-center rounded-lg font-medium px-4 py-2 text-sm border-2 border-zinc-300 text-zinc-700 hover:bg-zinc-100 hover:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-zinc-500 transition-colors"
            >
              Ir al inicio
            </button>
          </div>

          {import.meta.env.DEV && error ? (
            <details className="mt-6 text-xs">
              <summary className="cursor-pointer text-gray-500 hover:text-gray-700 font-medium">
                Detalles técnicos (solo visible en dev)
              </summary>
              <div className="mt-3 space-y-2">
                <div>
                  <div className="text-gray-500 font-semibold">Message</div>
                  <pre className="mt-1 whitespace-pre-wrap break-words text-red-700 bg-red-50 rounded p-2">
                    {error.message}
                  </pre>
                </div>
                {error.stack ? (
                  <div>
                    <div className="text-gray-500 font-semibold">Stack</div>
                    <pre className="mt-1 whitespace-pre-wrap break-words text-gray-700 bg-gray-50 rounded p-2 overflow-auto max-h-64">
                      {error.stack}
                    </pre>
                  </div>
                ) : null}
              </div>
            </details>
          ) : null}
        </div>
      </div>
    )
  }
}

export default ErrorBoundary
