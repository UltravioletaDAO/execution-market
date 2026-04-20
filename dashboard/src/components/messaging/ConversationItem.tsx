import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import type { ConversationPreview } from "../../types/xmtp";

interface Props {
  preview: ConversationPreview;
  onClick: () => void;
}

/** Shorten an Ethereum address or inbox id for display. */
function shorten(id: string): string {
  if (id.startsWith("0x") && id.length === 42) return `${id.slice(0, 6)}...${id.slice(-4)}`;
  // inbox ids are longer hashes — show the first and last 4 chars
  return id.length > 12 ? `${id.slice(0, 6)}...${id.slice(-4)}` : id;
}

export function ConversationItem({ preview, onClick }: Props) {
  const displayId = preview.peerAddress ?? preview.peerInboxId;
  const displayName = preview.resolvedName || shorten(displayId);
  const avatarLetters = displayId.replace(/^0x/, "").slice(0, 2).toUpperCase();

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors border-b border-white/5 text-left"
    >
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
        <span className="text-white/60 text-sm font-mono">{avatarLetters}</span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-white text-sm font-medium truncate">{displayName}</span>
          {preview.lastMessageAt && (
            <span className="text-white/30 text-xs shrink-0 ml-2">
              {formatDistanceToNow(preview.lastMessageAt, { locale: es, addSuffix: false })}
            </span>
          )}
        </div>
        <p className="text-white/40 text-sm truncate mt-0.5">
          {preview.lastMessage ?? "Sin mensajes"}
        </p>
      </div>

      {/* Unread badge */}
      {preview.unreadCount > 0 && (
        <span className="bg-red-600 text-white text-[10px] font-bold rounded-full h-5 min-w-[20px] flex items-center justify-center px-1 shrink-0">
          {preview.unreadCount}
        </span>
      )}
    </button>
  );
}
