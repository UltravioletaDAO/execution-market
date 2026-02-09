/**
 * Context hooks
 *
 * Custom hooks for accessing context values.
 */

import { useContext } from 'react';
import { AuthContext } from './AuthContext';
import type { AuthContextValue } from './AuthContext';

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
