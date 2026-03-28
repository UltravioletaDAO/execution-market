import React from 'react'

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

/**
 * Global error boundary that catches React render errors.
 * Shows a dark-themed fallback UI with error details (dev only) and a reload button.
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('[ErrorBoundary] Uncaught error:', error)
    console.error('[ErrorBoundary] Component stack:', errorInfo.componentStack)
    this.setState({ errorInfo })
  }

  handleReload = (): void => {
    window.location.reload()
  }

  render(): React.ReactNode {
    if (!this.state.hasError) {
      return this.props.children
    }

    if (this.props.fallback) {
      return this.props.fallback
    }

    const isDev = import.meta.env.DEV
    const { error, errorInfo } = this.state

    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-6">
        <div className="max-w-xl w-full bg-gray-800 rounded-lg border border-gray-700 shadow-xl p-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg
                className="w-5 h-5 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-white">Something went wrong</h1>
          </div>

          <p className="text-gray-400 mb-6">
            An unexpected error occurred. Please reload the page to try again.
          </p>

          {isDev && error && (
            <div className="mb-6 space-y-3">
              <div className="bg-gray-900 rounded border border-gray-700 p-4">
                <p className="text-sm font-mono text-red-400 break-all">
                  {error.name}: {error.message}
                </p>
              </div>

              {error.stack && (
                <details className="group">
                  <summary className="text-sm text-em-400 cursor-pointer hover:text-em-300 select-none">
                    Stack trace
                  </summary>
                  <pre className="mt-2 bg-gray-900 rounded border border-gray-700 p-4 text-xs text-gray-400 font-mono overflow-x-auto max-h-60 overflow-y-auto whitespace-pre-wrap">
                    {error.stack}
                  </pre>
                </details>
              )}

              {errorInfo?.componentStack && (
                <details className="group">
                  <summary className="text-sm text-em-400 cursor-pointer hover:text-em-300 select-none">
                    Component stack
                  </summary>
                  <pre className="mt-2 bg-gray-900 rounded border border-gray-700 p-4 text-xs text-gray-400 font-mono overflow-x-auto max-h-60 overflow-y-auto whitespace-pre-wrap">
                    {errorInfo.componentStack}
                  </pre>
                </details>
              )}
            </div>
          )}

          <button
            onClick={this.handleReload}
            className="w-full px-4 py-2.5 bg-em-600 hover:bg-em-500 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-em-400 focus:ring-offset-2 focus:ring-offset-gray-800"
          >
            Reload Page
          </button>
        </div>
      </div>
    )
  }
}

export default ErrorBoundary
