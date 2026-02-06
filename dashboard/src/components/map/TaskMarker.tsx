/**
 * TaskMarker Component
 *
 * Custom marker for tasks on the map.
 * Shows bounty amount in the marker and status color.
 */

import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import type { Task, TaskStatus } from '../../types/database';

interface TaskMarkerProps {
  task: Task;
  onClick?: (task: Task) => void;
  isSelected?: boolean;
}

// Status colors for markers
const STATUS_COLORS: Record<TaskStatus, { bg: string; border: string; text: string }> = {
  published: { bg: '#4b4b4b', border: '#3f3f46', text: '#ffffff' },      // Green - available
  accepted: { bg: '#404040', border: '#2a2a2a', text: '#ffffff' },       // Blue - assigned
  in_progress: { bg: '#8a8a8a', border: '#787878', text: '#000000' },    // Yellow - in progress
  submitted: { bg: '#7a7a7a', border: '#6f6f6f', text: '#ffffff' },      // Purple - submitted
  verifying: { bg: '#6b6b6b', border: '#636363', text: '#ffffff' },      // Indigo - verifying
  completed: { bg: '#71717a', border: '#52525b', text: '#ffffff' },      // Gray - completed
  disputed: { bg: '#1f1f1f', border: '#2f2f2f', text: '#ffffff' },       // Red - disputed
  expired: { bg: '#a1a1aa', border: '#71717a', text: '#ffffff' },        // Light gray - expired
  cancelled: { bg: '#d4d4d8', border: '#a1a1aa', text: '#3f3f46' },      // Lighter gray - cancelled
};

// Format bounty for display in marker
function formatBountyShort(amount: number): string {
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(amount >= 10000 ? 0 : 1)}K`;
  }
  if (amount >= 100) {
    return `$${Math.round(amount)}`;
  }
  return `$${amount.toFixed(amount < 10 ? 2 : 0)}`;
}

// Create a custom icon with bounty amount
function createTaskIcon(task: Task, isSelected: boolean = false): L.DivIcon {
  const colors = STATUS_COLORS[task.status];
  const bountyText = formatBountyShort(task.bounty_usd);
  const size = isSelected ? 48 : 40;
  const fontSize = isSelected ? 12 : 10;

  const html = `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background-color: ${colors.bg};
      border: 3px solid ${isSelected ? '#000000' : colors.border};
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: ${isSelected ? '0 4px 12px rgba(0,0,0,0.4)' : '0 2px 8px rgba(0,0,0,0.3)'};
      transition: all 0.2s ease;
    ">
      <span style="
        transform: rotate(45deg);
        color: ${colors.text};
        font-size: ${fontSize}px;
        font-weight: bold;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
      ">${bountyText}</span>
    </div>
  `;

  return L.divIcon({
    className: 'task-marker',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
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

export { createTaskIcon, STATUS_COLORS };
export default TaskMarker;
