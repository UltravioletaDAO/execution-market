export interface ConversationPreview {
  id: string;
  peerAddress: string;
  lastMessage: string | null;
  lastMessageAt: Date | null;
  unreadCount: number;
  resolvedName?: string;
}

export interface XMTPMessage {
  id: string;
  content: string;
  senderAddress: string;
  sentAt: Date;
  conversationId: string;
}
