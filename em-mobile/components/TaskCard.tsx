import { View, Text, Pressable } from "react-native";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import type { Task } from "../hooks/api/useTasks";
import { TASK_CATEGORIES } from "../constants/categories";
import { NETWORKS } from "../constants/networks";

function formatDeadline(deadline: string, t: (key: string) => string): string {
  const now = new Date();
  const dl = new Date(deadline);
  const diffMs = dl.getTime() - now.getTime();

  if (diffMs < 0) return t("task.expired");

  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (hours > 24) return `${Math.floor(hours / 24)}d`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatBounty(bounty: number): string {
  if (bounty >= 1) return `$${bounty.toFixed(2)}`;
  return `$${bounty.toFixed(3)}`;
}

interface TaskCardProps {
  task: Task;
  compact?: boolean;
}

export function TaskCard({ task, compact = false }: TaskCardProps) {
  const { t } = useTranslation();
  const category = TASK_CATEGORIES.find((c) => c.key === task.category);
  const network = NETWORKS.find((n) => n.key === task.payment_network);

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
      {!compact && task.skills_required?.length > 0 && (
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

      {/* Min reputation */}
      {task.min_reputation > 0 && (
        <View className="mt-2">
          <Text className="text-yellow-500 text-xs">
            ⭐ {t("task.minReputation")}: {task.min_reputation}
          </Text>
        </View>
      )}
    </Pressable>
  );
}
