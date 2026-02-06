/**
 * TaskMap Component
 *
 * Main map component for displaying task locations.
 * Shows task markers, user location, and radius circles.
 * Supports click-to-set-location for agents.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Circle, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Task, Location } from '../../types/database';
import { useLocation, type Position } from './useLocation';
import { TaskCluster } from './TaskCluster';
import { TaskMarker } from './TaskMarker';

import 'leaflet/dist/leaflet.css';

interface TaskMapProps {
  tasks: Task[];
  selectedTaskId?: string;
  onTaskClick?: (task: Task) => void;
  onLocationSelect?: (location: Location) => void;
  selectionMode?: boolean;
  showUserLocation?: boolean;
  showClusters?: boolean;
  userLocationRadius?: number; // Show radius around user in km
  center?: [number, number];
  zoom?: number;
  className?: string;
  height?: string;
}

// Default map center (Mexico City)
const DEFAULT_CENTER: [number, number] = [19.4326, -99.1332];
const DEFAULT_ZOOM = 12;

// User location marker
const createUserIcon = (): L.DivIcon => {
  const html = `
    <div style="
      width: 24px;
      height: 24px;
      background-color: #404040;
      border: 4px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 8px rgba(64, 64, 64, 0.5);
    ">
      <div style="
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
      "></div>
    </div>
  `;

  return L.divIcon({
    className: 'user-location-marker',
    html,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
};

// Selection cursor marker
const createSelectionIcon = (): L.DivIcon => {
  const html = `
    <div style="
      width: 32px;
      height: 32px;
      border: 3px dashed #1f1f1f;
      border-radius: 50%;
      animation: pulse 1.5s ease-in-out infinite;
    ">
      <div style="
        width: 8px;
        height: 8px;
        background: #1f1f1f;
        border-radius: 50%;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
      "></div>
    </div>
    <style>
      @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.1); }
      }
    </style>
  `;

  return L.divIcon({
    className: 'selection-marker',
    html,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Map controller for programmatic interactions
function MapController({
  center,
  zoom,
  onBoundsChange,
}: {
  center?: [number, number];
  zoom?: number;
  onBoundsChange?: (bounds: L.LatLngBounds) => void;
}) {
  const map = useMap();

  // Update map view when center/zoom props change
  useEffect(() => {
    if (center) {
      map.setView(center, zoom ?? map.getZoom());
    }
  }, [map, center, zoom]);

  // Report bounds changes
  useMapEvents({
    moveend: () => {
      onBoundsChange?.(map.getBounds());
    },
    zoomend: () => {
      onBoundsChange?.(map.getBounds());
    },
  });

  return null;
}

// Click handler for selection mode
function SelectionHandler({
  enabled,
  onSelect,
}: {
  enabled: boolean;
  onSelect: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click: (e) => {
      if (enabled) {
        onSelect(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

// Fit map bounds to show all tasks (currently unused but kept for future use)
function _useFitBounds(
  map: L.Map | null,
  tasks: Task[],
  userPosition: Position | null
) {
  useEffect(() => {
    if (!map || tasks.length === 0) return;

    const points: L.LatLngExpression[] = tasks
      .filter((t) => t.location)
      .map((t) => [t.location!.lat, t.location!.lng]);

    if (userPosition) {
      points.push([userPosition.latitude, userPosition.longitude]);
    }

    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
  }, [map, tasks, userPosition]);
}

export function TaskMap({
  tasks,
  selectedTaskId,
  onTaskClick,
  onLocationSelect,
  selectionMode = false,
  showUserLocation = true,
  showClusters = true,
  userLocationRadius,
  center,
  zoom,
  className = '',
  height = '400px',
}: TaskMapProps) {
  const [selectionLocation, setSelectionLocation] = useState<Location | null>(null);
  const [_mapBounds, setMapBounds] = useState<L.LatLngBounds | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  const {
    position: userPosition,
    isLoading: locationLoading,
    error: locationError,
    getCurrentPosition,
    isSupported: locationSupported,
  } = useLocation({ watchPosition: showUserLocation });

  // Get the selected task
  const selectedTask = useMemo(
    () => tasks.find((t) => t.id === selectedTaskId),
    [tasks, selectedTaskId]
  );

  // Determine map center
  const mapCenter: [number, number] = useMemo(() => {
    if (center) return center;
    if (selectedTask?.location) {
      return [selectedTask.location.lat, selectedTask.location.lng];
    }
    if (userPosition) {
      return [userPosition.latitude, userPosition.longitude];
    }
    // Center on first task with location
    const firstTaskWithLocation = tasks.find((t) => t.location);
    if (firstTaskWithLocation?.location) {
      return [firstTaskWithLocation.location.lat, firstTaskWithLocation.location.lng];
    }
    return DEFAULT_CENTER;
  }, [center, selectedTask, userPosition, tasks]);

  // Handle location selection in selection mode
  const handleLocationSelect = useCallback(
    (lat: number, lng: number) => {
      const location = { lat, lng };
      setSelectionLocation(location);
      onLocationSelect?.(location);
    },
    [onLocationSelect]
  );

  // Handle task click
  const handleTaskClick = useCallback(
    (task: Task) => {
      onTaskClick?.(task);
      // Center map on clicked task
      if (task.location && mapRef.current) {
        mapRef.current.setView([task.location.lat, task.location.lng], 15);
      }
    },
    [onTaskClick]
  );

  // Center on user location
  const handleCenterOnUser = useCallback(() => {
    if (userPosition && mapRef.current) {
      mapRef.current.setView(
        [userPosition.latitude, userPosition.longitude],
        15
      );
    } else if (locationSupported) {
      getCurrentPosition().then((pos) => {
        if (mapRef.current) {
          mapRef.current.setView([pos.latitude, pos.longitude], 15);
        }
      });
    }
  }, [userPosition, locationSupported, getCurrentPosition]);

  // Fit bounds to show all tasks
  const handleFitBounds = useCallback(() => {
    if (!mapRef.current) return;

    const points: L.LatLngExpression[] = tasks
      .filter((t) => t.location)
      .map((t) => [t.location!.lat, t.location!.lng]);

    if (userPosition) {
      points.push([userPosition.latitude, userPosition.longitude]);
    }

    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      mapRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
  }, [tasks, userPosition]);

  // Tasks with location only
  const tasksWithLocation = useMemo(
    () => tasks.filter((t) => t.location),
    [tasks]
  );

  return (
    <div className={`relative ${className}`} style={{ height }}>
      {/* Map container */}
      <MapContainer
        center={mapCenter}
        zoom={zoom ?? DEFAULT_ZOOM}
        className="h-full w-full rounded-lg"
        ref={mapRef}
        style={{ background: '#f4f4f5' }}
      >
        {/* Map tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Map controller */}
        <MapController
          center={center}
          zoom={zoom}
          onBoundsChange={setMapBounds}
        />

        {/* Selection handler */}
        {selectionMode && (
          <SelectionHandler
            enabled={selectionMode}
            onSelect={handleLocationSelect}
          />
        )}

        {/* Task markers - either clustered or individual */}
        {showClusters ? (
          <TaskCluster
            tasks={tasksWithLocation}
            onTaskClick={handleTaskClick}
            selectedTaskId={selectedTaskId}
          />
        ) : (
          tasksWithLocation.map((task) => (
            <TaskMarker
              key={task.id}
              task={task}
              onClick={handleTaskClick}
              isSelected={task.id === selectedTaskId}
            />
          ))
        )}

        {/* Selected task radius */}
        {selectedTask?.location && selectedTask.location_radius_km && (
          <Circle
            center={[selectedTask.location.lat, selectedTask.location.lng]}
            radius={selectedTask.location_radius_km * 1000}
            pathOptions={{
              color: '#52525b',
              fillColor: '#52525b',
              fillOpacity: 0.1,
              weight: 2,
              dashArray: '5, 5',
            }}
          />
        )}

        {/* User location marker */}
        {showUserLocation && userPosition && (
          <>
            <Marker
              position={[userPosition.latitude, userPosition.longitude]}
              icon={createUserIcon()}
            />
            {/* User location accuracy circle */}
            {userPosition.accuracy > 50 && (
              <Circle
                center={[userPosition.latitude, userPosition.longitude]}
                radius={userPosition.accuracy}
                pathOptions={{
                  color: '#404040',
                  fillColor: '#404040',
                  fillOpacity: 0.1,
                  weight: 1,
                }}
              />
            )}
            {/* User search radius */}
            {userLocationRadius && (
              <Circle
                center={[userPosition.latitude, userPosition.longitude]}
                radius={userLocationRadius * 1000}
                pathOptions={{
                  color: '#404040',
                  fillColor: '#404040',
                  fillOpacity: 0.05,
                  weight: 2,
                }}
              />
            )}
          </>
        )}

        {/* Selection marker */}
        {selectionMode && selectionLocation && (
          <Marker
            position={[selectionLocation.lat, selectionLocation.lng]}
            icon={createSelectionIcon()}
          />
        )}
      </MapContainer>

      {/* Map controls overlay */}
      <div className="absolute top-3 right-3 z-[1000] flex flex-col gap-2">
        {/* Center on user location */}
        {locationSupported && (
          <button
            onClick={handleCenterOnUser}
            disabled={locationLoading}
            className="w-10 h-10 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 disabled:opacity-50 flex items-center justify-center transition-colors"
            title="Mi ubicacion"
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

        {/* Fit all tasks */}
        {tasksWithLocation.length > 0 && (
          <button
            onClick={handleFitBounds}
            className="w-10 h-10 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 flex items-center justify-center transition-colors"
            title="Ver todas las tareas"
          >
            <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
        )}
      </div>

      {/* Selection mode indicator */}
      {selectionMode && (
        <div className="absolute bottom-3 left-3 right-3 z-[1000] text-center">
          <span className="inline-block px-4 py-2 bg-black/75 text-white text-sm rounded-lg">
            Haz click en el mapa para seleccionar ubicacion
          </span>
        </div>
      )}

      {/* Task count badge */}
      <div className="absolute bottom-3 right-3 z-[1000]">
        <span className="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-gray-300 rounded-full shadow-sm text-xs font-medium text-gray-700">
          <svg className="w-3.5 h-3.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          {tasksWithLocation.length} tarea{tasksWithLocation.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Location error */}
      {locationError && showUserLocation && (
        <div className="absolute top-3 left-3 z-[1000] max-w-xs">
          <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-xs text-red-600">{locationError}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default TaskMap;
