import {
  View,
  Text,
  ScrollView,
  Pressable,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../providers/AuthProvider";
import { useMyTasks } from "../../hooks/api/useTasks";
import { TaskCard } from "../../components/TaskCard";
import { ConnectWalletButton } from "../../components/ConnectWalletButton";

type TabFilter = "active" | "completed" | "all";

export default function MyTasksScreen() {
  const { t } = useTranslation();
  const { isAuthenticated, executor } = useAuth();
  const [activeTab, setActiveTab] = useState<TabFilter>("active");

  const {
    data: allTasks,
    isLoading,
    refetch,
    isRefetching,
  } = useMyTasks(executor?.id || null);

  const filteredTasks = allTasks?.filter((task) => {
    switch (activeTab) {
      case "active":
        return ["accepted", "in_progress", "submitted"].includes(task.status);
      case "completed":
        return ["completed", "cancelled", "expired"].includes(task.status);
      default:
        return true;
    }
  });

  if (!isAuthenticated) {
    return (
      <SafeAreaView className="flex-1 bg-black">
        <View className="px-4 pt-4">
          <Text className="text-white text-2xl font-bold">
            {t("myTasks.title")}
          </Text>
        </View>
        <View className="flex-1 items-center justify-center px-6">
          <Text style={{ fontSize: 48 }}>📋</Text>
          <Text className="text-gray-400 text-lg text-center mt-4 mb-8">
            {t("myTasks.connectWallet")}
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
        <Text className="text-white text-2xl font-bold">
          {t("myTasks.title")}
        </Text>
      </View>

      {/* Tab Filters */}
      <View className="flex-row px-4 gap-2 mb-2">
        {(["active", "completed", "all"] as TabFilter[]).map((tab) => (
          <Pressable
            key={tab}
            className={`flex-1 rounded-full py-2 items-center ${
              activeTab === tab ? "bg-white" : "bg-surface"
            }`}
            onPress={() => setActiveTab(tab)}
          >
            <Text
              className={`text-sm font-medium ${
                activeTab === tab ? "text-black" : "text-gray-400"
              }`}
            >
              {t(`myTasks.${tab}`)}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Task List */}
      <ScrollView
        className="flex-1 px-4"
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor="#ffffff"
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {isLoading && (
          <View className="items-center justify-center py-20">
            <ActivityIndicator color="#ffffff" size="large" />
          </View>
        )}

        {!isLoading && filteredTasks?.length === 0 && (
          <View className="items-center justify-center py-20">
            <Text style={{ fontSize: 48 }}>📋</Text>
            <Text className="text-gray-500 text-lg mt-4">
              {t("myTasks.empty")}
            </Text>
          </View>
        )}

        {filteredTasks?.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}

        <View className="h-4" />
      </ScrollView>
    </SafeAreaView>
  );
}
