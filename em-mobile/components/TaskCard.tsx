import { View, Text, Pressable } from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import type { Task } from "../hooks/api/useTasks";
import { TASK_CATEGORIES } from "../constants/categories";
import { NETWORKS } from "../constants/networks";
import { ReputationBadge } from "./ReputationBadge";
import { useAgentReputation } from "../hooks/api/useReputation";

function formatDeadline(deadline: string, t: (key: string) => string): string {
  if (!deadline) return "—";
  const now = new Date();
  const dl = new Date(deadline);
  if (isNaN(dl.getTime())) return "—";
  const diffMs = dl.getTime() - now.getTime();

  if (diffMs < 0) return t("task.expired");

  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (hours > 24) return `${Math.floor(hours / 24)}d`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatBounty(bounty: number | null | undefined): string {
  const val = typeof bounty === "number" ? bounty : parseFloat(String(bounty)) || 0;
  if (val >= 1) return `$${val.toFixed(2)}`;
  return `$${val.toFixed(3)}`;
}

interface TaskCardProps {
  task: Task;
  compact?: boolean;
}

export function TaskCard({ task, compact = false }: TaskCardProps) {
  const { t } = useTranslation();
  const category = TASK_CATEGORIES.find((c) => c.key === task.category);
  const network = NETWORKS.find((n) => n.key === task.payment_network);
  const { data: agentRep } = useAgentReputation(task.erc8004_agent_id);

  return (
    <Pressable
      className="bg-surface rounded-2xl p-4 mb-3 active:opacity-80"
      onPress={() => router.push(`/task/${task.id}`)}
    >
      {/* Header: Category + Deadline */}
      <View className="flex-row items-center justify-between mb-2">
        <View className="flex-row items-center">
          <Text style={{ fontSize: 16 }}>{category?.icon || "📌"}</Text>
          <Text className="text-gray-400 text-xs ml-2">
            {t(`categories.${task.category}`, task.category)}
          </Text>
        </View>
        <View className="flex-row items-center">
          <Text className="text-gray-500 text-xs">
            {"\u23F1"} {formatDeadline(task.deadline, t)}
          </Text>
        </View>
      </View>

      {/* Title */}
      <Text className="text-white font-bold text-base mb-1" numberOfLines={2}>
        {task.title}
      </Text>

      {!compact && (
        <>
          {/* Instructions preview */}
          <Text className="text-gray-400 text-sm mb-3" numberOfLines={2}>
            {task.instructions}
          </Text>

          {/* Location */}
          {task.location_hint && (
            <View className="flex-row items-center mb-2">
              <Text className="text-gray-500 text-xs">
                📍 {task.location_hint}
              </Text>
            </View>
          )}
        </>
      )}

      {/* Footer: Bounty + Network + Evidence count */}
      <View className="flex-row items-center justify-between mt-1">
        <View className="flex-row items-center">
          <View className="bg-green-900/30 rounded-full px-3 py-1">
            <Text className="text-green-400 font-bold text-sm">
              {formatBounty(task.bounty_usd)} {task.payment_token || "USDC"}
            </Text>
            {typeof task.bounty_usd === "number" && task.bounty_usd > 0 && (
              <Text className="text-gray-500 text-[10px]">
                Net: ${(task.bounty_usd * 0.87).toFixed(2)}
              </Text>
            )}
          </View>
          {network && (
            <View
              className="rounded-full px-2 py-1 ml-2"
              style={{ backgroundColor: `${network.color}20` }}
            >
              <Text
                style={{
                  color: network.color,
                  fontSize: 10,
                  fontWeight: "600",
                }}
              >
                {network.name}
              </Text>
            </View>
          )}
        </View>
        {task.evidence_schema?.required && (
          <Text className="text-gray-500 text-xs">
            {t("task.evidenceCount", { count: task.evidence_schema.required.length })}
          </Text>
        )}
      </View>

      {/* Skills required */}
      {!compact && Array.isArray(task.skills_required) && task.skills_required.length > 0 && (
        <View className="flex-row flex-wrap gap-1 mt-2">
          {task.skills_required.slice(0, 3).map((skill) => (
            <View
              key={skill}
              className="bg-surface-light rounded-full px-2 py-0.5"
            >
              <Text className="text-gray-400 text-xs">{skill}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Agent info with real reputation score */}
      {task.agent_name && (
        <View className="flex-row items-center justify-between mt-2">
          <View className="flex-row items-center flex-1">
            <Text className="text-gray-500 text-xs" numberOfLines={1}>
              {t("browse.postedBy")} {task.agent_name}
            </Text>
            {task.erc8004_agent_id && (
              <View className="bg-blue-900/30 rounded-full px-2 py-0.5 ml-2">
                <Text className="text-blue-400 text-xs font-medium">
                  #{task.erc8004_agent_id}
                </Text>
              </View>
            )}
          </View>
          {agentRep && agentRep.score > 0 && (
            <ReputationBadge score={agentRep.score} size="sm" />
          )}
        </View>
      )}

      {/* Min reputation */}
      {task.min_reputation > 0 && (
        <View className="mt-2">
          <Text className="text-yellow-500 text-xs">
            {t("task.minReputation")}: {task.min_reputation}
          </Text>
        </View>
      )}
    </Pressable>
  );
}
