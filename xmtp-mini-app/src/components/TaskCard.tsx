import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import type { Task } from "../services/types";

const CATEGORY_LABELS: Record<string, string> = {
  physical_presence: "Presencia Fisica",
  knowledge_access: "Acceso a Info",
  human_authority: "Autoridad Humana",
  simple_action: "Accion Simple",
  digital_physical: "Digital + Fisico",
};

interface Props {
  task: Task;
}

export function TaskCard({ task }: Props) {
  const navigate = useNavigate();
  const bounty = parseFloat(String(task.bounty_usdc ?? 0)).toFixed(2);
  const deadline = new Date(task.deadline);
  const isExpired = deadline < new Date();
  const timeLeft = isExpired
    ? "Expirado"
    : formatDistanceToNow(deadline, { locale: es, addSuffix: false });

  return (
    <button
      onClick={() => navigate(`/task/${task.id}`)}
      className="w-full text-left p-4 border border-white/10 rounded-xl hover:border-white/20 active:bg-white/5 transition-all"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-semibold text-sm truncate">{task.title}</h3>
          <p className="text-white/50 text-xs mt-1">
            {CATEGORY_LABELS[task.category] ?? task.category}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-white font-bold text-sm">${bounty}</p>
          <p className="text-white/40 text-xs">USDC</p>
        </div>
      </div>
      <div className="flex items-center gap-3 mt-3 text-xs">
        <span className={`${isExpired ? "text-em-red" : "text-white/50"}`}>
          {isExpired ? "Expirado" : `${timeLeft} restante`}
        </span>
        <span className="text-white/30">|</span>
        <span className="text-white/50 capitalize">{task.payment_network ?? "base"}</span>
      </div>
    </button>
  );
}
