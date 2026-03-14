import { View, Text, Pressable, ActivityIndicator } from "react-native";
import { useTranslation } from "react-i18next";
import { useUserLocation } from "../hooks/useUserLocation";

interface GPSCaptureProps {
  onCapture: (coords: { lat: number; lng: number; accuracy: number; timestamp: string }) => void;
}

function getAccuracyLabel(accuracy: number, t: (key: string) => string): { label: string; color: string } {
  if (accuracy <= 10) return { label: t("gps.excellent"), color: "text-green-400" };
  if (accuracy <= 30) return { label: t("gps.good"), color: "text-green-300" };
  if (accuracy <= 100) return { label: t("gps.acceptable"), color: "text-yellow-400" };
  return { label: t("gps.low"), color: "text-red-400" };
}

export function GPSCapture({ onCapture }: GPSCaptureProps) {
  const { t } = useTranslation();
  const { location, error, loading, requestLocation } = useUserLocation();

  const accuracy = location ? getAccuracyLabel(location.accuracy, t) : null;

  return (
    <View className="bg-surface rounded-2xl p-4">
      <View className="flex-row items-center justify-between mb-3">
        <Text className="text-white font-bold">{t("gps.title")}</Text>
        {location && (
          <Pressable onPress={requestLocation}>
            <Text className="text-blue-400 text-sm">{t("gps.refresh")}</Text>
          </Pressable>
        )}
      </View>

      {loading && (
        <View className="items-center py-4">
          <ActivityIndicator color="#ffffff" />
          <Text className="text-gray-400 text-sm mt-2">
            {t("gps.gettingLocation")}
          </Text>
        </View>
      )}

      {error && !loading && (
        <View className="bg-red-900/20 rounded-xl p-3 mb-3">
          <Text className="text-red-400 text-sm">{error}</Text>
        </View>
      )}

      {!location && !loading && (
        <Pressable
          className="bg-surface-light rounded-xl py-4 items-center"
          onPress={requestLocation}
        >
          <Text style={{ fontSize: 24 }}>{"\uD83D\uDCCD"}</Text>
          <Text className="text-gray-400 text-sm mt-2">
            {t("gps.tapToCapture")}
          </Text>
        </Pressable>
      )}

      {location && !loading && (
        <View>
          <View className="flex-row justify-between mb-2">
            <View>
              <Text className="text-gray-400 text-xs">{t("gps.latitude")}</Text>
              <Text className="text-white font-mono text-sm">
                {location.lat.toFixed(6)}
              </Text>
            </View>
            <View className="items-end">
              <Text className="text-gray-400 text-xs">{t("gps.longitude")}</Text>
              <Text className="text-white font-mono text-sm">
                {location.lng.toFixed(6)}
              </Text>
            </View>
          </View>

          <View className="flex-row items-center justify-between mt-2 pt-2 border-t border-gray-800">
            <View className="flex-row items-center">
              <Text className="text-gray-400 text-xs mr-2">{t("gps.accuracy")}</Text>
              <Text className={`text-xs font-bold ${accuracy?.color}`}>
                {accuracy?.label} ({location.accuracy.toFixed(0)}m)
              </Text>
            </View>
            <Pressable
              className="bg-white rounded-full px-4 py-2"
              onPress={() =>
                onCapture({
                  lat: location.lat,
                  lng: location.lng,
                  accuracy: location.accuracy,
                  timestamp: new Date().toISOString(),
                })
              }
            >
              <Text className="text-black font-bold text-xs">{t("common.confirm")}</Text>
            </Pressable>
          </View>

          {/* Accuracy bar */}
          <View className="mt-3 bg-gray-800 rounded-full h-2 overflow-hidden">
            <View
              className="h-full rounded-full"
              style={{
                width: `${Math.max(5, Math.min(100, 100 - location.accuracy))}%`,
                backgroundColor:
                  location.accuracy <= 10 ? "#4ade80" :
                  location.accuracy <= 30 ? "#86efac" :
                  location.accuracy <= 100 ? "#facc15" : "#f87171",
              }}
            />
          </View>
        </View>
      )}
    </View>
  );
}
