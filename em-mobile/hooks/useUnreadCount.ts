import { useState, useEffect, useCallback } from "react";
import { useXMTP } from "../providers/XMTPProvider";

export function useUnreadCount() {
  const { client } = useXMTP();
  const [totalUnread, setTotalUnread] = useState(0);

  const computeUnread = useCallback(async () => {
    if (!client) return;
    try {
      const AsyncStorage = (await import("@react-native-async-storage/async-storage")).default;
      const convos = await client.conversations.list();
      let total = 0;
      for (const convo of convos) {
        const lastReadKey = `xmtp_last_read_${convo.id ?? convo.topic}`;
        const lastReadStr = await AsyncStorage.getItem(lastReadKey);
        const lastRead = lastReadStr ? new Date(lastReadStr) : new Date(0);
        const messages = await convo.messages({ after: lastRead });
        const unread = messages.filter((m: any) => m.senderAddress !== client.address).length;
        total += unread;
      }
      setTotalUnread(total);
    } catch (err) {
      console.error("[XMTP] Unread count error:", err);
    }
  }, [client]);

  useEffect(() => {
    computeUnread();
    const interval = setInterval(computeUnread, 30_000);
    return () => clearInterval(interval);
  }, [computeUnread]);

  const markAsRead = useCallback(async (conversationId: string) => {
    try {
      const AsyncStorage = (await import("@react-native-async-storage/async-storage")).default;
      await AsyncStorage.setItem(`xmtp_last_read_${conversationId}`, new Date().toISOString());
      setTotalUnread(prev => Math.max(0, prev - 1));
    } catch { /* ignore */ }
  }, []);

  return { totalUnread, markAsRead, refresh: computeUnread };
}
