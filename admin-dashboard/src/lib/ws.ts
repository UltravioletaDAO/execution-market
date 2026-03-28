/**
 * WebSocket client for Execution Market Admin Dashboard.
 *
 * Connects to the MCP server WebSocket endpoint for real-time event streaming.
 * Gracefully degrades when the server does not support WebSocket connections.
 *
 * Server event format (from mcp_server/websocket/server.py):
 *   {
 *     type: "event",
 *     payload: {
 *       event: "TaskCreated" | "PaymentReleased" | ...,
 *       payload: { ... },
 *       room: string | null,
 *       metadata: { event_id, timestamp, version }
 *     },
 *     id: string,
 *     timestamp: string,
 *     correlation_id: string | null
 *   }
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { API_BASE } from './api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface WSEvent {
  /** Server-level message type (e.g. "event", "welcome", "pong") */
  type: string
  /** For type=event, payload contains the WebSocketEvent dict */
  payload: {
    event?: string
    payload?: Record<string, unknown>
    room?: string | null
    metadata?: { event_id: string; timestamp: string; version: string }
  }
  id?: string
  timestamp?: string
  correlation_id?: string | null
}

type EventCallback = (event: WSEvent) => void

// ---------------------------------------------------------------------------
// AdminWebSocket — singleton WebSocket manager
// ---------------------------------------------------------------------------

class AdminWebSocket {
  private ws: WebSocket | null = null
  private listeners = new Map<string, Set<EventCallback>>()
  private globalListeners = new Set<EventCallback>()
  private statusListeners = new Set<(status: ConnectionStatus) => void>()

  private _status: ConnectionStatus = 'disconnected'
  private _lastEvent: WSEvent | null = null
  private _lastEventTime: Date | null = null

  private reconnectAttempt = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private intentionalClose = false

  private readonly maxReconnectDelay = 30_000 // 30s ceiling
  private readonly baseDelay = 1_000 // 1s initial

  // -- Public getters -------------------------------------------------------

  get status(): ConnectionStatus {
    return this._status
  }

  get lastEvent(): WSEvent | null {
    return this._lastEvent
  }

  get lastEventTime(): Date | null {
    return this._lastEventTime
  }

  // -- Connection -----------------------------------------------------------

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.intentionalClose = false
    this.setStatus('connecting')

    const wsUrl = this.deriveWsUrl()

    try {
      this.ws = new WebSocket(wsUrl)
    } catch {
      this.setStatus('error')
      this.scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.reconnectAttempt = 0
      this.setStatus('connected')
      this.startPing()
    }

    this.ws.onmessage = (messageEvent) => {
      try {
        const data: WSEvent = JSON.parse(messageEvent.data)
        this._lastEvent = data
        this._lastEventTime = new Date()
        this.dispatch(data)
      } catch {
        // Ignore unparseable frames
      }
    }

    this.ws.onerror = () => {
      this.setStatus('error')
    }

    this.ws.onclose = () => {
      this.stopPing()
      this.ws = null
      if (!this.intentionalClose) {
        this.setStatus('disconnected')
        this.scheduleReconnect()
      } else {
        this.setStatus('disconnected')
      }
    }
  }

  disconnect(): void {
    this.intentionalClose = true
    this.clearReconnect()
    this.stopPing()
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this.setStatus('disconnected')
  }

  // -- Event subscription ---------------------------------------------------

  /**
   * Listen for a specific event type.
   * For server-level types use the raw type string ("welcome", "pong", etc.).
   * For domain events, use the WebSocketEventType value ("TaskCreated", "PaymentReleased", etc.)
   * or a prefix like "Task" to match all task events.
   */
  on(eventType: string, callback: EventCallback): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType)!.add(callback)
  }

  off(eventType: string, callback: EventCallback): void {
    this.listeners.get(eventType)?.delete(callback)
  }

  /** Listen for ALL incoming messages regardless of type. */
  onAny(callback: EventCallback): void {
    this.globalListeners.add(callback)
  }

  offAny(callback: EventCallback): void {
    this.globalListeners.delete(callback)
  }

  /** Subscribe to connection status changes. */
  onStatus(callback: (status: ConnectionStatus) => void): void {
    this.statusListeners.add(callback)
  }

  offStatus(callback: (status: ConnectionStatus) => void): void {
    this.statusListeners.delete(callback)
  }

  // -- Internals ------------------------------------------------------------

  private deriveWsUrl(): string {
    // VITE_API_URL is typically "https://api.execution.market" or "http://localhost:8000"
    const base = API_BASE.replace(/\/$/, '')
    const wsBase = base.replace(/^http/, 'ws')
    return `${wsBase}/ws`
  }

  private setStatus(s: ConnectionStatus): void {
    if (this._status === s) return
    this._status = s
    for (const cb of this.statusListeners) {
      try { cb(s) } catch { /* swallow */ }
    }
  }

  private dispatch(event: WSEvent): void {
    // Notify global listeners
    for (const cb of this.globalListeners) {
      try { cb(event) } catch { /* swallow */ }
    }

    // Match by server-level type (e.g. "event", "welcome")
    const byType = this.listeners.get(event.type)
    if (byType) {
      for (const cb of byType) {
        try { cb(event) } catch { /* swallow */ }
      }
    }

    // For "event" messages, also dispatch by the domain event name
    if (event.type === 'event' && event.payload?.event) {
      const domainEvent = event.payload.event // e.g. "TaskCreated"
      const byDomain = this.listeners.get(domainEvent)
      if (byDomain) {
        for (const cb of byDomain) {
          try { cb(event) } catch { /* swallow */ }
        }
      }
    }
  }

  private scheduleReconnect(): void {
    this.clearReconnect()
    const delay = Math.min(this.baseDelay * Math.pow(2, this.reconnectAttempt), this.maxReconnectDelay)
    this.reconnectAttempt++
    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  private clearReconnect(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private startPing(): void {
    this.stopPing()
    // Send a ping every 25s to keep the connection alive
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping', payload: {} }))
        } catch { /* ignore */ }
      }
    }, 25_000)
  }

  private stopPing(): void {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }
}

// ---------------------------------------------------------------------------
// Singleton export
// ---------------------------------------------------------------------------

export const adminWS = new AdminWebSocket()

// ---------------------------------------------------------------------------
// React hooks
// ---------------------------------------------------------------------------

/**
 * Core hook: provides connection status and last event.
 * Automatically connects on mount, disconnects when no consumers remain.
 */
export function useWebSocket(): {
  isConnected: boolean
  status: ConnectionStatus
  lastEvent: WSEvent | null
  lastEventTime: Date | null
} {
  const [status, setStatus] = useState<ConnectionStatus>(adminWS.status)
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(adminWS.lastEvent)
  const [lastEventTime, setLastEventTime] = useState<Date | null>(adminWS.lastEventTime)

  useEffect(() => {
    const handleStatus = (s: ConnectionStatus) => setStatus(s)
    const handleEvent = (e: WSEvent) => {
      setLastEvent(e)
      setLastEventTime(new Date())
    }

    adminWS.onStatus(handleStatus)
    adminWS.onAny(handleEvent)

    // Connect if not already
    if (adminWS.status === 'disconnected' || adminWS.status === 'error') {
      adminWS.connect()
    }

    return () => {
      adminWS.offStatus(handleStatus)
      adminWS.offAny(handleEvent)
    }
  }, [])

  return {
    isConnected: status === 'connected',
    status,
    lastEvent,
    lastEventTime,
  }
}

/**
 * Auto-invalidate React Query caches when relevant WebSocket events arrive.
 *
 * Event-to-query-key mapping:
 *   Task*       -> ['tasks'], ['phantom-tasks'], ['stats']
 *   Submission* -> ['tasks']
 *   Payment*    -> ['payments'], ['payment-stats'], ['accrued-fees']
 *   config.*    -> ['config']
 */
export function useWebSocketInvalidation(): void {
  const queryClient = useQueryClient()
  const handlerRef = useRef<EventCallback | null>(null)

  const invalidate = useCallback(
    (keys: string[]) => {
      for (const key of keys) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }
    },
    [queryClient],
  )

  useEffect(() => {
    const handler: EventCallback = (msg) => {
      if (msg.type !== 'event' || !msg.payload?.event) return

      const event = msg.payload.event

      if (event.startsWith('Task')) {
        invalidate(['tasks', 'phantom-tasks', 'stats'])
      } else if (event.startsWith('Submission')) {
        invalidate(['tasks'])
      } else if (event.startsWith('Payment')) {
        invalidate(['payments', 'payment-stats', 'accrued-fees'])
      } else if (event.startsWith('config') || event.startsWith('Config')) {
        invalidate(['config'])
      } else if (event.startsWith('Application') || event.startsWith('Worker')) {
        invalidate(['tasks', 'stats'])
      }
    }

    handlerRef.current = handler
    adminWS.onAny(handler)

    return () => {
      adminWS.offAny(handler)
    }
  }, [invalidate])
}
