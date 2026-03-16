import { useState, useMemo } from "react";
import { View, Text, ScrollView, Pressable, RefreshControl, Linking, Alert, Image } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../providers/AuthProvider";
import { ConnectWalletButton } from "../../components/ConnectWalletButton";
import { useEarningsSummary, usePaymentHistory, CompletedTaskEarning } from "../../hooks/api/useEarnings";
import { getExplorerTxUrl } from "../../constants/networks";
import { router } from "expo-router";

const CHAIN_IMAGES: Record<string, number> = {
  base: require("../../assets/images/chains/base.png"),
  ethereum: require("../../assets/images/chains/ethereum.png"),
  polygon: require("../../assets/images/chains/polygon.png"),
  arbitrum: require("../../assets/images/chains/arbitrum.png"),
  avalanche: require("../../assets/images/chains/avalanche.png"),
  optimism: require("../../assets/images/chains/optimism.png"),
  celo: require("../../assets/images/chains/celo.png"),
  monad: require("../../assets/images/chains/monad.png"),
};

type ChartPeriod = "7d" | "30d" | "all";

const PERIODS: { value: ChartPeriod; labelKey: string }[] = [
  { value: "7d", labelKey: "earnings.period7d" },
  { value: "30d", labelKey: "earnings.period30d" },
  { value: "all", labelKey: "earnings.periodAll" },
];

function getPeriodCutoff(period: ChartPeriod): number {
  const now = Date.now();
  switch (period) {
    case "7d":
      return now - 7 * 24 * 60 * 60 * 1000;
    case "30d":
      return now - 30 * 24 * 60 * 60 * 1000;
    case "all":
      return 0;
  }
}

/** Group earnings by day and return daily totals for chart bars */
function groupByDay(
  items: CompletedTaskEarning[],
  period: ChartPeriod
): { label: string; value: number }[] {
  const cutoff = getPeriodCutoff(period);
  const filtered = items.filter(
    (e) => new Date(e.completed_at).getTime() >= cutoff
  );

  if (filtered.length === 0) return [];

  // Group by date string
  const groups: Record<string, number> = {};
  for (const item of filtered) {
    const d = new Date(item.completed_at);
    const key = `${d.getMonth() + 1}/${d.getDate()}`;
    groups[key] = (groups[key] || 0) + item.earned_usdc;
  }

  // Sort by date order (entries are already sorted desc, reverse for chart)
  const entries = Object.entries(groups);

  // For readability, limit to ~7 bars max by merging if needed
  if (entries.length > 7) {
    // Show last 7 entries
    return entries.slice(-7).map(([label, value]) => ({ label, value }));
  }

  return entries.map(([label, value]) => ({ label, value }));
}

function EarningsChart({
  history,
  period,
  onPeriodChange,
  t,
}: {
  history: CompletedTaskEarning[];
  period: ChartPeriod;
  onPeriodChange: (p: ChartPeriod) => void;
  t: (key: string) => string;
}) {
  const chartData = useMemo(() => groupByDay(history, period), [history, period]);
  const maxValue = useMemo(
    () => Math.max(...chartData.map((d) => d.value), 0.01),
    [chartData]
  );
  const periodTotal = useMemo(
    () => chartData.reduce((sum, d) => sum + d.value, 0),
    [chartData]
  );

  return (
    <View className="bg-surface rounded-2xl mb-4 overflow-hidden">
      {/* Period selector */}
      <View className="flex-row justify-between items-center px-4 pt-4 pb-2">
        <Text className="text-white font-bold text-base">
          {t("earnings.earningsChart")}
        </Text>
        <View className="flex-row bg-black/30 rounded-lg p-0.5">
          {PERIODS.map((p) => (
            <Pressable
              key={p.value}
              onPress={() => onPeriodChange(p.value)}
              className={`px-3 py-1 rounded-md ${
                period === p.value ? "bg-white/15" : ""
              }`}
            >
              <Text
                className={`text-xs font-medium ${
                  period === p.value ? "text-white" : "text-gray-500"
                }`}
              >
                {t(p.labelKey)}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Period total */}
      <View className="px-4 pb-2">
        <Text className="text-green-400 text-xl font-bold">
          ${periodTotal.toFixed(2)}
        </Text>
      </View>

      {/* Bar chart */}
      <View className="px-4 pb-4">
        {chartData.length === 0 ? (
          <View className="items-center py-6">
            <Text className="text-gray-600 text-sm">
              {t("earnings.noDataForPeriod")}
            </Text>
          </View>
        ) : (
          <View style={{ height: 120 }} className="flex-row items-end justify-between">
            {chartData.map((point, index) => {
              const barHeight = Math.max((point.value / maxValue) * 100, 4);
              return (
                <View
                  key={index}
                  className="flex-1 items-center mx-0.5"
                  style={{ height: "100%", justifyContent: "flex-end" }}
                >
                  {point.value > 0 && (
                    <Text className="text-gray-500 text-[9px] mb-1">
                      ${point.value.toFixed(2)}
                    </Text>
                  )}
                  <View
                    className="w-full rounded-t bg-green-500/80"
                    style={{
                      height: `${barHeight}%`,
                      minHeight: 4,
                      maxWidth: 40,
                    }}
                  />
                  <Text className="text-gray-600 text-[9px] mt-1" numberOfLines={1}>
                    {point.label}
                  </Text>
                </View>
              );
            })}
          </View>
        )}
      </View>
    </View>
  );
}

export default function EarningsScreen() {
  const { t } = useTranslation();
  const { isAuthenticated, executor } = useAuth();
  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>("30d");

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

        {/* Earnings Chart */}
        {history && history.length > 0 && (
          <EarningsChart
            history={history}
            period={chartPeriod}
            onPeriodChange={setChartPeriod}
            t={t}
          />
        )}

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
                  WebBrowser.openBrowserAsync(getExplorerTxUrl(earning.payment_network, earning.tx_hash!)).catch(() => Linking.openURL(getExplorerTxUrl(earning.payment_network, earning.tx_hash!)).catch(() => {}));
                }}
              >
                {CHAIN_IMAGES[earning.payment_network] && (
                  <Image
                    source={CHAIN_IMAGES[earning.payment_network]}
                    style={{ width: 14, height: 14, borderRadius: 7, marginRight: 4 }}
                  />
                )}
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
                {CHAIN_IMAGES[earning.payment_network] && (
                  <Image
                    source={CHAIN_IMAGES[earning.payment_network]}
                    style={{ width: 14, height: 14, borderRadius: 7, marginRight: 4 }}
                  />
                )}
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
