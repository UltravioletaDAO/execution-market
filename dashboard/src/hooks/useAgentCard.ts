/**
 * useAgentCard - Fetch any agent's public profile by wallet address
 *
 * Returns display_name, avatar_url, wallet_address, agent_type,
 * reputation_score, tasks_completed, tasks_posted, skills, member_since.
 * Caches results in a module-level Map to avoid re-fetching in one session.
 */

import { useState, useEffect, useRef } from 'react'
import { supabase } from '../lib/supabase'
import type { Executor, AgentType, SocialLinks } from '../types/database'

export interface AgentCardData {
  wallet_address: string
  display_name: string | null
  avatar_url: string | null
  bio: string | null
  agent_type: AgentType
  erc8004_agent_id: number | null
  reputation_score: number
  tasks_completed: number
  tasks_posted: number
  tasks_disputed: number
  avg_rating: number | null
  skills: string[]
  social_links?: SocialLinks | null
  world_human_id: number | null
  world_verified_at: string | null
  ens_name: string | null
  ens_avatar: string | null
  ens_subname: string | null
  member_since: string // created_at
}

// Module-level cache — survives across component mounts within the same session
const agentCardCache = new Map<string, AgentCardData>()

export function useAgentCard(walletAddress?: string | null) {
  const [data, setData] = useState<AgentCardData | null>(
    walletAddress ? agentCardCache.get(walletAddress) ?? null : null
  )
  const [loading, setLoading] = useState(!data && !!walletAddress)
  const [error, setError] = useState<string | null>(null)
  const cancelledRef = useRef(false)

  useEffect(() => {
    cancelledRef.current = false

    if (!walletAddress) {
      setData(null)
      setLoading(false)
      return
    }

    // Return cached if available
    const cached = agentCardCache.get(walletAddress)
    if (cached) {
      setData(cached)
      setLoading(false)
      return
    }

    const wallet = walletAddress! // Safe: guarded by early return above

    async function fetchAgent() {
      setLoading(true)
      setError(null)

      try {
        // Fetch executor profile
        // Prefer agent record over worker record for the same wallet.
        // A wallet may have both (agent publishes tasks, worker completes them).
        const { data: agentExec } = await supabase
          .from('executors')
          .select('wallet_address, display_name, avatar_url, bio, agent_type, erc8004_agent_id, reputation_score, tasks_completed, tasks_disputed, avg_rating, skills, social_links, world_human_id, world_verified_at, ens_name, ens_avatar, ens_subname, created_at')
          .eq('wallet_address', wallet)
          .eq('executor_type', 'agent')
          .single()

        const executor = agentExec || (await supabase
          .from('executors')
          .select('wallet_address, display_name, avatar_url, bio, agent_type, erc8004_agent_id, reputation_score, tasks_completed, tasks_disputed, avg_rating, skills, social_links, world_human_id, world_verified_at, ens_name, ens_avatar, ens_subname, created_at')
          .eq('wallet_address', wallet)
          .limit(1)
          .single()
        ).data

        const execError = executor ? null : new Error('not found')

        if (execError) {
          // Try matching by ID in case walletAddress is actually an executor ID
          const { data: execById, error: byIdError } = await supabase
            .from('executors')
            .select('wallet_address, display_name, avatar_url, bio, agent_type, erc8004_agent_id, reputation_score, tasks_completed, tasks_disputed, avg_rating, skills, social_links, world_human_id, world_verified_at, ens_name, ens_avatar, ens_subname, created_at')
            .eq('id', wallet)
            .single()

          if (byIdError) throw new Error('Agent not found')
          if (cancelledRef.current) return

          const result = buildCardData(execById, 0)
          agentCardCache.set(wallet, result)
          setData(result)
          setLoading(false)
          return
        }

        if (cancelledRef.current) return

        // Count tasks posted by this wallet (agent_id is the wallet address in tasks table)
        const { count: tasksPosted } = await supabase
          .from('tasks')
          .select('id', { count: 'exact', head: true })
          .eq('agent_id', wallet)

        if (cancelledRef.current) return

        const result = buildCardData(executor, tasksPosted ?? 0)
        agentCardCache.set(wallet, result)
        setData(result)
      } catch (err) {
        if (!cancelledRef.current) {
          setError(err instanceof Error ? err.message : 'Failed to load agent')
        }
      } finally {
        if (!cancelledRef.current) {
          setLoading(false)
        }
      }
    }

    fetchAgent()

    return () => {
      cancelledRef.current = true
    }
  }, [walletAddress])

  return { data, loading, error }
}

function buildCardData(executor: Record<string, unknown>, tasksPosted: number): AgentCardData {
  return {
    wallet_address: (executor.wallet_address as string) ?? '',
    display_name: (executor.display_name as string | null) ?? null,
    avatar_url: (executor.avatar_url as string | null) ?? null,
    bio: (executor.bio as string | null) ?? null,
    agent_type: (executor.agent_type as AgentType) ?? 'human',
    erc8004_agent_id: (executor.erc8004_agent_id as number | null) ?? null,
    reputation_score: (executor.reputation_score as number) ?? 0,
    tasks_completed: (executor.tasks_completed as number) ?? 0,
    tasks_posted: tasksPosted,
    tasks_disputed: (executor.tasks_disputed as number) ?? 0,
    avg_rating: (executor.avg_rating as number | null) ?? null,
    skills: (executor.skills as string[]) ?? [],
    social_links: (executor.social_links as SocialLinks | null) ?? null,
    world_human_id: (executor.world_human_id as number | null) ?? null,
    world_verified_at: (executor.world_verified_at as string | null) ?? null,
    ens_name: (executor.ens_name as string | null) ?? null,
    ens_avatar: (executor.ens_avatar as string | null) ?? null,
    ens_subname: (executor.ens_subname as string | null) ?? null,
    member_since: (executor.created_at as string) ?? new Date().toISOString(),
  }
}

/** Preload an agent card into cache from an existing Executor object */
export function preloadAgentCard(executor: Executor, tasksPosted = 0) {
  const card: AgentCardData = {
    wallet_address: executor.wallet_address,
    display_name: executor.display_name,
    avatar_url: executor.avatar_url,
    bio: executor.bio,
    agent_type: executor.agent_type ?? 'human',
    erc8004_agent_id: executor.erc8004_agent_id ?? null,
    reputation_score: executor.reputation_score,
    tasks_completed: executor.tasks_completed,
    tasks_posted: tasksPosted,
    tasks_disputed: executor.tasks_disputed,
    avg_rating: executor.avg_rating,
    skills: executor.skills ?? [],
    social_links: executor.social_links ?? null,
    world_human_id: executor.world_human_id ?? null,
    world_verified_at: executor.world_verified_at ?? null,
    ens_name: executor.ens_name ?? null,
    ens_avatar: executor.ens_avatar ?? null,
    ens_subname: executor.ens_subname ?? null,
    member_since: executor.created_at,
  }
  agentCardCache.set(executor.wallet_address, card)
  return card
}

/** Clear the agent card cache (e.g., on logout) */
export function clearAgentCardCache() {
  agentCardCache.clear()
}
