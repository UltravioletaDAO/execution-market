import { useState, useEffect, useCallback, useRef } from "react";
import { useXMTP } from "../providers/XMTPProvider";

export interface XMTPMessage {
  id: string;
  content: string;
  senderAddress: string;
  sentAt: Date;
}

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

        // peerAddress can be:
        //   - an Ethereum address (0x + 40 hex chars) → findOrCreateDmWithIdentity
        //   - a conversation ID (any other format) → findConversation directly
        const isEthAddress = /^0x[0-9a-fA-F]{40}$/.test(peerAddress);
        let convo: any;
        if (isEthAddress) {
          const { PublicIdentity } = await import("@xmtp/react-native-sdk");
          const identity = new PublicIdentity(peerAddress, "ETHEREUM");
          convo = await client.conversations.findOrCreateDmWithIdentity(identity);
        } else {
          // conversation ID from the list — open existing conversation directly
          convo = await client.conversations.findConversation(peerAddress);
        }
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
            try {
              setMessages((prev) => {
                if (prev.some((m) => m.id === msg.id)) return prev;
                return [...prev, normalizeMessage(msg)];
              });
            } catch {
              // IDBDatabase errors during message processing are non-fatal
            }
          }
        });
        if (cancelled) {
          try { unsub(); } catch { /* ignore */ }
        } else {
          unsubscribeRef.current = unsub;
        }
      } catch (err) {
        console.error("[XMTP] Init conversation failed:", err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    init();
    return () => {
      cancelled = true;
      try { unsubscribeRef.current?.(); } catch { /* ignore */ }
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
  // v5: sentNs is a BigInt in nanoseconds (field is sentNs, not sentAtNs)
  let sentAt: Date;
  const nsValue = msg.sentNs ?? msg.sentAtNs ?? msg.insertedAtNs;
  if (nsValue !== undefined && nsValue !== null) {
    sentAt = new Date(Number(BigInt(nsValue) / 1000000n));
  } else if (msg.sentAt instanceof Date) {
    sentAt = msg.sentAt;
  } else if (msg.sentAt) {
    sentAt = new Date(msg.sentAt);
  } else {
    sentAt = new Date();
  }

  // v5: senderInboxId (not senderAddress)
  const senderAddress: string =
    msg.senderAddress ?? msg.senderInboxId ?? "unknown";

  // v5: content() is a METHOD, not a property — call it
  let content = "";
  try {
    const raw = typeof msg.content === "function" ? msg.content() : msg.content;
    content =
      typeof raw === "string"
        ? raw
        : typeof raw?.text === "string"
        ? raw.text
        : JSON.stringify(raw ?? "");
  } catch {
    content = msg.fallback ?? "";
  }

  return {
    id: msg.id ?? String(Date.now()),
    content,
    senderAddress,
    sentAt,
  };
}
