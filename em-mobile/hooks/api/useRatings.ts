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

      // Attempt 1: plain query without join (most resilient)
      // The join `tasks:task_id (title)` can fail if the FK isn't exposed
      // via PostgREST or if RLS on tasks blocks the anon role.
      const { data, error } = await supabase
        .from("ratings")
        .select(
          "id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at"
        )
        .eq("executor_id", executorId)
        .eq("is_public", true)
        .order("created_at", { ascending: false })
        .limit(50);

      if (error) {
        console.warn(
          "[useRatingsHistory] Supabase query failed, returning empty:",
          error.message
        );
        // Graceful degradation — show empty state instead of crashing
        return [];
      }

      return (data || []).map((row: any) => ({
        id: row.id,
        executor_id: row.executor_id,
        task_id: row.task_id,
        rater_id: row.rater_id,
        rater_type: row.rater_type,
        rating: row.rating,
        stars: row.stars,
        comment: row.comment,
        created_at: row.created_at,
        task_title: null, // No join — title unavailable from this query
      }));
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

      const { data, error } = await supabase
        .from("ratings")
        .select(
          "id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at"
        )
        .eq("task_id", taskId)
        .order("created_at", { ascending: true })
        .limit(10);

      if (error) {
        console.warn(
          "[useTaskRatings] Supabase query failed, returning empty:",
          error.message
        );
        return { agentRating: null, workerRating: null };
      }

      const rows = (data || []).map((row: any) => ({
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
          "id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at"
        )
        .eq("rater_id", executorId)
        .eq("is_public", true)
        .order("created_at", { ascending: false })
        .limit(50);

      if (error) {
        console.warn(
          "[useRatingsGiven] Supabase query failed, returning empty:",
          error.message
        );
        return [];
      }

      return (data || []).map((row: any) => ({
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
      }));
    },
    enabled: !!executorId,
    staleTime: 60_000,
  });
}
