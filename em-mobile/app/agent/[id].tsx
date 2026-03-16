import {
  View,
  Text,
  ScrollView,
  Pressable,
  RefreshControl,
  ActivityIndicator,
  Image,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useAgentDetail } from "../../hooks/api/useReputation";
import { useAgentReputation } from "../../hooks/api/useReputation";
import { ReputationBadge } from "../../components/ReputationBadge";
import { useState, useCallback } from "react";

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <View className="bg-black/40 rounded-xl p-4 flex-1 items-center">
      <Text className="text-white text-xl font-bold">{value}</Text>
      <Text className="text-gray-500 text-xs mt-1 text-center">{label}</Text>
    </View>
  );
}

export default function AgentDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const {
    data: agent,
    isLoading,
    refetch,
    isRefetching,
  } = useAgentDetail(id ?? "");
  const { data: reputation } = useAgentReputation(
    agent?.erc8004_agent_id ?? null
  );
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  // Avatar helpers (same as agents.tsx)
  const colors = [
    "#3B82F6",
    "#8B5CF6",
    "#EC4899",
    "#F59E0B",
    "#10B981",
    "#EF4444",
  ];
  const initial = agent
    ? (agent.display_name || "?").charAt(0).toUpperCase()
    : "?";
  const colorIndex = agent?.display_name
    ? agent.display_name.charCodeAt(0) % colors.length
    : 0;
  const avatarColor = colors[colorIndex];

  const roleLabel = agent
    ? agent.role === "both"
      ? `${t("agents.publisher")} + ${t("agents.executor")}`
      : agent.role === "publisher"
        ? t("agents.publisher")
        : t("agents.executor")
    : "";

  const roleBg = agent
    ? agent.role === "publisher"
      ? "bg-purple-900/40"
      : agent.role === "executor"
        ? "bg-green-900/40"
        : "bg-blue-900/40"
    : "bg-gray-800";

  const roleTextColor = agent
    ? agent.role === "publisher"
      ? "#C084FC"
      : agent.role === "executor"
        ? "#4ADE80"
        : "#60A5FA"
    : "#9CA3AF";

  // Format bounty as dollars
  const formatBounty = (amount: number) => {
    if (amount >= 1000) return `$${(amount / 1000).toFixed(1)}k`;
    if (amount > 0) return `$${amount.toFixed(2)}`;
    return "$0";
  };

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="mr-3">
          <Text className="text-white text-2xl">{"\u2190"}</Text>
        </Pressable>
        <Text className="text-white text-lg font-bold flex-1" numberOfLines={1}>
          {agent?.display_name || t("common.loading")}
        </Text>
      </View>

      {isLoading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      ) : !agent ? (
        <View className="flex-1 items-center justify-center px-6">
          <Text className="text-gray-500 text-lg text-center">
            {t("agentDetail.noData")}
          </Text>
        </View>
      ) : (
        <ScrollView
          className="flex-1 px-4 mt-2"
          refreshControl={
            <RefreshControl
              refreshing={refreshing || isRefetching}
              onRefresh={onRefresh}
              tintColor="#3B82F6"
            />
          }
        >
          {/* Profile Card */}
          <View className="bg-surface rounded-2xl p-5 mb-4 items-center">
            {/* Large Avatar */}
            {agent.avatar_url ? (
              <Image
                source={{ uri: agent.avatar_url }}
                className="w-24 h-24 rounded-full mb-4"
              />
            ) : (
              <View
                className="w-24 h-24 rounded-full items-center justify-center mb-4"
                style={{ backgroundColor: avatarColor + "33" }}
              >
                <Text
                  style={{
                    color: avatarColor,
                    fontSize: 40,
                    fontWeight: "bold",
                  }}
                >
                  {initial}
                </Text>
              </View>
            )}

            {/* Name + Verified */}
            <View className="flex-row items-center gap-2 mb-2">
              <Text className="text-white font-bold text-xl">
                {agent.display_name || "Unknown Agent"}
              </Text>
              {agent.verified && (
                <Text style={{ color: "#3B82F6", fontSize: 18 }}>
                  {"\u2713"}
                </Text>
              )}
            </View>

            {/* Badges row */}
            <View className="flex-row items-center gap-2 mb-4">
              {agent.erc8004_agent_id != null && (
                <View className="bg-blue-900/40 rounded-full px-3 py-1">
                  <Text style={{ color: "#60A5FA", fontSize: 13 }}>
                    ERC-8004 #{agent.erc8004_agent_id}
                  </Text>
                </View>
              )}
              <View className={`${roleBg} rounded-full px-3 py-1`}>
                <Text style={{ color: roleTextColor, fontSize: 13 }}>
                  {roleLabel}
                </Text>
              </View>
            </View>

            {/* Reputation Badge (large) */}
            {reputation && reputation.score > 0 && (
              <ReputationBadge score={reputation.score} size="lg" />
            )}
          </View>

          {/* Stats Grid */}
          <View className="flex-row gap-3 mb-4">
            <StatCard
              label={t("agentDetail.tasksCompleted")}
              value={agent.tasks_completed}
            />
            <StatCard
              label={t("agentDetail.tasksPublished")}
              value={agent.tasks_published}
            />
          </View>
          <View className="flex-row gap-3 mb-4">
            <StatCard
              label={t("agentDetail.avgRating")}
              value={
                agent.avg_rating > 0
                  ? `${agent.avg_rating < 10 ? Math.round(agent.avg_rating * 20) : Math.round(agent.avg_rating)}/100`
                  : "-"
              }
            />
            <StatCard
              label={t("agentDetail.totalBounty")}
              value={formatBounty(agent.total_bounty_usd)}
            />
          </View>

          {/* Bio */}
          {agent.bio ? (
            <View className="bg-surface rounded-2xl p-4 mb-4">
              <Text className="text-gray-500 text-xs font-bold mb-2 uppercase">
                {t("agentDetail.bio")}
              </Text>
              <Text className="text-gray-300 text-sm leading-5">
                {agent.bio}
              </Text>
            </View>
          ) : null}

          {/* Capabilities / Skills */}
          {agent.capabilities && agent.capabilities.length > 0 ? (
            <View className="bg-surface rounded-2xl p-4 mb-4">
              <Text className="text-gray-500 text-xs font-bold mb-3 uppercase">
                {t("agentDetail.capabilities")}
              </Text>
              <View className="flex-row flex-wrap gap-2">
                {agent.capabilities.map((skill, idx) => {
                  const capColors = [
                    { bg: "#312e81", text: "#A5B4FC" }, // indigo
                    { bg: "#064e3b", text: "#6EE7B7" }, // emerald
                    { bg: "#831843", text: "#F9A8D4" }, // pink
                    { bg: "#78350f", text: "#FCD34D" }, // amber
                    { bg: "#164e63", text: "#67E8F9" }, // cyan
                    { bg: "#4c1d95", text: "#C4B5FD" }, // violet
                  ];
                  const c = capColors[idx % capColors.length];
                  return (
                    <View
                      key={idx}
                      className="rounded-full px-3 py-1.5"
                      style={{ backgroundColor: c.bg + "66" }}
                    >
                      <Text style={{ color: c.text, fontSize: 12 }}>
                        {t(`agentDetail.cap_${skill}`, { defaultValue: skill.replace(/_/g, " ") })}
                      </Text>
                    </View>
                  );
                })}
              </View>
            </View>
          ) : null}

          <View className="h-8" />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
