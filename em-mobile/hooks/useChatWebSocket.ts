import { useCallback, useEffect, useRef, useState } from "react";
import { AppState, type AppStateStatus } from "react-native";
import { supabase } from "../lib/supabase";

const API_URL = process.env.EXPO_PUBLIC_API_URL || "https://api.execution.market";
const WS_URL = API_URL.replace(/^http/, "ws");

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

export interface ChatMessage {
  type: "message" | "system" | "error";
  nick: string;
  text: string;
  source: "irc" | "mobile" | "xmtp" | "system";
  timestamp: string;
  task_id: string;
}

export interface ChatHistory {
  messages: ChatMessage[];
  channel: string;
  task_id: string;
  connected_users: number;
}

interface ChatError {
  type: "error";
  code: string;
  text: string;
}

// ------------------------------------------------------------------
// Hook
// ------------------------------------------------------------------

export function useChatWebSocket(taskId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef(1000);
  const mountedRef = useRef(true);
  const queueRef = useRef<string[]>([]);

  // ------------------------------------------------------------------
  // Connect
  // ------------------------------------------------------------------

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (!taskId) return;

    setIsConnecting(true);
    setError(null);

    // Get auth token
    let token = "";
    try {
      const { data } = await supabase.auth.getSession();
      token = data?.session?.access_token ?? "";
    } catch {
      setError("auth_failed");
      setIsConnecting(false);
      return;
    }

    if (!token) {
      setError("auth_failed");
      setIsConnecting(false);
      return;
    }

    const url = `${WS_URL}/ws/chat/${taskId}?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        backoffRef.current = 1000; // reset backoff

        // Flush queued messages
        while (queueRef.current.length > 0) {
          const queued = queueRef.current.shift();
          if (queued && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "message", text: queued }));
          }
        }
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);

          // History payload (first message after connect)
          if (data.messages && Array.isArray(data.messages)) {
            const history = data as ChatHistory;
            setMessages(history.messages);
            return;
          }

          // Error payload
          if (data.type === "error") {
            const err = data as ChatError;
            setError(err.text);
            return;
          }

          // Regular message
          const msg = data as ChatMessage;
          setMessages((prev) => [...prev, msg]);
        } catch {
          // Ignore unparseable messages
        }
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        setIsConnecting(false);
        wsRef.current = null;

        // 4001 = auth failed, 4003 = not authorized, 4004 = feature disabled
        if (event.code >= 4000 && event.code < 4100) {
          setError(event.reason || "connection_rejected");
          return; // Don't reconnect on auth errors
        }

        // Auto-reconnect with exponential backoff
        const delay = backoffRef.current;
        backoffRef.current = Math.min(delay * 2, 30000);
        reconnectTimer.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, delay);
      };

      ws.onerror = () => {
        // onclose will fire after this, handling reconnection
      };
    } catch {
      setIsConnecting(false);
      setError("connection_failed");
    }
  }, [taskId]);

  // ------------------------------------------------------------------
  // Send message
  // ------------------------------------------------------------------

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "message", text: trimmed }));
      } else {
        // Queue for when connection is restored (max 20)
        if (queueRef.current.length < 20) {
          queueRef.current.push(trimmed);
        }
      }
    },
    []
  );

  // ------------------------------------------------------------------
  // Reconnect (manual)
  // ------------------------------------------------------------------

  const reconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    backoffRef.current = 1000;
    connect();
  }, [connect]);

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------

  useEffect(() => {
    mountedRef.current = true;
    connect();

    // Handle app state changes (reconnect when coming back to foreground)
    const handleAppState = (state: AppStateStatus) => {
      if (state === "active" && !wsRef.current) {
        connect();
      }
    };
    const sub = AppState.addEventListener("change", handleAppState);

    return () => {
      mountedRef.current = false;
      sub.remove();
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    messages,
    sendMessage,
    isConnected,
    isConnecting,
    error,
    reconnect,
  };
}
