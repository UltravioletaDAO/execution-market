/**
 * ConnectionStatus — compact WebSocket status indicator for the admin header.
 *
 * States:
 *   connected   -> green dot + "Live"
 *   connecting  -> yellow dot + "Connecting..."
 *   disconnected / error -> gray dot + "Offline"
 *
 * Tooltip shows last event timestamp when available.
 */

import { useState, useRef, useEffect } from 'react'
import { useWebSocket } from '../lib/ws'
import type { ConnectionStatus as Status } from '../lib/ws'

const STATUS_CONFIG: Record<Status, { color: string; label: string; ring: string }> = {
  connected:    { color: 'bg-green-500', label: 'Live',           ring: 'ring-green-500/30' },
  connecting:   { color: 'bg-yellow-500', label: 'Connecting...', ring: 'ring-yellow-500/30' },
  disconnected: { color: 'bg-gray-500',  label: 'Offline',        ring: 'ring-gray-500/30' },
  error:        { color: 'bg-gray-500',  label: 'Offline',        ring: 'ring-gray-500/30' },
}

function formatTime(date: Date | null): string {
  if (!date) return 'No events received'
  const diff = Math.round((Date.now() - date.getTime()) / 1000)
  if (diff < 5) return 'Just now'
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return date.toLocaleTimeString()
}

export default function ConnectionStatus() {
  const { status, lastEventTime } = useWebSocket()
  const [showTooltip, setShowTooltip] = useState(false)
  const [, setTick] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const config = STATUS_CONFIG[status]

  // Refresh the relative timestamp every 10s while tooltip is visible
  useEffect(() => {
    if (showTooltip && lastEventTime) {
      intervalRef.current = setInterval(() => setTick((t) => t + 1), 10_000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [showTooltip, lastEventTime])

  return (
    <div
      className="relative inline-flex items-center gap-1.5 cursor-default select-none"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Dot with pulse ring for connected state */}
      <span className="relative flex h-2.5 w-2.5">
        {status === 'connected' && (
          <span
            className={`absolute inset-0 rounded-full ${config.color} opacity-40 animate-ping`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${config.color}`} />
      </span>

      <span className="text-xs text-gray-400">{config.label}</span>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute top-full right-0 mt-2 px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-xs text-gray-300 whitespace-nowrap z-50 shadow-lg">
          <div>WebSocket: {status}</div>
          <div className="text-gray-400 mt-0.5">Last event: {formatTime(lastEventTime)}</div>
        </div>
      )}
    </div>
  )
}
