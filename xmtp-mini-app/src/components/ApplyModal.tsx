import { useState } from "react";
import { api } from "../services/api";
import { useXMTPMiniApp } from "../context/XMTPMiniAppProvider";
import type { Task } from "../services/types";

interface Props {
  task: Task;
  isOpen: boolean;
  onClose: () => void;
  onApplied: () => void;
}

export function ApplyModal({ task, isOpen, onClose, onApplied }: Props) {
  const { walletAddress, sendMessage } = useXMTPMiniApp();
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApply = async () => {
    if (!walletAddress) {
      setError("Wallet no conectada");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await api.post("/api/v1/tasks/apply", {
        task_id: task.id,
        wallet_address: walletAddress,
        message: message || undefined,
      });
      // Send confirmation to chat
      await sendMessage(`Aplique a la tarea: "${task.title}" ($${task.bounty_usdc} USDC)`);
      onApplied();
      onClose();
    } catch (err: any) {
      setError(err.message || "Error al aplicar");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-end sm:items-center justify-center">
      <div className="bg-neutral-900 w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl p-6">
        <h2 className="text-white font-bold text-lg mb-1">Aplicar a Tarea</h2>
        <p className="text-white/60 text-sm mb-4">{task.title}</p>

        <div className="mb-4">
          <label className="text-white/50 text-xs mb-1 block">Mensaje (opcional)</label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Por que eres el indicado para esta tarea..."
            rows={3}
            className="w-full bg-white/5 rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 border border-white/10 focus:border-white/30 outline-none resize-none"
          />
        </div>

        <div className="flex items-center justify-between mb-4 p-3 bg-white/5 rounded-xl">
          <span className="text-white/60 text-sm">Bounty</span>
          <span className="text-white font-bold">${parseFloat(String(task.bounty_usdc ?? 0)).toFixed(2)} USDC</span>
        </div>

        {error && (
          <p className="text-em-red text-sm mb-3">{error}</p>
        )}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 text-white/60 border border-white/10 rounded-xl hover:bg-white/5"
          >
            Cancelar
          </button>
          <button
            onClick={handleApply}
            disabled={isSubmitting}
            className="flex-1 py-3 bg-white text-black font-semibold rounded-xl hover:bg-white/90 disabled:opacity-50"
          >
            {isSubmitting ? "Enviando..." : "Aplicar"}
          </button>
        </div>
      </div>
    </div>
  );
}
