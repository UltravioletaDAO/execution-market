import { useState, useEffect, useCallback } from "react";
import { useFocusEffect } from "expo-router";
import { useXMTP } from "../providers/XMTPProvider";

export interface ConversationPreview {
  id: string;
  peerAddress: string;
  lastMessage: string | null;
  lastMessageAt: Date | null;
  unreadCount: number;
}

export function useConversations() {
  const { client, isConnected } = useXMTP();
  const [previews, setPreviews] = useState<ConversationPreview[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadConversations = useCallback(async () => {
    if (!client) return;
    setIsLoading(true);
    try {
      await client.conversations.sync().catch(() => {});

      const convos = await client.conversations.list();
      const items: ConversationPreview[] = [];

      for (const convo of convos) {
        try {
          // v5: lastMessage is a property on Dm, not a method
          const lastMsg = convo.lastMessage ?? null;

          // v5: peerInboxId() is an async method
          let peerAddress = convo.id;
          if (typeof convo.peerInboxId === "function") {
            try {
              peerAddress = (await convo.peerInboxId()) ?? convo.id;
            } catch {
              // leave as convo.id
            }
          } else if (convo.peerAddress) {
            peerAddress = convo.peerAddress;
          }

          // v5: sentNs (not sentAtNs) — BigInt nanoseconds
          let lastMessageAt: Date | null = null;
          if (lastMsg) {
            const ns = lastMsg.sentNs ?? lastMsg.sentAtNs ?? lastMsg.insertedAtNs;
            if (ns !== undefined && ns !== null) {
              lastMessageAt = new Date(Number(BigInt(ns) / 1000000n));
            } else if (lastMsg.sentAt instanceof Date) {
              lastMessageAt = lastMsg.sentAt;
            }
          }

          // v5: content() is a method, not a property
          let lastMessageContent: string | null = null;
          if (lastMsg) {
            try {
              const raw = typeof lastMsg.content === "function"
                ? lastMsg.content()
                : lastMsg.content;
              lastMessageContent =
                typeof raw === "string"
                  ? raw
                  : typeof raw?.text === "string"
                  ? raw.text
                  : lastMsg.fallback ?? null;
            } catch {
              lastMessageContent = lastMsg.fallback ?? null;
            }
          }

          items.push({
            id: convo.id,
            peerAddress,
            lastMessage: lastMessageContent,
            lastMessageAt,
            unreadCount: 0,
          });
        } catch {
          // skip broken conversations
        }
      }

      items.sort((a, b) => (b.lastMessageAt?.getTime() ?? 0) - (a.lastMessageAt?.getTime() ?? 0));
      setPreviews(items);
    } catch (err) {
      console.error("[XMTP] Failed to load conversations:", err);
    } finally {
      setIsLoading(false);
    }
  }, [client]);

  // Load on connect
  useEffect(() => {
    if (isConnected) loadConversations();
  }, [isConnected, loadConversations]);

  // Reload every time the Messages tab comes into focus
  useFocusEffect(
    useCallback(() => {
      if (isConnected) loadConversations();
    }, [isConnected, loadConversations])
  );

  // Stream new conversations
  useEffect(() => {
    if (!client) return;
    let unsubscribe: (() => void) | null = null;

    client.conversations
      .stream(() => { loadConversations(); })
      .then((unsub: () => void) => { unsubscribe = unsub; })
      .catch(() => {});

    return () => { unsubscribe?.(); };
  }, [client, loadConversations]);

  return { previews, isLoading, refresh: loadConversations };
}
