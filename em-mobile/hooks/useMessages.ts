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
          setMessages(msgs.reverse().map(normalize));
        }
      } catch (err) {
        console.error("[XMTP] Init conversation failed:", err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    init();
    return () => { cancelled = true; };
  }, [client, peerAddress]);

  useEffect(() => {
    const convo = conversationRef.current;
    if (!convo) return;
    let cancelled = false;
    const stream = async () => {
      try {
        for await (const msg of await convo.streamMessages()) {
          if (cancelled) break;
          setMessages(prev => [...prev, normalize(msg)]);
        }
      } catch { /* stream ended */ }
    };
    stream();
    return () => { cancelled = true; };
  }, [conversationRef.current]);

  const sendMessage = useCallback(async (text: string) => {
    const convo = conversationRef.current;
    if (!convo || !text.trim()) return;
    setIsSending(true);
    try {
      await convo.send(text);
    } finally {
      setIsSending(false);
    }
  }, []);

  return { messages, isLoading, isSending, sendMessage };
}

function normalize(msg: any): XMTPMessage {
  return {
    id: msg.id,
    content: typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content),
    senderAddress: msg.senderAddress,
    sentAt: msg.sentAt instanceof Date ? msg.sentAt : new Date(msg.sentAt),
  };
}
