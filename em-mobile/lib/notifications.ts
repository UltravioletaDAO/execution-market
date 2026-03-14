import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { Platform } from "react-native";
import { apiClient } from "./api";

// Configure notification behavior
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    console.log("Push notifications require a physical device");
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    return null;
  }

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "Execution Market",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
    });
  }

  const projectId =
    process.env.EXPO_PUBLIC_PROJECT_ID ||
    Constants.expoConfig?.extra?.eas?.projectId;

  if (!projectId) {
    console.warn("No EAS projectId configured for push notifications");
    return null;
  }

  const token = await Notifications.getExpoPushTokenAsync({ projectId });

  return token.data;
}

export async function registerPushToken(executorId: string, pushToken: string) {
  try {
    await apiClient("/api/v1/notifications/register", {
      method: "POST",
      body: { executor_id: executorId, push_token: pushToken, platform: Platform.OS },
    });
  } catch {
    // Silent fail — push registration is optional
  }
}

export function addNotificationListener(
  callback: (notification: Notifications.Notification) => void
) {
  return Notifications.addNotificationReceivedListener(callback);
}

export function addNotificationResponseListener(
  callback: (response: Notifications.NotificationResponse) => void
) {
  return Notifications.addNotificationResponseReceivedListener(callback);
}
