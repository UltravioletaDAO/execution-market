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
import { useAuth } from "../providers/AuthProvider";
import { useRatingsHistory, RatingEntry } from "../hooks/api/useRatings";
import { ReputationBadge } from "../components/ReputationBadge";

function StarRow({ stars }: { stars: number }) {
  const fullStars = Math.floor(stars);
  const hasHalf = stars - fullStars >= 0.5;
  const emptyStars = 5 - fullStars - (hasHalf ? 1 : 0);

  return (
    <View className="flex-row items-center">
      {Array.from({ length: fullStars }).map((_, i) => (
        <Text key={`full-${i}`} style={{ color: "#FFD700", fontSize: 16 }}>
          {"\u2605"}
        </Text>
      ))}
      {hasHalf && (
        <Text style={{ color: "#FFD700", fontSize: 16 }}>{"\u2606"}</Text>
      )}
      {Array.from({ length: emptyStars }).map((_, i) => (
        <Text key={`empty-${i}`} style={{ color: "#374151", fontSize: 16 }}>
          {"\u2606"}
        </Text>
      ))}
    </View>
  );
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function RatingCard({ entry }: { entry: RatingEntry }) {
  const stars = entry.stars ?? (entry.rating / 100) * 5;

  return (
    <View className="bg-surface rounded-2xl p-4 mb-3">
      <View className="flex-row items-center justify-between mb-2">
        <StarRow stars={stars} />
        <Text className="text-gray-500 text-xs">{formatDate(entry.created_at)}</Text>
      </View>
      {entry.task_title ? (
        <Text className="text-gray-400 text-sm mb-1" numberOfLines={1}>
          {entry.task_title}
        </Text>
      ) : null}
      {entry.comment ? (
        <Text className="text-gray-300 text-sm mt-1">{entry.comment}</Text>
      ) : null}
      <View className="flex-row items-center mt-2 gap-2">
        <Text className="text-gray-600 text-xs">
          {entry.rating}/100
        </Text>
        {entry.rater_type ? (
          <Text className="text-gray-600 text-xs">
            {"\u00B7"} {entry.rater_type}
          </Text>
        ) : null}
      </View>
    </View>
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
        <Text className="text-white text-2xl font-bold">
          {avgRating > 0 ? avgRating.toFixed(1) : "\u2014"}
        </Text>
        <Text className="text-gray-400 text-xs mt-1">
          {t("ratings.avgRating")}
        </Text>
        {avgRating > 0 && (
          <View className="mt-1">
            <StarRow stars={avgRating} />
          </View>
        )}
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

export default function RatingsScreen() {
  const { t } = useTranslation();
  const { executor } = useAuth();
  const executorId = executor?.id || null;
  const {
    data: ratings,
    isLoading,
    refetch,
    isRefetching,
  } = useRatingsHistory(executorId);

  const totalRatings = ratings?.length ?? 0;
  const avgStars =
    totalRatings > 0
      ? ratings!.reduce((sum, r) => sum + (r.stars ?? (r.rating / 100) * 5), 0) /
        totalRatings
      : 0;

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
          avgRating={avgStars}
          totalRatings={totalRatings}
          reputationScore={executor?.reputation_score || 0}
        />

        {/* Ratings List */}
        {isLoading ? (
          <View className="items-center justify-center py-20">
            <ActivityIndicator color="#ffffff" size="large" />
          </View>
        ) : !ratings || ratings.length === 0 ? (
          <View className="items-center justify-center py-20 px-6">
            <Text style={{ fontSize: 40 }}>{"\u2B50"}</Text>
            <Text className="text-gray-500 text-base text-center mt-4">
              {t("ratings.noRatings")}
            </Text>
          </View>
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
