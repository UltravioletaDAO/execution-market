/**
 * Notification hooks
 *
 * Custom hooks for accessing notification context.
 */

import { useContext } from 'react';
import { NotificationContext } from './NotificationProvider';
import type { NotificationContextValue } from '../../types/notification';

export function useNotificationContext(): NotificationContextValue {
  const context = useContext(NotificationContext);

  if (context === undefined) {
    throw new Error('useNotificationContext must be used within a NotificationProvider');
  }

  return context;
}
