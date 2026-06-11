import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
  const displayId = preview.peerAddress ?? preview.peerInboxId;
  const displayName = preview.resolvedName || shorten(displayId);
  const avatarLetters = displayId.replace(/^0x/, "").slice(0, 2).toUpperCase();

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-zinc-50 transition-colors border-b border-zinc-100 text-left"
    >
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center shrink-0">
        <span className="text-zinc-600 text-sm font-mono">{avatarLetters}</span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-zinc-900 text-sm font-medium truncate">{displayName}</span>
          {preview.lastMessageAt && (
            <span className="text-zinc-400 text-xs shrink-0 ml-2">
              {formatDistanceToNow(preview.lastMessageAt, { locale: es, addSuffix: false })}
            </span>
          )}
        </div>
        <p className="text-zinc-500 text-sm truncate mt-0.5">
          {preview.lastMessage ?? t("messages.noMessages", "No messages yet")}
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
