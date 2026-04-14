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
        className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-full text-xs sm:text-sm bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
        title="Desactivar notificaciones push"
      >
        🔔 <span className="hidden sm:inline">Activas</span>
      </button>
    );
  }

  if (status === 'denied') {
    return (
      <span className="text-xs text-red-500" title="Permisos denegados en el navegador">
        🔕 <span className="hidden sm:inline">Denegadas</span>
      </span>
    );
  }

  if (status === 'error') {
    return (
      <button
        onClick={subscribe}
        className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-full text-xs sm:text-sm bg-red-100 text-red-600 hover:bg-red-200"
        title={errorDetail || 'Error al activar notificaciones'}
      >
        🔕 <span className="hidden sm:inline">{errorDetail || 'Error al activar'}</span>
      </button>
    );
  }

  return (
    <button
      onClick={subscribe}
      disabled={status === 'loading'}
      className={`flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-full text-xs sm:text-sm bg-gray-100 text-gray-600 hover:bg-gray-200 ${
        status === 'loading' ? 'opacity-50 cursor-not-allowed' : ''
      }`}
      title="Activar notificaciones push"
    >
      {status === 'loading' ? '...' : <><span>🔔</span> <span className="hidden sm:inline">Notificaciones</span></>}
    </button>
  );
}
