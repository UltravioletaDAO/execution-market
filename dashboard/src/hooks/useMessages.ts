import { useState, useEffect, useCallback, useRef } from "react";
import { useXMTP } from "../context/XMTPContext";
import type { XMTPMessage } from "../types/xmtp";
import type { Conversation, DecodedMessage } from "@xmtp/browser-sdk";

/**
 * Open / resume a DM with `peerInboxId` and stream its messages.
 *
 * XMTP v5 uses inbox IDs (MLS) as the canonical identifier. When navigating
 * from an Ethereum address, resolve it to an inbox ID first via
 * `client.findInboxIdByIdentifier()` and remember the mapping with
 * `rememberPeerAddress()` (see useConversations).
 */
export function useMessages(peerInboxId: string | null) {
  const { client } = useXMTP();
  const [messages, setMessages] = useState<XMTPMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  // Keep conversation in both ref (for callbacks) and state (for effect deps)
  const conversationRef = useRef<Conversation | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);

  // Initialize conversation and load messages
  useEffect(() => {
    if (!client || !peerInboxId) return;
    let cancelled = false;

    const init = async () => {
      setIsLoading(true);
      try {
        const convo = await client.conversations.newDm(peerInboxId);
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
  }, [client, peerInboxId]);

  // Stream new messages
  useEffect(() => {
    if (!conversation) return;
    let cancelled = false;

    const stream = async () => {
      try {
        for await (const msg of conversation.streamMessages()) {
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

function normalizeMessage(msg: DecodedMessage): XMTPMessage {
  return {
    id: msg.id,
    content: typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content),
    senderInboxId: msg.senderInboxId,
    sentAt: msg.sentAt instanceof Date ? msg.sentAt : new Date(msg.sentAt),
    conversationId: msg.conversationId ?? "",
  };
}
