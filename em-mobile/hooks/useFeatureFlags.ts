import { createContext, useContext } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'https://api.execution.market';
const CACHE_KEY = 'em_feature_flags';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export interface FeatureFlags {
  mode: 'conservative' | 'standard';
  visibility: {
    chainLogos: boolean;
    chainSelector: boolean;
    blockchainDetails: boolean;
    stablecoinNames: boolean;
    protocolDetails: boolean;
    escrowDetails: boolean;
    onboardingCryptoSlides: boolean;
    faqBlockchain: boolean;
    aiAgentReferences: boolean;
  };
}

const DEFAULT_FLAGS: FeatureFlags = {
  mode: 'conservative',
  visibility: {
    chainLogos: false,
    chainSelector: false,
    blockchainDetails: false,
    stablecoinNames: false,
    protocolDetails: false,
    escrowDetails: false,
    onboardingCryptoSlides: false,
    faqBlockchain: false,
    aiAgentReferences: true,
  },
};

export const FeatureFlagContext = createContext<FeatureFlags>(DEFAULT_FLAGS);

export function useFeatureFlags(): FeatureFlags {
  return useContext(FeatureFlagContext);
}

export async function fetchFeatureFlags(): Promise<FeatureFlags> {
  try {
    // Check cache first
    const cached = await AsyncStorage.getItem(CACHE_KEY);
    if (cached) {
      const { flags, timestamp } = JSON.parse(cached);
      if (Date.now() - timestamp < CACHE_TTL) return flags;
    }

    const res = await fetch(`${API_URL}/api/v1/tasks/config/mobile`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const flags = await res.json();

    // Cache
    await AsyncStorage.setItem(CACHE_KEY, JSON.stringify({ flags, timestamp: Date.now() }));
    return flags;
  } catch {
    // Return cached or defaults on error
    try {
      const cached = await AsyncStorage.getItem(CACHE_KEY);
      if (cached) return JSON.parse(cached).flags;
    } catch {}
    return DEFAULT_FLAGS;
  }
}
