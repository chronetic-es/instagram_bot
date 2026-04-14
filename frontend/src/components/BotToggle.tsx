import { useState } from 'react';
import { settingsApi } from '../api';

interface Props {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}

export function BotToggle({ enabled, onChange }: Props) {
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    if (loading) return;

    if (enabled) {
      const confirmed = window.confirm(
        '¿Pausar el bot? Las conversaciones seguirán siendo visibles pero el bot no responderá automáticamente.'
      );
      if (!confirmed) return;
    }

    setLoading(true);
    try {
      await settingsApi.update(!enabled);
      onChange(!enabled);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleToggle}
      disabled={loading}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
        enabled
          ? 'bg-green-100 text-green-700 hover:bg-green-200'
          : 'bg-red-100 text-red-700 hover:bg-red-200'
      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <span
        className={`inline-block w-2 h-2 rounded-full ${enabled ? 'bg-green-500' : 'bg-red-500'}`}
      />
      {loading ? '...' : enabled ? 'Bot activo' : 'Bot pausado'}
    </button>
  );
}
