import React from 'react';
import { useFeatureFlags } from '../hooks/useFeatureFlags';

interface Props {
  flag: keyof ReturnType<typeof useFeatureFlags>['visibility'];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function FeatureGate({ flag, children, fallback = null }: Props) {
  const { visibility } = useFeatureFlags();
  return visibility[flag] ? <>{children}</> : <>{fallback}</>;
}
