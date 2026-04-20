export interface ConversationPreview {
  id: string;
  peerInboxId: string;
  /** Resolved Ethereum address for display, when available. */
  peerAddress?: string;
  lastMessage: string | null;
  lastMessageAt: Date | null;
  unreadCount: number;
  resolvedName?: string;
}

export interface XMTPMessage {
  id: string;
  content: string;
  senderInboxId: string;
  sentAt: Date;
  conversationId: string;
}
