import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useXMTP } from '../context/XMTPContext'
import { useConversations } from '../hooks/useConversations'
import { ConversationItem } from '../components/messaging/ConversationItem'
import { ConversationThread } from '../components/messaging/ConversationThread'

export function Messages() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { isConnected, isConnecting, connect, error } = useXMTP()
  const { previews, isLoading } = useConversations()
  const [selectedPeer, setSelectedPeer] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const filtered = previews.filter(
    (p) =>
      p.peerAddress.toLowerCase().includes(search.toLowerCase()) ||
      (p.resolvedName?.toLowerCase().includes(search.toLowerCase()) ?? false),
  )

  // Not connected — show connect prompt
  if (!isConnected) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="font-bold text-lg text-gray-900">
            {t('messages.title', 'Messages')}
          </h1>
        </div>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <svg className="w-16 h-16 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
          </svg>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">
            {t('messages.connectTitle', 'Connect to XMTP')}
          </h2>
          <p className="text-gray-500 text-sm mb-6 max-w-md">
            {t('messages.connectDescription', 'Connect your wallet to XMTP to send and receive encrypted messages with other users.')}
          </p>
          {error && (
            <p className="text-red-500 text-sm mb-4">{error}</p>
          )}
          <button
            onClick={connect}
            disabled={isConnecting}
            className="px-6 py-2.5 bg-emerald-500 text-white font-semibold rounded-lg hover:bg-emerald-400 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isConnecting
              ? t('common.loading', 'Loading...')
              : t('messages.connect', 'Connect XMTP')}
          </button>
        </div>
      </div>
    )
  }

  // Mobile: if a peer is selected, show only the thread
  // Desktop: show split layout
  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Page header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="font-bold text-lg text-gray-900">
          {t('messages.title', 'Messages')}
        </h1>
      </div>

      {/* Split layout */}
      <div className="flex bg-white rounded-xl border border-gray-200 overflow-hidden" style={{ height: 'calc(100vh - 180px)' }}>
        {/* Conversation list — hidden on mobile when thread is open */}
        <div className={`w-full md:w-80 lg:w-96 border-r border-gray-200 flex flex-col ${selectedPeer ? 'hidden md:flex' : 'flex'}`}>
          {/* Search */}
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <svg className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('messages.searchPlaceholder', 'Search conversations...')}
                className="w-full bg-gray-50 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-900 placeholder-gray-400 border border-gray-200 focus:border-gray-400 focus:ring-0 outline-none"
              />
            </div>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex justify-center py-12">
                <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-gray-400 text-sm">
                  {search
                    ? t('messages.noResults', 'No results')
                    : t('messages.noConversations', 'No conversations yet')}
                </p>
              </div>
            ) : (
              filtered.map((preview) => (
                <ConversationItem
                  key={preview.peerAddress}
                  preview={preview}
                  onClick={() => setSelectedPeer(preview.peerAddress)}
                />
              ))
            )}
          </div>
        </div>

        {/* Thread panel */}
        <div className={`flex-1 flex flex-col ${selectedPeer ? 'flex' : 'hidden md:flex'}`}>
          {selectedPeer ? (
            <ConversationThread
              peerAddress={selectedPeer}
              onBack={() => setSelectedPeer(null)}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
                </svg>
                <p className="text-gray-400 text-sm">
                  {t('messages.selectConversation', 'Select a conversation to start messaging')}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
