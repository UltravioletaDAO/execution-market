import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  Pressable,
  ActivityIndicator,
  Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { router } from "expo-router";
import { useAvailableTasks, useRecentActivity } from "../../hooks/api/useTasks";
import type { Task } from "../../hooks/api/useTasks";
import { useUserLocation } from "../../hooks/useUserLocation";
import { TaskCard } from "../../components/TaskCard";
import { TaskMap } from "../../components/TaskMap";
import { CategoryFilter } from "../../components/CategoryFilter";
import { DrawerMenu } from "../../components/DrawerMenu";
import { TASK_CATEGORIES } from "../../constants/categories";
import { NETWORKS } from "../../constants/networks";

type ViewMode = "list" | "map";

// Chain logo images mapped by network key
const CHAIN_IMAGES: Record<string, number> = {
  base: require("../../assets/images/chains/base.png"),
  ethereum: require("../../assets/images/chains/ethereum.png"),
  polygon: require("../../assets/images/chains/polygon.png"),
  arbitrum: require("../../assets/images/chains/arbitrum.png"),
  avalanche: require("../../assets/images/chains/avalanche.png"),
  optimism: require("../../assets/images/chains/optimism.png"),
  celo: require("../../assets/images/chains/celo.png"),
  monad: require("../../assets/images/chains/monad.png"),
  skale: require("../../assets/images/chains/skale.png"),
};

function formatTimeAgo(dateString: string, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMin < 1) return t("browse.timeNow");
  if (diffMin < 60) return t("browse.timeMinutes", { count: diffMin });
  if (diffHours < 24) return t("browse.timeHours", { count: diffHours });
  if (diffDays < 7) return t("browse.timeDays", { count: diffDays });
  return t("browse.timeWeeks", { count: Math.floor(diffDays / 7) });
}

function formatBounty(bounty: number): string {
  if (bounty >= 1) return `$${bounty.toFixed(2)}`;
  return `$${bounty.toFixed(3)}`;
}

interface StatusConfig {
  label: string;
  dotColor: string;
  bgColor: string;
  textColor: string;
}

function getStatusConfig(status: string, t: (key: string) => string): StatusConfig {
  switch (status) {
    case "completed":
      return {
        label: t("browse.activityCompleted"),
        dotColor: "#22c55e",
        bgColor: "rgba(34, 197, 94, 0.15)",
        textColor: "#4ade80",
      };
    case "in_progress":
    case "submitted":
    case "verifying":
      return {
        label: t("browse.activityInProgress"),
        dotColor: "#f59e0b",
        bgColor: "rgba(245, 158, 11, 0.15)",
        textColor: "#fbbf24",
      };
    case "accepted":
      return {
        label: t("browse.activityAccepted"),
        dotColor: "#3b82f6",
        bgColor: "rgba(59, 130, 246, 0.15)",
        textColor: "#60a5fa",
      };
    case "published":
    default:
      return {
        label: t("browse.activityNew"),
        dotColor: "#ffffff",
        bgColor: "rgba(255, 255, 255, 0.08)",
        textColor: "#d1d5db",
      };
  }
}

function ActivityCard({ task, t }: { task: Task; t: (key: string) => string }) {
  const category = TASK_CATEGORIES.find((c) => c.key === task.category);
  const network = NETWORKS.find((n) => n.key === task.payment_network);
  const statusConfig = getStatusConfig(task.status, t);
  const chainImage = CHAIN_IMAGES[task.payment_network];

  return (
    <Pressable
      className="rounded-xl px-3 py-2.5 mb-1.5 active:opacity-80"
      style={{
        backgroundColor: "#1a1a1a",
        borderWidth: 1,
        borderColor: "rgba(255,255,255,0.06)",
      }}
      onPress={() => router.push(`/task/${task.id}`)}
    >
      {/* Single row: icon + content + bounty */}
      <View className="flex-row items-center">
        {/* Category icon */}
        <Text style={{ fontSize: 18, marginRight: 10 }}>{category?.icon || "📌"}</Text>

        {/* Middle: title + meta row */}
        <View className="flex-1 mr-3">
          <Text className="text-white font-semibold text-sm" numberOfLines={1}>
            {task.title}
          </Text>
          <View className="flex-row items-center mt-1 gap-2">
            {/* Status dot + label */}
            <View className="flex-row items-center">
              <View
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: 2.5,
                  backgroundColor: statusConfig.dotColor,
                  marginRight: 3,
                }}
              />
              <Text style={{ color: statusConfig.textColor, fontSize: 10, fontWeight: "600" }}>
                {statusConfig.label}
              </Text>
            </View>

            {/* Chain logo + name */}
            {network && (
              <View className="flex-row items-center">
                {chainImage && (
                  <Image
                    source={chainImage}
                    style={{ width: 12, height: 12, borderRadius: 6, marginRight: 3 }}
                  />
                )}
                <Text style={{ color: network.color, fontSize: 10, fontWeight: "500" }}>
                  {network.name}
                </Text>
              </View>
            )}

            {/* Agent name */}
            {task.agent_name && (
              <Text className="text-gray-600 text-xs" numberOfLines={1}>
                {task.agent_name}
              </Text>
            )}

            {/* Time ago */}
            <Text className="text-gray-600 text-xs">
              {formatTimeAgo(task.created_at, t)}
            </Text>
          </View>
        </View>

        {/* Bounty badge (right side) */}
        <View className="bg-green-900/30 rounded-full px-2.5 py-1">
          <Text className="text-green-400 font-bold text-xs">
            {formatBounty(task.bounty_usd)}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

type StatusFilter = "all" | "completed" | "in_progress" | "published";

function StatusFilterPills({
  selected,
  onSelect,
}: {
  selected: StatusFilter;
  onSelect: (f: StatusFilter) => void;
}) {
  const { t } = useTranslation();
  const filters: { key: StatusFilter; label: string }[] = [
    { key: "all", label: t("browse.filterAll") },
    { key: "completed", label: t("browse.filterCompleted") },
    { key: "in_progress", label: t("browse.filterInProgress") },
    { key: "published", label: t("browse.filterNew") },
  ];

  return (
    <View className="flex-row gap-2 mb-3">
      {filters.map((f) => (
        <Pressable
          key={f.key}
          className={`rounded-full px-3 py-1.5 ${
            selected === f.key ? "bg-white" : "bg-surface"
          }`}
          style={
            selected !== f.key
              ? { borderWidth: 1, borderColor: "rgba(255,255,255,0.08)" }
              : undefined
          }
          onPress={() => onSelect(f.key)}
        >
          <Text
            className={`text-xs font-semibold ${
              selected === f.key ? "text-black" : "text-gray-400"
            }`}
          >
            {f.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

function ActivityFeed({
  categoryFilter,
  statusFilter,
}: {
  categoryFilter: string | null;
  statusFilter: StatusFilter;
}) {
  const { t } = useTranslation();
  const {
    data: rawActivities,
    isLoading,
    isError,
  } = useRecentActivity(30);

  let activities = rawActivities;

  // Apply category filter
  if (categoryFilter) {
    activities = activities?.filter((task) => task.category === categoryFilter);
  }

  // Apply status filter
  if (statusFilter !== "all" && activities) {
    if (statusFilter === "in_progress") {
      activities = activities.filter((task) =>
        ["in_progress", "submitted", "verifying", "accepted"].includes(task.status)
      );
    } else {
      activities = activities.filter((task) => task.status === statusFilter);
    }
  }

  // Limit to 15 if no filters
  if (!categoryFilter && statusFilter === "all") {
    activities = activities?.slice(0, 15);
  }

  if (isLoading) {
    return (
      <View className="px-4 py-4">
        <Text className="text-white font-bold text-lg mb-3">
          {t("browse.activityTitle")}
        </Text>
        <View className="items-center py-6">
          <ActivityIndicator color="#ffffff" size="small" />
        </View>
      </View>
    );
  }

  if (isError || !activities?.length) {
    return (
      <View className="px-4 py-4">
        <Text className="text-white font-bold text-lg mb-3">
          {t("browse.activityTitle")}
        </Text>
        <View className="items-center py-4">
          <Text className="text-gray-600 text-sm">
            {t("browse.activityEmpty")}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View className="py-3 px-4">
      <Text className="text-white font-bold text-lg mb-3">
        {t("browse.activityTitle")}
      </Text>
      {activities.map((task) => (
        <ActivityCard key={task.id} task={task} t={t} />
      ))}
    </View>
  );
}

export default function BrowseTasksScreen() {
  const { t } = useTranslation();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { location, requestLocation } = useUserLocation();

  const {
    data: tasks,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useAvailableTasks({
    category: selectedCategory || undefined,
    lat: location?.lat,
    lng: location?.lng,
    radius_km: location ? 50 : undefined,
    limit: 50,
  });

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Drawer Menu */}
      <DrawerMenu visible={drawerOpen} onClose={() => setDrawerOpen(false)} />

      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-1">
        <Pressable
          className="w-9 h-9 items-center justify-center mr-3"
          onPress={() => setDrawerOpen(true)}
        >
          <Text style={{ color: "#ffffff", fontSize: 22 }}>{"\u2630"}</Text>
        </Pressable>
        <View className="flex-1">
          <Text className="text-white text-2xl font-bold">
            {t("browse.title")}
          </Text>
          <Text className="text-gray-500 text-sm mt-0.5">
            {t("browse.subtitle")}
          </Text>
        </View>
      </View>

      {/* View Mode Toggle */}
      <View className="flex-row px-4 gap-2 mb-1 mt-2">
        <Pressable
          className={`flex-1 rounded-full py-2 items-center ${
            viewMode === "list" ? "bg-white" : "bg-surface"
          }`}
          onPress={() => setViewMode("list")}
        >
          <Text
            className={`font-medium ${
              viewMode === "list" ? "text-black font-bold" : "text-gray-400"
            }`}
          >
            {t("browse.listView")}
          </Text>
        </Pressable>
        <Pressable
          className={`flex-1 rounded-full py-2 items-center ${
            viewMode === "map" ? "bg-white" : "bg-surface"
          }`}
          onPress={() => {
            setViewMode("map");
            if (!location) requestLocation();
          }}
        >
          <Text
            className={`font-medium ${
              viewMode === "map" ? "text-black font-bold" : "text-gray-400"
            }`}
          >
            {t("browse.mapView")}
          </Text>
        </Pressable>
      </View>

      {/* Category Filter */}
      <CategoryFilter
        selected={selectedCategory}
        onSelect={setSelectedCategory}
      />

      {/* Loading State */}
      {isLoading && (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color="#ffffff" size="large" />
          <Text className="text-gray-500 mt-4">{t("common.loading")}</Text>
        </View>
      )}

      {/* Error State */}
      {isError && (
        <View className="flex-1 items-center justify-center py-20">
          <Text className="text-red-500 text-lg mb-2">
            {t("common.error")}
          </Text>
          <Text className="text-gray-500 text-center mb-4">
            {(error as Error)?.message || "Unknown error"}
          </Text>
          <View className="bg-surface rounded-full px-6 py-3">
            <Text
              className="text-white font-medium"
              onPress={() => refetch()}
            >
              {t("common.retry")}
            </Text>
          </View>
        </View>
      )}

      {/* Map View */}
      {!isLoading && !isError && viewMode === "map" && (
        <ScrollView
          className="flex-1"
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={handleRefresh}
              tintColor="#ffffff"
            />
          }
        >
          <View className="px-4 pt-2">
            <TaskMap tasks={(tasks || []).filter((t) => t.status === "published")} userLocation={location} />
          </View>
          {/* Compact task list below map */}
          <View className="px-4 mt-3">
            {tasks?.filter((t) => t.location_lat != null && t.location_lng != null).length === 0 && (
              <Text className="text-gray-500 text-sm text-center py-4">
                {t("browse.noLocationTasks")}
              </Text>
            )}
            {tasks?.map((task) => (
              <TaskCard key={task.id} task={task} compact />
            ))}
            <View className="h-4" />
          </View>
        </ScrollView>
      )}

      {/* List View */}
      {!isLoading && !isError && viewMode === "list" && (
        <ScrollView
          className="flex-1 px-4"
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={handleRefresh}
              tintColor="#ffffff"
            />
          }
          showsVerticalScrollIndicator={false}
        >
          {/* Status Filter Pills */}
          <View className="mt-2">
            <StatusFilterPills selected={statusFilter} onSelect={setStatusFilter} />
          </View>

          {/* Activity Feed */}
          <View className="-mx-4 -mt-1">
            <ActivityFeed categoryFilter={selectedCategory} statusFilter={statusFilter} />
          </View>

          {/* Separator */}
          <View className="h-px bg-white/5 my-2" />

          {/* Available Tasks heading */}
          <Text className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-3 mt-2">
            {t("browse.availableTasks")}
          </Text>

          {tasks?.length === 0 && (
            <View className="items-center justify-center py-20">
              <Text style={{ fontSize: 48 }}>🔍</Text>
              <Text className="text-gray-500 text-lg mt-4">
                {t("browse.empty")}
              </Text>
            </View>
          )}

          {tasks?.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}

          {/* Bottom padding for tab bar */}
          <View className="h-4" />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
