import React, { useEffect, useState } from 'react';
import { FeatureFlagContext, FeatureFlags, fetchFeatureFlags } from '../hooks/useFeatureFlags';

const DEFAULT_FLAGS: FeatureFlags = {
  mode: 'conservative',
  visibility: { chainLogos: false, chainSelector: false, blockchainDetails: false, stablecoinNames: false, protocolDetails: false, escrowDetails: false, onboardingCryptoSlides: false, faqBlockchain: false, aiAgentReferences: true },
};

export function FeatureFlagProvider({ children }: { children: React.ReactNode }) {
  const [flags, setFlags] = useState<FeatureFlags>(DEFAULT_FLAGS);

  useEffect(() => {
    fetchFeatureFlags().then(setFlags);
    const interval = setInterval(() => fetchFeatureFlags().then(setFlags), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <FeatureFlagContext.Provider value={flags}>
      {children}
    </FeatureFlagContext.Provider>
  );
}
