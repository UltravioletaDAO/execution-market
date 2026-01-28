/**
 * Map Components Index
 *
 * Export all map-related components and utilities.
 */

// Main components
export { TaskMap } from './TaskMap';
export { LocationPicker, geocodeAddress, reverseGeocode } from './LocationPicker';
export { TaskMarker, createTaskIcon, STATUS_COLORS } from './TaskMarker';
export { TaskCluster } from './TaskCluster';
export { NearbyTasks } from './NearbyTasks';

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
