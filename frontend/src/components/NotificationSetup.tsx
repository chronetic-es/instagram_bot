import { usePushNotifications } from '../hooks/usePushNotifications';

export function NotificationSetup() {
  const { status, errorDetail, subscribe, unsubscribe, isSupported } = usePushNotifications();

  if (!isSupported) {
    return (
      <span className="text-xs text-gray-400">Notificaciones no soportadas</span>
    );
  }

  if (status === 'granted') {
    return (
      <button
        onClick={unsubscribe}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
        title="Desactivar notificaciones push"
      >
        🔔 Activas
      </button>
    );
  }

  if (status === 'denied') {
    return (
      <span className="text-xs text-red-500" title="Permisos denegados en el navegador">
        🔕 Denegadas
      </span>
    );
  }

  if (status === 'error') {
    return (
      <button
        onClick={subscribe}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm bg-red-100 text-red-600 hover:bg-red-200"
        title={errorDetail || 'Error al activar notificaciones'}
      >
        🔕 {errorDetail || 'Error al activar'}
      </button>
    );
  }

  return (
    <button
      onClick={subscribe}
      disabled={status === 'loading'}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm bg-gray-100 text-gray-600 hover:bg-gray-200 ${
        status === 'loading' ? 'opacity-50 cursor-not-allowed' : ''
      }`}
      title="Activar notificaciones push"
    >
      {status === 'loading' ? '...' : '🔔 Notificaciones'}
    </button>
  );
}
