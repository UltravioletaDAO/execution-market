/**
 * useLocation Hook
 *
 * Comprehensive location hook for the map components.
 * Provides current position, watch position, distance calculations,
 * and permission handling.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { Task, Location } from '../../types/database';

// Re-export the Position interface for external use
export interface Position {
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp: number;
}

export interface LocationState {
  position: Position | null;
  error: string | null;
  isLoading: boolean;
  isSupported: boolean;
  isWatching: boolean;
  permissionState: PermissionState | null;
}

export interface UseLocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
  watchPosition?: boolean;
}

export interface TaskWithDistance extends Task {
  distance: number; // Distance in km
}

/**
 * Calculate distance between two coordinates using the Haversine formula.
 * Returns distance in kilometers.
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
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

function toRad(deg: number): number {
  return deg * (Math.PI / 180);
}

/**
 * Check if a position is within a specified radius of a target location.
 */
export function isWithinRadius(
  userLat: number,
  userLon: number,
  targetLat: number,
  targetLon: number,
  radiusKm: number
): boolean {
  const distance = calculateDistance(userLat, userLon, targetLat, targetLon);
  return distance <= radiusKm;
}

/**
 * Calculate distance from user position to a task location.
 * Returns null if task has no location.
 */
export function getDistanceToTask(
  userPosition: Position | null,
  task: Task
): number | null {
  if (!userPosition || !task.location) return null;

  return calculateDistance(
    userPosition.latitude,
    userPosition.longitude,
    task.location.lat,
    task.location.lng
  );
}

/**
 * Sort tasks by distance from user position.
 * Tasks without location are placed at the end.
 */
export function sortTasksByDistance(
  tasks: Task[],
  userPosition: Position | null
): TaskWithDistance[] {
  if (!userPosition) {
    return tasks.map((task) => ({ ...task, distance: Infinity }));
  }

  return tasks
    .map((task) => ({
      ...task,
      distance: getDistanceToTask(userPosition, task) ?? Infinity,
    }))
    .sort((a, b) => a.distance - b.distance);
}

/**
 * Filter tasks within a radius from user position.
 */
export function filterTasksByRadius(
  tasks: Task[],
  userPosition: Position | null,
  radiusKm: number
): TaskWithDistance[] {
  if (!userPosition) return [];

  return sortTasksByDistance(tasks, userPosition).filter(
    (task) => task.distance <= radiusKm
  );
}

/**
 * Format distance for display.
 */
export function formatDistance(distanceKm: number): string {
  if (distanceKm === Infinity) return 'Ubicacion desconocida';
  if (distanceKm < 0.1) return 'Muy cerca';
  if (distanceKm < 1) return `${Math.round(distanceKm * 1000)} m`;
  if (distanceKm < 10) return `${distanceKm.toFixed(1)} km`;
  return `${Math.round(distanceKm)} km`;
}

/**
 * Convert Position to Location (database format).
 */
export function positionToLocation(position: Position): Location {
  return {
    lat: position.latitude,
    lng: position.longitude,
  };
}

/**
 * Convert Location (database format) to Position.
 */
export function locationToPosition(location: Location): Pick<Position, 'latitude' | 'longitude'> {
  return {
    latitude: location.lat,
    longitude: location.lng,
  };
}

/**
 * Main location hook for map components.
 */
export function useLocation(options: UseLocationOptions = {}) {
  const {
    enableHighAccuracy = true,
    timeout = 30000,
    maximumAge = 0,
    watchPosition = false,
  } = options;

  const [state, setState] = useState<LocationState>({
    position: null,
    error: null,
    isLoading: false,
    isSupported: typeof navigator !== 'undefined' && 'geolocation' in navigator,
    isWatching: false,
    permissionState: null,
  });

  const watchIdRef = useRef<number | null>(null);

  // Check permission state on mount
  useEffect(() => {
    if (!state.isSupported || typeof navigator === 'undefined') return;

    navigator.permissions
      ?.query({ name: 'geolocation' })
      .then((result) => {
        setState((s) => ({ ...s, permissionState: result.state }));

        result.onchange = () => {
          setState((s) => ({ ...s, permissionState: result.state }));
        };
      })
      .catch(() => {
        // Permissions API not supported in this browser
      });
  }, [state.isSupported]);

  /**
   * Get current position once.
   */
  const getCurrentPosition = useCallback((): Promise<Position> => {
    return new Promise((resolve, reject) => {
      if (!state.isSupported) {
        const error = new Error('Geolocation is not supported');
        setState((s) => ({ ...s, error: error.message }));
        reject(error);
        return;
      }

      setState((s) => ({ ...s, isLoading: true, error: null }));

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const position: Position = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            timestamp: pos.timestamp,
          };

          setState((s) => ({
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
              errorMessage = 'Permiso de ubicacion denegado. Por favor habilita el acceso.';
              break;
            case err.POSITION_UNAVAILABLE:
              errorMessage = 'Ubicacion no disponible. Verifica tu configuracion GPS.';
              break;
            case err.TIMEOUT:
              errorMessage = 'Tiempo de espera agotado. Intenta de nuevo.';
              break;
            default:
              errorMessage = 'Error al obtener ubicacion.';
          }

          setState((s) => ({
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

  /**
   * Start watching position changes.
   */
  const startWatching = useCallback(() => {
    if (!state.isSupported || watchIdRef.current !== null) return;

    setState((s) => ({ ...s, isWatching: true }));

    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setState((s) => ({
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
        setState((s) => ({
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
  }, [state.isSupported, enableHighAccuracy, timeout, maximumAge]);

  /**
   * Stop watching position changes.
   */
  const stopWatching = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
      setState((s) => ({ ...s, isWatching: false }));
    }
  }, []);

  /**
   * Request permission by attempting to get position.
   */
  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      await getCurrentPosition();
      return true;
    } catch {
      return false;
    }
  }, [getCurrentPosition]);

  /**
   * Clear any error state.
   */
  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  // Auto-start watching if requested
  useEffect(() => {
    if (watchPosition && state.isSupported) {
      startWatching();
    }

    return () => {
      stopWatching();
    };
  }, [watchPosition, state.isSupported, startWatching, stopWatching]);

  return {
    ...state,
    getCurrentPosition,
    startWatching,
    stopWatching,
    requestPermission,
    clearError,
  };
}

export default useLocation;
