import { useState, useEffect } from "react";
import { api } from "../services/api";
import { useXMTPMiniApp } from "../context/XMTPMiniAppProvider";
import type { Executor, ReputationScore } from "../services/types";

export function Profile() {
  const { walletAddress } = useXMTPMiniApp();
  const [executor, setExecutor] = useState<Executor | null>(null);
  const [reputation, setReputation] = useState<ReputationScore | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!walletAddress) {
      setIsLoading(false);
      return;
    }
    loadProfile();
  }, [walletAddress]);

  async function loadProfile() {
    setIsLoading(true);
    try {
      const [exec, rep] = await Promise.allSettled([
        api.get<Executor>(`/api/v1/workers/by-wallet/${walletAddress}`),
        api.get<ReputationScore>(`/api/v1/reputation/${walletAddress}`),
      ]);
      if (exec.status === "fulfilled") setExecutor(exec.value);
      if (rep.status === "fulfilled") setReputation(rep.value);
    } finally {
      setIsLoading(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  if (!walletAddress) {
    return (
      <div className="px-4 pt-8 text-center">
        <p className="text-white/60">Conecta tu wallet para ver tu perfil</p>
      </div>
    );
  }

  const shortAddr = `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}`;

  return (
    <div className="px-4 pt-4">
      <h1 className="text-white text-2xl font-bold mb-6">Perfil</h1>

      {/* Wallet */}
      <div className="p-4 bg-white/5 rounded-xl mb-4">
        <p className="text-white/40 text-xs">Wallet</p>
        <p className="text-white font-mono text-sm mt-1">{shortAddr}</p>
      </div>

      {/* Executor info */}
      {executor && (
        <div className="p-4 bg-white/5 rounded-xl mb-4">
          <p className="text-white font-semibold">{executor.display_name ?? "Sin nombre"}</p>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <p className="text-white/40 text-xs">Tareas Completadas</p>
              <p className="text-white text-lg font-bold">{executor.tasks_completed}</p>
            </div>
            <div>
              <p className="text-white/40 text-xs">Reputacion</p>
              <p className="text-white text-lg font-bold">
                {reputation ? `${reputation.average_score.toFixed(1)}/5` : "N/A"}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Reputation details */}
      {reputation && reputation.recent_feedback.length > 0 && (
        <div>
          <h2 className="text-white/60 text-sm font-medium mb-3">Feedback Reciente</h2>
          <div className="space-y-2">
            {reputation.recent_feedback.slice(0, 5).map((fb, i) => (
              <div key={i} className="p-3 bg-white/5 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-white text-sm">
                    {"\u2605".repeat(fb.score)}{"\u2606".repeat(5 - fb.score)}
                  </span>
                  <span className="text-white/30 text-xs">
                    {fb.from_address.slice(0, 6)}...
                  </span>
                </div>
                {fb.comment && (
                  <p className="text-white/60 text-sm mt-1">{fb.comment}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!executor && (
        <div className="text-center py-8">
          <p className="text-white/50 text-sm">No estas registrado como executor.</p>
          <p className="text-white/30 text-xs mt-1">Usa el bot de XMTP para registrarte: /register</p>
        </div>
      )}
    </div>
  );
}
