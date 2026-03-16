import { useState, useEffect } from "react";
import { api } from "../services/api";
import { useXMTPMiniApp } from "../context/XMTPMiniAppProvider";
import type { PaymentEvent } from "../services/types";

const EXPLORER_URLS: Record<string, string> = {
  base: "https://basescan.org/tx/",
  ethereum: "https://etherscan.io/tx/",
  polygon: "https://polygonscan.com/tx/",
  arbitrum: "https://arbiscan.io/tx/",
  avalanche: "https://snowtrace.io/tx/",
  optimism: "https://optimistic.etherscan.io/tx/",
  celo: "https://celoscan.io/tx/",
  monad: "https://explorer.monad.xyz/tx/",
};

export function Payments() {
  const { walletAddress } = useXMTPMiniApp();
  const [payments, setPayments] = useState<PaymentEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!walletAddress) {
      setIsLoading(false);
      return;
    }
    api.get<any>(`/api/v1/payments/history`, { wallet: walletAddress, limit: "20" })
      .then((data) => setPayments(Array.isArray(data) ? data : data.payments ?? []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [walletAddress]);

  const totalEarned = payments.reduce((sum, p) => sum + (p.amount ?? 0), 0);

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="px-4 pt-4">
      <h1 className="text-white text-2xl font-bold mb-4">Pagos</h1>

      {/* Total earnings */}
      <div className="p-4 bg-white/5 rounded-xl mb-6">
        <p className="text-white/40 text-xs">Total Ganado</p>
        <p className="text-white text-3xl font-bold mt-1">${totalEarned.toFixed(2)}</p>
        <p className="text-white/40 text-sm">USDC</p>
      </div>

      {/* Payment history */}
      {payments.length === 0 ? (
        <p className="text-white/40 text-center py-8">No hay pagos registrados</p>
      ) : (
        <div className="space-y-2">
          {payments.map((p) => {
            const explorerBase = EXPLORER_URLS[p.chain] ?? "https://blockscan.com/tx/";
            const shortHash = p.tx_hash ? `${p.tx_hash.slice(0, 10)}...` : "\u2014";
            return (
              <div key={p.id} className="p-3 bg-white/5 rounded-xl flex items-center justify-between">
                <div>
                  <p className="text-white text-sm font-medium">+${(p.amount ?? 0).toFixed(2)} USDC</p>
                  <p className="text-white/40 text-xs capitalize">{p.chain}</p>
                </div>
                {p.tx_hash && (
                  <a
                    href={`${explorerBase}${p.tx_hash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-white/30 text-xs hover:text-white/60"
                  >
                    {shortHash}
                  </a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
