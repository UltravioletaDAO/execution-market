import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

export type ApplicationResultState =
  | 'success'
  | 'success_suggest_worldid'
  | 'blocked_worldid'
  | 'blocked_t1_dual'
  | 'already_applied'
  | 'error'

interface ApplicationResultViewProps {
  state: ApplicationResultState
  /** Bounty threshold that triggers World ID requirement (T2) */
  worldIdThreshold?: number
  /** Bounty floor for T1 (VeryAI palm OR Orb). Defaults to 50. */
  veryAiFloor?: number
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
  worldIdThreshold = 500,
  veryAiFloor = 50,
  errorMessage,
  onClose,
  onRetry,
}: ApplicationResultViewProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  if (state === 'success' || state === 'success_suggest_worldid') {
    return (
      <div role="status" className="flex flex-col items-center text-center py-6 px-4 space-y-4">
        {/* Success checkmark — semantic green for success state only */}
        <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center">
          <svg aria-hidden="true" className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h3 className="text-lg font-bold text-zinc-900">
          {t('application.result.successTitle', 'Application submitted!')}
        </h3>
        <p className="text-sm text-zinc-600 max-w-xs">
          {t(
            'application.result.successMessage',
            'Your application has been sent. The agent will review it and decide whether to assign you this task.'
          )}
        </p>

        {/* World ID suggestion for low-value tasks */}
        {state === 'success_suggest_worldid' && (
          <div className="w-full bg-zinc-50 border border-zinc-200 rounded-xl p-4 mt-2">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                <img src="/worldcoin.png" alt="" className="w-5 h-5 object-contain" onError={hideOnError} />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-zinc-800">
                  {t('application.result.suggestWorldIdTitle', 'Unlock higher-value tasks')}
                </p>
                <p className="text-xs text-zinc-600 mt-1">
                  {t(
                    'application.result.suggestWorldIdMessage',
                    'Verify with World ID to access tasks worth ${{threshold}} or more. It only takes a minute.',
                    { threshold: worldIdThreshold }
                  )}
                </p>
                <button
                  onClick={() => navigate('/profile')}
                  className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-zinc-900 hover:text-zinc-700 underline underline-offset-2"
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
            className="flex-1 py-2.5 text-sm font-medium text-zinc-700 hover:text-zinc-900 border border-zinc-300 rounded-xl transition-colors"
          >
            {t('common.close', 'Close')}
          </button>
          <button
            onClick={() => {
              onClose()
              navigate('/tasks', { state: { tab: 'mine' } })
            }}
            className="flex-1 py-2.5 bg-zinc-900 text-white text-sm font-semibold rounded-xl hover:bg-zinc-800 transition-colors"
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

        <h3 className="text-lg font-bold text-zinc-900">
          {t('application.result.blockedTitle', 'Identity verification required')}
        </h3>

        <p className="text-sm text-zinc-600 max-w-xs">
          {t(
            'application.result.blockedMessage',
            'Tasks with a bounty of ${{threshold}} or more require World ID Orb verification to protect against fraud.',
            { threshold: worldIdThreshold }
          )}
        </p>

        {/* Explainer box */}
        <div className="w-full bg-zinc-50 border border-zinc-200 rounded-xl p-4 text-left">
          <div className="flex items-start gap-3">
            <svg aria-hidden="true" className="w-5 h-5 text-zinc-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            <div>
              <p className="text-xs text-zinc-600 leading-relaxed">
                {t(
                  'application.result.blockedExplainer',
                  'World ID verifies you are a unique person without revealing your identity. You only need to verify once — it takes about a minute.'
                )}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-amber-50 text-amber-800 border border-amber-300">
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
            className="flex-1 py-2.5 text-sm font-medium text-zinc-700 hover:text-zinc-900 border border-zinc-300 rounded-xl transition-colors"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            onClick={() => {
              onClose()
              navigate('/profile')
            }}
            className="flex-1 py-2.5 bg-zinc-900 text-white text-sm font-semibold rounded-xl hover:bg-zinc-800 transition-colors flex items-center justify-center gap-2"
          >
            <img src="/worldcoin.png" alt="" className="w-4 h-4" onError={hideOnError} />
            {t('application.result.verifyCta', 'Verify with World ID')}
          </button>
        </div>
      </div>
    )
  }

  if (state === 'blocked_t1_dual') {
    // T1 band ($50 - <$500): worker has neither palm nor Orb. Two CTAs
    // side-by-side, fastest path wins. Both deep-link to /profile so the
    // worker lands on the verification cards.
    return (
      <div role="alert" className="flex flex-col items-center text-center py-6 px-4 space-y-4">
        <div className="w-16 h-16 bg-zinc-100 rounded-full flex items-center justify-center">
          <svg aria-hidden="true" className="w-8 h-8 text-zinc-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
        </div>

        <h3 className="text-lg font-bold text-zinc-900">
          {t('application.result.blockedT1Title', 'Human verification required')}
        </h3>

        <p className="text-sm text-zinc-600 max-w-xs">
          {t(
            'application.result.blockedT1Message',
            'Tasks between ${{floor}} and ${{threshold}} require human verification. Pick whichever path is fastest for you.',
            { floor: veryAiFloor, threshold: worldIdThreshold },
          )}
        </p>

        {/* Dual provider CTAs side-by-side */}
        <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            onClick={() => {
              onClose()
              navigate('/profile')
            }}
            className="flex flex-col items-center gap-2 p-4 border border-zinc-200 rounded-xl hover:bg-zinc-50 transition-colors"
          >
            <img src="/worldcoin.png" alt="" className="w-8 h-8" onError={hideOnError} />
            <span className="text-sm font-semibold text-zinc-900">
              {t('application.result.verifyOrbCta', 'Verify with Orb')}
            </span>
            <span className="text-xs text-zinc-500">
              {t('application.result.verifyOrbHint', 'Visit a Worldcoin Orb once')}
            </span>
          </button>

          <button
            onClick={() => {
              onClose()
              navigate('/profile')
            }}
            className="flex flex-col items-center gap-2 p-4 border border-zinc-200 rounded-xl hover:bg-zinc-50 transition-colors"
          >
            {/* Palm icon — same path as VeryAiBadge */}
            <svg
              className="w-8 h-8 text-zinc-900"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M10.05 4.575a1.575 1.575 0 1 0-3.15 0v3m3.15-3v-1.5a1.575 1.575 0 0 1 3.15 0v1.5m-3.15 0 .075 5.925m3.075.75V4.575m0 0a1.575 1.575 0 0 1 3.15 0V15M6.9 7.575a1.575 1.575 0 1 0-3.15 0v8.175a6.75 6.75 0 0 0 6.75 6.75h2.018a5.25 5.25 0 0 0 3.712-1.538l1.732-1.732a5.25 5.25 0 0 0 1.538-3.712l.003-2.024a.668.668 0 0 1 .198-.471 1.575 1.575 0 1 0-2.228-2.228 3.818 3.818 0 0 0-1.12 2.687M6.9 7.575V12m6.27 4.318A4.49 4.49 0 0 1 16.35 15" />
            </svg>
            <span className="text-sm font-semibold text-zinc-900">
              {t('application.result.verifyPalmCta', 'Verify with palm')}
            </span>
            <span className="text-xs text-zinc-500">
              {t('application.result.verifyPalmHint', 'VeryAI palm-print biometric')}
            </span>
          </button>
        </div>

        <button
          onClick={onClose}
          className="w-full py-2.5 text-sm font-medium text-zinc-700 hover:text-zinc-900 border border-zinc-300 rounded-xl transition-colors"
        >
          {t('common.cancel', 'Cancel')}
        </button>
      </div>
    )
  }

  if (state === 'already_applied') {
    return (
      <div role="status" className="flex flex-col items-center text-center py-6 px-4 space-y-4">
        {/* Info icon — neutral zinc */}
        <div className="w-16 h-16 bg-zinc-100 rounded-full flex items-center justify-center">
          <svg aria-hidden="true" className="w-8 h-8 text-zinc-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        <h3 className="text-lg font-bold text-zinc-900">
          {t('application.result.alreadyAppliedTitle', 'Already applied')}
        </h3>
        <p className="text-sm text-zinc-600 max-w-xs">
          {t(
            'application.result.alreadyAppliedMessage',
            'You have already applied to this task. The agent is reviewing applications and will assign a worker soon.'
          )}
        </p>

        {/* CTA */}
        <div className="flex gap-3 w-full pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 text-sm font-medium text-zinc-700 hover:text-zinc-900 border border-zinc-300 rounded-xl transition-colors"
          >
            {t('common.close', 'Close')}
          </button>
          <button
            onClick={() => {
              onClose()
              navigate('/tasks', { state: { tab: 'mine' } })
            }}
            className="flex-1 py-2.5 bg-zinc-900 text-white text-sm font-semibold rounded-xl hover:bg-zinc-800 transition-colors"
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
      {/* Error icon — semantic red */}
      <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center">
        <svg aria-hidden="true" className="w-8 h-8 text-red-700" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
      </div>

      <h3 className="text-lg font-bold text-zinc-900">
        {t('application.result.errorTitle', 'Something went wrong')}
      </h3>
      <p className="text-sm text-zinc-600 max-w-xs">
        {errorMessage || t('application.result.errorMessage', 'Could not submit your application. Please try again.')}
      </p>

      {/* CTA */}
      <div className="flex gap-3 w-full pt-2">
        <button
          onClick={onClose}
          className="flex-1 py-2.5 text-sm font-medium text-zinc-700 hover:text-zinc-900 border border-zinc-300 rounded-xl transition-colors"
        >
          {t('common.close', 'Close')}
        </button>
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex-1 py-2.5 bg-zinc-900 text-white text-sm font-semibold rounded-xl hover:bg-zinc-800 transition-colors"
          >
            {t('common.retry', 'Retry')}
          </button>
        )}
      </div>
    </div>
  )
}
