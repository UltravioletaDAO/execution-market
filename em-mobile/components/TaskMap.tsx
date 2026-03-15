import { View, Text, Dimensions } from "react-native";
import { router } from "expo-router";
import type { Task } from "../hooks/api/useTasks";
import { TASK_CATEGORIES } from "../constants/categories";

// Native-only: react-native-maps loaded conditionally for Expo Go compat
let MapView: React.ComponentType<any> | null = null;
let Marker: React.ComponentType<any> | null = null;
let PROVIDER_DEFAULT: unknown = undefined;

try {
  const maps = require("react-native-maps");
  MapView = maps.default;
  Marker = maps.Marker;
  PROVIDER_DEFAULT = maps.PROVIDER_DEFAULT;
} catch {
  // react-native-maps not available (Expo Go without native modules)
}

/** Compute a region that fits all task markers with padding, or fall back to a global view. */
function computeRegion(
  tasksWithLocation: Task[],
  userLocation?: { lat: number; lng: number } | null
) {
  // Global/world view as the default
  const GLOBAL_REGION = {
    latitude: 20,
    longitude: 0,
    latitudeDelta: 120,
    longitudeDelta: 120,
  };

  if (tasksWithLocation.length === 0) {
    return GLOBAL_REGION;
  }

  // Collect all points (tasks + optional user location)
  const lats = tasksWithLocation.map((t) => t.location_lat!);
  const lngs = tasksWithLocation.map((t) => t.location_lng!);
  if (userLocation) {
    lats.push(userLocation.lat);
    lngs.push(userLocation.lng);
  }

  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  const latDelta = Math.max((maxLat - minLat) * 1.5, 2); // at least 2 degrees
  const lngDelta = Math.max((maxLng - minLng) * 1.5, 2);

  return {
    latitude: (minLat + maxLat) / 2,
    longitude: (minLng + maxLng) / 2,
    latitudeDelta: latDelta,
    longitudeDelta: lngDelta,
  };
}

/** Category-based pin colors for visual distinction on the map. */
const CATEGORY_COLORS: Record<string, string> = {
  physical_presence: "#ef4444", // red
  knowledge_access: "#3b82f6", // blue
  human_authority: "#a855f7", // purple
  simple_action: "#f59e0b", // amber
  digital_physical: "#10b981", // emerald
};

const MAP_HEIGHT = Math.max(Dimensions.get("window").height * 0.55, 300);

interface TaskMapProps {
  tasks: Task[];
  userLocation?: { lat: number; lng: number } | null;
  onMarkerPress?: (task: Task) => void;
}

export function TaskMap({ tasks, userLocation, onMarkerPress }: TaskMapProps) {
  const tasksWithLocation = tasks.filter(
    (t) =>
      t.location_lat != null && t.location_lng != null && t.status === "published"
  );

  if (!MapView || !Marker) {
    return (
      <View
        className="bg-surface rounded-2xl p-8 items-center justify-center"
        style={{ height: MAP_HEIGHT }}
      >
        <Text style={{ fontSize: 32 }}>🗺️</Text>
        <Text className="text-gray-500 text-sm mt-2">
          Mapa no disponible en esta plataforma
        </Text>
      </View>
    );
  }

  const initialRegion = computeRegion(tasksWithLocation, userLocation);

  return (
    <View className="rounded-2xl overflow-hidden" style={{ height: MAP_HEIGHT }}>
      <MapView
        provider={PROVIDER_DEFAULT}
        style={{ width: "100%", height: "100%" }}
        initialRegion={initialRegion}
        showsUserLocation={!!userLocation}
        showsMyLocationButton={true}
      >
        {tasksWithLocation.map((task) => {
          const category = TASK_CATEGORIES.find((c) => c.key === task.category);
          const pinColor = CATEGORY_COLORS[task.category] || "#ef4444";
          return (
            <Marker
              key={task.id}
              coordinate={{
                latitude: task.location_lat!,
                longitude: task.location_lng!,
              }}
              title={task.title}
              description={`$${(typeof task.bounty_usd === "number" ? task.bounty_usd : 0).toFixed(2)} USDC${task.location_hint ? " - " + task.location_hint : ""}`}
              onCalloutPress={() => {
                if (onMarkerPress) onMarkerPress(task);
                else router.push(`/task/${task.id}`);
              }}
            >
              <View
                style={{ backgroundColor: pinColor }}
                className="rounded-full w-9 h-9 items-center justify-center border-2 border-white shadow-lg"
              >
                <Text style={{ fontSize: 15 }}>{category?.icon || "📌"}</Text>
              </View>
            </Marker>
          );
        })}
      </MapView>

      {/* Task count badge */}
      {tasksWithLocation.length > 0 && (
        <View
          className="absolute top-3 left-3 rounded-full px-3 py-1 flex-row items-center"
          style={{ backgroundColor: "rgba(0,0,0,0.7)" }}
        >
          <Text className="text-white text-xs font-semibold">
            {tasksWithLocation.length} tarea{tasksWithLocation.length !== 1 ? "s" : ""} en mapa
          </Text>
        </View>
      )}

      {tasksWithLocation.length === 0 && (
        <View
          className="absolute inset-0 items-center justify-center"
          pointerEvents="none"
        >
          <View
            className="rounded-xl px-4 py-2"
            style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
          >
            <Text className="text-gray-300 text-sm">
              No hay tareas con ubicacion
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}
