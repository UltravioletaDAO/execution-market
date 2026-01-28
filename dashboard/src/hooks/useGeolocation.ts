/**
 * Geolocation Hook
 *
 * Gets current position with high accuracy for task verification.
 */

import { useState, useCallback, useEffect } from 'react';

interface Position {
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp: number;
}

interface GeolocationState {
  position: Position | null;
  error: string | null;
  isLoading: boolean;
  isSupported: boolean;
  permissionState: PermissionState | null;
}

interface GeolocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
  watchPosition?: boolean;
}

export function useGeolocation(options: GeolocationOptions = {}) {
  const {
    enableHighAccuracy = true,
    timeout = 30000,
    maximumAge = 0,
    watchPosition = false,
  } = options;

  const [state, setState] = useState<GeolocationState>({
    position: null,
    error: null,
    isLoading: false,
    isSupported: 'geolocation' in navigator,
    permissionState: null,
  });

  // Check permission state
  useEffect(() => {
    if (!state.isSupported) return;

    navigator.permissions
      .query({ name: 'geolocation' })
      .then((result) => {
        setState(s => ({ ...s, permissionState: result.state }));

        result.onchange = () => {
          setState(s => ({ ...s, permissionState: result.state }));
        };
      })
      .catch(() => {
        // Permissions API not supported
      });
  }, [state.isSupported]);

  const getCurrentPosition = useCallback((): Promise<Position> => {
    return new Promise((resolve, reject) => {
      if (!state.isSupported) {
        reject(new Error('Geolocation is not supported'));
        return;
      }

      setState(s => ({ ...s, isLoading: true, error: null }));

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const position: Position = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            timestamp: pos.timestamp,
          };

          setState(s => ({
            ...s,
            position,
            isLoading: false,
            error: null,
          }));

          resolve(position);
        },
        (err) => {
          let errorMessage: string;

          switch (err.code) {
            case err.PERMISSION_DENIED:
              errorMessage = 'Location permission denied. Please enable location access.';
              break;
            case err.POSITION_UNAVAILABLE:
              errorMessage = 'Location unavailable. Please check your GPS settings.';
              break;
            case err.TIMEOUT:
              errorMessage = 'Location request timed out. Please try again.';
              break;
            default:
              errorMessage = 'Failed to get location.';
          }

          setState(s => ({
            ...s,
            isLoading: false,
            error: errorMessage,
          }));

          reject(new Error(errorMessage));
        },
        {
          enableHighAccuracy,
          timeout,
          maximumAge,
        }
      );
    });
  }, [state.isSupported, enableHighAccuracy, timeout, maximumAge]);

  // Watch position if enabled
  useEffect(() => {
    if (!watchPosition || !state.isSupported) return;

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setState(s => ({
          ...s,
          position: {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            timestamp: pos.timestamp,
          },
          error: null,
        }));
      },
      (err) => {
        setState(s => ({
          ...s,
          error: err.message,
        }));
      },
      {
        enableHighAccuracy,
        timeout,
        maximumAge,
      }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
    };
  }, [watchPosition, state.isSupported, enableHighAccuracy, timeout, maximumAge]);

  const requestPermission = useCallback(async () => {
    try {
      await getCurrentPosition();
      return true;
    } catch {
      return false;
    }
  }, [getCurrentPosition]);

  return {
    ...state,
    getCurrentPosition,
    requestPermission,
  };
}

/**
 * Calculate distance between two coordinates (Haversine formula)
 */
export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Earth radius in km
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; // Distance in km
}

function toRad(deg: number): number {
  return deg * (Math.PI / 180);
}

/**
 * Check if position is within radius of target
 */
export function isWithinRadius(
  position: Position,
  targetLat: number,
  targetLon: number,
  radiusKm: number
): boolean {
  const distance = calculateDistance(
    position.latitude,
    position.longitude,
    targetLat,
    targetLon
  );
  return distance <= radiusKm;
}

export default useGeolocation;
