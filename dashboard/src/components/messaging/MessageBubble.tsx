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
          ? "bg-zinc-900 text-white rounded-br-md"
          : "bg-zinc-100 text-zinc-900 rounded-bl-md"
      }`}>
        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        <span className={`text-[10px] mt-1 block ${isMine ? "text-zinc-400" : "text-zinc-500"}`}>
          {formatDistanceToNow(message.sentAt, { addSuffix: true, locale: es })}
        </span>
      </div>
    </div>
  );
}
