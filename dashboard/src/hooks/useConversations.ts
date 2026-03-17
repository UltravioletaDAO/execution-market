import { useState, useEffect, useCallback } from "react";
import { useXMTP } from "../context/XMTPContext";
import type { ConversationPreview } from "../types/xmtp";

const LAST_READ_KEY = "xmtp_last_read";

/** Read the last-read timestamp map from localStorage */
function getLastReadMap(): Record<string, number> {
  try {
    const raw = localStorage.getItem(LAST_READ_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** Mark a conversation as read (persist to localStorage) */
export function markConversationRead(peerAddress: string) {
  const map = getLastReadMap();
  map[peerAddress.toLowerCase()] = Date.now();
  localStorage.setItem(LAST_READ_KEY, JSON.stringify(map));
}

/** Compute unread count: 1 if latest message is after last-read, else 0 */
function computeUnreadCount(peerAddress: string, lastMessageAt: Date | null): number {
  if (!lastMessageAt) return 0;
  const map = getLastReadMap();
  const lastRead = map[peerAddress.toLowerCase()] ?? 0;
  return lastMessageAt.getTime() > lastRead ? 1 : 0;
}

export function useConversations() {
  const { client, isConnected } = useXMTP();
  const [previews, setPreviews] = useState<ConversationPreview[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadConversations = useCallback(async () => {
    if (!client) return;
    setIsLoading(true);
    try {
      const convos = await client.conversations.list();
      const items: ConversationPreview[] = [];

      for (const convo of convos) {
        const messages = await convo.messages({ limit: 1 });
        const lastMsg = messages[0];
        const lastMessageAt = lastMsg?.sentAt ?? null;
        items.push({
          id: convo.id ?? convo.topic,
          peerAddress: convo.peerAddress,
          lastMessage: lastMsg
            ? typeof lastMsg.content === "string"
              ? lastMsg.content
              : "[Attachment]"
            : null,
          lastMessageAt,
          unreadCount: computeUnreadCount(convo.peerAddress, lastMessageAt),
        });
      }

      items.sort((a, b) => {
        const ta = a.lastMessageAt?.getTime() ?? 0;
        const tb = b.lastMessageAt?.getTime() ?? 0;
        return tb - ta;
      });

      setPreviews(items);
    } catch (err) {
      console.error("[XMTP] Failed to load conversations:", err);
    } finally {
      setIsLoading(false);
    }
  }, [client]);

  useEffect(() => {
    if (isConnected) loadConversations();
  }, [isConnected, loadConversations]);

  // Stream new conversations
  useEffect(() => {
    if (!client) return;
    let cancelled = false;
    const stream = async () => {
      try {
        for await (const _convo of await client.conversations.stream()) {
          if (cancelled) break;
          loadConversations();
        }
      } catch {
        // Stream ended
      }
    };
    stream();
    return () => { cancelled = true; };
  }, [client, loadConversations]);

  return { previews, isLoading, refresh: loadConversations, markConversationRead };
}
