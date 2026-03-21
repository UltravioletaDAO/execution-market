import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../lib/api";

export interface LeaderboardEntry {
  id: string;
  display_name: string | null;
  reputation_score: number;
  tier: string | null;
  tasks_completed: number;
  avg_rating: number | null;
  rank: number;
  badges_count: number;
}

export interface AgentReputation {
  agent_id: number;
  count: number;
  score: number;
  network: string;
}

export function useLeaderboard(limit: number = 20) {
  return useQuery<LeaderboardEntry[]>({
    queryKey: ["leaderboard", limit],
    queryFn: async () => {
      const response = await apiClient<{ workers: LeaderboardEntry[] }>(
        `/api/v1/reputation/leaderboard?limit=${limit}`
      );
      return response.workers || [];
    },
    staleTime: 60_000,
  });
}

export function useAgentReputation(agentId: number | null) {
  return useQuery<AgentReputation>({
    queryKey: ["agent_reputation", agentId],
    queryFn: () =>
      apiClient<AgentReputation>(`/api/v1/reputation/agents/${agentId}`),
    enabled: !!agentId,
    staleTime: 5 * 60_000,
  });
}

export interface AgentDirectoryEntry {
  executor_id: string;
  display_name: string;
  capabilities?: string[];
  rating: number;
  tasks_completed: number;
  avg_rating: number;
  erc8004_agent_id?: number;
  verified: boolean;
  bio?: string;
  avatar_url?: string;
  role: "publisher" | "executor" | "both";
  tasks_published: number;
  total_bounty_usd: number;
  active_tasks: number;
}

export function useAgentDirectory(limit: number = 20) {
  return useQuery<AgentDirectoryEntry[]>({
    queryKey: ["agents", "directory", limit],
    queryFn: async () => {
      const response = await apiClient<{ agents: AgentDirectoryEntry[] }>(
        `/api/v1/agents/directory?limit=${limit}`
      );
      return response.agents || [];
    },
    staleTime: 60_000,
  });
}

export function useAgentDetail(executorId: string) {
  return useQuery<AgentDirectoryEntry | null>({
    queryKey: ["agents", "detail", executorId],
    queryFn: async () => {
      const response = await apiClient<{ agents: AgentDirectoryEntry[] }>(
        `/api/v1/agents/directory?limit=100`
      );
      const agents = response.agents || [];
      return agents.find((a) => a.executor_id === executorId) || null;
    },
    enabled: !!executorId,
    staleTime: 60_000,
  });
}
