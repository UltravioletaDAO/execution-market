import { useState, useEffect, useCallback, useRef } from "react";
import { useXMTP } from "../providers/XMTPProvider";

export interface XMTPMessage {
  id: string;
  content: string;
  senderAddress: string;
  sentAt: Date;
}

/**
 * useMessages — open or create a DM conversation with peerAddress and
 * stream messages using the XMTP v5 native SDK.
 *
 * v5 API differences from v3:
 *   - findOrCreateDmWithIdentity(PublicIdentity) instead of newConversation(address)
 *   - dm.streamMessages(callback) instead of for-await stream
 *   - dm.messages({ limit }) returns array directly
 */
export function useMessages(peerAddress: string | null) {
  const { client } = useXMTP();
  const [messages, setMessages] = useState<XMTPMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const conversationRef = useRef<any>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!client || !peerAddress) return;
    let cancelled = false;

    const init = async () => {
      setIsLoading(true);
      try {
        await client.conversations.sync().catch(() => {});

        // v5: findOrCreateDmWithIdentity takes a PublicIdentity object
        const { PublicIdentity } = await import("@xmtp/react-native-sdk");
        const identity = new PublicIdentity(peerAddress, "ETHEREUM");
        const convo = await client.conversations.findOrCreateDmWithIdentity(identity);
        if (cancelled) return;

        conversationRef.current = convo;
        await convo.sync().catch(() => {});

        const msgs = await convo.messages({ limit: 50 });
        if (!cancelled) {
          setMessages([...msgs].reverse().map(normalizeMessage));
        }

        // v5: streamMessages(callback) — returns unsubscribe fn
        const unsub = await convo.streamMessages((msg: any) => {
          if (!cancelled) {
            setMessages((prev) => {
              // avoid duplicates
              if (prev.some((m) => m.id === msg.id)) return prev;
              return [...prev, normalizeMessage(msg)];
            });
          }
        });
        unsubscribeRef.current = unsub;
      } catch (err) {
        console.error("[XMTP] Init conversation failed:", err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    init();
    return () => {
      cancelled = true;
      unsubscribeRef.current?.();
      unsubscribeRef.current = null;
      conversationRef.current = null;
    };
  }, [client, peerAddress]);

  const sendMessage = useCallback(async (text: string) => {
    const convo = conversationRef.current;
    if (!convo || !text.trim()) return;
    setIsSending(true);
    try {
      await convo.send(text);
    } catch (err) {
      console.error("[XMTP] Send failed:", err);
    } finally {
      setIsSending(false);
    }
  }, []);

  return { messages, isLoading, isSending, sendMessage };
}

function normalizeMessage(msg: any): XMTPMessage {
  let sentAt: Date;
  if (msg.sentAtNs !== undefined && msg.sentAtNs !== null) {
    sentAt = new Date(Number(BigInt(msg.sentAtNs) / 1000000n));
  } else if (msg.sentAt instanceof Date) {
    sentAt = msg.sentAt;
  } else if (msg.sentAt) {
    sentAt = new Date(msg.sentAt);
  } else {
    sentAt = new Date();
  }

  const senderAddress: string =
    msg.senderAddress ?? msg.senderInboxId ?? "unknown";

  return {
    id: msg.id ?? String(Date.now()),
    content:
      typeof msg.content === "string"
        ? msg.content
        : JSON.stringify(msg.content ?? ""),
    senderAddress,
    sentAt,
  };
}
