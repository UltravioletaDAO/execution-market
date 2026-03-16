import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { api } from "../services/api";
import { ApplyModal } from "../components/ApplyModal";
import { EvidenceCapture } from "../components/EvidenceCapture";
import type { Task } from "../services/types";

export function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showApply, setShowApply] = useState(false);
  const [tab, setTab] = useState<"detail" | "evidence">("detail");

  useEffect(() => {
    if (!id) return;
    setIsLoading(true);
    api.get<Task>(`/api/v1/tasks/${id}`)
      .then(setTask)
      .catch(() => navigate("/"))
      .finally(() => setIsLoading(false));
  }, [id, navigate]);

  if (isLoading || !task) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  const bounty = parseFloat(String(task.bounty_usdc ?? 0)).toFixed(2);
  const deadline = new Date(task.deadline);
  const isExpired = deadline < new Date();

  return (
    <div className="px-4 pt-4 pb-24">
      {/* Back button */}
      <button onClick={() => navigate(-1)} className="text-white/50 text-sm mb-4 flex items-center gap-1">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Volver
      </button>

      {/* Title + bounty */}
      <h1 className="text-white text-xl font-bold">{task.title}</h1>
      <div className="flex items-center gap-4 mt-2 text-sm">
        <span className="text-white font-bold">${bounty} USDC</span>
        <span className="text-white/40 capitalize">{task.payment_network ?? "base"}</span>
        <span className={isExpired ? "text-em-red" : "text-white/50"}>
          {isExpired ? "Expirado" : formatDistanceToNow(deadline, { locale: es, addSuffix: true })}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 mt-6 border-b border-white/10">
        <button
          onClick={() => setTab("detail")}
          className={`pb-2 text-sm font-medium transition-colors ${
            tab === "detail" ? "text-white border-b-2 border-white" : "text-white/40"
          }`}
        >
          Detalles
        </button>
        {task.status !== "published" && task.evidence_requirements && (
          <button
            onClick={() => setTab("evidence")}
            className={`pb-2 text-sm font-medium transition-colors ${
              tab === "evidence" ? "text-white border-b-2 border-white" : "text-white/40"
            }`}
          >
            Evidencia
          </button>
        )}
      </div>

      {/* Content */}
      {tab === "detail" ? (
        <div className="mt-4 space-y-4">
          <div>
            <h3 className="text-white/40 text-xs uppercase mb-1">Instrucciones</h3>
            <p className="text-white/80 text-sm whitespace-pre-wrap">{task.instructions}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-white/5 rounded-xl">
              <p className="text-white/40 text-xs">Categoria</p>
              <p className="text-white text-sm mt-0.5 capitalize">{task.category?.replace(/_/g, " ")}</p>
            </div>
            <div className="p-3 bg-white/5 rounded-xl">
              <p className="text-white/40 text-xs">Estado</p>
              <p className="text-white text-sm mt-0.5 capitalize">{task.status}</p>
            </div>
          </div>

          {task.evidence_requirements && task.evidence_requirements.length > 0 && (
            <div>
              <h3 className="text-white/40 text-xs uppercase mb-2">Evidencia Requerida</h3>
              <div className="space-y-2">
                {task.evidence_requirements.map((req, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className={req.required ? "text-em-red" : "text-white/30"}>
                      {req.required ? "*" : "-"}
                    </span>
                    <span className="text-white/70">{req.label}</span>
                    <span className="text-white/30 text-xs capitalize">({req.type})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-4">
          <EvidenceCapture
            requirements={task.evidence_requirements ?? []}
            onCapture={(type, data) => {
              console.log("Captured:", type, data);
              // TODO: connect to submission service
            }}
          />
        </div>
      )}

      {/* Apply button (only if published) */}
      {task.status === "published" && (
        <div className="fixed bottom-16 left-0 right-0 p-4 bg-gradient-to-t from-black via-black to-transparent">
          <button
            onClick={() => setShowApply(true)}
            className="w-full py-3.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90 active:bg-white/80 transition-colors"
          >
            Aplicar — ${bounty} USDC
          </button>
        </div>
      )}

      <ApplyModal
        task={task}
        isOpen={showApply}
        onClose={() => setShowApply(false)}
        onApplied={() => {
          setTask({ ...task, status: "applied" as any });
        }}
      />
    </div>
  );
}
