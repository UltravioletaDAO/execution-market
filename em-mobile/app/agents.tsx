import { View, Text, ScrollView, Pressable, RefreshControl, ActivityIndicator, Image } from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useAgentDirectory, AgentDirectoryEntry } from "../hooks/api/useReputation";
import { useAgentReputation } from "../hooks/api/useReputation";
import { ReputationBadge } from "../components/ReputationBadge";
import { useState, useCallback, useMemo } from "react";

type RoleTab = "all" | "publisher" | "executor";

function RoleTabSelector({
  activeTab,
  onTabChange,
}: {
  activeTab: RoleTab;
  onTabChange: (tab: RoleTab) => void;
}) {
  const { t } = useTranslation();

  const tabs: { value: RoleTab; label: string }[] = [
    { value: "all", label: t("agents.tabAll") },
    { value: "publisher", label: t("agents.tabPublishers") },
    { value: "executor", label: t("agents.tabExecutors") },
  ];

  return (
    <View className="flex-row bg-surface rounded-xl p-1 mb-4">
      {tabs.map((tab) => (
        <Pressable
          key={tab.value}
          className={`flex-1 py-2 rounded-lg items-center ${
            activeTab === tab.value ? "bg-white/10" : ""
          }`}
          onPress={() => onTabChange(tab.value)}
        >
          <Text
            className={`text-sm font-medium ${
              activeTab === tab.value ? "text-white" : "text-gray-500"
            }`}
          >
            {tab.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

function AgentCard({ agent }: { agent: AgentDirectoryEntry }) {
  const { t } = useTranslation();
  const { data: reputation } = useAgentReputation(agent.erc8004_agent_id ?? null);

  const initial = (agent.display_name || "?").charAt(0).toUpperCase();

  // Deterministic color from name
  const colors = ["#3B82F6", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#EF4444"];
  const colorIndex = agent.display_name
    ? agent.display_name.charCodeAt(0) % colors.length
    : 0;
  const avatarColor = colors[colorIndex];

  const roleLabel =
    agent.role === "both"
      ? `${t("agents.publisher")} + ${t("agents.executor")}`
      : agent.role === "publisher"
        ? t("agents.publisher")
        : t("agents.executor");

  const roleBg =
    agent.role === "publisher"
      ? "bg-purple-900/40"
      : agent.role === "executor"
        ? "bg-green-900/40"
        : "bg-blue-900/40";

  const roleTextColor =
    agent.role === "publisher"
      ? "#C084FC"
      : agent.role === "executor"
        ? "#4ADE80"
        : "#60A5FA";

  return (
    <Pressable
      onPress={() => router.push(`/agent/${agent.executor_id}`)}
      className="bg-surface rounded-2xl p-4 mb-3"
    >
      {/* Top row: avatar + name + badges */}
      <View className="flex-row items-center mb-3">
        {agent.avatar_url ? (
          <Image
            source={{ uri: agent.avatar_url }}
            className="w-12 h-12 rounded-full"
          />
        ) : (
          <View
            className="w-12 h-12 rounded-full items-center justify-center"
            style={{ backgroundColor: avatarColor + "33" }}
          >
            <Text style={{ color: avatarColor, fontSize: 20, fontWeight: "bold" }}>
              {initial}
            </Text>
          </View>
        )}

        <View className="flex-1 ml-3">
          <View className="flex-row items-center flex-wrap gap-1.5">
            <Text className="text-white font-bold text-base">
              {agent.display_name || "Unknown Agent"}
            </Text>
            {agent.verified && (
              <Text style={{ color: "#3B82F6", fontSize: 14 }}>{"\u2713"}</Text>
            )}
          </View>

          <View className="flex-row items-center gap-2 mt-1">
            {agent.erc8004_agent_id != null && (
              <View className="bg-blue-900/40 rounded-full px-2 py-0.5">
                <Text style={{ color: "#60A5FA", fontSize: 11 }}>
                  #{agent.erc8004_agent_id}
                </Text>
              </View>
            )}
            <View className={`${roleBg} rounded-full px-2 py-0.5`}>
              <Text style={{ color: roleTextColor, fontSize: 11 }}>
                {roleLabel}
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* Bio */}
      {agent.bio ? (
        <Text className="text-gray-400 text-sm mb-3" numberOfLines={2}>
          {agent.bio}
        </Text>
      ) : null}

      {/* Stats row */}
      <View className="flex-row items-center justify-between">
        <View className="flex-row items-center gap-4">
          {/* Score */}
          <View className="flex-row items-center">
            <Text className="text-gray-300 text-sm">
              {agent.avg_rating > 0
                ? `${agent.avg_rating < 10 ? Math.round(agent.avg_rating * 20) : Math.round(agent.avg_rating)}/100`
                : "-"}
            </Text>
          </View>

          {/* Tasks completed */}
          <Text className="text-gray-500 text-xs">
            {t("leaderboard.tasksCompleted", { count: agent.tasks_completed })}
          </Text>

          {/* Tasks published */}
          <Text className="text-gray-500 text-xs">
            {t("agents.tasksPublished", { count: agent.tasks_published })}
          </Text>
        </View>

        {/* Reputation badge */}
        {reputation && reputation.score > 0 && (
          <ReputationBadge score={reputation.score} size="sm" />
        )}
      </View>
    </Pressable>
  );
}

export default function AgentsScreen() {
  const { t } = useTranslation();
  const { data: agents, isLoading, refetch, isRefetching } = useAgentDirectory();
  const [refreshing, setRefreshing] = useState(false);
  const [roleTab, setRoleTab] = useState<RoleTab>("all");

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  const filteredAgents = useMemo(() => {
    if (!agents) return [];
    if (roleTab === "all") return agents;
    return agents.filter((a) => a.role === roleTab || a.role === "both");
  }, [agents, roleTab]);

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="mr-3">
          <Text className="text-white text-2xl">{"\u2190"}</Text>
        </Pressable>
        <View>
          <Text className="text-white text-2xl font-bold">{t("agents.title")}</Text>
          <Text className="text-gray-500 text-sm">{t("agents.subtitle")}</Text>
        </View>
      </View>

      {isLoading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      ) : !agents || agents.length === 0 ? (
        <View className="flex-1 items-center justify-center px-6">
          <Text className="text-gray-500 text-lg text-center">
            {t("agents.noAgents")}
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
          <RoleTabSelector activeTab={roleTab} onTabChange={setRoleTab} />
          {filteredAgents.length === 0 ? (
            <View className="items-center justify-center py-20 px-6">
              <Text className="text-gray-500 text-base text-center">
                {t("agents.noAgents")}
              </Text>
            </View>
          ) : (
            filteredAgents.map((agent) => (
              <AgentCard key={agent.executor_id} agent={agent} />
            ))
          )}
          <View className="h-8" />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
