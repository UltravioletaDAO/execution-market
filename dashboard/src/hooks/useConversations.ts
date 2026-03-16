import { useState, useEffect, useCallback } from "react";
import { useXMTP } from "../context/XMTPContext";
import type { ConversationPreview } from "../types/xmtp";

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
        items.push({
          id: convo.id ?? convo.topic,
          peerAddress: convo.peerAddress,
          lastMessage: lastMsg
            ? typeof lastMsg.content === "string"
              ? lastMsg.content
              : "[Attachment]"
            : null,
          lastMessageAt: lastMsg?.sentAt ?? null,
          unreadCount: 0, // Computed from localStorage in useXMTPNotifications
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

  return { previews, isLoading, refresh: loadConversations };
}
