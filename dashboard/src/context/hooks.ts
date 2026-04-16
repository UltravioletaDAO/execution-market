/**
 * Context hooks
 *
 * Custom hooks for accessing context values.
 */

import { useContext } from 'react';
import { AuthContext } from './AuthContextDef';
import type { AuthContextValue } from './AuthContextDef';

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
