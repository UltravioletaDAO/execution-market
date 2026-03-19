import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useXMTP } from "../../context/XMTPContext";

interface Props {
  walletAddress: string;
  onStartChat: (address: string) => void;
  label?: string;
}

export function DirectMessageButton({ walletAddress, onStartChat, label }: Props) {
  const { t } = useTranslation();
  const { client, isConnected } = useXMTP();
  const displayLabel = label || t('messaging.sendMessage', 'Send Message');
  const [canMessage, setCanMessage] = useState<boolean | null>(null);

  useEffect(() => {
    if (!client || !walletAddress) return;
    // Check if peer has XMTP enabled
    const check = async () => {
      try {
        const result = await client.canMessage([walletAddress]);
        setCanMessage(result?.[walletAddress] ?? false);
      } catch {
        setCanMessage(false);
      }
    };
    check();
  }, [client, walletAddress]);

  if (!isConnected) return null;

  return (
    <button
      onClick={() => canMessage && onStartChat(walletAddress)}
      disabled={!canMessage}
      className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      title={canMessage === false ? t('messaging.xmtpNotEnabled', 'This user does not have XMTP enabled') : t('messaging.sendViaXmtp', 'Send message via XMTP')}
    >
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
      </svg>
      <span>{displayLabel}</span>
    </button>
  );
}
