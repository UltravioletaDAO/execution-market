/**
 * TaskCluster Component
 *
 * Clusters nearby tasks when zoomed out.
 * Shows count and average bounty, expands on click.
 */

import { useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { useState, useEffect, useMemo, useCallback } from 'react';
import type { Task } from '../../types/database';
import { TaskMarker } from './TaskMarker';

interface TaskClusterProps {
  tasks: Task[];
  onTaskClick?: (task: Task) => void;
  selectedTaskId?: string;
  clusterRadius?: number; // in pixels
}

interface Cluster {
  id: string;
  center: { lat: number; lng: number };
  tasks: Task[];
  totalBounty: number;
  avgBounty: number;
}

// Determine cluster color based on average bounty
function getClusterColor(avgBounty: number): { bg: string; border: string } {
  if (avgBounty >= 100) return { bg: '#22c55e', border: '#16a34a' }; // High value - green
  if (avgBounty >= 50) return { bg: '#3b82f6', border: '#2563eb' };  // Medium-high - blue
  if (avgBounty >= 20) return { bg: '#eab308', border: '#ca8a04' };  // Medium - yellow
  return { bg: '#6b7280', border: '#4b5563' };                        // Low - gray
}

// Create cluster icon
function createClusterIcon(cluster: Cluster): L.DivIcon {
  const colors = getClusterColor(cluster.avgBounty);
  const size = Math.min(60, 40 + cluster.tasks.length * 2);

  const html = `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background-color: ${colors.bg};
      border: 3px solid ${colors.border};
      border-radius: 50%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: 0 3px 10px rgba(0,0,0,0.3);
      cursor: pointer;
      transition: transform 0.2s ease;
    " class="cluster-marker" data-cluster-id="${cluster.id}">
      <span style="
        color: white;
        font-size: ${size > 50 ? 14 : 12}px;
        font-weight: bold;
        line-height: 1;
      ">${cluster.tasks.length}</span>
      <span style="
        color: rgba(255,255,255,0.9);
        font-size: ${size > 50 ? 10 : 8}px;
        margin-top: 1px;
      ">$${Math.round(cluster.avgBounty)}</span>
    </div>
  `;

  return L.divIcon({
    className: 'task-cluster',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// Calculate distance between two points in pixels on the map
function getPixelDistance(
  map: L.Map,
  latlng1: L.LatLng,
  latlng2: L.LatLng
): number {
  const point1 = map.latLngToLayerPoint(latlng1);
  const point2 = map.latLngToLayerPoint(latlng2);
  return Math.sqrt(
    Math.pow(point1.x - point2.x, 2) + Math.pow(point1.y - point2.y, 2)
  );
}

// Cluster tasks based on pixel distance at current zoom
function clusterTasks(
  map: L.Map,
  tasks: Task[],
  clusterRadius: number
): { clusters: Cluster[]; unclustered: Task[] } {
  const tasksWithLocation = tasks.filter((t) => t.location);
  const clusters: Cluster[] = [];
  const clustered = new Set<string>();

  tasksWithLocation.forEach((task) => {
    if (clustered.has(task.id) || !task.location) return;

    const nearby = tasksWithLocation.filter((other) => {
      if (other.id === task.id || clustered.has(other.id) || !other.location)
        return false;

      const distance = getPixelDistance(
        map,
        L.latLng(task.location!.lat, task.location!.lng),
        L.latLng(other.location!.lat, other.location!.lng)
      );

      return distance < clusterRadius;
    });

    if (nearby.length > 0) {
      const clusterTasks = [task, ...nearby];
      clusterTasks.forEach((t) => clustered.add(t.id));

      // Calculate center
      const lats = clusterTasks.map((t) => t.location!.lat);
      const lngs = clusterTasks.map((t) => t.location!.lng);
      const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
      const centerLng = lngs.reduce((a, b) => a + b, 0) / lngs.length;

      // Calculate bounty stats
      const totalBounty = clusterTasks.reduce((sum, t) => sum + t.bounty_usd, 0);
      const avgBounty = totalBounty / clusterTasks.length;

      clusters.push({
        id: `cluster-${task.id}`,
        center: { lat: centerLat, lng: centerLng },
        tasks: clusterTasks,
        totalBounty,
        avgBounty,
      });
    }
  });

  const unclustered = tasksWithLocation.filter((t) => !clustered.has(t.id));

  return { clusters, unclustered };
}

export function TaskCluster({
  tasks,
  onTaskClick,
  selectedTaskId,
  clusterRadius = 60,
}: TaskClusterProps) {
  const map = useMap();
  const [zoom, setZoom] = useState(map.getZoom());
  const [expandedClusterId, setExpandedClusterId] = useState<string | null>(null);

  // Track zoom changes
  useMapEvents({
    zoomend: () => {
      setZoom(map.getZoom());
      setExpandedClusterId(null); // Reset expanded cluster on zoom
    },
  });

  // Compute clusters based on current zoom
  const { clusters, unclustered } = useMemo(() => {
    // At high zoom levels, don't cluster
    if (zoom >= 15) {
      return {
        clusters: [],
        unclustered: tasks.filter((t) => t.location),
      };
    }

    return clusterTasks(map, tasks, clusterRadius);
  }, [map, tasks, zoom, clusterRadius]);

  // Handle cluster click - zoom to fit or expand
  const handleClusterClick = useCallback(
    (cluster: Cluster) => {
      if (expandedClusterId === cluster.id) {
        // Already expanded, zoom to fit
        const bounds = L.latLngBounds(
          cluster.tasks.map((t) => L.latLng(t.location!.lat, t.location!.lng))
        );
        map.fitBounds(bounds, { padding: [50, 50] });
        setExpandedClusterId(null);
      } else {
        // Expand to show individual markers
        setExpandedClusterId(cluster.id);
      }
    },
    [map, expandedClusterId]
  );

  // Render cluster markers
  useEffect(() => {
    const markers: L.Marker[] = [];

    clusters.forEach((cluster) => {
      if (expandedClusterId === cluster.id) return; // Skip expanded cluster

      const icon = createClusterIcon(cluster);
      const marker = L.marker([cluster.center.lat, cluster.center.lng], { icon });

      marker.on('click', () => handleClusterClick(cluster));

      // Popup with cluster info
      marker.bindPopup(`
        <div class="p-2 min-w-[150px]">
          <h4 class="font-bold text-sm mb-1">${cluster.tasks.length} tareas</h4>
          <p class="text-xs text-gray-600 mb-1">
            Bounty total: $${cluster.totalBounty.toFixed(2)}
          </p>
          <p class="text-xs text-gray-600 mb-2">
            Promedio: $${cluster.avgBounty.toFixed(2)}
          </p>
          <p class="text-xs text-blue-600">
            Click para expandir
          </p>
        </div>
      `);

      marker.addTo(map);
      markers.push(marker);
    });

    return () => {
      markers.forEach((marker) => marker.remove());
    };
  }, [clusters, expandedClusterId, map, handleClusterClick]);

  // Get tasks to render as individual markers
  const individualTasks = useMemo(() => {
    const expandedCluster = clusters.find((c) => c.id === expandedClusterId);
    if (expandedCluster) {
      return [...unclustered, ...expandedCluster.tasks];
    }
    return unclustered;
  }, [clusters, unclustered, expandedClusterId]);

  return (
    <>
      {individualTasks.map((task) => (
        <TaskMarker
          key={task.id}
          task={task}
          onClick={onTaskClick}
          isSelected={task.id === selectedTaskId}
        />
      ))}
    </>
  );
}

export default TaskCluster;
