import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import type { Conversation, ConversationState } from '../types';

type Filter = 'all' | 'bot_managed' | 'self_managed';

interface Props {
  conversations: Conversation[];
  selectedId?: string;
  onSelect: (conv: Conversation) => void;
}

export function ConversationList({ conversations, selectedId, onSelect }: Props) {
  const [filter, setFilter] = useState<Filter>('all');

  const filtered = conversations.filter((c) => {
    if (filter === 'all') return true;
    return c.state === filter;
  });

  const tabs: { label: string; value: Filter }[] = [
    { label: 'Todas', value: 'all' },
    { label: '🤖 Bot', value: 'bot_managed' },
    { label: '👤 Manuales', value: 'self_managed' },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 bg-white">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              filter === tab.value
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 && (
          <div className="p-6 text-center text-gray-400 text-sm">
            No hay conversaciones
          </div>
        )}
        {filtered.map((conv) => (
          <ConversationItem
            key={conv.id}
            conversation={conv}
            isSelected={conv.id === selectedId}
            onClick={() => onSelect(conv)}
          />
        ))}
      </div>
    </div>
  );
}

interface ItemProps {
  conversation: Conversation;
  isSelected: boolean;
  onClick: () => void;
}

function ConversationItem({ conversation: conv, isSelected, onClick }: ItemProps) {
  const timeAgo = conv.last_message_at
    ? formatDistanceToNow(new Date(conv.last_message_at), { addSuffix: true, locale: es })
    : '';

  const avatar = conv.profile_pic_url;
  const initials = (conv.instagram_username ?? conv.instagram_user_id).slice(0, 2).toUpperCase();

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors border-b border-gray-100 ${
        isSelected ? 'bg-blue-50 border-l-2 border-l-blue-600' : ''
      }`}
    >
      {/* Avatar */}
      <div className="relative flex-shrink-0">
        {avatar ? (
          <img
            src={avatar}
            alt={conv.instagram_username ?? ''}
            className="w-12 h-12 rounded-full object-cover"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center text-white font-semibold text-sm">
            {initials}
          </div>
        )}
        {/* State indicator */}
        <div
          className={`absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full border-2 border-white flex items-center justify-center text-[8px] ${
            conv.state === 'bot_managed' ? 'bg-blue-500' : 'bg-orange-400'
          }`}
        >
          {conv.state === 'bot_managed' ? '🤖' : '👤'}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="font-medium text-sm text-gray-900 truncate">
            {conv.instagram_username ?? conv.instagram_user_id}
          </span>
          <span className="text-xs text-gray-400 flex-shrink-0 ml-2">{timeAgo}</span>
        </div>
        <div className="flex items-center justify-between mt-0.5">
          <span className="text-xs text-gray-500 truncate">
            {conv.last_message?.content ?? 'Sin mensajes'}
          </span>
          <div className="flex items-center gap-1 flex-shrink-0 ml-2">
            {conv.needs_attention && (
              <span className="text-red-500 text-sm" title="Requiere atención del dueño">🔔</span>
            )}
            {conv.unread_count > 0 && (
              <span className="bg-blue-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium">
                {conv.unread_count > 9 ? '9+' : conv.unread_count}
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
