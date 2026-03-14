import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../lib/api";
import type { Task } from "./useTasks";

interface CreateH2ATaskParams {
  title: string;
  instructions: string;
  category: string;
  bounty_usd: number;
  deadline_hours: number;
  evidence_required: string[];
  evidence_optional?: string[];
  target_executor_type?: "any" | "human" | "agent" | "robot";
  auto_verify?: boolean;
  capabilities_required?: string[];
  token?: string;
}

export function useCreateH2ATask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ token, ...params }: CreateH2ATaskParams) => {
      return apiClient<Task>("/api/v1/h2a/tasks", {
        method: "POST",
        body: params,
        token,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["h2a-tasks"] });
    },
  });
}

export function useMyPublishedTasks(token?: string) {
  return useQuery<Task[]>({
    queryKey: ["h2a-tasks", "mine"],
    queryFn: () =>
      apiClient<Task[]>("/api/v1/h2a/tasks?my_tasks=true", { token }),
    enabled: !!token,
  });
}

export function useH2ASubmissions(taskId: string, token?: string) {
  return useQuery({
    queryKey: ["h2a-submissions", taskId],
    queryFn: () =>
      apiClient(`/api/v1/h2a/tasks/${taskId}/submissions`, { token }),
    enabled: !!taskId && !!token,
  });
}

export function useApproveH2ASubmission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      taskId,
      submissionId,
      verdict,
      notes,
      token,
    }: {
      taskId: string;
      submissionId: string;
      verdict: "accepted" | "rejected" | "needs_revision";
      notes?: string;
      token?: string;
    }) => {
      return apiClient(`/api/v1/h2a/tasks/${taskId}/approve`, {
        method: "POST",
        body: { submission_id: submissionId, verdict, notes },
        token,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["h2a-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["h2a-submissions"] });
    },
  });
}
