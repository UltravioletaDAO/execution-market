/**
 * LocationPicker Component
 *
 * Interactive location input with map, search, and current location.
 * Used by agents to set task locations.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, Circle } from 'react-leaflet';
import L from 'leaflet';
import type { Location } from '../../types/database';
import { useLocation } from './useLocation';

import 'leaflet/dist/leaflet.css';

interface LocationPickerProps {
  value: Location | null;
  onChange: (location: Location | null) => void;
  radiusKm?: number;
  onRadiusChange?: (radius: number) => void;
  showRadiusControl?: boolean;
  placeholder?: string;
  className?: string;
}

// Default map center (Mexico City)
const DEFAULT_CENTER: [number, number] = [19.4326, -99.1332];
const DEFAULT_ZOOM = 12;

// Create a custom pin icon
const createPinIcon = (isUser: boolean = false): L.DivIcon => {
  const color = isUser ? '#3b82f6' : '#ef4444';
  const size = isUser ? 20 : 32;

  const html = isUser
    ? `<div style="
        width: ${size}px;
        height: ${size}px;
        background-color: ${color};
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      "></div>`
    : `<div style="
        width: ${size}px;
        height: ${size}px;
        background-color: ${color};
        border: 3px solid white;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      ">
        <div style="
          width: 8px;
          height: 8px;
          background: white;
          border-radius: 50%;
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%) rotate(45deg);
        "></div>
      </div>`;

  return L.divIcon({
    className: 'location-picker-marker',
    html,
    iconSize: [size, size],
    iconAnchor: isUser ? [size / 2, size / 2] : [size / 2, size],
  });
};

// Map click handler component
function MapClickHandler({
  onClick,
}: {
  onClick: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click: (e) => {
      onClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Geocoding function (using Nominatim - free, no API key needed)
async function geocodeAddress(
  query: string
): Promise<{ lat: number; lng: number; display_name: string } | null> {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        query
      )}&limit=1`,
      {
        headers: {
          'User-Agent': 'Chamba Dashboard',
        },
      }
    );

    const data = await response.json();
    if (data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
        display_name: data[0].display_name,
      };
    }
    return null;
  } catch (error) {
    console.error('Geocoding error:', error);
    return null;
  }
}

// Reverse geocoding function
async function reverseGeocode(
  lat: number,
  lng: number
): Promise<string | null> {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
      {
        headers: {
          'User-Agent': 'Chamba Dashboard',
        },
      }
    );

    const data = await response.json();
    if (data.display_name) {
      // Return a shorter version of the address
      const parts = data.display_name.split(', ');
      return parts.slice(0, 3).join(', ');
    }
    return null;
  } catch (error) {
    console.error('Reverse geocoding error:', error);
    return null;
  }
}

export function LocationPicker({
  value,
  onChange,
  radiusKm,
  onRadiusChange,
  showRadiusControl = false,
  placeholder = 'Buscar direccion...',
  className = '',
}: LocationPickerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [address, setAddress] = useState<string | null>(null);
  const [localRadius, setLocalRadius] = useState(radiusKm ?? 1);
  const mapRef = useRef<L.Map | null>(null);

  const {
    position: userPosition,
    isLoading: locationLoading,
    error: locationError,
    getCurrentPosition,
    isSupported: locationSupported,
  } = useLocation();

  // Update address when value changes
  useEffect(() => {
    if (value) {
      reverseGeocode(value.lat, value.lng).then((addr) => {
        if (addr) setAddress(addr);
      });
    } else {
      setAddress(null);
    }
  }, [value]);

  // Handle search submit
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;

    setSearchLoading(true);
    setSearchError(null);

    const result = await geocodeAddress(searchQuery);

    if (result) {
      const location = { lat: result.lat, lng: result.lng };
      onChange(location);
      setAddress(result.display_name);

      // Center map on result
      if (mapRef.current) {
        mapRef.current.setView([result.lat, result.lng], 15);
      }
    } else {
      setSearchError('No se encontro la direccion. Intenta ser mas especifico.');
    }

    setSearchLoading(false);
  }, [searchQuery, onChange]);

  // Handle map click
  const handleMapClick = useCallback(
    (lat: number, lng: number) => {
      const location = { lat, lng };
      onChange(location);
    },
    [onChange]
  );

  // Handle current location button
  const handleCurrentLocation = useCallback(async () => {
    try {
      const pos = await getCurrentPosition();
      const location = { lat: pos.latitude, lng: pos.longitude };
      onChange(location);

      if (mapRef.current) {
        mapRef.current.setView([pos.latitude, pos.longitude], 15);
      }
    } catch {
      // Error is handled in the hook
    }
  }, [getCurrentPosition, onChange]);

  // Handle radius change
  const handleRadiusChange = useCallback(
    (newRadius: number) => {
      setLocalRadius(newRadius);
      onRadiusChange?.(newRadius);
    },
    [onRadiusChange]
  );

  // Clear selection
  const handleClear = useCallback(() => {
    onChange(null);
    setSearchQuery('');
    setAddress(null);
  }, [onChange]);

  // Determine map center
  const mapCenter: [number, number] = value
    ? [value.lat, value.lng]
    : userPosition
    ? [userPosition.latitude, userPosition.longitude]
    : DEFAULT_CENTER;

  const actualRadius = radiusKm ?? localRadius;

  return (
    <div className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Search bar */}
      <div className="p-3 border-b border-gray-200">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSearch();
                }
              }}
              placeholder={placeholder}
              className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {searchLoading && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>
          <button
            onClick={handleSearch}
            disabled={searchLoading || !searchQuery.trim()}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            Buscar
          </button>
        </div>

        {searchError && (
          <p className="mt-2 text-xs text-red-600">{searchError}</p>
        )}
      </div>

      {/* Map */}
      <div className="h-64 relative">
        <MapContainer
          center={mapCenter}
          zoom={value ? 15 : DEFAULT_ZOOM}
          className="h-full w-full"
          ref={mapRef}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapClickHandler onClick={handleMapClick} />

          {/* Selected location marker */}
          {value && (
            <>
              <Marker
                position={[value.lat, value.lng]}
                icon={createPinIcon(false)}
              />
              {/* Radius circle */}
              {actualRadius > 0 && (
                <Circle
                  center={[value.lat, value.lng]}
                  radius={actualRadius * 1000} // Convert km to meters
                  pathOptions={{
                    color: '#3b82f6',
                    fillColor: '#3b82f6',
                    fillOpacity: 0.1,
                    weight: 2,
                  }}
                />
              )}
            </>
          )}

          {/* User location marker */}
          {userPosition && (
            <Marker
              position={[userPosition.latitude, userPosition.longitude]}
              icon={createPinIcon(true)}
            />
          )}
        </MapContainer>

        {/* Map overlay buttons */}
        <div className="absolute top-2 right-2 z-[1000] flex flex-col gap-2">
          {locationSupported && (
            <button
              onClick={handleCurrentLocation}
              disabled={locationLoading}
              className="w-10 h-10 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 disabled:opacity-50 flex items-center justify-center"
              title="Usar mi ubicacion"
            >
              {locationLoading ? (
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              )}
            </button>
          )}

          {value && (
            <button
              onClick={handleClear}
              className="w-10 h-10 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 flex items-center justify-center"
              title="Limpiar seleccion"
            >
              <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Click instruction overlay */}
        {!value && (
          <div className="absolute bottom-2 left-2 right-2 z-[1000] text-center">
            <span className="inline-block px-3 py-1 bg-black/70 text-white text-xs rounded-full">
              Haz click en el mapa para seleccionar ubicacion
            </span>
          </div>
        )}
      </div>

      {/* Selected location info */}
      <div className="p-3 border-t border-gray-200">
        {value ? (
          <div className="space-y-3">
            {/* Address display */}
            <div className="flex items-start gap-2">
              <svg className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <div className="flex-1 min-w-0">
                {address ? (
                  <p className="text-sm text-gray-900 truncate">{address}</p>
                ) : (
                  <p className="text-sm text-gray-500">Cargando direccion...</p>
                )}
                <p className="text-xs text-gray-500 mt-0.5">
                  {value.lat.toFixed(6)}, {value.lng.toFixed(6)}
                </p>
              </div>
            </div>

            {/* Radius control */}
            {showRadiusControl && (
              <div className="pt-2 border-t border-gray-100">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Radio de tarea: {actualRadius} km
                </label>
                <input
                  type="range"
                  min={0.1}
                  max={50}
                  step={0.1}
                  value={actualRadius}
                  onChange={(e) => handleRadiusChange(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>100m</span>
                  <span>50km</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2 text-gray-500">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-sm">
              Ninguna ubicacion seleccionada
            </span>
          </div>
        )}

        {/* Location error */}
        {locationError && (
          <p className="mt-2 text-xs text-red-600 flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {locationError}
          </p>
        )}
      </div>
    </div>
  );
}

export { geocodeAddress, reverseGeocode };
export default LocationPicker;
