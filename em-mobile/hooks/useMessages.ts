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
 * stream messages using the XMTP v5 browser SDK.
 *
 * @param peerAddress - Ethereum address (0x...) of the conversation peer
 */
export function useMessages(peerAddress: string | null) {
  const { client } = useXMTP();
  const [messages, setMessages] = useState<XMTPMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const conversationRef = useRef<any>(null);
  const [conversation, setConversation] = useState<any>(null);

  useEffect(() => {
    if (!client || !peerAddress) return;
    let cancelled = false;

    const init = async () => {
      setIsLoading(true);
      try {
        // XMTP v5: sync conversations first
        await client.conversations.sync().catch(() => {});

        // v5: use newDmWithIdentifier for EOA addresses
        const convo = await client.conversations.newDmWithIdentifier(
          { identifier: peerAddress, type: "EOA" },
        );
        conversationRef.current = convo;

        // v5: sync the conversation before reading messages
        await convo.sync().catch(() => {});

        const msgs = await convo.messages({ limit: 50 });
        if (!cancelled) {
          setMessages([...msgs].reverse().map(normalizeMessage));
          setConversation(convo);
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
      conversationRef.current = null;
      setConversation(null);
    };
  }, [client, peerAddress]);

  // Stream new messages from the conversation
  useEffect(() => {
    if (!conversation) return;
    let cancelled = false;

    const stream = async () => {
      try {
        const s = await conversation.stream();
        for await (const msg of s) {
          if (cancelled) break;
          setMessages((prev) => [...prev, normalizeMessage(msg)]);
        }
      } catch {
        // Stream ended or not supported
      }
    };

    stream();
    return () => {
      cancelled = true;
    };
  }, [conversation]);

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

/**
 * Normalize an XMTP v5 message to a flat XMTPMessage shape.
 * v5 uses sentAtNs (BigInt nanoseconds) and senderInboxId instead of senderAddress.
 */
function normalizeMessage(msg: any): XMTPMessage {
  // Derive sentAt: v5 uses sentAtNs (BigInt ns), v1/v2 used sentAt (Date)
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

  // Derive sender: v5 uses senderInboxId, v1/v2 used senderAddress
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
