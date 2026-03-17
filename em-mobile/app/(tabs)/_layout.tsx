import { Tabs } from "expo-router";
import { Text, View, Platform } from "react-native";
import { useTranslation } from "react-i18next";

function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const icons: Record<string, string> = {
    browse: "🔍",
    "my-tasks": "📋",
    publish: "➕",
    messages: "💬",
    earnings: "💰",
    profile: "👤",
  };
  return (
    <View className={`items-center justify-center ${focused ? "opacity-100" : "opacity-50"}`}>
      <Text style={{ fontSize: 24 }}>{icons[name] || "•"}</Text>
    </View>
  );
}

export default function TabLayout() {
  const { t } = useTranslation();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: "#000000",
          borderTopColor: "#1a1a1a",
          borderTopWidth: 1,
          height: Platform.OS === "android" ? 90 : 80,
          paddingBottom: Platform.OS === "android" ? 30 : 20,
          paddingTop: 8,
        },
        tabBarActiveTintColor: "#ffffff",
        tabBarInactiveTintColor: "#666666",
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: t("tabs.browse", "Browse"),
          tabBarIcon: ({ focused }) => <TabIcon name="browse" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="my-tasks"
        options={{
          title: t("tabs.myTasks", "My Tasks"),
          tabBarIcon: ({ focused }) => <TabIcon name="my-tasks" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="publish"
        options={{
          title: t("tabs.publish", "Publish"),
          tabBarIcon: ({ focused }) => <TabIcon name="publish" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="messages"
        options={{
          title: t("tabs.messages", "Messages"),
          tabBarIcon: ({ focused }) => <TabIcon name="messages" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="earnings"
        options={{
          title: t("tabs.earnings", "Earnings"),
          tabBarIcon: ({ focused }) => <TabIcon name="earnings" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t("tabs.profile", "Profile"),
          tabBarIcon: ({ focused }) => <TabIcon name="profile" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
