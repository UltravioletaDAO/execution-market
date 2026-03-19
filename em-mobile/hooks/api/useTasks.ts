import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../lib/api";
import { supabase } from "../../lib/supabase";

export interface Task {
  id: string;
  title: string;
  instructions: string;
  category: string;
  status: string;
  bounty_usd: number;
  deadline: string;
  created_at: string;
  agent_id: string;
  executor_id: string | null;
  location_hint: string | null;
  location_lat: number | null;
  location_lng: number | null;
  min_reputation: number;
  payment_network: string;
  payment_token: string;
  evidence_schema: {
    required: string[];
    optional?: string[];
  } | null;
  skills_required: string[] | null;
  erc8004_agent_id: number | null;
  agent_name: string | null;
  target_executor_type: string | null;
  escrow_tx: string | null;
  payment_tx: string | null;
  escrow_status?: string | null;
}

interface TaskFilters {
  category?: string;
  status?: string;
  lat?: number;
  lng?: number;
  radius_km?: number;
  limit?: number;
  offset?: number;
}

export function useAvailableTasks(filters: TaskFilters = {}) {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.lat) params.set("lat", String(filters.lat));
  if (filters.lng) params.set("lng", String(filters.lng));
  if (filters.radius_km) params.set("radius_km", String(filters.radius_km));
  params.set("limit", String(filters.limit || 50));
  if (filters.offset) params.set("offset", String(filters.offset));

  const queryString = params.toString();

  return useQuery<Task[]>({
    queryKey: ["tasks", "available", filters],
    queryFn: async () => {
      const response = await apiClient<{ tasks: Task[] } | Task[]>(
        `/api/v1/tasks/available?${queryString}`
      );
      // API returns { tasks: [...] } wrapper, extract the array
      if (Array.isArray(response)) return response;
      if (response && "tasks" in response) return response.tasks;
      return [];
    },
    staleTime: 30_000,
  });
}

export function useTask(taskId: string | undefined) {
  return useQuery<Task>({
    queryKey: ["task", taskId],
    queryFn: async () => {
      // Try API first, fall back to direct Supabase query if API fails
      // (handles cases where API returns 401/403/500 but task exists in DB)
      try {
        return await apiClient<Task>(`/api/v1/tasks/${taskId}`);
      } catch (apiError) {
        // Fallback: fetch directly from Supabase
        const { data, error } = await supabase
          .from("tasks")
          .select("*")
          .eq("id", taskId)
          .single();

        if (error || !data) {
          // Re-throw original API error if Supabase also fails
          throw apiError;
        }

        // Map raw Supabase row to Task shape (DB column names may differ slightly)
        return {
          id: data.id,
          title: data.title ?? "",
          instructions: data.instructions ?? "",
          category: data.category ?? "other",
          status: data.status ?? "published",
          bounty_usd: typeof data.bounty_usd === "number" ? data.bounty_usd : parseFloat(data.bounty_usd) || 0,
          deadline: data.deadline ?? new Date(Date.now() + 86400000).toISOString(),
          created_at: data.created_at ?? new Date().toISOString(),
          agent_id: data.agent_id ?? "",
          executor_id: data.executor_id ?? null,
          location_hint: data.location_hint ?? null,
          location_lat: data.location_lat ?? null,
          location_lng: data.location_lng ?? null,
          min_reputation: data.min_reputation ?? 0,
          payment_network: data.payment_network ?? "base",
          payment_token: (data.payment_token && !data.payment_token.startsWith("0x"))
            ? data.payment_token : "USDC",
          evidence_schema: data.evidence_schema ?? null,
          skills_required: data.required_capabilities ?? null,
          erc8004_agent_id: data.erc8004_agent_id ?? null,
          agent_name: data.metadata?.erc8004?.name ?? data.metadata?.agent_name ?? null,
          target_executor_type: data.target_executor_type ?? null,
          escrow_tx: data.escrow_tx ?? null,
          payment_tx: data.payment_tx ?? null,
          escrow_status: null, // Not available in direct Supabase query (lives in escrows table)
        } as Task;
      }
    },
    enabled: !!taskId,
    retry: 1,
  });
}

export function useMyTasks(executorId: string | null) {
  return useQuery({
    queryKey: ["tasks", "mine", executorId],
    queryFn: async () => {
      if (!executorId) return [];

      const { data, error } = await supabase
        .from("tasks")
        .select("*")
        .eq("executor_id", executorId)
        .order("created_at", { ascending: false });

      if (error) throw error;
      return (data || []) as Task[];
    },
    enabled: !!executorId,
  });
}

export function useApplyToTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      taskId,
      executorId,
      message,
    }: {
      taskId: string;
      executorId: string;
      message?: string;
    }) => {
      return apiClient(`/api/v1/tasks/${taskId}/apply`, {
        method: "POST",
        body: { executor_id: executorId, message },
      });
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["task", variables.taskId] });
      queryClient.invalidateQueries({
        queryKey: ["myApplication", variables.taskId],
      });
    },
  });
}

export function useMyApplication(taskId: string | undefined, executorId: string | null) {
  return useQuery<{ applied: boolean; status: string | null }>({
    queryKey: ["myApplication", taskId, executorId],
    queryFn: async () => {
      if (!taskId || !executorId) return { applied: false, status: null };

      const { data, error } = await supabase
        .from("task_applications")
        .select("status")
        .eq("task_id", taskId)
        .eq("executor_id", executorId)
        .maybeSingle();

      if (error) {
        // Table might not exist — fall back to checking if executor_id matches
        return { applied: false, status: null };
      }

      if (data) {
        return { applied: true, status: data.status };
      }
      return { applied: false, status: null };
    },
    enabled: !!taskId && !!executorId,
  });
}

export function useRecentActivity(limit: number = 20) {
  return useQuery<Task[]>({
    queryKey: ["tasks", "activity", limit],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("tasks")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(limit);

      if (error) throw error;
      return (data || []) as Task[];
    },
    staleTime: 30_000,
  });
}

/** Fetch executor's own submission for a task.
 *  Uses Supabase directly (like ratings) for reliability — the REST API
 *  endpoint can fail silently if auth/RLS is misconfigured.
 */
export function useMySubmission(
  taskId: string | undefined,
  executorId: string | undefined
) {
  return useQuery({
    queryKey: ["my_submission", taskId, executorId],
    queryFn: async () => {
      if (!taskId || !executorId) return null;

      const { data, error } = await supabase
        .from("submissions")
        .select("*")
        .eq("task_id", taskId)
        .eq("executor_id", executorId)
        .limit(1)
        .maybeSingle();

      if (error) {
        // Fallback to REST API if Supabase direct query fails (RLS)
        console.warn("[useMySubmission] Supabase query failed, trying REST API:", error.message);
        try {
          const response = await apiClient<{ data: any }>(
            `/api/v1/workers/tasks/${taskId}/my-submission?executor_id=${executorId}`
          );
          return response.data || response;
        } catch {
          return null;
        }
      }

      return data;
    },
    enabled: !!taskId && !!executorId,
    staleTime: 60_000,
  });
}

export function usePlatformConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: () => apiClient<Record<string, unknown>>("/api/v1/config"),
    staleTime: 5 * 60_000, // 5 minutes
  });
}
