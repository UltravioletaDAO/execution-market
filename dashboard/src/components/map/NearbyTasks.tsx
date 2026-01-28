/**
 * NearbyTasks Component
 *
 * List of tasks near the user's location.
 * Sorted by distance, filters by radius, updates as user moves.
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import type { Task, TaskStatus } from '../../types/database';
import {
  useLocation,
  filterTasksByRadius,
  formatDistance,
  type TaskWithDistance,
} from './useLocation';

interface NearbyTasksProps {
  tasks: Task[];
  onTaskClick?: (task: Task) => void;
  defaultRadius?: number;
  maxRadius?: number;
  showRadiusFilter?: boolean;
  watchPosition?: boolean;
  className?: string;
  emptyMessage?: string;
}

// Status colors for badges
const STATUS_COLORS: Record<TaskStatus, string> = {
  published: 'bg-green-100 text-green-800',
  accepted: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  submitted: 'bg-purple-100 text-purple-800',
  verifying: 'bg-indigo-100 text-indigo-800',
  completed: 'bg-gray-100 text-gray-800',
  disputed: 'bg-red-100 text-red-800',
  expired: 'bg-gray-100 text-gray-500',
  cancelled: 'bg-gray-100 text-gray-400',
};

const STATUS_LABELS: Record<TaskStatus, string> = {
  published: 'Disponible',
  accepted: 'Aceptada',
  in_progress: 'En Progreso',
  submitted: 'Enviada',
  verifying: 'Verificando',
  completed: 'Completada',
  disputed: 'En Disputa',
  expired: 'Expirada',
  cancelled: 'Cancelada',
};

// Format bounty
function formatBounty(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

// Format deadline
function formatDeadline(deadline: string): string {
  const date = new Date(deadline);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffMs < 0) return 'Expirada';
  if (diffHours < 1) return '<1h';
  if (diffHours < 24) return `${diffHours}h`;
  return `${diffDays}d`;
}

// Individual task item
function TaskItem({
  task,
  onClick,
}: {
  task: TaskWithDistance;
  onClick?: () => void;
}) {
  const isExpiringSoon =
    new Date(task.deadline).getTime() - Date.now() < 24 * 60 * 60 * 1000;

  return (
    <article
      className="p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-all cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        {/* Distance badge */}
        <div className="flex-shrink-0 w-16 text-center">
          <div className="inline-flex flex-col items-center justify-center px-2 py-1 bg-blue-50 rounded-lg">
            <svg className="w-4 h-4 text-blue-600 mb-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-xs font-medium text-blue-700">
              {formatDistance(task.distance)}
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <span
              className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[task.status]}`}
            >
              {STATUS_LABELS[task.status]}
            </span>
            <span
              className={`text-xs ${isExpiringSoon ? 'text-orange-600 font-medium' : 'text-gray-500'}`}
            >
              {formatDeadline(task.deadline)}
            </span>
          </div>

          {/* Title */}
          <h4 className="font-medium text-gray-900 text-sm line-clamp-1 mb-1">
            {task.title}
          </h4>

          {/* Footer */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-green-600">
              {formatBounty(task.bounty_usd)}
            </span>
            {task.location_hint && (
              <span className="text-xs text-gray-500 truncate max-w-[120px]">
                {task.location_hint}
              </span>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

export function NearbyTasks({
  tasks,
  onTaskClick,
  defaultRadius = 10,
  maxRadius = 100,
  showRadiusFilter = true,
  watchPosition = false,
  className = '',
  emptyMessage = 'No hay tareas cerca de tu ubicacion.',
}: NearbyTasksProps) {
  const [radius, setRadius] = useState(defaultRadius);

  const {
    position,
    isLoading,
    error,
    isWatching,
    getCurrentPosition,
    startWatching,
    stopWatching,
    requestPermission,
    isSupported,
    permissionState,
  } = useLocation({ watchPosition });

  // Filter and sort tasks by distance
  const nearbyTasks = useMemo(() => {
    return filterTasksByRadius(tasks, position, radius);
  }, [tasks, position, radius]);

  // Handle request location permission
  const handleRequestLocation = useCallback(async () => {
    await requestPermission();
  }, [requestPermission]);

  // Handle refresh location
  const handleRefresh = useCallback(() => {
    getCurrentPosition();
  }, [getCurrentPosition]);

  // Handle toggle watching
  const handleToggleWatch = useCallback(() => {
    if (isWatching) {
      stopWatching();
    } else {
      startWatching();
    }
  }, [isWatching, startWatching, stopWatching]);

  // Auto-get position on mount if not watching
  useEffect(() => {
    if (!watchPosition && !position && isSupported && permissionState === 'granted') {
      getCurrentPosition();
    }
  }, [watchPosition, position, isSupported, permissionState, getCurrentPosition]);

  // Render permission request state
  if (!position && permissionState !== 'granted') {
    return (
      <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
        <div className="text-center py-6">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Permitir acceso a ubicacion
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            Para mostrarte tareas cercanas, necesitamos acceso a tu ubicacion.
          </p>
          <button
            onClick={handleRequestLocation}
            disabled={isLoading}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-colors font-medium"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Obteniendo ubicacion...
              </span>
            ) : (
              'Permitir ubicacion'
            )}
          </button>
          {error && (
            <p className="mt-3 text-sm text-red-600">{error}</p>
          )}
        </div>
      </div>
    );
  }

  // Render loading state
  if (isLoading && !position) {
    return (
      <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
        <div className="text-center py-8">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-gray-600">Obteniendo tu ubicacion...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Tareas cercanas
            <span className="text-sm font-normal text-gray-500">
              ({nearbyTasks.length})
            </span>
          </h3>

          <div className="flex items-center gap-2">
            {/* Watch toggle */}
            <button
              onClick={handleToggleWatch}
              className={`p-2 rounded-lg transition-colors ${
                isWatching
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title={isWatching ? 'Detener seguimiento' : 'Seguir ubicacion'}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {isWatching ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.636 18.364a9 9 0 010-12.728m12.728 0a9 9 0 010 12.728m-9.9-2.829a5 5 0 010-7.07m7.072 0a5 5 0 010 7.07M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                )}
              </svg>
            </button>

            {/* Refresh button */}
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
              title="Actualizar ubicacion"
            >
              <svg
                className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Radius filter */}
        {showRadiusFilter && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Radio: {radius} km
            </label>
            <input
              type="range"
              min={1}
              max={maxRadius}
              value={radius}
              onChange={(e) => setRadius(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>1 km</span>
              <span>{maxRadius} km</span>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        {/* Watching indicator */}
        {isWatching && (
          <div className="mt-2 flex items-center gap-2 text-xs text-blue-600">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
            Siguiendo tu ubicacion...
          </div>
        )}
      </div>

      {/* Task list */}
      <div className="p-3 max-h-[400px] overflow-y-auto">
        {nearbyTasks.length > 0 ? (
          <div className="space-y-2">
            {nearbyTasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                onClick={() => onTaskClick?.(task)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
            </div>
            <p className="text-sm text-gray-600">{emptyMessage}</p>
            <p className="text-xs text-gray-400 mt-1">
              Intenta aumentar el radio de busqueda.
            </p>
          </div>
        )}
      </div>

      {/* Footer stats */}
      {nearbyTasks.length > 0 && (
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 rounded-b-lg">
          <div className="flex items-center justify-between text-xs text-gray-600">
            <span>
              {nearbyTasks.length} tarea{nearbyTasks.length !== 1 ? 's' : ''} en {radius}km
            </span>
            <span>
              Total: {formatBounty(nearbyTasks.reduce((sum, t) => sum + t.bounty_usd, 0))}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default NearbyTasks;
