import { useEffect, useRef } from "react";
import { useXMTP } from "../context/XMTPContext";

export function useXMTPNotifications() {
  const { client } = useXMTP();
  const notifiedRef = useRef(new Set<string>());

  useEffect(() => {
    if (!client) return;
    let cancelled = false;

    const listen = async () => {
      try {
        for await (const message of await client.conversations.streamAllMessages()) {
          if (cancelled) break;
          if (message.senderAddress === client.address) continue;
          if (notifiedRef.current.has(message.id)) continue;
          notifiedRef.current.add(message.id);

          // Cap set size
          if (notifiedRef.current.size > 1000) {
            const arr = Array.from(notifiedRef.current);
            notifiedRef.current = new Set(arr.slice(-500));
          }

          // Browser notification
          if (Notification.permission === "granted") {
            const content = typeof message.content === "string"
              ? message.content.slice(0, 100)
              : "Nuevo mensaje";
            const shortAddr = `${message.senderAddress.slice(0, 6)}...${message.senderAddress.slice(-4)}`;
            new Notification(`Mensaje de ${shortAddr}`, {
              body: content,
              icon: "/favicon.ico",
            });
          }
        }
      } catch {
        // Stream ended
      }
    };

    // Request notification permission
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }

    listen();
    return () => { cancelled = true; };
  }, [client]);
}
