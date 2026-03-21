import { View, Text, Dimensions } from "react-native";
import type { Task } from "../hooks/api/useTasks";

const MAP_HEIGHT = Math.max(Dimensions.get("window").height * 0.55, 300);

interface TaskMapProps {
  tasks: Task[];
  userLocation?: { lat: number; lng: number } | null;
  onMarkerPress?: (task: Task) => void;
}

export function TaskMap({ tasks }: TaskMapProps) {
  const tasksWithLocation = tasks.filter(
    (t) => t.location_lat != null && t.location_lng != null
  );

  return (
    <View
      className="bg-surface rounded-2xl p-8 items-center justify-center"
      style={{ height: MAP_HEIGHT }}
    >
      <Text style={{ fontSize: 32 }}>🗺️</Text>
      <Text className="text-gray-500 text-sm mt-2">
        Mapa no disponible en web
      </Text>
      {tasksWithLocation.length > 0 && (
        <Text className="text-gray-600 text-xs mt-1">
          {tasksWithLocation.length} tarea{tasksWithLocation.length !== 1 ? "s" : ""} con ubicacion
        </Text>
      )}
    </View>
  );
}
