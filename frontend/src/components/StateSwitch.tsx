import { useState } from 'react';
import type { ConversationState } from '../types';
import { conversationsApi } from '../api';

interface Props {
  conversationId: string;
  state: ConversationState;
  onChange: (state: ConversationState) => void;
}

export function StateSwitch({ conversationId, state, onChange }: Props) {
  const [loading, setLoading] = useState(false);

  const isBot = state === 'bot_managed';

  const handleToggle = async () => {
    if (loading) return;
    const newState: ConversationState = isBot ? 'self_managed' : 'bot_managed';
    setLoading(true);
    try {
      await conversationsApi.updateState(conversationId, newState);
      onChange(newState);
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
      className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
        isBot
          ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
          : 'bg-orange-100 text-orange-700 hover:bg-orange-200'
      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {loading ? '...' : isBot ? '🤖 Bot' : '👤 Manual'}
    </button>
  );
}
