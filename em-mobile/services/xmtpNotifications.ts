import * as Notifications from "expo-notifications";

// Configure notification handler
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    priority: Notifications.AndroidNotificationPriority.HIGH,
  }),
});

export async function startXMTPNotificationListener(client: any) {
  try {
    const stream = await client.conversations.streamAllMessages();

    for await (const message of stream) {
      if (message.senderAddress === client.address) continue;

      const content = typeof message.content === "string"
        ? message.content.slice(0, 100)
        : "Nuevo mensaje";

      const shortAddress = `${message.senderAddress.slice(0, 6)}...${message.senderAddress.slice(-4)}`;

      await Notifications.scheduleNotificationAsync({
        content: {
          title: `Mensaje de ${shortAddress}`,
          body: content,
          data: {
            type: "xmtp_message",
            peerAddress: message.senderAddress,
          },
          sound: "default",
        },
        trigger: null,
      });
    }
  } catch (err) {
    __DEV__ && console.error("[XMTP] Notification listener error:", err);
  }
}

export function setupNotificationResponseHandler() {
  Notifications.addNotificationResponseReceivedListener(response => {
    const data = response.notification.request.content.data;
    if (data?.type === "xmtp_message" && data.peerAddress) {
      // Navigation handled by app root listener
      __DEV__ && console.log("[XMTP] Notification tapped for:", data.peerAddress);
    }
  });
}
