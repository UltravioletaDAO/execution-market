import { useState, useEffect, useCallback } from "react";
import { useXMTP } from "../providers/XMTPProvider";

export interface ConversationPreview {
  id: string;
  // peerAddress is the Ethereum address (EOA identifier) of the peer.
  // In XMTP v5 this is derived from peerInboxId resolution.
  peerAddress: string;
  lastMessage: string | null;
  lastMessageAt: Date | null;
  unreadCount: number;
  resolvedName?: string;
}

export function useConversations() {
  const { client, isConnected } = useXMTP();
  const [previews, setPreviews] = useState<ConversationPreview[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadConversations = useCallback(async () => {
    if (!client) return;
    setIsLoading(true);
    try {
      // XMTP v5: sync first, then list
      await client.conversations.sync().catch(() => {});

      const convos = await client.conversations.list();
      const items: ConversationPreview[] = [];

      for (const convo of convos) {
        try {
          // v5: get the last message
          const lastMsg = await convo.lastMessage().catch(() => null);

          // v5: for DMs, get peer inbox ID then resolve to address
          let peerAddress = convo.id; // fallback to convo ID
          if (typeof convo.peerInboxId === "function") {
            try {
              const peerInboxId = await convo.peerInboxId();
              // Map inboxId back to identifier if possible
              // For EOA wallets the inboxId often encodes the address
              peerAddress = peerInboxId ?? convo.id;
            } catch {
              // leave as convo.id
            }
          } else if (convo.peerAddress) {
            // Legacy v1/v2 compatibility
            peerAddress = convo.peerAddress;
          }

          // v5: sentAtNs is BigInt nanoseconds
          const lastMessageAt = lastMsg
            ? lastMsg.sentAtNs
              ? new Date(Number(BigInt(lastMsg.sentAtNs) / 1000000n))
              : lastMsg.sentAt instanceof Date
              ? lastMsg.sentAt
              : null
            : null;

          const lastMessageContent = lastMsg
            ? typeof lastMsg.content === "string"
              ? lastMsg.content
              : "[Attachment]"
            : null;

          items.push({
            id: convo.id,
            peerAddress,
            lastMessage: lastMessageContent,
            lastMessageAt,
            unreadCount: 0,
          });
        } catch {
          // Skip conversations that fail to load
        }
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
        const s = await client.conversations.stream();
        for await (const _convo of s) {
          if (cancelled) break;
          loadConversations();
        }
      } catch {
        // Stream ended or not supported
      }
    };

    stream();
    return () => {
      cancelled = true;
    };
  }, [client, loadConversations]);

  return { previews, isLoading, refresh: loadConversations };
}
