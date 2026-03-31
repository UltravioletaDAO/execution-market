/**
 * EvidencePreview Component
 *
 * Preview component for captured evidence items.
 * Shows thumbnail, GPS coordinates, timestamp, and upload status.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { GPSPosition } from './GPSCapture'

export type UploadStatus = 'pending' | 'uploading' | 'success' | 'error'

export interface EvidenceItem {
  id: string
  type: 'photo' | 'photo_geo' | 'video' | 'document'
  file?: File
  dataUrl?: string
  url?: string
  timestamp: Date
  gps?: GPSPosition
  uploadStatus: UploadStatus
  uploadProgress?: number
  error?: string
  metadata?: {
    width?: number
    height?: number
    size?: number
    mimeType?: string
    deviceModel?: string
    captureSource?: 'camera' | 'gallery' | 'unknown'
  }
}

export interface EvidencePreviewProps {
  /** Evidence item to display */
  evidence: EvidenceItem
  /** Callback to delete/remove the evidence */
  onDelete?: (id: string) => void
  /** Callback to retake the evidence */
  onRetake?: (id: string) => void
  /** Callback to retry upload */
  onRetry?: (id: string) => void
  /** Show detailed metadata */
  showDetails?: boolean
  /** Compact mode */
  compact?: boolean
  /** Disable actions */
  disabled?: boolean
  /** Additional CSS classes */
  className?: string
}

export function EvidencePreview({
  evidence,
  onDelete,
  onRetake,
  onRetry,
  showDetails = false,
  compact = false,
  disabled = false,
  className = '',
}: EvidencePreviewProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(showDetails)
  const [imageError, setImageError] = useState(false)

  // Get preview source
  const getPreviewSrc = (): string => {
    if (evidence.dataUrl) return evidence.dataUrl
    if (evidence.url) return evidence.url
    if (evidence.file) return URL.createObjectURL(evidence.file)
    return ''
  }

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  // Get status color classes
  const getStatusColor = (): { bg: string; text: string; border: string } => {
    switch (evidence.uploadStatus) {
      case 'pending':
        return { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-600 dark:text-gray-400', border: 'border-gray-300 dark:border-gray-600' }
      case 'uploading':
        return { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-600 dark:text-blue-400', border: 'border-blue-300 dark:border-blue-700' }
      case 'success':
        return { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-600 dark:text-emerald-400', border: 'border-emerald-300 dark:border-emerald-700' }
      case 'error':
        return { bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-600 dark:text-red-400', border: 'border-red-300 dark:border-red-700' }
    }
  }

  // Get status icon
  const StatusIcon = () => {
    switch (evidence.uploadStatus) {
      case 'pending':
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      case 'uploading':
        return (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )
      case 'success':
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )
      case 'error':
        return (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
    }
  }

  // Get status label
  const getStatusLabel = (): string => {
    switch (evidence.uploadStatus) {
      case 'pending':
        return t('evidence.status.pending', 'Pendiente')
      case 'uploading':
        return evidence.uploadProgress !== undefined
          ? `${evidence.uploadProgress}%`
          : t('evidence.status.uploading', 'Subiendo...')
      case 'success':
        return t('evidence.status.uploaded', 'Subido')
      case 'error':
        return t('evidence.status.error', 'Error')
    }
  }

  const statusColors = getStatusColor()

  // Compact mode rendering
  if (compact) {
    return (
      <div className={`flex items-center gap-3 p-2 rounded-lg border ${statusColors.border} ${statusColors.bg} ${className}`}>
        {/* Thumbnail */}
        <div className="relative w-12 h-12 rounded overflow-hidden flex-shrink-0 bg-gray-200 dark:bg-gray-700">
          {!imageError ? (
            <img
              src={getPreviewSrc()}
              alt={t('evidence.thumbnail', 'Miniatura')}
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          )}

          {/* Upload progress overlay */}
          {evidence.uploadStatus === 'uploading' && evidence.uploadProgress !== undefined && (
            <div
              className="absolute inset-0 bg-black/50 flex items-center justify-center"
              style={{
                background: `linear-gradient(to top, rgba(64, 64, 64, 0.5) ${evidence.uploadProgress}%, transparent ${evidence.uploadProgress}%)`,
              }}
            >
              <span className="text-white text-xs font-bold">{evidence.uploadProgress}%</span>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 text-xs ${statusColors.text}`}>
              <StatusIcon />
              <span>{getStatusLabel()}</span>
            </span>
            {evidence.gps && (
              <span className="text-xs text-green-600 dark:text-green-400">GPS</span>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
            {evidence.timestamp.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}
            {evidence.metadata?.size && ` - ${formatFileSize(evidence.metadata.size)}`}
          </p>
        </div>

        {/* Actions */}
        {!disabled && (
          <div className="flex items-center gap-1">
            {evidence.uploadStatus === 'error' && onRetry && (
              <button
                onClick={() => onRetry(evidence.id)}
                className="p-1.5 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded transition-colors"
                aria-label={t('evidence.retry', 'Reintentar')}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            )}
            {evidence.uploadStatus !== 'uploading' && onDelete && (
              <button
                onClick={() => onDelete(evidence.id)}
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
                aria-label={t('evidence.delete', 'Eliminar')}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>
    )
  }

  // Full mode rendering
  return (
    <div className={`rounded-lg border ${statusColors.border} overflow-hidden ${className}`}>
      {/* Image preview */}
      <div className="relative aspect-[4/3] bg-gray-100 dark:bg-gray-800">
        {!imageError ? (
          <img
            src={getPreviewSrc()}
            alt={t('evidence.preview', 'Vista previa')}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-center">
              <svg className="w-12 h-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <p className="mt-2 text-sm text-gray-500">{t('evidence.noPreview', 'Vista previa no disponible')}</p>
            </div>
          </div>
        )}

        {/* Upload progress overlay */}
        {evidence.uploadStatus === 'uploading' && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 relative">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="rgba(255,255,255,0.3)"
                    strokeWidth="8"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke="white"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={`${(evidence.uploadProgress || 0) * 2.83} 283`}
                    className="transition-all duration-300"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-white text-lg font-bold">{evidence.uploadProgress || 0}%</span>
                </div>
              </div>
              <p className="mt-2 text-white text-sm">{t('evidence.uploading', 'Subiendo...')}</p>
            </div>
          </div>
        )}

        {/* Status badge */}
        <div className={`absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 rounded-full ${statusColors.bg} ${statusColors.text} text-xs font-medium`}>
          <StatusIcon />
          <span>{getStatusLabel()}</span>
        </div>

        {/* Verification badges */}
        <div className="absolute bottom-2 left-2 flex flex-wrap gap-1.5">
          {/* GPS badge */}
          {evidence.gps && (
            <div className="flex items-center gap-1 px-2 py-1 bg-green-500/90 text-white text-xs rounded-full">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              <span>GPS</span>
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
          )}

          {/* Timestamp badge */}
          <div className="flex items-center gap-1 px-2 py-1 bg-black/60 text-white text-xs rounded-full">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{evidence.timestamp.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}</span>
          </div>

          {/* Camera source badge */}
          {evidence.metadata?.captureSource === 'camera' && (
            <div className="flex items-center gap-1 px-2 py-1 bg-blue-500/90 text-white text-xs rounded-full">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              </svg>
              <span>{t('evidence.camera', 'Camara')}</span>
            </div>
          )}
        </div>
      </div>

      {/* Details section */}
      <div className={`p-3 ${statusColors.bg}`}>
        {/* Expandable details */}
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between text-left"
        >
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('evidence.details', 'Detalles')}
          </span>
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {expanded && (
          <div className="mt-3 space-y-2 text-xs">
            {/* GPS coordinates — hidden by default for privacy (streaming protection) */}
            {evidence.gps && (
              <GpsCoordToggle gps={evidence.gps} />
            )}

            {/* Timestamp */}
            <div className="flex items-start gap-2">
              <svg className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  {evidence.timestamp.toLocaleDateString('es', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
                <p className="text-gray-500 dark:text-gray-400">
                  {evidence.timestamp.toLocaleTimeString('es', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </p>
              </div>
            </div>

            {/* File info */}
            {evidence.metadata && (
              <div className="flex items-start gap-2">
                <svg className="w-4 h-4 text-gray-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div className="space-y-0.5">
                  {evidence.metadata.size && (
                    <p className="text-gray-700 dark:text-gray-300">
                      {t('evidence.size', 'Tamano')}: {formatFileSize(evidence.metadata.size)}
                    </p>
                  )}
                  {evidence.metadata.width && evidence.metadata.height && (
                    <p className="text-gray-500 dark:text-gray-400">
                      {t('evidence.dimensions', 'Dimensiones')}: {evidence.metadata.width} x {evidence.metadata.height}
                    </p>
                  )}
                  {evidence.metadata.mimeType && (
                    <p className="text-gray-500 dark:text-gray-400">
                      {t('evidence.type', 'Tipo')}: {evidence.metadata.mimeType}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Error message */}
            {evidence.error && (
              <div className="flex items-start gap-2 p-2 bg-red-100 dark:bg-red-900/30 rounded">
                <svg className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p className="text-red-700 dark:text-red-400">{evidence.error}</p>
              </div>
            )}
          </div>
        )}

        {/* Action buttons — only show for pending/error, not after successful upload */}
        {!disabled && (evidence.uploadStatus === 'pending' || evidence.uploadStatus === 'error') && (
          <div className="mt-3 flex gap-2">
            {evidence.uploadStatus === 'error' && onRetry && (
              <button
                onClick={() => onRetry(evidence.id)}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {t('evidence.retry', 'Reintentar')}
              </button>
            )}
            {onRetake && (
              <button
                onClick={() => onRetake(evidence.id)}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                </svg>
                {t('evidence.retake', 'Volver a tomar')}
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(evidence.id)}
                className="flex items-center justify-center px-3 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                aria-label={t('evidence.delete', 'Eliminar')}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/** Small toggle to show/hide GPS coordinates (privacy for streaming) */
function GpsCoordToggle({ gps }: { gps: GPSPosition }) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(false)

  return (
    <div className="flex items-start gap-2">
      <svg className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
      </svg>
      <div>
        {visible ? (
          <div>
            <p className="text-gray-700 dark:text-gray-300 font-mono">
              {gps.latitude.toFixed(6)}, {gps.longitude.toFixed(6)}
            </p>
            <button type="button" onClick={() => setVisible(false)} className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 mt-0.5">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
              {t('gps.hideCoordinates', 'Hide coordinates')}
            </button>
          </div>
        ) : (
          <button type="button" onClick={() => setVisible(true)} className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            {t('gps.showCoordinates', 'Show coordinates')}
          </button>
        )}
        <p className="text-gray-500 dark:text-gray-400">
          {t('evidence.accuracy', 'Precision')}: +/-{gps.accuracy.toFixed(0)}m
        </p>
      </div>
    </div>
  )
}

export default EvidencePreview
