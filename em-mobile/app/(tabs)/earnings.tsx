import { View, Text, ScrollView, Pressable, RefreshControl, Linking } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../providers/AuthProvider";
import { ConnectWalletButton } from "../../components/ConnectWalletButton";
import { useEarningsSummary, usePaymentHistory } from "../../hooks/api/useEarnings";
import { getExplorerTxUrl } from "../../constants/networks";
import { router } from "expo-router";

export default function EarningsScreen() {
  const { t } = useTranslation();
  const { isAuthenticated, executor } = useAuth();

  const { data: summary, refetch: refetchSummary, isRefetching } = useEarningsSummary(executor?.id || null);
  const { data: history, refetch: refetchHistory } = usePaymentHistory(executor?.id || null);

  const onRefresh = () => {
    refetchSummary();
    refetchHistory();
  };

  if (!isAuthenticated) {
    return (
      <SafeAreaView className="flex-1 bg-black">
        <View className="px-4 pt-4">
          <Text className="text-white text-2xl font-bold">{t("earnings.title")}</Text>
        </View>
        <View className="flex-1 items-center justify-center px-6">
          <Text style={{ fontSize: 48 }}>💰</Text>
          <Text className="text-gray-400 text-lg text-center mt-4 mb-8">
            {t("earnings.connectToView")}
          </Text>
          <View className="w-full">
            <ConnectWalletButton />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="px-4 pt-4 pb-2">
        <Text className="text-white text-2xl font-bold">{t("earnings.title")}</Text>
      </View>

      <ScrollView
        className="flex-1 px-4"
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={onRefresh} tintColor="#fff" />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Total Earned Card */}
        <View className="bg-surface rounded-2xl p-6 mb-4 items-center">
          <Text className="text-gray-400 text-sm">{t("earnings.totalEarned")}</Text>
          <Text className="text-white text-4xl font-bold mt-2">
            ${(summary?.total_earned_usdc || 0).toFixed(2)}
          </Text>
          <Text className="text-gray-500 text-sm mt-1">USDC</Text>
        </View>

        {/* Stats Row */}
        <View className="flex-row gap-3 mb-4">
          <View className="flex-1 bg-surface rounded-2xl p-4 items-center">
            <Text className="text-gray-400 text-xs">{t("earnings.pending")}</Text>
            <Text className="text-yellow-400 text-xl font-bold mt-1">
              ${(summary?.pending_earnings_usdc || 0).toFixed(2)}
            </Text>
          </View>
          <View className="flex-1 bg-surface rounded-2xl p-4 items-center">
            <Text className="text-gray-400 text-xs">{t("earnings.thisMonth")}</Text>
            <Text className="text-green-400 text-xl font-bold mt-1">
              ${(summary?.this_month_usdc || 0).toFixed(2)}
            </Text>
          </View>
        </View>

        {/* Transaction History */}
        <Text className="text-white font-bold text-lg mb-3">
          {t("earnings.transactions")}
        </Text>

        {(!history || history.length === 0) && (
          <View className="bg-surface rounded-2xl p-8 items-center">
            <Text style={{ fontSize: 32 }}>📊</Text>
            <Text className="text-gray-500 mt-2">{t("earnings.empty")}</Text>
          </View>
        )}

        {history?.map((earning) => (
          <Pressable
            key={earning.task_id}
            className="bg-surface rounded-2xl p-4 mb-2"
            onPress={() => router.push(`/task/${earning.task_id}`)}
          >
            <View className="flex-row items-center justify-between">
              <View className="flex-1 mr-3">
                <Text className="text-white font-medium" numberOfLines={1}>
                  {earning.task_title}
                </Text>
                <Text className="text-gray-500 text-xs mt-0.5">
                  {new Date(earning.completed_at).toLocaleDateString(undefined, {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </Text>
              </View>
              <View className="items-end">
                <Text className="text-green-400 font-bold">
                  +${earning.earned_usdc.toFixed(2)}
                </Text>
                <Text className="text-gray-600 text-xs">
                  {t("earnings.netOf", { fee: "13%" })}
                </Text>
              </View>
            </View>

            {/* TX Link */}
            {earning.tx_hash && (
              <Pressable
                className="flex-row items-center mt-2 pt-2 border-t border-gray-800"
                onPress={(e) => {
                  e.stopPropagation?.();
                  Linking.openURL(getExplorerTxUrl(earning.payment_network, earning.tx_hash!));
                }}
              >
                <Text className="text-blue-400 text-xs flex-1">
                  {t("earnings.viewPayment")} · {earning.payment_network}
                </Text>
                <Text className="text-blue-400 text-xs">
                  {earning.tx_hash.slice(0, 10)}... ↗
                </Text>
              </Pressable>
            )}

            {!earning.tx_hash && (
              <View className="flex-row items-center mt-2 pt-2 border-t border-gray-800">
                <Text className="text-gray-600 text-xs">
                  {earning.payment_network}
                </Text>
              </View>
            )}
          </Pressable>
        ))}

        <View className="h-4" />
      </ScrollView>
    </SafeAreaView>
  );
}
