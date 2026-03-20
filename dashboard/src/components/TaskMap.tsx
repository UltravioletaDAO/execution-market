/**
 * TaskMap: Location-based task visualization.
 *
 * Uses react-leaflet (already in dashboard dependencies) to display
 * tasks on an interactive map. Pin colors by category.
 * Click marker to navigate to task detail.
 */

import { useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { useTranslation } from 'react-i18next'
import type { Task, TaskCategory } from '../types/database'

// Fix default marker icon path issue with Leaflet + bundlers
import 'leaflet/dist/leaflet.css'

// Ensure default icon images are loaded correctly
// Leaflet bundler workaround: _getIconUrl is a private method not exposed in the type definitions,
// but must be deleted to prevent broken icon URLs when using module bundlers (Vite/Webpack).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface TaskMapProps {
  tasks: Task[]
  onTaskClick?: (task: Task) => void
  className?: string
}

// Color mapping for task categories
const CATEGORY_COLORS: Record<string, string> = {
  physical_presence: '#EF4444',  // red
  knowledge_access: '#3B82F6',   // blue
  human_authority: '#8B5CF6',    // purple
  simple_action: '#10B981',      // green
  digital_physical: '#F59E0B',   // amber
  data_processing: '#06B6D4',    // cyan
  research: '#6366F1',           // indigo
  content_generation: '#EC4899', // pink
  code_execution: '#14B8A6',     // teal
  api_integration: '#F97316',    // orange
  multi_step_workflow: '#84CC16',// lime
}

function createCategoryIcon(category: string): L.DivIcon {
  const color = CATEGORY_COLORS[category] || '#6B7280'
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: 24px; height: 24px; border-radius: 50%;
      background: ${color}; border: 2px solid white;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  })
}

// Category display labels (fallback for non-i18n contexts)
const CATEGORY_LABELS: Record<string, string> = {
  physical_presence: 'Physical Presence',
  knowledge_access: 'Knowledge Access',
  human_authority: 'Human Authority',
  simple_action: 'Simple Action',
  digital_physical: 'Digital-Physical',
  data_processing: 'Data Processing',
  research: 'Research',
  content_generation: 'Content Generation',
  code_execution: 'Code Execution',
  api_integration: 'API Integration',
  multi_step_workflow: 'Multi-Step Workflow',
}

export function TaskMap({ tasks, onTaskClick, className = '' }: TaskMapProps) {
  const { t } = useTranslation()

  // Filter tasks that have location coordinates
  const geoTasks = useMemo(() => {
    return tasks.filter((task) => {
      return task.location != null && !isNaN(task.location.lat) && !isNaN(task.location.lng)
    })
  }, [tasks])

  // Calculate map center from tasks, default to world center
  const center = useMemo<[number, number]>(() => {
    if (geoTasks.length === 0) return [20, 0]
    const avgLat =
      geoTasks.reduce((sum, t) => sum + (t.location?.lat ?? 0), 0) /
      geoTasks.length
    const avgLng =
      geoTasks.reduce((sum, t) => sum + (t.location?.lng ?? 0), 0) /
      geoTasks.length
    return [avgLat, avgLng]
  }, [geoTasks])

  const zoom = geoTasks.length === 0 ? 2 : geoTasks.length === 1 ? 13 : 5

  if (geoTasks.length === 0) {
    return (
      <div className={`bg-white rounded-xl border border-slate-200 p-8 text-center ${className}`}>
        <svg className="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <p className="text-sm text-slate-500">
          {t('taskMap.noLocationTasks', 'No tasks with location data available.')}
        </p>
      </div>
    )
  }

  return (
    <div className={`bg-white rounded-xl border border-slate-200 overflow-hidden ${className}`}>
      {/* Legend */}
      <div className="px-4 py-2 border-b border-slate-100 flex items-center gap-3 flex-wrap">
        <span className="text-xs font-medium text-slate-500">
          {t('taskMap.legend', 'Categories')}:
        </span>
        {Object.entries(CATEGORY_COLORS)
          .filter(([cat]) => geoTasks.some((t) => t.category === cat))
          .map(([cat, color]) => (
            <div key={cat} className="flex items-center gap-1">
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-slate-500">
                {CATEGORY_LABELS[cat] || cat}
              </span>
            </div>
          ))}
      </div>

      {/* Map */}
      <div style={{ height: 420 }}>
        <MapContainer
          center={center}
          zoom={zoom}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {geoTasks.map((task) => {
            const lat = task.location!.lat
            const lng = task.location!.lng
            const icon = createCategoryIcon(task.category)

            return (
              <Marker key={task.id} position={[lat, lng]} icon={icon}>
                <Popup>
                  <div className="max-w-[200px]">
                    <h4 className="font-semibold text-sm text-slate-900 mb-1 line-clamp-2">
                      {task.title}
                    </h4>
                    <div className="text-xs text-slate-500 mb-1">
                      {CATEGORY_LABELS[task.category] || task.category}
                    </div>
                    <div className="text-xs font-medium text-green-600 mb-2">
                      ${(task.bounty_usd ?? 0).toFixed(2)} USDC
                    </div>
                    {onTaskClick && (
                      <button
                        onClick={() => onTaskClick(task)}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {t('taskMap.viewDetails', 'View Details')} &rarr;
                      </button>
                    )}
                  </div>
                </Popup>
              </Marker>
            )
          })}
        </MapContainer>
      </div>
    </div>
  )
}

export default TaskMap
