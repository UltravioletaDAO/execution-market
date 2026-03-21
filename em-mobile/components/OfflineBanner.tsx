import { useEffect, useState } from 'react';
import { View, Text } from 'react-native';
import NetInfo from '@react-native-community/netinfo';
import { Ionicons } from '@expo/vector-icons';

export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOffline(!(state.isConnected && state.isInternetReachable !== false));
    });
    return () => unsubscribe();
  }, []);

  if (!isOffline) return null;

  return (
    <View className="bg-red-900/80 px-4 py-2 flex-row items-center justify-center">
      <Ionicons name="cloud-offline-outline" size={16} color="#fca5a5" />
      <Text className="text-red-200 text-sm ml-2">No internet connection</Text>
    </View>
  );
}
