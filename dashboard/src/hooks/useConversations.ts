import { useState, useEffect, useCallback } from "react";
import { useXMTP } from "../context/XMTPContext";
import type { ConversationPreview } from "../types/xmtp";

const LAST_READ_KEY = "xmtp_last_read";
const PEER_ADDRESS_KEY = "xmtp_peer_address_map";

/** Read the last-read timestamp map from localStorage */
function getLastReadMap(): Record<string, number> {
  try {
    const raw = localStorage.getItem(LAST_READ_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** inboxId → Ethereum address mapping (populated when we open a DM by address). */
function getPeerAddressMap(): Record<string, string> {
  try {
    const raw = localStorage.getItem(PEER_ADDRESS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function rememberPeerAddress(peerInboxId: string, peerAddress: string) {
  const map = getPeerAddressMap();
  map[peerInboxId.toLowerCase()] = peerAddress.toLowerCase();
  localStorage.setItem(PEER_ADDRESS_KEY, JSON.stringify(map));
}

/** Mark a conversation as read (persist to localStorage) */
export function markConversationRead(peerInboxId: string) {
  const map = getLastReadMap();
  map[peerInboxId.toLowerCase()] = Date.now();
  localStorage.setItem(LAST_READ_KEY, JSON.stringify(map));
}

function computeUnreadCount(peerInboxId: string, lastMessageAt: Date | null): number {
  if (!lastMessageAt) return 0;
  const map = getLastReadMap();
  const lastRead = map[peerInboxId.toLowerCase()] ?? 0;
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
      const addressMap = getPeerAddressMap();
      const items: ConversationPreview[] = [];

      for (const convo of convos) {
        // DMs expose peerInboxId() — groups don't. Skip groups for now (DM-only UI).
        if (typeof convo.peerInboxId !== "function") continue;

        let peerInboxId: string;
        try {
          peerInboxId = await convo.peerInboxId();
        } catch {
          continue;
        }

        // Prefer the built-in lastMessage field (avoids an extra round-trip).
        const lastMsg = convo.lastMessage ?? (await convo.messages({ limit: 1 }))[0];
        const lastMessageAt = lastMsg?.sentAt ?? null;

        items.push({
          id: convo.id,
          peerInboxId,
          peerAddress: addressMap[peerInboxId.toLowerCase()],
          lastMessage: lastMsg
            ? typeof lastMsg.content === "string"
              ? lastMsg.content
              : "[Attachment]"
            : null,
          lastMessageAt,
          unreadCount: computeUnreadCount(peerInboxId, lastMessageAt),
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

  // Stream new conversations. In v5 `stream()` returns a Promise<AsyncIterable>.
  useEffect(() => {
    if (!client) return;
    let cancelled = false;
    const run = async () => {
      try {
        const stream = await client.conversations.stream();
        for await (const _ of stream) {
          if (cancelled) break;
          loadConversations();
          void _;
        }
      } catch {
        // Stream ended
      }
    };
    run();
    return () => { cancelled = true; };
  }, [client, loadConversations]);

  return { previews, isLoading, refresh: loadConversations, markConversationRead };
}
