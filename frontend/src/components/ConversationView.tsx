import { useState, useEffect, useRef, useCallback } from 'react';
import type { Conversation, ConversationDetail, ConversationState, Message } from '../types';
import { conversationsApi } from '../api';
import { MessageBubble } from './MessageBubble';
import { StateSwitch } from './StateSwitch';

interface Props {
  conversationId: string;
  onBack?: () => void;
  onConversationUpdate?: (conv: Partial<Conversation>) => void;
}

export function ConversationView({ conversationId, onBack, onConversationUpdate }: Props) {
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [inputText, setInputText] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialLoadRef = useRef(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await conversationsApi.get(conversationId);
      setDetail(data);
      // Mark as read and immediately clear needs_attention without waiting for WS round-trip
      await conversationsApi.markRead(conversationId).catch(() => {});
      setDetail((prev) => prev ? { ...prev, needs_attention: false } : prev);
      onConversationUpdate?.({ id: conversationId, needs_attention: false });
    } catch (err: any) {
      setError(err.message ?? 'Error al cargar la conversación');
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    load();
  }, [load]);

  // Scroll to bottom when messages change; instant on initial load, smooth for new messages
  useEffect(() => {
    if (!detail?.messages.length) return;
    const behavior = initialLoadRef.current ? 'instant' : 'smooth';
    initialLoadRef.current = false;
    messagesEndRef.current?.scrollIntoView({ behavior });
  }, [detail?.messages.length]);

  // Expose method to append new messages from WebSocket
  useEffect(() => {
    const handler = (event: CustomEvent<Message>) => {
      if (event.detail.conversation_id !== conversationId) return;
      setDetail((prev) => {
        if (!prev) return prev;
        const exists = prev.messages.some((m) => m.id === event.detail.id);
        if (exists) return prev;
        return { ...prev, messages: [...prev.messages, event.detail] };
      });
    };
    window.addEventListener('ws:new_message', handler as EventListener);
    return () => window.removeEventListener('ws:new_message', handler as EventListener);
  }, [conversationId]);

  // Update conversation state from WebSocket conversation_updated events
  useEffect(() => {
    const handler = (event: CustomEvent) => {
      const update = event.detail;
      if (update.id !== conversationId) return;
      setDetail((prev) => prev ? { ...prev, ...update } : prev);
    };
    window.addEventListener('ws:conversation_updated', handler as EventListener);
    return () => window.removeEventListener('ws:conversation_updated', handler as EventListener);
  }, [conversationId]);

  const isWithin24h = () => {
    if (!detail) return false;
    const lastUser = [...(detail.messages ?? [])]
      .reverse()
      .find((m) => m.direction === 'inbound');
    if (!lastUser) return false;
    const diff = Date.now() - new Date(lastUser.created_at).getTime();
    return diff < 24 * 60 * 60 * 1000;
  };

  const handleSend = async () => {
    if (!inputText.trim() || sending) return;
    setSendError(null);
    setSending(true);
    try {
      const msg = await conversationsApi.sendMessage(conversationId, inputText.trim()) as Message;
      setInputText('');
      setDetail((prev) => {
        if (!prev) return prev;
        const exists = prev.messages.some((m) => m.id === msg.id);
        if (exists) return prev;
        return { ...prev, messages: [...prev.messages, msg] };
      });
    } catch (err: any) {
      setSendError(err.message ?? 'Error al enviar');
    } finally {
      setSending(false);
    }
  };

  const handleStateChange = (state: ConversationState) => {
    setDetail((prev) => prev ? { ...prev, state } : prev);
    onConversationUpdate?.({ id: conversationId, state });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Cargando...</div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="text-red-500">{error ?? 'Error desconocido'}</div>
        <button onClick={load} className="text-blue-600 underline text-sm">
          Reintentar
        </button>
      </div>
    );
  }

  const within24h = isWithin24h();
  const hasUserMessages = detail.messages.some((m) => m.direction === 'inbound');

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 bg-white flex-shrink-0">
        {onBack && (
          <button onClick={onBack} className="text-gray-500 hover:text-gray-700 mr-1">
            ←
          </button>
        )}
        {detail.profile_pic_url ? (
          <img
            src={detail.profile_pic_url}
            alt={detail.instagram_username ?? ''}
            className="w-9 h-9 rounded-full object-cover"
          />
        ) : (
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center text-white font-semibold text-xs">
            {(detail.instagram_username ?? detail.instagram_user_id).slice(0, 2).toUpperCase()}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-gray-900 truncate">
            {detail.instagram_username ?? detail.instagram_user_id}
          </div>
          {detail.instagram_username && (
            <div className="text-xs text-gray-400">@{detail.instagram_username}</div>
          )}
        </div>
        <StateSwitch
          conversationId={conversationId}
          state={detail.state}
          onChange={handleStateChange}
        />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {detail.messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-8">Sin mensajes aún</div>
        )}
        {detail.messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 24h warning */}
      {hasUserMessages && !within24h && (
        <div className="mx-4 mb-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          ⚠️ No se puede responder. Han pasado más de 24 horas desde el último mensaje del usuario.
        </div>
      )}

      {/* Send error */}
      {sendError && (
        <div className="mx-4 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          {sendError}
        </div>
      )}

      {/* Input */}
      <div className="flex items-end gap-2 px-4 py-3 border-t border-gray-200 bg-white flex-shrink-0">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Escribe un mensaje..."
          rows={1}
          className="flex-1 resize-none rounded-2xl border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-h-32"
          style={{ minHeight: '40px' }}
        />
        <button
          onClick={handleSend}
          disabled={!inputText.trim() || sending}
          className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {sending ? (
            <span className="text-xs">...</span>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
