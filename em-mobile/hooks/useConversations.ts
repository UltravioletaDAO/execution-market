import { useState, useEffect, useCallback } from "react";
import { useFocusEffect } from "expo-router";
import { useXMTP } from "../providers/XMTPProvider";

export interface ConversationPreview {
  /** XMTP conversation ID — used for navigation */
  convoId: string;
  /** Resolved ETH address (0x...) or abbreviated inbox ID for display */
  peerAddress: string;
  lastMessage: string | null;
  lastMessageAt: Date | null;
  unreadCount: number;
}

/** Try to resolve an XMTP inbox ID to the first associated ETH address. */
async function resolveInboxIdToAddress(
  client: any,
  inboxId: string
): Promise<string> {
  try {
    const states: any[] = await client.inboxStates(false, [inboxId]);
    const state = states?.[0];
    // InboxState has an `identifiers` array of PublicIdentity objects
    const ethIdentifier = state?.identifiers?.find(
      (id: any) => id.identifierType === "ETHEREUM" || id.identifierKind === "ETHEREUM"
    );
    if (ethIdentifier?.identifier) return ethIdentifier.identifier;
    // fallback: first identifier whatever type
    if (state?.identifiers?.[0]?.identifier) return state.identifiers[0].identifier;
  } catch {
    // ignore
  }
  // fallback: show abbreviated inbox ID
  return `${inboxId.slice(0, 6)}...${inboxId.slice(-4)}`;
}

export function useConversations() {
  const { client, isConnected } = useXMTP();
  const [previews, setPreviews] = useState<ConversationPreview[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadConversations = useCallback(async () => {
    if (!client) return;
    setIsLoading(true);
    try {
      await client.conversations.sync().catch(() => {
        // IDBDatabase errors during sync are non-fatal
      });

      const convos = await client.conversations.list();
      const items: ConversationPreview[] = [];

      for (const convo of convos) {
        try {
          // v5: lastMessage is a property on Dm (set in constructor)
          const lastMsg = convo.lastMessage ?? null;

          // v5: peerInboxId() is async — get inbox ID then resolve to ETH address
          let peerAddress = `${convo.id.slice(0, 6)}...${convo.id.slice(-4)}`;
          if (typeof convo.peerInboxId === "function") {
            try {
              const inboxId: string = await convo.peerInboxId();
              if (inboxId) {
                peerAddress = await resolveInboxIdToAddress(client, inboxId);
              }
            } catch {
              // leave abbreviated convo.id
            }
          } else if (convo.peerAddress) {
            peerAddress = convo.peerAddress;
          }

          // v5: sentNs (BigInt nanoseconds)
          let lastMessageAt: Date | null = null;
          if (lastMsg) {
            const ns = lastMsg.sentNs ?? lastMsg.sentAtNs ?? lastMsg.insertedAtNs;
            if (ns != null) {
              lastMessageAt = new Date(Number(BigInt(ns) / 1000000n));
            } else if (lastMsg.sentAt instanceof Date) {
              lastMessageAt = lastMsg.sentAt;
            }
          }

          // v5: content() is a method
          let lastMessageContent: string | null = null;
          if (lastMsg) {
            try {
              const raw = typeof lastMsg.content === "function"
                ? lastMsg.content()
                : lastMsg.content;
              lastMessageContent =
                typeof raw === "string" && raw
                  ? raw
                  : typeof raw?.text === "string" && raw.text
                  ? raw.text
                  : lastMsg.fallback ?? null;
            } catch {
              lastMessageContent = lastMsg.fallback ?? null;
            }
          }

          items.push({
            convoId: convo.id,
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
      __DEV__ && console.error("[XMTP] Failed to load conversations:", err);
    } finally {
      setIsLoading(false);
    }
  }, [client]);

  useEffect(() => {
    if (isConnected) loadConversations();
  }, [isConnected, loadConversations]);

  useFocusEffect(
    useCallback(() => {
      if (isConnected) loadConversations();
    }, [isConnected, loadConversations])
  );

  useEffect(() => {
    if (!client) return;
    let unsubscribe: (() => void) | null = null;
    let cancelled = false;
    client.conversations
      .stream(() => {
        if (!cancelled) loadConversations();
      })
      .then((unsub: () => void) => {
        if (cancelled) {
          // Component unmounted before stream connected — clean up immediately
          try { unsub(); } catch { /* ignore */ }
        } else {
          unsubscribe = unsub;
        }
      })
      .catch((err: any) => {
        // IDBDatabase "connection is closing" errors are expected during teardown
        if (!cancelled) {
          __DEV__ && console.warn("[XMTP] Conversation stream error:", err?.message ?? err);
        }
      });
    return () => {
      cancelled = true;
      try { unsubscribe?.(); } catch { /* ignore */ }
    };
  }, [client, loadConversations]);

  return { previews, isLoading, refresh: loadConversations };
}
