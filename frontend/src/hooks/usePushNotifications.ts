import { useState, useCallback, useEffect } from 'react';
import { pushApi } from '../api';

// VITE_VAPID_PUBLIC_KEY is set in frontend/.env
const VAPID_PUBLIC_KEY: string = (typeof import.meta !== 'undefined' && (import.meta as Record<string, any>).env?.VITE_VAPID_PUBLIC_KEY) ?? '';

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const buffer = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    buffer[i] = rawData.charCodeAt(i);
  }
  return buffer.buffer;
}

export function usePushNotifications() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'granted' | 'denied' | 'error' | 'unsupported'>('idle');
  const [errorDetail, setErrorDetail] = useState<string>('');

  const isSupported =
    'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;

  // On mount, restore status if there's already an active subscription
  useEffect(() => {
    if (!isSupported) return;
    navigator.serviceWorker.getRegistration('/').then((reg) => {
      reg?.pushManager.getSubscription().then((sub) => {
        if (sub) setStatus('granted');
      });
    });
  }, [isSupported]);

  const subscribe = useCallback(async () => {
    if (!isSupported) {
      setStatus('unsupported');
      return;
    }

    setStatus('loading');

    try {
      if (!VAPID_PUBLIC_KEY) {
        setErrorDetail('VITE_VAPID_PUBLIC_KEY no configurada');
        setStatus('error');
        return;
      }

      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        setStatus('denied');
        return;
      }

      const registration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      await navigator.serviceWorker.ready;

      // Clear any stale subscription from a previous key before subscribing
      const existing = await registration.pushManager.getSubscription();
      if (existing) await existing.unsubscribe();

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });

      await pushApi.subscribe(subscription.toJSON() as PushSubscriptionJSON);
      setStatus('granted');
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error('Push subscription failed:', err);
      setErrorDetail(msg);
      setStatus('error');
    }
  }, [isSupported]);

  const unsubscribe = useCallback(async () => {
    try {
      const registration = await navigator.serviceWorker.getRegistration('/');
      if (!registration) return;
      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) return;
      await pushApi.unsubscribe(subscription.endpoint);
      await subscription.unsubscribe();
      setStatus('idle');
    } catch (err) {
      console.error('Push unsubscription failed:', err);
    }
  }, []);

  return { status, errorDetail, subscribe, unsubscribe, isSupported };
}
