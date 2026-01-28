/**
 * EvidenceVerification Component
 *
 * Displays verification badges for evidence items.
 * Shows GPS verified, timestamp verified, photo integrity, and AI detection status.
 */

import { useTranslation } from 'react-i18next'
import type { GPSPosition } from './GPSCapture'

export interface VerificationResult {
  verified: boolean
  confidence?: number
  message?: string
  timestamp?: Date
}

export interface EvidenceVerificationData {
  gps?: {
    verified: boolean
    position?: GPSPosition
    matchesTaskLocation?: boolean
    distance?: number
    maxDistance?: number
  }
  timestamp?: {
    verified: boolean
    capturedAt?: Date
    withinDeadline?: boolean
    suspicious?: boolean
    message?: string
  }
  integrity?: {
    verified: boolean
    hashMatch?: boolean
    metadataIntact?: boolean
    suspiciousEdits?: boolean
    message?: string
  }
  aiDetection?: {
    checked: boolean
    isAiGenerated: boolean
    confidence?: number
    message?: string
  }
}

export interface EvidenceVerificationProps {
  /** Verification data */
  verification: EvidenceVerificationData
  /** Display mode */
  mode?: 'badges' | 'list' | 'detailed'
  /** Compact mode */
  compact?: boolean
  /** Show only failed verifications */
  showOnlyIssues?: boolean
  /** Additional CSS classes */
  className?: string
}

type BadgeStatus = 'verified' | 'warning' | 'failed' | 'pending'

interface Badge {
  id: string
  label: string
  status: BadgeStatus
  icon: React.ReactNode
  message?: string
  detail?: string
}

export function EvidenceVerification({
  verification,
  mode = 'badges',
  compact = false,
  showOnlyIssues = false,
  className = '',
}: EvidenceVerificationProps) {
  const { t } = useTranslation()

  // Build badges array
  const getBadges = (): Badge[] => {
    const badges: Badge[] = []

    // GPS verification badge
    if (verification.gps) {
      const { gps } = verification
      let status: BadgeStatus = 'pending'
      let message = ''
      let detail = ''

      if (gps.verified) {
        if (gps.matchesTaskLocation !== false) {
          status = 'verified'
          message = t('verification.gps.verified', 'Ubicacion verificada')
          if (gps.distance !== undefined && gps.maxDistance) {
            detail = t('verification.gps.withinRange', 'A {{distance}}m del objetivo (max: {{max}}m)', {
              distance: gps.distance.toFixed(0),
              max: gps.maxDistance,
            })
          }
        } else {
          status = 'warning'
          message = t('verification.gps.outsideRange', 'Fuera del rango permitido')
          if (gps.distance !== undefined && gps.maxDistance) {
            detail = t('verification.gps.distanceExceeded', '{{distance}}m de {{max}}m permitidos', {
              distance: gps.distance.toFixed(0),
              max: gps.maxDistance,
            })
          }
        }
      } else {
        status = 'failed'
        message = t('verification.gps.missing', 'Sin datos GPS')
      }

      badges.push({
        id: 'gps',
        label: t('verification.gps.label', 'GPS'),
        status,
        message,
        detail,
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
        ),
      })
    }

    // Timestamp verification badge
    if (verification.timestamp) {
      const { timestamp } = verification
      let status: BadgeStatus = 'pending'
      let message = ''
      let detail = ''

      if (timestamp.verified) {
        if (timestamp.withinDeadline !== false && !timestamp.suspicious) {
          status = 'verified'
          message = t('verification.timestamp.verified', 'Marca de tiempo valida')
          if (timestamp.capturedAt) {
            detail = timestamp.capturedAt.toLocaleString('es', {
              dateStyle: 'short',
              timeStyle: 'short',
            })
          }
        } else if (timestamp.suspicious) {
          status = 'warning'
          message = timestamp.message || t('verification.timestamp.suspicious', 'Marca de tiempo sospechosa')
        } else {
          status = 'warning'
          message = t('verification.timestamp.outsideDeadline', 'Fuera del plazo')
        }
      } else {
        status = 'failed'
        message = timestamp.message || t('verification.timestamp.invalid', 'Marca de tiempo invalida')
      }

      badges.push({
        id: 'timestamp',
        label: t('verification.timestamp.label', 'Tiempo'),
        status,
        message,
        detail,
        icon: (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ),
      })
    }

    // Photo integrity badge
    if (verification.integrity) {
      const { integrity } = verification
      let status: BadgeStatus = 'pending'
      let message = ''

      if (integrity.verified) {
        if (!integrity.suspiciousEdits) {
          status = 'verified'
          message = t('verification.integrity.verified', 'Imagen autentica')
        } else {
          status = 'warning'
          message = integrity.message || t('verification.integrity.modified', 'Posibles modificaciones detectadas')
        }
      } else {
        status = 'failed'
        message = integrity.message || t('verification.integrity.failed', 'No se pudo verificar integridad')
      }

      badges.push({
        id: 'integrity',
        label: t('verification.integrity.label', 'Integridad'),
        status,
        message,
        icon: (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        ),
      })
    }

    // AI detection badge
    if (verification.aiDetection) {
      const { aiDetection } = verification
      let status: BadgeStatus = 'pending'
      let message = ''
      let detail = ''

      if (aiDetection.checked) {
        if (!aiDetection.isAiGenerated) {
          status = 'verified'
          message = t('verification.ai.authentic', 'No es generada por IA')
          if (aiDetection.confidence) {
            detail = t('verification.ai.confidence', '{{confidence}}% confianza', {
              confidence: (aiDetection.confidence * 100).toFixed(0),
            })
          }
        } else {
          status = 'failed'
          message = aiDetection.message || t('verification.ai.detected', 'Posible imagen generada por IA')
          if (aiDetection.confidence) {
            detail = t('verification.ai.probability', '{{probability}}% probabilidad IA', {
              probability: (aiDetection.confidence * 100).toFixed(0),
            })
          }
        }
      } else {
        status = 'pending'
        message = t('verification.ai.pending', 'Verificacion IA pendiente')
      }

      badges.push({
        id: 'ai',
        label: t('verification.ai.label', 'IA'),
        status,
        message,
        detail,
        icon: (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        ),
      })
    }

    // Filter if showOnlyIssues is true
    if (showOnlyIssues) {
      return badges.filter(b => b.status !== 'verified')
    }

    return badges
  }

  // Get status colors
  const getStatusColors = (status: BadgeStatus): {
    bg: string
    text: string
    border: string
    icon: string
  } => {
    switch (status) {
      case 'verified':
        return {
          bg: 'bg-emerald-50 dark:bg-emerald-900/20',
          text: 'text-emerald-700 dark:text-emerald-400',
          border: 'border-emerald-200 dark:border-emerald-800',
          icon: 'text-emerald-600 dark:text-emerald-400',
        }
      case 'warning':
        return {
          bg: 'bg-amber-50 dark:bg-amber-900/20',
          text: 'text-amber-700 dark:text-amber-400',
          border: 'border-amber-200 dark:border-amber-800',
          icon: 'text-amber-600 dark:text-amber-400',
        }
      case 'failed':
        return {
          bg: 'bg-red-50 dark:bg-red-900/20',
          text: 'text-red-700 dark:text-red-400',
          border: 'border-red-200 dark:border-red-800',
          icon: 'text-red-600 dark:text-red-400',
        }
      case 'pending':
      default:
        return {
          bg: 'bg-gray-50 dark:bg-gray-800',
          text: 'text-gray-600 dark:text-gray-400',
          border: 'border-gray-200 dark:border-gray-700',
          icon: 'text-gray-500 dark:text-gray-400',
        }
    }
  }

  // Get status indicator icon
  const StatusIndicator = ({ status }: { status: BadgeStatus }) => {
    switch (status) {
      case 'verified':
        return (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )
      case 'warning':
        return (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        )
      case 'failed':
        return (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        )
      case 'pending':
      default:
        return (
          <svg className="w-3 h-3 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        )
    }
  }

  const badges = getBadges()

  // No badges to show
  if (badges.length === 0) {
    return null
  }

  // Badges mode (inline pills)
  if (mode === 'badges') {
    return (
      <div className={`flex flex-wrap gap-1.5 ${className}`}>
        {badges.map((badge) => {
          const colors = getStatusColors(badge.status)
          return (
            <div
              key={badge.id}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text} ${compact ? '' : 'border ' + colors.border}`}
              title={badge.message + (badge.detail ? `\n${badge.detail}` : '')}
            >
              <span className={colors.icon}>{badge.icon}</span>
              {!compact && <span>{badge.label}</span>}
              <StatusIndicator status={badge.status} />
            </div>
          )
        })}
      </div>
    )
  }

  // List mode (vertical stack)
  if (mode === 'list') {
    return (
      <div className={`space-y-2 ${className}`}>
        {badges.map((badge) => {
          const colors = getStatusColors(badge.status)
          return (
            <div
              key={badge.id}
              className={`flex items-center justify-between p-2 rounded-lg ${colors.bg} ${colors.border} border`}
            >
              <div className="flex items-center gap-2">
                <span className={colors.icon}>{badge.icon}</span>
                <span className={`text-sm font-medium ${colors.text}`}>{badge.label}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs ${colors.text}`}>{badge.message}</span>
                <StatusIndicator status={badge.status} />
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  // Detailed mode (full info)
  return (
    <div className={`space-y-3 ${className}`}>
      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('verification.title', 'Verificacion de Evidencia')}
      </h4>
      <div className="space-y-2">
        {badges.map((badge) => {
          const colors = getStatusColors(badge.status)
          return (
            <div
              key={badge.id}
              className={`p-3 rounded-lg ${colors.bg} ${colors.border} border`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${badge.status === 'verified' ? 'bg-emerald-100 dark:bg-emerald-900/30' : badge.status === 'warning' ? 'bg-amber-100 dark:bg-amber-900/30' : badge.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30' : 'bg-gray-100 dark:bg-gray-800'}`}>
                  <span className={colors.icon}>{badge.icon}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-medium ${colors.text}`}>
                      {badge.label}
                    </span>
                    <div className={`flex items-center gap-1 ${colors.text}`}>
                      <StatusIndicator status={badge.status} />
                      <span className="text-xs capitalize">
                        {badge.status === 'verified' ? t('verification.status.verified', 'Verificado') :
                         badge.status === 'warning' ? t('verification.status.warning', 'Advertencia') :
                         badge.status === 'failed' ? t('verification.status.failed', 'Fallido') :
                         t('verification.status.pending', 'Pendiente')}
                      </span>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    {badge.message}
                  </p>
                  {badge.detail && (
                    <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-500">
                      {badge.detail}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Summary */}
      {!showOnlyIssues && (
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">
              {t('verification.summary', 'Resumen')}
            </span>
            <div className="flex items-center gap-3">
              <span className="text-emerald-600 dark:text-emerald-400">
                {badges.filter(b => b.status === 'verified').length} {t('verification.passed', 'OK')}
              </span>
              {badges.filter(b => b.status === 'warning').length > 0 && (
                <span className="text-amber-600 dark:text-amber-400">
                  {badges.filter(b => b.status === 'warning').length} {t('verification.warnings', 'advertencias')}
                </span>
              )}
              {badges.filter(b => b.status === 'failed').length > 0 && (
                <span className="text-red-600 dark:text-red-400">
                  {badges.filter(b => b.status === 'failed').length} {t('verification.failures', 'fallos')}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EvidenceVerification
