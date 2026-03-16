import {
  View,
  Text,
  ScrollView,
  Pressable,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useLeaderboard, LeaderboardEntry } from "../hooks/api/useReputation";
import { ReputationBadge } from "../components/ReputationBadge";

function getRankColor(rank: number): string {
  if (rank === 1) return "#FFD700"; // gold
  if (rank === 2) return "#C0C0C0"; // silver
  if (rank === 3) return "#CD7F32"; // bronze
  return "#6B7280"; // gray
}

function LeaderboardCard({ entry }: { entry: LeaderboardEntry }) {
  const { t } = useTranslation();
  const rankColor = getRankColor(entry.rank);

  // Convert 0-5 scale to 0-100 if needed
  const displayScore =
    entry.avg_rating != null && entry.avg_rating > 0
      ? entry.avg_rating < 10
        ? Math.round(entry.avg_rating * 20)
        : Math.round(entry.avg_rating)
      : null;

  return (
    <View className="bg-surface rounded-2xl p-4 mb-3 flex-row items-center">
      {/* Rank */}
      <View className="w-10 items-center mr-3">
        <Text
          style={{
            color: rankColor,
            fontSize: entry.rank <= 3 ? 24 : 18,
            fontWeight: "bold",
          }}
        >
          {entry.rank}
        </Text>
      </View>

      {/* Info */}
      <View className="flex-1">
        <Text className="text-white text-base font-semibold">
          {entry.display_name || "Anonymous"}
        </Text>
        <View className="flex-row items-center mt-1.5 gap-3">
          <ReputationBadge score={entry.reputation_score} size="sm" />
          <Text className="text-gray-500 text-xs">
            {t("leaderboard.tasksCompleted", {
              count: entry.tasks_completed,
            })}
          </Text>
        </View>
        {displayScore != null && (
          <View className="mt-1.5">
            <Text className="text-gray-300 text-xs font-semibold">
              {displayScore}/100
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

export default function LeaderboardScreen() {
  const { t } = useTranslation();
  const { data: entries, isLoading, refetch, isRefetching } = useLeaderboard();

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
            {t("leaderboard.title")}
          </Text>
          <Text className="text-gray-500 text-sm mt-1">
            {t("leaderboard.subtitle")}
          </Text>
        </View>

        {/* Content */}
        {isLoading ? (
          <View className="items-center justify-center py-20">
            <ActivityIndicator color="#ffffff" size="large" />
          </View>
        ) : !entries || entries.length === 0 ? (
          <View className="items-center justify-center py-20">
            <Text className="text-gray-500 text-base">
              {t("leaderboard.noWorkers")}
            </Text>
          </View>
        ) : (
          <View className="mb-8">
            {entries.map((entry) => (
              <LeaderboardCard key={entry.id} entry={entry} />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
