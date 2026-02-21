/**
 * React hook for WebSocket real-time updates
 */
import { useEffect } from 'react';
import { websocketService } from '../lib/websocket';
import { useAuthStore } from '../store/auth';

type MessageHandler = (message: any) => void;

export function useWebSocket() {
  const token = useAuthStore((state) => state.token);

  useEffect(() => {
    if (token) {
      websocketService.connect(token);

      return () => {
        // Don't disconnect on unmount, keep connection alive
      };
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
