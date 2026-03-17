import { useState, useEffect, useCallback, useRef } from "react";
import { useXMTP } from "../context/XMTPContext";
import type { XMTPMessage } from "../types/xmtp";

export function useMessages(peerAddress: string | null) {
  const { client } = useXMTP();
  const [messages, setMessages] = useState<XMTPMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  // Keep conversation in both ref (for callbacks) and state (for effect deps)
  const conversationRef = useRef<any>(null);
  const [conversation, setConversation] = useState<any>(null);

  // Initialize conversation and load messages
  useEffect(() => {
    if (!client || !peerAddress) return;
    let cancelled = false;

    const init = async () => {
      setIsLoading(true);
      try {
        const convo = await client.conversations.newConversation(peerAddress);
        conversationRef.current = convo;

        const msgs = await convo.messages({ limit: 50 });
        if (!cancelled) {
          setMessages(msgs.reverse().map(normalizeMessage));
          setConversation(convo);
        }
      } catch (err) {
        console.error("[XMTP] Failed to init conversation:", err);
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

  // Stream new messages — depends on `conversation` state, not ref
  useEffect(() => {
    if (!conversation) return;
    let cancelled = false;

    const stream = async () => {
      try {
        for await (const msg of await conversation.streamMessages()) {
          if (cancelled) break;
          setMessages(prev => [...prev, normalizeMessage(msg)]);
        }
      } catch {
        // Stream ended
      }
    };

    stream();
    return () => { cancelled = true; };
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

  const loadMore = useCallback(async () => {
    const convo = conversationRef.current;
    if (!convo || messages.length === 0) return;
    try {
      const older = await convo.messages({
        limit: 50,
        before: messages[0]?.sentAt,
      });
      setMessages(prev => [...older.reverse().map(normalizeMessage), ...prev]);
    } catch (err) {
      console.error("[XMTP] Load more failed:", err);
    }
  }, [messages]);

  return { messages, isLoading, isSending, sendMessage, loadMore };
}

function normalizeMessage(msg: any): XMTPMessage {
  return {
    id: msg.id,
    content: typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content),
    senderAddress: msg.senderAddress,
    sentAt: msg.sentAt instanceof Date ? msg.sentAt : new Date(msg.sentAt),
    conversationId: msg.conversationId ?? "",
  };
}
