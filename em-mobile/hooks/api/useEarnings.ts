import { useQuery } from "@tanstack/react-query";
import { supabase } from "../../lib/supabase";

interface EarningsSummary {
  total_earned_usdc: number;
  balance_usdc: number;
  pending_earnings_usdc: number;
  this_month_usdc: number;
}

interface PaymentEvent {
  id: string;
  task_id: string;
  event_type: string;
  amount_usdc: number;
  tx_hash: string | null;
  network: string;
  created_at: string;
}

export interface CompletedTaskEarning {
  task_id: string;
  task_title: string;
  bounty_usd: number;
  earned_usdc: number; // bounty * 0.87 (after 13% platform fee)
  payment_network: string;
  completed_at: string;
  tx_hash: string | null;
  event_type: string;
}

const PLATFORM_FEE = 0.13;

export function useEarningsSummary(executorId: string | null) {
  return useQuery<EarningsSummary>({
    queryKey: ["earnings", "summary", executorId],
    queryFn: async () => {
      if (!executorId) throw new Error("No executor ID");

      const { data: tasks } = await supabase
        .from("tasks")
        .select("bounty_usd, status")
        .eq("executor_id", executorId);

      const completed = tasks?.filter((t) => t.status === "completed") || [];
      const pending = tasks?.filter((t) => ["submitted", "in_progress"].includes(t.status)) || [];

      const totalEarned = completed.reduce((sum, t) => sum + (t.bounty_usd || 0) * (1 - PLATFORM_FEE), 0);
      const pendingEarnings = pending.reduce((sum, t) => sum + (t.bounty_usd || 0) * (1 - PLATFORM_FEE), 0);

      // This month filter
      const now = new Date();
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

      return {
        total_earned_usdc: totalEarned,
        balance_usdc: totalEarned,
        pending_earnings_usdc: pendingEarnings,
        this_month_usdc: totalEarned, // Simplified
      };
    },
    enabled: !!executorId,
  });
}

export function usePaymentHistory(executorId: string | null) {
  return useQuery<CompletedTaskEarning[]>({
    queryKey: ["earnings", "history", executorId],
    queryFn: async () => {
      if (!executorId) return [];

      // Get completed tasks for this executor (primary source of truth)
      const { data: tasks } = await supabase
        .from("tasks")
        .select("id, title, bounty_usd, status, payment_network, updated_at")
        .eq("executor_id", executorId)
        .eq("status", "completed")
        .order("updated_at", { ascending: false })
        .limit(50);

      if (!tasks || tasks.length === 0) return [];

      // Try to enrich with payment TX hashes from payment_events
      const taskIds = tasks.map((t) => t.id);
      // Query all worker-payment event types (varies by payment mode)
      const { data: events } = await supabase
        .from("payment_events")
        .select("task_id, event_type, tx_hash, amount_usdc")
        .in("task_id", taskIds)
        .in("event_type", [
          "settle_worker_direct",  // Fase 1 (default production)
          "escrow_release",        // Fase 2 (on-chain escrow)
          "h2a_settle_worker",     // H2A (human-published)
          "disburse_worker",       // Legacy preauth
          "settle",                // Legacy catch-all
        ]);

      // Build a map of task_id -> best TX hash (prefer specific worker events)
      const txMap = new Map<string, { tx_hash: string | null; amount_usdc: number; event_type: string }>();
      const priorityTypes = ["settle_worker_direct", "escrow_release", "h2a_settle_worker", "disburse_worker"];
      for (const ev of events || []) {
        const existing = txMap.get(ev.task_id);
        if (!existing || priorityTypes.includes(ev.event_type)) {
          txMap.set(ev.task_id, {
            tx_hash: ev.tx_hash,
            amount_usdc: ev.amount_usdc,
            event_type: ev.event_type,
          });
        }
      }

      return tasks.map((task) => {
        const paymentInfo = txMap.get(task.id);
        const earned = paymentInfo?.amount_usdc ?? task.bounty_usd * (1 - PLATFORM_FEE);

        return {
          task_id: task.id,
          task_title: task.title,
          bounty_usd: task.bounty_usd,
          earned_usdc: earned,
          payment_network: task.payment_network,
          completed_at: task.updated_at,
          tx_hash: paymentInfo?.tx_hash ?? null,
          event_type: paymentInfo?.event_type ?? "completed",
        };
      });
    },
    enabled: !!executorId,
  });
}

/** Get payment events for a specific task (used in task detail timeline) */
export function useTaskPaymentEvents(taskId: string | undefined) {
  return useQuery<PaymentEvent[]>({
    queryKey: ["payment_events", taskId],
    queryFn: async () => {
      if (!taskId) return [];

      const { data } = await supabase
        .from("payment_events")
        .select("*")
        .eq("task_id", taskId)
        .order("created_at", { ascending: true });

      return (data || []) as PaymentEvent[];
    },
    enabled: !!taskId,
  });
}
