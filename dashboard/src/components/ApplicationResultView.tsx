import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

export type ApplicationResultState =
  | 'success'
  | 'success_suggest_worldid'
  | 'blocked_worldid'
  | 'already_applied'
  | 'error'

interface ApplicationResultViewProps {
  state: ApplicationResultState
  /** Bounty threshold that triggers World ID requirement */
  worldIdThreshold?: number
  /** Error message to display in error state */
  errorMessage?: string
  onClose: () => void
  onRetry?: () => void
}

/** Hide image on load failure instead of showing broken icon */
function hideOnError(e: React.SyntheticEvent<HTMLImageElement>) {
  e.currentTarget.style.display = 'none'
}

export function ApplicationResultView({
  state,
  worldIdThreshold = 5,
  errorMessage,
  onClose,
  onRetry,
}: ApplicationResultViewProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  if (state === 'success' || state === 'success_suggest_worldid') {
    return (
      <div role="status" className="flex flex-col items-center text-center py-6 px-4 space-y-4">
        {/* Success checkmark */}
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
          <svg aria-hidden="true" className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h3 className="text-lg font-bold text-gray-900">
          {t('application.result.successTitle', 'Application submitted!')}
        </h3>
        <p className="text-sm text-gray-600 max-w-xs">
          {t(
            'application.result.successMessage',
            'Your application has been sent. The agent will review it and decide whether to assign you this task.'
          )}
        </p>

        {/* World ID suggestion for low-value tasks */}
        {state === 'success_suggest_worldid' && (
          <div className="w-full bg-gray-50 border border-gray-200 rounded-xl p-4 mt-2">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                <img src="/worldcoin.png" alt="" className="w-5 h-5 object-contain" onError={hideOnError} />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-gray-800">
                  {t('application.result.suggestWorldIdTitle', 'Unlock higher-value tasks')}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {t(
                    'application.result.suggestWorldIdMessage',
                    'Verify with World ID to access tasks worth ${{threshold}} or more. It only takes a minute.',
                    { threshold: worldIdThreshold }
                  )}
                </p>
                <button
                  onClick={() => navigate('/profile')}
                  className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-black hover:text-gray-700 underline underline-offset-2"
                >
                  <img src="/worldcoin.png" alt="" className="w-3 h-3" onError={hideOnError} />
                  {t('application.result.suggestWorldIdCta', 'Verify now')}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CTA */}
        <div className="flex gap-3 w-full pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 border border-gray-200 rounded-xl transition-colors"
          >
            {t('common.close', 'Close')}
          </button>
          <button
            onClick={() => {
              onClose()
              navigate('/tasks', { state: { tab: 'mine' } })
            }}
            className="flex-1 py-2.5 bg-gray-900 text-white text-sm font-semibold rounded-xl hover:bg-gray-800 transition-colors"
          >
            {t('application.result.viewMyTasks', 'View my tasks')}
          </button>
        </div>
      </div>
    )
  }

  if (state === 'blocked_worldid') {
    return (
      <div role="alert" className="flex flex-col items-center text-center py-6 px-4 space-y-4">
        {/* World ID logo */}
        <div className="w-16 h-16 rounded-full flex items-center justify-center overflow-hidden bg-black">
          <img src="/worldcoin.png" alt="World ID" className="w-10 h-10 object-contain" onError={hideOnError} />
        </div>

        <h3 className="text-lg font-bold text-gray-900">
          {t('application.result.blockedTitle', 'Identity verification required')}
        </h3>

        <p className="text-sm text-gray-600 max-w-xs">
          {t(
            'application.result.blockedMessage',
            'Tasks with a bounty of ${{threshold}} or more require World ID Orb verification to protect against fraud.',
            { threshold: worldIdThreshold }
          )}
        </p>

        {/* Explainer box */}
        <div className="w-full bg-gray-50 border border-gray-200 rounded-xl p-4 text-left">
          <div className="flex items-start gap-3">
            <svg aria-hidden="true" className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            <div>
              <p className="text-xs text-gray-500 leading-relaxed">
                {t(
                  'application.result.blockedExplainer',
                  'World ID verifies you are a unique person without revealing your identity. You only need to verify once — it takes about a minute.'
                )}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-amber-100 text-amber-800">
                  {t('application.result.blockedThreshold', 'Required for tasks >= ${{threshold}}', {
                    threshold: worldIdThreshold,
                  })}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="flex gap-3 w-full pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 border border-gray-200 rounded-xl transition-colors"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            onClick={() => {
              onClose()
              navigate('/profile')
            }}
            className="flex-1 py-2.5 bg-black text-white text-sm font-semibold rounded-xl hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
          >
            <img src="/worldcoin.png" alt="" className="w-4 h-4" onError={hideOnError} />
            {t('application.result.verifyCta', 'Verify with World ID')}
          </button>
        </div>
      </div>
    )
  }

  if (state === 'already_applied') {
    return (
      <div role="status" className="flex flex-col items-center text-center py-6 px-4 space-y-4">
        {/* Info icon */}
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
          <svg aria-hidden="true" className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        <h3 className="text-lg font-bold text-gray-900">
          {t('application.result.alreadyAppliedTitle', 'Already applied')}
        </h3>
        <p className="text-sm text-gray-600 max-w-xs">
          {t(
            'application.result.alreadyAppliedMessage',
            'You have already applied to this task. The agent is reviewing applications and will assign a worker soon.'
          )}
        </p>

        {/* CTA */}
        <div className="flex gap-3 w-full pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 border border-gray-200 rounded-xl transition-colors"
          >
            {t('common.close', 'Close')}
          </button>
          <button
            onClick={() => {
              onClose()
              navigate('/tasks', { state: { tab: 'mine' } })
            }}
            className="flex-1 py-2.5 bg-gray-900 text-white text-sm font-semibold rounded-xl hover:bg-gray-800 transition-colors"
          >
            {t('application.result.viewMyTasks', 'View my tasks')}
          </button>
        </div>
      </div>
    )
  }

  // Error state
  return (
    <div role="alert" className="flex flex-col items-center text-center py-6 px-4 space-y-4">
      {/* Error icon */}
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
        <svg aria-hidden="true" className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
      </div>

      <h3 className="text-lg font-bold text-gray-900">
        {t('application.result.errorTitle', 'Something went wrong')}
      </h3>
      <p className="text-sm text-gray-600 max-w-xs">
        {errorMessage || t('application.result.errorMessage', 'Could not submit your application. Please try again.')}
      </p>

      {/* CTA */}
      <div className="flex gap-3 w-full pt-2">
        <button
          onClick={onClose}
          className="flex-1 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 border border-gray-200 rounded-xl transition-colors"
        >
          {t('common.close', 'Close')}
        </button>
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex-1 py-2.5 bg-gray-900 text-white text-sm font-semibold rounded-xl hover:bg-gray-800 transition-colors"
          >
            {t('common.retry', 'Retry')}
          </button>
        )}
      </div>
    </div>
  )
}
