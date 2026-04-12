/**
 * GPSCapture Component
 *
 * Location verification component that gets current position via Geolocation API.
 * Shows accuracy indicator, mini map preview, and handles permission states.
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { detectGpsPlatform, getPermissionHintKey } from '../../utils/gpsPermissionHint'

export interface GPSPosition {
  latitude: number
  longitude: number
  accuracy: number
  altitude?: number | null
  altitudeAccuracy?: number
  heading?: number
  speed?: number
  timestamp: number
  /** How this position was obtained: 'exif', 'browser', 'browser_fallback', or 'watch'. */
  source?: string
}

export interface GPSCaptureProps {
  /** Callback when position is obtained */
  onPositionChange: (position: GPSPosition | null) => void
  /** Callback on error */
  onError?: (error: string) => void
  /** Enable high accuracy mode (uses more battery) */
  highAccuracy?: boolean
  /** Maximum age of cached position in ms */
  maxAge?: number
  /** Timeout for position request in ms */
  timeout?: number
  /** Watch position continuously */
  watchMode?: boolean
  /** Minimum accuracy required in meters */
  minAccuracy?: number
  /** Show mini map preview */
  showMap?: boolean
  /** Compact mode (less visual elements) */
  compact?: boolean
  /** Additional CSS classes */
  className?: string
}

type PermissionStatus = 'prompt' | 'granted' | 'denied' | 'unknown'

export function GPSCapture({
  onPositionChange,
  onError,
  highAccuracy = true,
  maxAge = 30000,
  timeout = 30000,
  watchMode = false,
  minAccuracy,
  showMap = true,
  compact = false,
  className = '',
}: GPSCaptureProps) {
  const { t } = useTranslation()
  const watchIdRef = useRef<number | null>(null)
  const retryCountRef = useRef(0)
  const MAX_RETRIES = 2

  const [position, setPosition] = useState<GPSPosition | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [permissionStatus, setPermissionStatus] = useState<PermissionStatus>('unknown')
  const [isSupported] = useState(() => 'geolocation' in navigator)
  const [showCoords, setShowCoords] = useState(false)

  // Detect platform once for permission-denied hints
  const platformHintKey = useMemo(() => getPermissionHintKey(detectGpsPlatform()), [])

  // Check permission status on mount
  useEffect(() => {
    if (!isSupported) return

    navigator.permissions
      ?.query({ name: 'geolocation' })
      .then((result) => {
        setPermissionStatus(result.state)
        result.onchange = () => setPermissionStatus(result.state)
      })
      .catch(() => {
        // Permissions API not supported - state unknown
      })
  }, [isSupported])

  // Get accuracy quality label
  const getAccuracyQuality = useCallback((meters: number): {
    label: string
    color: string
    bgColor: string
    quality: 'excellent' | 'good' | 'fair' | 'poor'
  } => {
    if (meters <= 10) {
      return { label: t('gps.excellent', 'Excelente'), color: 'text-emerald-600', bgColor: 'bg-emerald-500', quality: 'excellent' }
    } else if (meters <= 30) {
      return { label: t('gps.good', 'Buena'), color: 'text-blue-600', bgColor: 'bg-blue-500', quality: 'good' }
    } else if (meters <= 100) {
      return { label: t('gps.fair', 'Aceptable'), color: 'text-amber-600', bgColor: 'bg-amber-500', quality: 'fair' }
    } else {
      return { label: t('gps.poor', 'Baja'), color: 'text-red-600', bgColor: 'bg-red-500', quality: 'poor' }
    }
  }, [t])

  // Handle position success
  const handleSuccess = useCallback((pos: GeolocationPosition) => {
    const newPosition: GPSPosition = {
      latitude: pos.coords.latitude,
      longitude: pos.coords.longitude,
      accuracy: pos.coords.accuracy,
      altitude: pos.coords.altitude ?? undefined,
      altitudeAccuracy: pos.coords.altitudeAccuracy ?? undefined,
      heading: pos.coords.heading ?? undefined,
      speed: pos.coords.speed ?? undefined,
      timestamp: pos.timestamp,
    }

    // Check minimum accuracy requirement
    if (minAccuracy && pos.coords.accuracy > minAccuracy) {
      setError(t('gps.lowAccuracy', 'Precision insuficiente. Muevete a un area abierta.'))
      // Still update position but don't clear error
    } else {
      setError(null)
    }

    setPosition(newPosition)
    setIsLoading(false)
    onPositionChange(newPosition)
  }, [minAccuracy, onPositionChange, t])

  // Handle position error — retries automatically on timeout/unavailable
  const handleError = useCallback((err: GeolocationPositionError) => {
    let errorMessage: string

    switch (err.code) {
      case err.PERMISSION_DENIED:
        errorMessage = t('gps.permissionDenied', 'Permiso de ubicacion denegado')
        setPermissionStatus('denied')
        break
      case err.POSITION_UNAVAILABLE:
        errorMessage = t('gps.unavailable', 'Ubicacion no disponible')
        break
      case err.TIMEOUT:
        errorMessage = t('gps.timeout', 'Tiempo agotado. Intenta de nuevo.')
        break
      default:
        errorMessage = t('gps.error', 'Error obteniendo ubicacion')
    }

    // Auto-retry on timeout or position unavailable (not on permission denied)
    if (err.code !== err.PERMISSION_DENIED && retryCountRef.current < MAX_RETRIES) {
      retryCountRef.current += 1
      // Retry with relaxed settings: lower accuracy, longer timeout, allow cached
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          retryCountRef.current = 0
          handleSuccess(pos)
        },
        (retryErr) => {
          // Final failure after retries
          const msg = retryErr.code === retryErr.PERMISSION_DENIED
            ? t('gps.permissionDenied', 'Permiso de ubicacion denegado')
            : retryErr.code === retryErr.TIMEOUT
            ? t('gps.timeout', 'Tiempo agotado. Intenta de nuevo.')
            : t('gps.unavailable', 'Ubicacion no disponible')
          setError(msg)
          setIsLoading(false)
          if (retryErr.code === retryErr.PERMISSION_DENIED) setPermissionStatus('denied')
          onError?.(msg)
          onPositionChange(null)
        },
        {
          enableHighAccuracy: false,
          timeout: 30000,
          maximumAge: 120000,
        }
      )
      return
    }

    retryCountRef.current = 0
    setError(errorMessage)
    setIsLoading(false)
    onError?.(errorMessage)
    onPositionChange(null)
  }, [onError, onPositionChange, t, handleSuccess])

  // Get current position — quick low-accuracy fix first, then upgrade
  const getCurrentPosition = useCallback(() => {
    if (!isSupported) {
      setError(t('gps.notSupported', 'Geolocalizacion no soportada'))
      return
    }

    retryCountRef.current = 0
    setIsLoading(true)
    setError(null)

    if (highAccuracy) {
      // Quick low-accuracy fix first (IP/WiFi ~2s), then upgrade to high accuracy.
      // Works on all platforms: mobile gets GPS upgrade, desktop gets instant IP fix.
      navigator.geolocation.getCurrentPosition(
        (quickPos) => {
          handleSuccess(quickPos)
          navigator.geolocation.getCurrentPosition(
            handleSuccess,
            () => { /* high-accuracy upgrade failed — keep the quick fix */ },
            { enableHighAccuracy: true, timeout, maximumAge: maxAge }
          )
        },
        handleError,
        { enableHighAccuracy: false, timeout: 5000, maximumAge: 60000 }
      )
    } else {
      navigator.geolocation.getCurrentPosition(
        handleSuccess,
        handleError,
        { enableHighAccuracy: false, timeout, maximumAge: maxAge }
      )
    }
  }, [isSupported, handleSuccess, handleError, highAccuracy, timeout, maxAge, t])

  // Watch position mode
  useEffect(() => {
    if (!watchMode || !isSupported) return

    setIsLoading(true)

    // Quick low-accuracy fix first (IP/WiFi) — shows position in <2s on desktop
    // instead of waiting 30s for high-accuracy GPS that doesn't exist on PCs.
    navigator.geolocation.getCurrentPosition(
      handleSuccess,
      () => { /* quick fix failed — watchPosition below will handle it */ },
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 60000 }
    )

    // Then watch with high accuracy for continuous updates (upgrades the quick fix)
    watchIdRef.current = navigator.geolocation.watchPosition(
      handleSuccess,
      handleError,
      {
        enableHighAccuracy: highAccuracy,
        timeout,
        maximumAge: Math.min(maxAge, 10000), // More frequent updates in watch mode
      }
    )

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current)
        watchIdRef.current = null
      }
    }
  }, [watchMode, isSupported, handleSuccess, handleError, highAccuracy, timeout, maxAge])

  // Get position on mount. On iOS Safari, permissions.query('geolocation')
  // is not supported — permissionStatus stays 'unknown'. We auto-request
  // for 'granted' and 'unknown' (iOS where the site-level setting is "Allow").
  // Only skip auto-request for 'prompt' (desktop where we know it needs gesture).
  useEffect(() => {
    if (!watchMode && (permissionStatus === 'granted' || permissionStatus === 'unknown')) {
      getCurrentPosition()
    }
  }, [permissionStatus]) // eslint-disable-line react-hooks/exhaustive-deps

  // Generate map preview text (privacy-preserving — no third-party map service)
  // Previously used Yandex static maps which leaked exact GPS coordinates to a
  // third-party service. Replaced with text-only display per FE-011 security audit.
  // Coordinates rounded to ~1km precision for "location verified" without leaking
  // exact position. Phase 3 may add self-hosted tile rendering if visual maps needed.

  // Render not supported state
  if (!isSupported) {
    return (
      <div className={`p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg ${className}`}>
        <div className="flex items-center gap-3 text-red-700 dark:text-red-400">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
          <span className="text-sm">{t('gps.notSupported', 'Geolocalizacion no soportada en este dispositivo')}</span>
        </div>
      </div>
    )
  }

  // Compact mode rendering
  if (compact) {
    return (
      <div className={`flex items-center gap-3 ${className}`}>
        {/* Status indicator */}
        {isLoading ? (
          <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-xs">{t('gps.loading', 'Obteniendo...')}</span>
          </div>
        ) : position ? (
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${getAccuracyQuality(position.accuracy).bgColor}`} />
            {showCoords ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="text-xs text-gray-600 dark:text-gray-400 font-mono">
                  {position.latitude.toFixed(4)}, {position.longitude.toFixed(4)}
                </span>
                <button type="button" onClick={() => setShowCoords(false)} className="text-xs text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-0.5">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                  {t('gps.hideCoordinates', 'Hide coordinates')}
                </button>
              </span>
            ) : (
              <button type="button" onClick={() => setShowCoords(true)} className="text-xs text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-0.5">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                {t('gps.showCoordinates', 'Show coordinates')}
              </button>
            )}
            <span className={`text-xs ${getAccuracyQuality(position.accuracy).color}`}>
              (+/-{position.accuracy.toFixed(0)}m)
            </span>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-xs">{error}</span>
          </div>
        ) : null}

        {/* Refresh button */}
        {!isLoading && (
          <button
            type="button"
            onClick={getCurrentPosition}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label={t('gps.refresh', 'Actualizar ubicacion')}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}
      </div>
    )
  }

  // Full mode rendering
  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header with status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('gps.title', 'Ubicacion GPS')}
          </span>
        </div>

        {/* Permission badge */}
        {permissionStatus === 'denied' && (
          <span className="text-xs px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-full">
            {t('gps.permissionDeniedShort', 'Permiso denegado')}
          </span>
        )}
      </div>

      {/* Main content */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Location confirmation — privacy-preserving text display (FE-011)
            Previously rendered a Yandex static map image which leaked exact GPS
            coordinates to a third-party service. Replaced with rounded text coords
            (~1km precision) to confirm location capture without privacy leakage. */}
        {showMap && position && showCoords && (
          <div className="flex items-center justify-center h-20 bg-gray-100 dark:bg-gray-800">
            <div className="text-center">
              <svg className="w-6 h-6 mx-auto text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t('gps.locationCaptured', 'Location captured')} ({position.latitude.toFixed(2)}, {position.longitude.toFixed(2)})
              </p>
            </div>
          </div>
        )}

        {/* Prompt state — user must tap to activate GPS (desktop browsers) */}
        {!isLoading && !position && !error && permissionStatus === 'prompt' && (
          <div className="p-6 text-center">
            <button
              type="button"
              onClick={getCurrentPosition}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              </svg>
              {t('gps.activate', 'Activar GPS')}
            </button>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
              {t('gps.tapToActivate', 'Toca para permitir el acceso a tu ubicacion')}
            </p>
          </div>
        )}

        {/* Loading state */}
        {isLoading && !position && (
          <div className="p-6 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 mb-3">
              <svg className="w-6 h-6 text-blue-600 dark:text-blue-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              </svg>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('gps.acquiring', 'Obteniendo ubicacion GPS...')}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              {t('gps.waitMessage', 'Esto puede tomar unos segundos')}
            </p>
          </div>
        )}

        {/* Position info */}
        {position && (
          <div className="p-3 bg-white dark:bg-gray-800">
            <div className="flex items-center justify-between">
              <div>
                {showCoords ? (
                  <div>
                    <p className="text-sm font-mono text-gray-700 dark:text-gray-300">
                      {position.latitude.toFixed(6)}, {position.longitude.toFixed(6)}
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowCoords(false)}
                      className="flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:underline mt-1"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                      {t('gps.hideCoordinates', 'Hide coordinates')}
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowCoords(true)}
                    className="flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    {t('gps.showCoordinates', 'Show coordinates')}
                  </button>
                )}
                <div className="flex items-center gap-2 mt-1">
                  {/* Accuracy indicator */}
                  <div className={`flex items-center gap-1 text-xs ${getAccuracyQuality(position.accuracy).color}`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${getAccuracyQuality(position.accuracy).bgColor}`} />
                    <span>{t('gps.accuracy', 'Precision')}: {position.accuracy.toFixed(0)}m</span>
                    <span className="font-medium">({getAccuracyQuality(position.accuracy).label})</span>
                  </div>
                </div>
                {/* Altitude if available — only when coords visible */}
                {showCoords && position.altitude != null && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {t('gps.altitude', 'Altitud')}: {position.altitude.toFixed(0)}m
                    {position.altitudeAccuracy && ` (+/-${position.altitudeAccuracy.toFixed(0)}m)`}
                  </p>
                )}
              </div>

              {/* Refresh button */}
              <button
                type="button"
                onClick={getCurrentPosition}
                disabled={isLoading}
                className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                aria-label={t('gps.refresh', 'Actualizar ubicacion')}
              >
                <svg className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>

            {/* Accuracy visualization bar */}
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                <span>{t('gps.signalStrength', 'Senal GPS')}</span>
                <span>{Math.min(100, Math.max(0, 100 - position.accuracy)).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${getAccuracyQuality(position.accuracy).bgColor}`}
                  style={{ width: `${Math.min(100, Math.max(0, 100 - position.accuracy))}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && !position && (
          <div className="p-4">
            <div className="flex items-start gap-3 text-red-700 dark:text-red-400">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div className="flex-1">
                <p className="text-sm font-medium">{error}</p>
                {permissionStatus === 'denied' && (
                  <div className="text-xs mt-2 text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-md p-2 space-y-1">
                    <p className="font-medium">{t('gps.enableInSettings', 'Habilita el acceso a ubicacion en la configuracion del navegador')}:</p>
                    <p className="text-amber-700 dark:text-amber-400">{t(platformHintKey)}</p>
                  </div>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={getCurrentPosition}
              className="mt-3 w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {t('gps.tryAgain', 'Intentar de nuevo')}
            </button>
          </div>
        )}
      </div>

      {/* Min accuracy warning */}
      {minAccuracy && position && position.accuracy > minAccuracy && (
        <div className="p-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <p className="text-xs text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>
              {t('gps.minAccuracyWarning', 'Se requiere precision de {{min}}m o mejor. Actual: {{current}}m', {
                min: minAccuracy,
                current: position.accuracy.toFixed(0),
              })}
            </span>
          </p>
        </div>
      )}

      {/* Watch mode indicator */}
      {watchMode && (
        <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          {t('gps.tracking', 'Rastreando ubicacion en tiempo real')}
        </p>
      )}
    </div>
  )
}

export default GPSCapture
