import { useEffect, useRef, useState, useCallback } from "react";
import { useXMTP } from "../context/XMTPContext";

const UNREAD_KEY = "xmtp_unread_count";
const LAST_READ_KEY = "xmtp_last_read";

/** Read persisted total unread count */
function getPersistedUnread(): number {
  try {
    const raw = localStorage.getItem(UNREAD_KEY);
    return raw ? parseInt(raw, 10) || 0 : 0;
  } catch {
    return 0;
  }
}

/** Record that a new unread message arrived for a peer */
function bumpUnreadForPeer(peerAddress: string) {
  try {
    // Increment total unread counter
    const current = getPersistedUnread();
    localStorage.setItem(UNREAD_KEY, String(current + 1));

    // Update per-peer last-message timestamp so useConversations can compute unread
    // We do NOT update last-read here — that only happens when the user opens the conversation
    // The last-read map is in the same localStorage key used by useConversations
    const readMapRaw = localStorage.getItem(LAST_READ_KEY);
    const _readMap: Record<string, number> = readMapRaw ? JSON.parse(readMapRaw) : {};
    // No mutation needed — we just need the map to exist for useConversations
    // to compare against message timestamps. The message timestamp itself is
    // obtained from the XMTP message in useConversations.loadConversations().
  } catch {
    // localStorage unavailable
  }
}

export function useXMTPNotifications() {
  const { client } = useXMTP();
  const notifiedRef = useRef(new Set<string>());
  const [unreadCount, setUnreadCount] = useState(getPersistedUnread);

  /** Reset unread count (call when user views messages page) */
  const clearUnread = useCallback(() => {
    setUnreadCount(0);
    try {
      localStorage.setItem(UNREAD_KEY, "0");
    } catch {
      // ignore
    }
  }, []);

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

          // Track unread count
          bumpUnreadForPeer(message.senderAddress);
          setUnreadCount(getPersistedUnread());

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

  return { unreadCount, clearUnread };
}
