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

export function useRatingsHistory(executorId: string | null) {
  return useQuery<RatingEntry[]>({
    queryKey: ["ratings", "history", executorId],
    queryFn: async () => {
      if (!executorId) return [];

      // Query ratings table joined with tasks for the title
      const { data, error } = await supabase
        .from("ratings")
        .select(
          "id, executor_id, task_id, rater_id, rater_type, rating, stars, comment, created_at, tasks:task_id (title)"
        )
        .eq("executor_id", executorId)
        .eq("is_public", true)
        .order("created_at", { ascending: false })
        .limit(50);

      if (error) {
        console.error("[useRatingsHistory] Error fetching ratings:", error);
        throw error;
      }

      // Flatten the joined task title
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
        task_title: row.tasks?.title ?? null,
      }));
    },
    enabled: !!executorId,
    staleTime: 60_000,
  });
}
