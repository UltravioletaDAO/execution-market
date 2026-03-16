import { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  RefreshControl,
  ActivityIndicator,
  Linking,
} from "react-native";
import * as WebBrowser from "expo-web-browser";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useAuth } from "../providers/AuthProvider";
import {
  useRatingsHistory,
  useRatingsGiven,
  RatingEntry,
} from "../hooks/api/useRatings";
import { ReputationBadge } from "../components/ReputationBadge";
import { getExplorerTxUrl } from "../constants/networks";

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function RatingCard({ entry }: { entry: RatingEntry }) {
  const openTx = async () => {
    if (!entry.payment_tx || !entry.payment_network) return;
    const url = getExplorerTxUrl(entry.payment_network, entry.payment_tx);
    try {
      await WebBrowser.openBrowserAsync(url);
    } catch {
      Linking.openURL(url).catch(() => {});
    }
  };

  return (
    <Pressable
      className="bg-surface rounded-2xl p-4 mb-3"
      onPress={() => router.push(`/task/${entry.task_id}`)}
    >
      <View className="flex-row items-center justify-between mb-2">
        <View className="flex-row items-baseline">
          <Text className="text-white text-xl font-bold">{entry.rating}</Text>
          <Text className="text-gray-500 text-sm ml-1">/100</Text>
        </View>
        <Text className="text-gray-500 text-xs">{formatDate(entry.created_at)}</Text>
      </View>
      {entry.task_title ? (
        <Text className="text-white text-sm mb-1" numberOfLines={1}>
          {entry.task_title}
        </Text>
      ) : null}
      {entry.comment ? (
        <Text className="text-gray-300 text-sm italic mt-1">"{entry.comment}"</Text>
      ) : null}
      <View className="flex-row items-center justify-between mt-2">
        {entry.rater_type ? (
          <Text className="text-gray-600 text-xs">{entry.rater_type}</Text>
        ) : <View />}
        {entry.payment_tx && entry.payment_network ? (
          <Pressable onPress={openTx} hitSlop={8}>
            <Text className="text-blue-400 text-xs">
              TX: {entry.payment_tx.slice(0, 8)}... ↗
            </Text>
          </Pressable>
        ) : null}
      </View>
    </Pressable>
  );
}

function SummaryStats({
  avgRating,
  totalRatings,
  reputationScore,
}: {
  avgRating: number;
  totalRatings: number;
  reputationScore: number;
}) {
  const { t } = useTranslation();

  return (
    <View className="flex-row gap-3 mb-6">
      <View className="flex-1 bg-surface rounded-2xl p-4 items-center">
        <View className="flex-row items-baseline">
          <Text className="text-white text-2xl font-bold">
            {avgRating > 0 ? Math.round(avgRating) : "\u2014"}
          </Text>
          {avgRating > 0 && (
            <Text className="text-gray-500 text-sm ml-1">/100</Text>
          )}
        </View>
        <Text className="text-gray-400 text-xs mt-1">
          {t("ratings.avgRating")}
        </Text>
      </View>
      <View className="flex-1 bg-surface rounded-2xl p-4 items-center">
        <Text className="text-white text-2xl font-bold">{totalRatings}</Text>
        <Text className="text-gray-400 text-xs mt-1">
          {t("ratings.totalRatings")}
        </Text>
      </View>
      <View className="flex-1 bg-surface rounded-2xl p-4 items-center">
        <ReputationBadge score={reputationScore} size="sm" />
        <Text className="text-gray-400 text-xs mt-2">
          {t("reputation.score")}
        </Text>
      </View>
    </View>
  );
}

type TabType = "received" | "given";

function TabSelector({
  activeTab,
  onTabChange,
}: {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}) {
  const { t } = useTranslation();

  return (
    <View className="flex-row bg-surface rounded-xl p-1 mb-4">
      <Pressable
        className={`flex-1 py-2 rounded-lg items-center ${
          activeTab === "received" ? "bg-white/10" : ""
        }`}
        onPress={() => onTabChange("received")}
      >
        <Text
          className={`text-sm font-medium ${
            activeTab === "received" ? "text-white" : "text-gray-500"
          }`}
        >
          {t("ratings.tabReceived")}
        </Text>
      </Pressable>
      <Pressable
        className={`flex-1 py-2 rounded-lg items-center ${
          activeTab === "given" ? "bg-white/10" : ""
        }`}
        onPress={() => onTabChange("given")}
      >
        <Text
          className={`text-sm font-medium ${
            activeTab === "given" ? "text-white" : "text-gray-500"
          }`}
        >
          {t("ratings.tabGiven")}
        </Text>
      </Pressable>
    </View>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <View className="items-center justify-center py-20 px-6">
      <Text style={{ fontSize: 40 }}>{"\u2B50"}</Text>
      <Text className="text-gray-500 text-base text-center mt-4">
        {message}
      </Text>
    </View>
  );
}

export default function RatingsScreen() {
  const { t } = useTranslation();
  const { executor } = useAuth();
  const executorId = executor?.id || null;
  const [activeTab, setActiveTab] = useState<TabType>("received");

  const {
    data: ratingsReceived,
    isLoading: isLoadingReceived,
    refetch: refetchReceived,
    isRefetching: isRefetchingReceived,
  } = useRatingsHistory(executorId);

  const {
    data: ratingsGiven,
    isLoading: isLoadingGiven,
    refetch: refetchGiven,
    isRefetching: isRefetchingGiven,
  } = useRatingsGiven(executorId);

  const isLoading = activeTab === "received" ? isLoadingReceived : isLoadingGiven;
  const isRefetching = activeTab === "received" ? isRefetchingReceived : isRefetchingGiven;
  const ratings = activeTab === "received" ? ratingsReceived : ratingsGiven;

  const refetch = () => {
    if (activeTab === "received") {
      refetchReceived();
    } else {
      refetchGiven();
    }
  };

  // Summary stats are based on received ratings only
  const totalRatings = ratingsReceived?.length ?? 0;
  const avgScore =
    totalRatings > 0
      ? ratingsReceived!.reduce((sum, r) => sum + r.rating, 0) / totalRatings
      : 0;

  const emptyMessage =
    activeTab === "received"
      ? t("ratings.noRatings")
      : t("ratings.noRatingsGiven");

  return (
    <SafeAreaView className="flex-1 bg-black">
      {/* Header */}
      <View className="flex-row items-center px-4 pt-4 pb-2">
        <Pressable onPress={() => router.back()} className="py-2 pr-4">
          <Text className="text-white text-lg">
            {"\u2190"} {t("common.back")}
          </Text>
        </Pressable>
      </View>

      <ScrollView
        className="flex-1 px-4"
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor="#ffffff"
          />
        }
      >
        {/* Title */}
        <View className="mt-2 mb-6">
          <Text className="text-white text-2xl font-bold">
            {t("ratings.title")}
          </Text>
          <Text className="text-gray-500 text-sm mt-1">
            {t("ratings.subtitle")}
          </Text>
        </View>

        {/* Summary Stats */}
        <SummaryStats
          avgRating={avgScore}
          totalRatings={totalRatings}
          reputationScore={executor?.reputation_score || 0}
        />

        {/* Tab Selector */}
        <TabSelector activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Ratings List */}
        {isLoading ? (
          <View className="items-center justify-center py-20">
            <ActivityIndicator color="#ffffff" size="large" />
          </View>
        ) : !ratings || ratings.length === 0 ? (
          <EmptyState message={emptyMessage} />
        ) : (
          <View className="mb-8">
            {ratings.map((entry) => (
              <RatingCard key={entry.id} entry={entry} />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
