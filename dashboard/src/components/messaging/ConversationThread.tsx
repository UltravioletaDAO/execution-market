import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useMessages } from "../../hooks/useMessages";
import { useXMTP } from "../../context/XMTPContext";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";

interface Props {
  peerInboxId: string;
  peerAddress?: string;
  onBack: () => void;
  contextPrefix?: string;
}

function shorten(id: string): string {
  if (id.startsWith("0x") && id.length === 42) return `${id.slice(0, 6)}...${id.slice(-4)}`;
  return id.length > 12 ? `${id.slice(0, 6)}...${id.slice(-4)}` : id;
}

export function ConversationThread({ peerInboxId, peerAddress, onBack, contextPrefix }: Props) {
  const { t } = useTranslation();
  const { inboxId } = useXMTP();
  const { messages, isLoading, isSending, sendMessage, loadMore } = useMessages(peerInboxId);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isFirstSend = useRef(true);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const displayId = peerAddress ?? peerInboxId;
  const shortLabel = shorten(displayId);
  const avatarLetters = displayId.replace(/^0x/, "").slice(0, 2).toUpperCase();

  const handleSend = async (text: string) => {
    const prefixed = isFirstSend.current && contextPrefix && messages.length === 0
      ? `${contextPrefix}\n\n${text}`
      : text;
    isFirstSend.current = false;
    await sendMessage(prefixed);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-zinc-200">
        <button onClick={onBack} className="text-zinc-500 hover:text-zinc-900">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center">
          <span className="text-zinc-600 text-xs font-mono">{avatarLetters}</span>
        </div>
        <span className="text-zinc-900 text-sm font-medium">{shortLabel}</span>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-1"
        onScroll={(e) => {
          if ((e.target as HTMLDivElement).scrollTop === 0 && messages.length > 0) {
            loadMore();
          }
        }}
      >
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-zinc-200 border-t-zinc-600 rounded-full animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-zinc-500 text-sm">{t("messages.sendFirstMessage", "Send the first message")}</p>
          </div>
        ) : (
          messages.map(msg => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isMine={inboxId != null && msg.senderInboxId === inboxId}
            />
          ))
        )}
      </div>

      {/* Input */}
      <MessageInput onSend={handleSend} isSending={isSending} />
    </div>
  );
}
