import type { Message } from '../types';

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isInbound = message.direction === 'inbound';
  const isBot = message.sender_type === 'bot';
  const isOwner = message.sender_type === 'owner';

  const time = new Date(message.created_at).toLocaleTimeString('es', {
    hour: '2-digit',
    minute: '2-digit',
  });

  if (isInbound) {
    return (
      <div className="flex items-end gap-2 mb-3">
        <div className="max-w-[75%]">
          <div className="bg-gray-100 text-gray-900 rounded-2xl rounded-bl-sm px-4 py-2 text-sm">
            {message.content}
          </div>
          <div className="text-xs text-gray-400 mt-1 ml-1">{time}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-end justify-end gap-2 mb-3">
      <div className="max-w-[75%]">
        <div
          className={`rounded-2xl rounded-br-sm px-4 py-2 text-sm ${
            isBot
              ? 'bg-blue-600 text-white'
              : 'bg-green-600 text-white'
          }`}
        >
          {message.content}
        </div>
        <div className="text-xs text-gray-400 mt-1 mr-1 text-right">
          {isBot ? '🤖 Bot' : '👤 Tú'} · {time}
        </div>
      </div>
    </div>
  );
}
