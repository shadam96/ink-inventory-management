/**
 * React hook for WebSocket real-time updates
 */
import { useEffect } from 'react';
import { websocketService } from '../lib/websocket';
import { useAuthStore } from '../store/auth';

type MessageHandler = (message: any) => void;

export function useWebSocket() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const token = isAuthenticated ? localStorage.getItem('access_token') : null;

  useEffect(() => {
    if (token) {
      websocketService.connect(token);
    } else {
      // isAuthenticated flipped to false (logout) - disconnect the
      // singleton socket so the next user to log in on this tab/device
      // doesn't silently reuse the previous user's authenticated
      // connection (connect() no-ops if a socket is already OPEN).
      websocketService.disconnect();
    }
  }, [token]);

  const subscribe = (messageType: string, handler: MessageHandler) => {
    return websocketService.subscribe(messageType, handler);
  };

  const send = (message: any) => {
    websocketService.send(message);
  };

  return {
    subscribe,
    send,
    isConnected: websocketService.isConnected(),
  };
}

// Specific hooks for different message types

export function useAlertNotifications(handler: (alert: any) => void) {
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('alert', (message) => {
      handler(message.data);
    });

    return unsubscribe;
  }, [handler]);
}

export function useDashboardUpdates(handler: () => void) {
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('dashboard_refresh', handler);

    return unsubscribe;
  }, [handler]);
}

export function useInventoryUpdates(handler: (data: any) => void) {
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('inventory_update', (message) => {
      handler(message.data);
    });

    return unsubscribe;
  }, [handler]);
}
