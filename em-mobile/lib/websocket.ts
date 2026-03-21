import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";

const WS_URL = process.env.EXPO_PUBLIC_WS_URL || "wss://api.execution.market/ws";

interface WSMessage {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export function useWebSocket() {
  const { isAuthenticated, executor } = useAuth();
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (!isAuthenticated || !executor?.id) return;

    function connect() {
      const ws = new WebSocket(`${WS_URL}?user_id=${executor!.id}`);

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          handleMessage(msg);
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Reconnect after 5 seconds
        reconnectTimeout.current = setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    }

    connect();

    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [isAuthenticated, executor?.id]);

  function handleMessage(msg: WSMessage) {
    switch (msg.type) {
      case "task.created":
      case "task.updated":
      case "task.assigned":
        queryClient.invalidateQueries({ queryKey: ["tasks"] });
        break;
      case "submission.approved":
      case "submission.rejected":
        queryClient.invalidateQueries({ queryKey: ["tasks", "mine"] });
        break;
      case "payment.released":
        queryClient.invalidateQueries({ queryKey: ["earnings"] });
        queryClient.invalidateQueries({ queryKey: ["tasks", "mine"] });
        break;
      case "reputation.updated":
        // Refetch executor profile
        queryClient.invalidateQueries({ queryKey: ["executor"] });
        break;
    }
  }

  return { connected };
}
