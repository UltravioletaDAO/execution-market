import { createClient } from "@dynamic-labs/client";
import { ReactNativeExtension } from "@dynamic-labs/react-native-extension";

const DYNAMIC_ENVIRONMENT_ID =
  process.env.EXPO_PUBLIC_DYNAMIC_ENVIRONMENT_ID || "";

export const dynamicClient = createClient({
  environmentId: DYNAMIC_ENVIRONMENT_ID,
  appName: "Execution Market",
  appLogoUrl: "https://execution.market/favicon.ico",
}).extend(ReactNativeExtension());
