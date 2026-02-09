/**
 * Map Components Index
 *
 * Export all map-related components and utilities.
 */

// Main components
export { TaskMap } from './TaskMap';
export { LocationPicker } from './LocationPicker';
export { TaskMarker } from './TaskMarker';
export { TaskCluster } from './TaskCluster';
export { NearbyTasks } from './NearbyTasks';

// Utilities
export { geocodeAddress, reverseGeocode } from './geocoding';
export { createTaskIcon, STATUS_COLORS } from './marker-utils';

// Hook and utilities
export {
  useLocation,
  calculateDistance,
  isWithinRadius,
  getDistanceToTask,
  sortTasksByDistance,
  filterTasksByRadius,
  formatDistance,
  positionToLocation,
  locationToPosition,
  type Position,
  type LocationState,
  type UseLocationOptions,
  type TaskWithDistance,
} from './useLocation';

// Default export
export { TaskMap as default } from './TaskMap';
