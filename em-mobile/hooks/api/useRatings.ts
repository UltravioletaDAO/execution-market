import { useQuery } from "@tanstack/react-query";
import { supabase } from "../../lib/supabase";

export interface RatingEntry {
  id: string;
  executor_id: string;
  task_id: string;
  rater_id: string;
  rater_type: string | null;
  rating: number;
  stars: number | null;
  comment: string | null;
  created_at: string;
  task_title: string | null;
  payment_tx: string | null;
  payment_network: string | null;
  reputation_tx: string | null;
}

/**
 * Fetch ratings received by an executor.
 * Resilient: if the join or RLS fails, falls back to a plain query without
 * task titles, and ultimately returns an empty list on any error.
 */
export function useRatingsHistory(executorId: string | null) {
  return useQuery<RatingEntry[]>({
    queryKey: ["ratings", "history", executorId],
    queryFn: async () => {
      if (!executorId) return [];

      // Try join with tasks for title + payment info; fall back to plain query
      const { data, error } = await supabase
        .from("ratings")
        .select(
          "id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at, tasks:task_id(title, payment_tx, payment_network)"
        )
        .eq("executor_id", executorId)
        .eq("is_public", true)
        .order("created_at", { ascending: false })
        .limit(50);

      if (error) {
        // Fallback: plain query without join
        const { data: plain, error: plainErr } = await supabase
          .from("ratings")
          .select("id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at")
          .eq("executor_id", executorId)
          .eq("is_public", true)
          .order("created_at", { ascending: false })
          .limit(50);
        if (plainErr) return [];
        return (plain || []).map((row: any) => ({
          ...row, task_title: null, payment_tx: null, payment_network: null, reputation_tx: null,
        }));
      }

      // Fetch reputation_tx from feedback_documents for these tasks
      const taskIds = [...new Set((data || []).map((r: any) => r.task_id))];
      const feedbackMap: Record<string, string> = {};
      if (taskIds.length > 0) {
        const { data: fbDocs } = await supabase
          .from("feedback_documents")
          .select("task_id, reputation_tx, feedback_type")
          .in("task_id", taskIds)
          .not("reputation_tx", "is", null);
        for (const fb of fbDocs || []) {
          if (fb.reputation_tx && !feedbackMap[fb.task_id]) {
            feedbackMap[fb.task_id] = fb.reputation_tx;
          }
        }
      }

      return (data || []).map((row: any) => {
        const task = row.tasks || {};
        return {
          id: row.id,
          executor_id: row.executor_id,
          task_id: row.task_id,
          rater_id: row.rater_id,
          rater_type: row.rater_type,
          rating: row.rating,
          stars: row.stars,
          comment: row.comment,
          created_at: row.created_at,
          task_title: task.title || null,
          payment_tx: task.payment_tx || null,
          payment_network: task.payment_network || null,
          reputation_tx: feedbackMap[row.task_id] || null,
        };
      });
    },
    enabled: !!executorId,
    staleTime: 60_000,
  });
}

/**
 * Fetch ratings given BY this executor (as rater).
 * The rater_id in the ratings table stores the agent/rater identifier.
 * For executor-given ratings, we match on rater_id = executorId.
 *
 * Note: In the current schema, rater_id is a VARCHAR (agent ID or 'system'),
 * not a UUID FK to executors. So for executor-to-agent ratings, the rater_id
 * would be the executor's identifier string. We try both the executor UUID
 * and fall back gracefully.
 */
/**
 * Fetch ratings for a specific task (both agent→worker and worker→agent).
 * Returns { agentRating, workerRating } where each is a RatingEntry or null.
 */
export function useTaskRatings(taskId: string | null) {
  return useQuery<{ agentRating: RatingEntry | null; workerRating: RatingEntry | null }>({
    queryKey: ["ratings", "task", taskId],
    queryFn: async () => {
      if (!taskId) return { agentRating: null, workerRating: null };

      // Fetch ratings + feedback_documents (for reputation_tx) in parallel
      const [ratingsRes, feedbackRes] = await Promise.all([
        supabase
          .from("ratings")
          .select(
            "id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at"
          )
          .eq("task_id", taskId)
          .order("created_at", { ascending: true })
          .limit(10),
        supabase
          .from("feedback_documents")
          .select("feedback_type, reputation_tx")
          .eq("task_id", taskId)
          .not("reputation_tx", "is", null)
          .limit(10),
      ]);

      if (ratingsRes.error) {
        console.warn(
          "[useTaskRatings] Supabase query failed, returning empty:",
          ratingsRes.error.message
        );
        return { agentRating: null, workerRating: null };
      }

      // Map feedback_type → reputation_tx for lookup
      // feedback_type: "agent_rating" = agent rated worker, "worker_rating" = worker rated agent
      const feedbackTxMap: Record<string, string> = {};
      if (feedbackRes.data) {
        for (const fb of feedbackRes.data) {
          if (fb.reputation_tx) {
            // feedback_type naming: "agent_rating" = worker rated the agent,
            // "worker_rating" = agent rated the worker.
            // Map to rater_type used in ratings table:
            const raterType = fb.feedback_type === "agent_rating" ? "worker" : "agent";
            feedbackTxMap[raterType] = fb.reputation_tx;
          }
        }
      }

      const rows: RatingEntry[] = (ratingsRes.data || []).map((row: any) => ({
        id: row.id,
        executor_id: row.executor_id,
        task_id: row.task_id,
        rater_id: row.rater_id,
        rater_type: row.rater_type,
        rating: row.rating,
        stars: row.stars,
        comment: row.comment,
        created_at: row.created_at,
        task_title: null,
        payment_tx: null,
        payment_network: null,
        reputation_tx: feedbackTxMap[row.rater_type] || null,
      }));

      return {
        agentRating: rows.find((r) => r.rater_type === "agent") || null,
        workerRating: rows.find((r) => r.rater_type === "worker") || null,
      };
    },
    enabled: !!taskId,
    staleTime: 60_000,
  });
}

export function useRatingsGiven(executorId: string | null) {
  return useQuery<RatingEntry[]>({
    queryKey: ["ratings", "given", executorId],
    queryFn: async () => {
      if (!executorId) return [];

      const { data, error } = await supabase
        .from("ratings")
        .select(
          "id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at, tasks:task_id(title, payment_tx, payment_network)"
        )
        .eq("rater_id", executorId)
        .eq("is_public", true)
        .order("created_at", { ascending: false })
        .limit(50);

      if (error) {
        const { data: plain, error: plainErr } = await supabase
          .from("ratings")
          .select("id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at")
          .eq("rater_id", executorId)
          .eq("is_public", true)
          .order("created_at", { ascending: false })
          .limit(50);
        if (plainErr) return [];
        return (plain || []).map((row: any) => ({
          ...row, task_title: null, payment_tx: null, payment_network: null, reputation_tx: null,
        }));
      }

      // Fetch reputation_tx from feedback_documents for these tasks
      const taskIds = [...new Set((data || []).map((r: any) => r.task_id))];
      const feedbackMap: Record<string, string> = {};
      if (taskIds.length > 0) {
        const { data: fbDocs } = await supabase
          .from("feedback_documents")
          .select("task_id, reputation_tx, feedback_type")
          .in("task_id", taskIds)
          .not("reputation_tx", "is", null);
        for (const fb of fbDocs || []) {
          if (fb.reputation_tx && !feedbackMap[fb.task_id]) {
            feedbackMap[fb.task_id] = fb.reputation_tx;
          }
        }
      }

      return (data || []).map((row: any) => {
        const task = row.tasks || {};
        return {
          id: row.id,
          executor_id: row.executor_id,
          task_id: row.task_id,
          rater_id: row.rater_id,
          rater_type: row.rater_type,
          rating: row.rating,
          stars: row.stars,
          comment: row.comment,
          created_at: row.created_at,
          task_title: task.title || null,
          payment_tx: task.payment_tx || null,
          payment_network: task.payment_network || null,
          reputation_tx: feedbackMap[row.task_id] || null,
        };
      });
    },
    enabled: !!executorId,
    staleTime: 60_000,
  });
}
