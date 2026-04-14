import { useState, useEffect, useCallback } from 'react';
import type { Conversation, Profile, Settings, WsEvent } from '../types';
import { conversationsApi, settingsApi, authApi, profilesApi } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';
import { ConversationList } from '../components/ConversationList';
import { ConversationView } from '../components/ConversationView';
import { ProfileList } from '../components/ProfileList';
import { ProfileDetail } from '../components/ProfileDetail';
import { BotToggle } from '../components/BotToggle';
import { NotificationSetup } from '../components/NotificationSetup';
import { useNavigate } from 'react-router-dom';

type MainTab = 'conversations' | 'profiles';

export function DashboardPage() {
  const navigate = useNavigate();
  const [mainTab, setMainTab] = useState<MainTab>('conversations');

  // Conversations state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings>({ bot_enabled: true });
  const [loading, setLoading] = useState(true);
  const [mobileView, setMobileView] = useState<'list' | 'conversation'>('list');

  // Profiles state
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [profilesMobileView, setProfilesMobileView] = useState<'list' | 'detail'>('list');

  const loadData = useCallback(async () => {
    try {
      const [convs, sets, profs] = await Promise.all([
        conversationsApi.list(),
        settingsApi.get(),
        profilesApi.list(),
      ]);
      setConversations(convs);
      setSettings(sets);
      setProfiles(profs);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === 'new_message') {
      const { conversation_id, message } = event;

      setConversations((prev) => {
        const idx = prev.findIndex((c) => c.id === conversation_id);
        if (idx === -1) {
          conversationsApi.list().then(setConversations).catch(console.error);
          return prev;
        }
        const updated = { ...prev[idx] };
        updated.last_message = message;
        updated.last_message_at = message.created_at;
        if (message.direction === 'inbound' && conversation_id !== selectedConvId) {
          updated.unread_count = (updated.unread_count ?? 0) + 1;
        }
        const rest = prev.filter((c) => c.id !== conversation_id);
        return [updated, ...rest];
      });

      window.dispatchEvent(new CustomEvent('ws:new_message', { detail: message }));
    }

    if (event.type === 'conversation_updated') {
      const { conversation } = event;
      setConversations((prev) =>
        prev.map((c) => (c.id === conversation.id ? { ...c, ...conversation } : c))
      );
      window.dispatchEvent(new CustomEvent('ws:conversation_updated', { detail: conversation }));

      // Refresh profiles when a conversation transitions to self_managed (profile completion)
      if (conversation.state === 'self_managed') {
        profilesApi.list().then(setProfiles).catch(console.error);
      }
    }
  }, [selectedConvId]);

  useWebSocket(handleWsEvent);

  const handleViewConversation = (conversationId: string) => {
    setMainTab('conversations');
    setSelectedConvId(conversationId);
    setMobileView('conversation');
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-400 text-sm">Cargando...</div>
      </div>
    );
  }

  const totalUnread = conversations.reduce((sum, c) => sum + (c.unread_count ?? 0), 0);
  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) ?? null;

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center gap-2 mr-2">
          <span className="text-lg font-bold text-gray-900">GymDM</span>
          {totalUnread > 0 && (
            <span className="bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5 font-medium">
              {totalUnread}
            </span>
          )}
        </div>

        {/* Main tabs */}
        <div className="flex border border-gray-200 rounded-lg overflow-hidden text-sm">
          <button
            onClick={() => setMainTab('conversations')}
            className={`px-3 py-1.5 font-medium transition-colors ${
              mainTab === 'conversations'
                ? 'bg-blue-600 text-white'
                : 'text-gray-500 hover:text-gray-700 bg-white'
            }`}
          >
            Conversaciones
          </button>
          <button
            onClick={() => setMainTab('profiles')}
            className={`px-3 py-1.5 font-medium transition-colors flex items-center gap-1.5 ${
              mainTab === 'profiles'
                ? 'bg-blue-600 text-white'
                : 'text-gray-500 hover:text-gray-700 bg-white'
            }`}
          >
            Perfiles
            {profiles.length > 0 && (
              <span
                className={`text-xs rounded-full px-1.5 py-0.5 font-medium ${
                  mainTab === 'profiles' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {profiles.length}
              </span>
            )}
          </button>
        </div>

        <div className="flex-1" />
        <BotToggle
          enabled={settings.bot_enabled}
          onChange={(val) => setSettings((s) => ({ ...s, bot_enabled: val }))}
        />
        <NotificationSetup />
        <button
          onClick={handleLogout}
          className="text-gray-400 hover:text-gray-600 text-sm px-2 py-1"
          title="Cerrar sesión"
        >
          ⏻
        </button>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {mainTab === 'conversations' && (
          <>
            {/* Conversation List */}
            <div
              className={`flex flex-col border-r border-gray-200 bg-white ${
                mobileView === 'conversation' ? 'hidden' : 'flex'
              } w-full md:flex md:w-80 lg:w-96 flex-shrink-0`}
            >
              <ConversationList
                conversations={conversations}
                selectedId={selectedConvId ?? undefined}
                onSelect={(conv) => {
                  setSelectedConvId(conv.id);
                  setMobileView('conversation');
                }}
              />
            </div>

            {/* Conversation View */}
            <div
              className={`flex-1 overflow-hidden ${
                mobileView === 'list' ? 'hidden md:flex' : 'flex'
              } flex-col`}
            >
              {selectedConvId ? (
                <ConversationView
                  key={selectedConvId}
                  conversationId={selectedConvId}
                  onBack={() => setMobileView('list')}
                  onConversationUpdate={(update) => {
                    setConversations((prev) =>
                      prev.map((c) => (c.id === selectedConvId ? { ...c, ...update } : c))
                    );
                  }}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <div className="text-center">
                    <div className="text-4xl mb-3">💬</div>
                    <div className="text-sm">Selecciona una conversación</div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {mainTab === 'profiles' && (
          <>
            {/* Profile List */}
            <div
              className={`flex flex-col border-r border-gray-200 bg-white ${
                profilesMobileView === 'detail' ? 'hidden' : 'flex'
              } w-full md:flex md:w-80 lg:w-96 flex-shrink-0`}
            >
              <ProfileList
                profiles={profiles}
                selectedId={selectedProfileId ?? undefined}
                onSelect={(profile) => {
                  setSelectedProfileId(profile.id);
                  setProfilesMobileView('detail');
                }}
              />
            </div>

            {/* Profile Detail */}
            <div
              className={`flex-1 overflow-hidden ${
                profilesMobileView === 'list' ? 'hidden md:flex' : 'flex'
              } flex-col`}
            >
              {selectedProfile ? (
                <ProfileDetail
                  profile={selectedProfile}
                  onViewConversation={handleViewConversation}
                  onBack={() => setProfilesMobileView('list')}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <div className="text-center">
                    <div className="text-4xl mb-3">📋</div>
                    <div className="text-sm">Selecciona un perfil</div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
