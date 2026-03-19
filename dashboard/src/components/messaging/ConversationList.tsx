import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useConversations } from "../../hooks/useConversations";
import { ConversationItem } from "./ConversationItem";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSelectConversation: (peerAddress: string) => void;
}

export function ConversationList({ isOpen, onClose, onSelectConversation }: Props) {
  const { t } = useTranslation();
  const { previews, isLoading } = useConversations();
  const [search, setSearch] = useState("");

  const filtered = previews.filter(p =>
    p.peerAddress.toLowerCase().includes(search.toLowerCase()) ||
    (p.resolvedName?.toLowerCase().includes(search.toLowerCase()) ?? false)
  );

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 w-full sm:w-96 bg-black border-l border-white/10 z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <h2 className="text-lg font-bold text-white">{t('messages.title')}</h2>
          <button onClick={onClose} className="text-white/50 hover:text-white p-1">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="p-3 border-b border-white/10">
          <div className="relative">
            <svg className="absolute left-3 top-2.5 h-4 w-4 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={t('messages.searchPlaceholder')}
              className="w-full bg-white/5 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-white/40 border border-white/10 focus:border-white/30 outline-none"
            />
          </div>
        </div>

        {/* Conversations */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-white/40 text-sm">
                {search ? t('messages.noResults') : t('messages.noConversations')}
              </p>
            </div>
          ) : (
            filtered.map(preview => (
              <ConversationItem
                key={preview.peerAddress}
                preview={preview}
                onClick={() => onSelectConversation(preview.peerAddress)}
              />
            ))
          )}
        </div>
      </div>
    </>
  );
}
