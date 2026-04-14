import { useEffect, useRef, useCallback } from 'react';
import type { WsEvent } from '../types';

type EventHandler = (event: WsEvent) => void;

export function useWebSocket(onEvent: EventHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef<EventHandler>(onEvent);
  handlerRef.current = onEvent;

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${window.location.host}/api/ws`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data: WsEvent = JSON.parse(event.data);
        handlerRef.current(data);
      } catch (e) {
        console.error('Failed to parse WS message', e);
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed, reconnecting in 3s...', event.code);
      wsRef.current = null;
      // Reconnect unless it was a deliberate close (auth failure = 4001)
      if (event.code !== 4001) {
        setTimeout(connect, 3000);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close(1000);
    };
  }, [connect]);
}
