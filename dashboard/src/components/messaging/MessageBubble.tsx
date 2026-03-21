import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import type { XMTPMessage } from "../../types/xmtp";

interface Props {
  message: XMTPMessage;
  isMine: boolean;
}

export function MessageBubble({ message, isMine }: Props) {
  return (
    <div className={`flex ${isMine ? "justify-end" : "justify-start"} mb-2`}>
      <div className={`max-w-[75%] rounded-2xl px-4 py-2 ${
        isMine
          ? "bg-white text-black rounded-br-md"
          : "bg-white/10 text-white rounded-bl-md"
      }`}>
        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        <span className={`text-[10px] mt-1 block ${isMine ? "text-black/40" : "text-white/40"}`}>
          {formatDistanceToNow(message.sentAt, { addSuffix: true, locale: es })}
        </span>
      </div>
    </div>
  );
}
