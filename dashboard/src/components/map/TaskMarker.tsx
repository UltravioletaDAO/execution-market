/**
 * TaskMarker Component
 *
 * Custom marker for tasks on the map.
 * Shows bounty amount in the marker and status color.
 */

import { Marker, Popup } from 'react-leaflet';
import type { Task, TaskStatus } from '../../types/database';
import { createTaskIcon, STATUS_COLORS } from './marker-utils';

interface TaskMarkerProps {
  task: Task;
  onClick?: (task: Task) => void;
  isSelected?: boolean;
}

// Format deadline for popup
function formatDeadline(deadline: string): string {
  const date = new Date(deadline);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffMs < 0) return 'Expirada';
  if (diffHours < 1) return 'Menos de 1 hora';
  if (diffHours < 24) return `${diffHours} horas`;
  if (diffDays === 1) return '1 dia';
  return `${diffDays} dias`;
}

// Status labels in Spanish
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

export function TaskMarker({ task, onClick, isSelected = false }: TaskMarkerProps) {
  if (!task.location) return null;

  const icon = createTaskIcon(task, isSelected);
  const colors = STATUS_COLORS[task.status];

  return (
    <Marker
      position={[task.location.lat, task.location.lng]}
      icon={icon}
      eventHandlers={{
        click: () => onClick?.(task),
      }}
    >
      <Popup>
        <div className="min-w-[200px] p-1">
          {/* Status badge */}
          <div className="flex justify-between items-start mb-2">
            <span
              className="px-2 py-0.5 text-xs font-medium rounded-full"
              style={{
                backgroundColor: colors.bg,
                color: colors.text,
              }}
            >
              {STATUS_LABELS[task.status]}
            </span>
            <span className="text-xs text-gray-500">{formatDeadline(task.deadline)}</span>
          </div>

          {/* Title */}
          <h4 className="font-semibold text-gray-900 text-sm mb-1 line-clamp-2">
            {task.title}
          </h4>

          {/* Bounty */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-lg font-bold text-green-600">
              ${task.bounty_usd.toFixed(2)}
            </span>
            <span className="text-xs text-gray-400">{task.payment_token}</span>
          </div>

          {/* Location hint */}
          {task.location_hint && (
            <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                  clipRule="evenodd"
                />
              </svg>
              {task.location_hint}
            </p>
          )}

          {/* Radius info */}
          {task.location_radius_km && (
            <p className="text-xs text-blue-600">
              Radio: {task.location_radius_km} km
            </p>
          )}

          {/* Click to view details */}
          {onClick && (
            <button
              className="mt-2 w-full py-1.5 px-3 bg-gray-900 text-white text-xs font-medium rounded hover:bg-gray-800 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onClick(task);
              }}
            >
              Ver detalles
            </button>
          )}
        </div>
      </Popup>
    </Marker>
  );
}

export default TaskMarker;
