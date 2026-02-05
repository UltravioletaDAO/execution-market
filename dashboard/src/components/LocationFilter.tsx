/**
 * LocationFilter - Filter tasks by distance from current location
 *
 * Features:
 * - Distance slider (1-100 km)
 * - Current location detection via browser geolocation
 * - Manual address input
 * - Map preview placeholder
 * - Active filter badge
 */

import { useState, useEffect, useCallback } from 'react'

// GPS Coordinates type (exported for consumers)
export interface GPSCoordinates {
  lat: number
  lng: number
}

// Props interface
export interface LocationFilterProps {
  onFilterChange?: (distance: number, location: GPSCoordinates | null) => void
  onDistanceChange?: (distance: number) => void
  onLocationChange?: (location: GPSCoordinates | null) => void
  initialDistance?: number
  initialLocation?: GPSCoordinates
  maxDistance?: number
  showLocationButton?: boolean
}

// Location state type
interface LocationState {
  lat: number
  lng: number
  address?: string
}

// Get current position from browser geolocation
function getCurrentPosition(): Promise<{ lat: number; lng: number } | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null)
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        })
      },
      () => resolve(null),
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      }
    )
  })
}

export function LocationFilter({
  onFilterChange,
  onDistanceChange,
  onLocationChange,
  initialDistance = 25,
  initialLocation,
  maxDistance: _maxDistance = 100,
  showLocationButton: _showLocationButton = true,
}: LocationFilterProps) {
  const [distance, setDistance] = useState(initialDistance)
  const [location, setLocation] = useState<LocationState | null>(
    initialLocation ? { lat: initialLocation.lat, lng: initialLocation.lng } : null
  )
  const [locationLoading, setLocationLoading] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [manualAddress, setManualAddress] = useState('')
  const [showManualInput, setShowManualInput] = useState(false)

  // Notify parent of filter changes
  useEffect(() => {
    const coords = location ? { lat: location.lat, lng: location.lng } : null
    onFilterChange?.(distance, coords)
    onDistanceChange?.(distance)
    onLocationChange?.(coords)
  }, [distance, location, onFilterChange, onDistanceChange, onLocationChange])

  // Handle distance slider change
  const handleDistanceChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newDistance = parseInt(e.target.value, 10)
    setDistance(newDistance)
  }, [])

  // Request current location from browser
  const requestCurrentLocation = useCallback(async () => {
    setLocationLoading(true)
    setLocationError(null)

    try {
      const pos = await getCurrentPosition()
      if (pos) {
        setLocation({ lat: pos.lat, lng: pos.lng, address: 'Ubicacion actual' })
        setShowManualInput(false)
      } else {
        setLocationError('No se pudo obtener tu ubicacion. Verifica los permisos del navegador.')
      }
    } catch {
      setLocationError('Error al obtener ubicacion')
    } finally {
      setLocationLoading(false)
    }
  }, [])

  // Handle manual address submission
  const handleManualAddressSubmit = useCallback(() => {
    if (!manualAddress.trim()) return

    // In a real implementation, this would geocode the address
    // For now, we set a placeholder location with the address
    // This simulates geocoding - in production use a geocoding API
    setLocation({
      lat: 19.4326, // Default to Mexico City coordinates as placeholder
      lng: -99.1332,
      address: manualAddress.trim(),
    })
    setShowManualInput(false)
    setLocationError(null)
  }, [manualAddress])

  // Clear location filter
  const clearLocation = useCallback(() => {
    setLocation(null)
    setManualAddress('')
    setLocationError(null)
  }, [])

  // Determine city/region display
  const displayLocation = location?.address || (location ? `${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}` : null)

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      {/* Header with active filter badge */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="font-medium text-gray-900">Filtro de ubicacion</span>
        </div>

        {/* Active filter badge */}
        {location && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Filtro activo
          </span>
        )}
      </div>

      {/* Distance slider section */}
      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Mostrar tareas dentro de {distance} km
        </label>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-8">1 km</span>
          <input
            type="range"
            min={1}
            max={100}
            value={distance}
            onChange={handleDistanceChange}
            className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <span className="text-xs text-gray-500 w-12">100 km</span>
        </div>
        <div className="mt-1 text-center">
          <span className="inline-block px-3 py-1 bg-gray-100 text-gray-800 text-sm font-semibold rounded-full">
            {distance} km
          </span>
        </div>
      </div>

      {/* Location input section */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tu ubicacion
        </label>

        {/* Current location button */}
        <button
          onClick={requestCurrentLocation}
          disabled={locationLoading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors mb-3"
        >
          {locationLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Obteniendo ubicacion...</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span>Usar mi ubicacion actual</span>
            </>
          )}
        </button>

        {/* Toggle manual input */}
        <button
          onClick={() => setShowManualInput(!showManualInput)}
          className="w-full text-sm text-gray-600 hover:text-gray-800 underline mb-2"
        >
          {showManualInput ? 'Cancelar' : 'O ingresar direccion manualmente'}
        </button>

        {/* Manual address input */}
        {showManualInput && (
          <div className="flex gap-2">
            <input
              type="text"
              value={manualAddress}
              onChange={(e) => setManualAddress(e.target.value)}
              placeholder="Ej: Ciudad de Mexico, CDMX"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleManualAddressSubmit()
                }
              }}
            />
            <button
              onClick={handleManualAddressSubmit}
              disabled={!manualAddress.trim()}
              className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              Buscar
            </button>
          </div>
        )}

        {/* Error message */}
        {locationError && (
          <div className="mt-2 flex items-center gap-2 text-sm text-red-600">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>{locationError}</span>
          </div>
        )}
      </div>

      {/* City/Region display */}
      {displayLocation && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-sm font-medium text-green-800">{displayLocation}</span>
            </div>
            <button
              onClick={clearLocation}
              className="text-xs text-green-600 hover:text-green-800 underline"
            >
              Borrar
            </button>
          </div>
          {location && !location.address && (
            <p className="mt-1 text-xs text-green-600">
              Coordenadas: {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
            </p>
          )}
        </div>
      )}

      {/* Map preview placeholder */}
      <div className="mb-4">
        <div className="w-full h-32 bg-gray-100 border border-gray-200 rounded-lg flex items-center justify-center">
          <div className="text-center text-gray-400">
            <svg className="w-8 h-8 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <span className="text-xs">Vista previa del mapa</span>
          </div>
        </div>
      </div>

      {/* Filter summary */}
      <div className="pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          {location
            ? `Mostrando tareas dentro de ${distance} km de tu ubicacion`
            : 'Selecciona una ubicacion para filtrar por distancia'}
        </p>
      </div>
    </div>
  )
}
