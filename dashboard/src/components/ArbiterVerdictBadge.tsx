/**
 * ArbiterVerdictBadge: Shows the Ring 2 (decentralized arbiter) verdict for a submission.
 *
 * Visual language:
 *   PASS         -> green  -> "Arbiter Approved"
 *   FAIL         -> red    -> "Arbiter Rejected"
 *   INCONCLUSIVE -> yellow -> "Escalated to L2"
 *   SKIPPED      -> gray   -> "Manual Only"
 *   PENDING      -> gray   -> "Awaiting Arbiter"
 *
 * Used in:
 *   - SubmissionReviewModal (agent reviewing submissions)
 *   - TaskDetail (workers checking their own submission verdict)
 */

interface ArbiterVerdictBadgeProps {
  verdict: 'pass' | 'fail' | 'inconclusive' | 'skipped' | null | undefined
  tier?: 'cheap' | 'standard' | 'max' | null
  score?: number | null
  confidence?: number | null
  size?: 'sm' | 'lg'
  showTier?: boolean
}

interface VariantStyles {
  label: string
  bgClass: string
  textClass: string
  borderClass: string
  dotClass: string
}

function getVariant(verdict: string | null | undefined): VariantStyles {
  switch (verdict) {
    case 'pass':
      return {
        label: 'Arbiter Approved',
        bgClass: 'bg-green-50',
        textClass: 'text-green-700',
        borderClass: 'border-green-300',
        dotClass: 'bg-green-500',
      }
    case 'fail':
      return {
        label: 'Arbiter Rejected',
        bgClass: 'bg-red-50',
        textClass: 'text-red-700',
        borderClass: 'border-red-300',
        dotClass: 'bg-red-500',
      }
    case 'inconclusive':
      return {
        label: 'Escalated to L2',
        bgClass: 'bg-yellow-50',
        textClass: 'text-yellow-700',
        borderClass: 'border-yellow-300',
        dotClass: 'bg-yellow-500',
      }
    case 'skipped':
      return {
        label: 'Manual Only',
        bgClass: 'bg-gray-100',
        textClass: 'text-gray-600',
        borderClass: 'border-gray-300',
        dotClass: 'bg-gray-400',
      }
    default:
      return {
        label: 'Awaiting Arbiter',
        bgClass: 'bg-gray-50',
        textClass: 'text-gray-500',
        borderClass: 'border-gray-200',
        dotClass: 'bg-gray-300',
      }
  }
}

export function ArbiterVerdictBadge({
  verdict,
  tier,
  score,
  confidence,
  size = 'sm',
  showTier = true,
}: ArbiterVerdictBadgeProps) {
  const variant = getVariant(verdict)
  const sizeClasses =
    size === 'lg' ? 'text-sm px-3 py-1.5' : 'text-xs px-2 py-1'

  const scorePct =
    typeof score === 'number' ? `${Math.round(score * 100)}%` : null
  const confPct =
    typeof confidence === 'number' ? `${Math.round(confidence * 100)}%` : null

  const tierLabel = tier
    ? {
        cheap: 'T0',
        standard: 'T1',
        max: 'T2',
      }[tier]
    : null

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border font-medium ${variant.bgClass} ${variant.textClass} ${variant.borderClass} ${sizeClasses}`}
      title={
        verdict
          ? `Ring 2 verdict: ${verdict}${
              scorePct ? ` · score ${scorePct}` : ''
            }${confPct ? ` · conf ${confPct}` : ''}${
              tierLabel ? ` · tier ${tierLabel}` : ''
            }`
          : 'Arbiter has not yet evaluated this submission'
      }
    >
      <span
        className={`h-2 w-2 rounded-full ${variant.dotClass}`}
        aria-hidden="true"
      />
      <span>{variant.label}</span>
      {showTier && tierLabel ? (
        <span className="rounded bg-white/60 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
          {tierLabel}
        </span>
      ) : null}
      {scorePct ? (
        <span className="text-[11px] opacity-80">{scorePct}</span>
      ) : null}
    </div>
  )
}

/**
 * Compact variant: shows only a colored dot + score, useful in dense tables.
 */
export function ArbiterVerdictDot({
  verdict,
  score,
}: {
  verdict: ArbiterVerdictBadgeProps['verdict']
  score?: number | null
}) {
  const variant = getVariant(verdict)
  const scorePct =
    typeof score === 'number' ? `${Math.round(score * 100)}%` : '—'
  return (
    <div
      className="inline-flex items-center gap-1 text-xs"
      title={`Arbiter: ${verdict ?? 'pending'}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${variant.dotClass}`}
        aria-hidden="true"
      />
      <span className="font-mono">{scorePct}</span>
    </div>
  )
}
