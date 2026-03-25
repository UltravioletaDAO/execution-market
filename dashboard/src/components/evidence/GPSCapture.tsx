/**
 * GPSCapture Component
 *
 * Location verification component that gets current position via Geolocation API.
 * Shows accuracy indicator, mini map preview, and handles permission states.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'

export interface GPSPosition {
  latitude: number
  longitude: number
  accuracy: number
  altitude?: number
  altitudeAccuracy?: number
  heading?: number
  speed?: number
  timestamp: number
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
  timeout = 15000,
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
          timeout: 20000,
          maximumAge: 60000,
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

  // Get current position
  const getCurrentPosition = useCallback(() => {
    if (!isSupported) {
      setError(t('gps.notSupported', 'Geolocalizacion no soportada'))
      return
    }

    retryCountRef.current = 0
    setIsLoading(true)
    setError(null)

    navigator.geolocation.getCurrentPosition(
      handleSuccess,
      handleError,
      {
        enableHighAccuracy: highAccuracy,
        timeout,
        maximumAge: maxAge,
      }
    )
  }, [isSupported, handleSuccess, handleError, highAccuracy, timeout, maxAge, t])

  // Watch position mode
  useEffect(() => {
    if (!watchMode || !isSupported) return

    setIsLoading(true)

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

  // Generate static map URL (using OpenStreetMap static image proxy)
  const getMapUrl = useCallback((lat: number, lng: number, zoom = 15): string => {
    // Using a public static map service
    return `https://static-maps.yandex.ru/v1?ll=${lng},${lat}&z=${zoom}&size=300,150&l=map&pt=${lng},${lat},pm2rdm`
  }, [])

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
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {position.latitude.toFixed(4)}, {position.longitude.toFixed(4)}
            </span>
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
        {/* Map preview */}
        {showMap && position && (
          <div className="relative h-32 bg-gray-100 dark:bg-gray-800">
            <img
              src={getMapUrl(position.latitude, position.longitude)}
              alt={t('gps.mapAlt', 'Mapa de ubicacion')}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Hide image on error, show fallback
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
            {/* Fallback if map fails to load */}
            <div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800">
              <div className="text-center">
                <svg className="w-8 h-8 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
                <p className="text-xs text-gray-500 mt-1">
                  {position.latitude.toFixed(5)}, {position.longitude.toFixed(5)}
                </p>
              </div>
            </div>
            {/* Pin marker */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-full">
              <div className="relative">
                <svg className="w-8 h-8 text-red-600 drop-shadow-lg" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
                </svg>
              </div>
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
                <p className="text-sm font-mono text-gray-700 dark:text-gray-300">
                  {position.latitude.toFixed(6)}, {position.longitude.toFixed(6)}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  {/* Accuracy indicator */}
                  <div className={`flex items-center gap-1 text-xs ${getAccuracyQuality(position.accuracy).color}`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${getAccuracyQuality(position.accuracy).bgColor}`} />
                    <span>{t('gps.accuracy', 'Precision')}: {position.accuracy.toFixed(0)}m</span>
                    <span className="font-medium">({getAccuracyQuality(position.accuracy).label})</span>
                  </div>
                </div>
                {/* Altitude if available */}
                {position.altitude !== undefined && (
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
                  <p className="text-xs mt-1 text-gray-500 dark:text-gray-400">
                    {t('gps.enableInSettings', 'Habilita el acceso a ubicacion en la configuracion del navegador')}
                  </p>
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
