import { useEffect, useRef } from "react";
import { useMessages } from "../../hooks/useMessages";
import { useXMTP } from "../../context/XMTPContext";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";

interface Props {
  peerAddress: string;
  onBack: () => void;
  contextPrefix?: string;
}

export function ConversationThread({ peerAddress, onBack, contextPrefix }: Props) {
  const { walletAddress } = useXMTP();
  const { messages, isLoading, isSending, sendMessage, loadMore } = useMessages(peerAddress);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isFirstSend = useRef(true);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const shortAddr = `${peerAddress.slice(0, 6)}...${peerAddress.slice(-4)}`;

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
      <div className="flex items-center gap-3 p-4 border-b border-white/10">
        <button onClick={onBack} className="text-white/50 hover:text-white">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
          <span className="text-white/60 text-xs font-mono">
            {peerAddress.slice(2, 4).toUpperCase()}
          </span>
        </div>
        <span className="text-white text-sm font-medium">{shortAddr}</span>
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
            <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-white/30 text-sm">Envia el primer mensaje</p>
          </div>
        ) : (
          messages.map(msg => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isMine={msg.senderAddress.toLowerCase() === walletAddress?.toLowerCase()}
            />
          ))
        )}
      </div>

      {/* Input */}
      <MessageInput onSend={handleSend} isSending={isSending} />
    </div>
  );
}
