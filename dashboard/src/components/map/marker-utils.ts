/**
 * Map marker utilities
 *
 * Constants and functions for creating custom map markers.
 */

import L from 'leaflet';
import type { Task, TaskStatus } from '../../types/database';

// Status colors for markers
export const STATUS_COLORS: Record<TaskStatus, { bg: string; border: string; text: string }> = {
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
export function createTaskIcon(task: Task, isSelected: boolean = false): L.DivIcon {
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
