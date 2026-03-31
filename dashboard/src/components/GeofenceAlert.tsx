/**
 * GeofenceAlert Component
 *
 * Uses browser Geolocation API to check if the user is within the task's
 * location radius. Shows a warning if the user is too far from the task location.
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { detectGpsPlatform, getPermissionHintKey } from '../utils/gpsPermissionHint'

export interface GeofenceAlertProps {
  /** Task location (lat/lng) */
  taskLocation: { lat: number; lng: number }
  /** Allowed radius in kilometers (default: 0.5 = 500m) */
  radiusKm?: number
  /** Callback when geofence status changes */
  onStatusChange?: (isWithinRadius: boolean) => void
  /** Additional CSS classes */
  className?: string
}

interface GeofenceState {
  status: 'loading' | 'inside' | 'outside' | 'error' | 'unsupported'
  distanceMeters?: number
  accuracy?: number
  errorMessage?: string
}

/**
 * Calculate distance between two coordinates using Haversine formula.
 * Returns distance in meters.
 */
function haversineDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  const R = 6371000 // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

export function GeofenceAlert({
  taskLocation,
  radiusKm = 0.5,
  onStatusChange,
  className = '',
}: GeofenceAlertProps) {
  const { t } = useTranslation()
  const [state, setState] = useState<GeofenceState>({ status: 'loading' })
  const [dismissed, setDismissed] = useState(false)
  const platformHintKey = useMemo(() => getPermissionHintKey(detectGpsPlatform()), [])

  const radiusMeters = radiusKm * 1000

  const checkPosition = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setState({ status: 'unsupported' })
      return
    }

    setState((prev) => ({ ...prev, status: 'loading' }))

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const distance = haversineDistance(
          position.coords.latitude,
          position.coords.longitude,
          taskLocation.lat,
          taskLocation.lng
        )
        const isInside = distance <= radiusMeters
        setState({
          status: isInside ? 'inside' : 'outside',
          distanceMeters: distance,
          accuracy: position.coords.accuracy,
        })
        onStatusChange?.(isInside)
      },
      (err) => {
        let errorMessage: string
        switch (err.code) {
          case err.PERMISSION_DENIED:
            errorMessage = t('geofence.permissionDenied', 'Location permission denied')
            break
          case err.POSITION_UNAVAILABLE:
            errorMessage = t('geofence.unavailable', 'Location unavailable')
            break
          case err.TIMEOUT:
            errorMessage = t('geofence.timeout', 'Location request timed out')
            break
          default:
            errorMessage = t('geofence.error', 'Could not get location')
        }
        setState({ status: 'error', errorMessage })
        onStatusChange?.(false)
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 30000,
      }
    )
  }, [taskLocation.lat, taskLocation.lng, radiusMeters, onStatusChange, t])

  useEffect(() => {
    checkPosition()
  }, [checkPosition])

  // Don't render anything if dismissed or if user is inside the geofence
  if (dismissed) return null
  if (state.status === 'inside') return null
  if (state.status === 'loading') {
    return (
      <div className={`flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg ${className}`}>
        <svg className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <span className="text-sm text-blue-700">
          {t('geofence.checking', 'Checking your location...')}
        </span>
      </div>
    )
  }

  if (state.status === 'unsupported') return null

  if (state.status === 'error') {
    return (
      <div className={`p-3 bg-amber-50 border border-amber-200 rounded-lg ${className}`}>
        <div className="flex items-start gap-3">
          <svg
            className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div className="flex-1">
            <p className="text-sm text-amber-700">
              {t('geofence.cannotVerify', 'Cannot verify your location')}
            </p>
            <p className="text-xs text-amber-600 mt-1">{state.errorMessage}</p>
            {state.errorMessage?.includes('denied') && (
              <p className="text-xs font-medium text-amber-700 mt-1">
                {t(platformHintKey)}
              </p>
            )}
            <button
              onClick={checkPosition}
              className="mt-2 text-xs text-amber-700 hover:text-amber-900 underline"
            >
              {t('gps.tryAgain', 'Try again')}
            </button>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="text-amber-400 hover:text-amber-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    )
  }

  // status === 'outside'
  const distanceDisplay =
    state.distanceMeters !== undefined
      ? state.distanceMeters >= 1000
        ? `${(state.distanceMeters / 1000).toFixed(1)} km`
        : `${Math.round(state.distanceMeters)} m`
      : ''

  return (
    <div className={`p-3 bg-red-50 border border-red-200 rounded-lg ${className}`}>
      <div className="flex items-start gap-3">
        <svg
          className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
            clipRule="evenodd"
          />
        </svg>
        <div className="flex-1">
          <p className="text-sm font-medium text-red-700">
            {t('geofence.outsideRadius', 'You are outside the task area')}
          </p>
          <p className="text-xs text-red-600 mt-1">
            {t('geofence.distanceInfo', 'You are {{distance}} away. Required radius: {{radius}}.', {
              distance: distanceDisplay,
              radius: radiusKm >= 1 ? `${radiusKm} km` : `${Math.round(radiusMeters)} m`,
            })}
          </p>
          <p className="text-xs text-red-500 mt-1">
            {t(
              'geofence.submitAnyway',
              'You can still submit, but evidence may be flagged for review.'
            )}
          </p>
        </div>
        <div className="flex flex-col gap-1">
          <button
            onClick={checkPosition}
            className="text-xs text-red-600 hover:text-red-800 underline"
          >
            {t('geofence.recheck', 'Recheck')}
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="text-xs text-red-400 hover:text-red-600"
          >
            {t('common.dismiss', 'Dismiss')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default GeofenceAlert
