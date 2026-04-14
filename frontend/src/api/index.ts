import type { Conversation, ConversationDetail, ConversationState, Settings, Profile } from '../types';

const BASE = '/api';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (res.status === 401) {
    window.location.href = '/login';
    throw new Error('No autenticado');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth
export const authApi = {
  login: (username: string, password: string) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request<{ username: string }>('/auth/me'),
};

// Conversations
export const conversationsApi = {
  list: () => request<Conversation[]>('/conversations'),
  get: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  updateState: (id: string, state: ConversationState) =>
    request<Conversation>(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ state }),
    }),
  sendMessage: (id: string, text: string) =>
    request(`/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
  markRead: (id: string) =>
    request(`/conversations/${id}/read`, { method: 'POST' }),
};

// Settings
export const settingsApi = {
  get: () => request<Settings>('/settings'),
  update: (bot_enabled: boolean) =>
    request<Settings>('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ bot_enabled }),
    }),
};

// Profiles
export const profilesApi = {
  list: () => request<Profile[]>('/profiles'),
  get: (id: string) => request<Profile>(`/profiles/${id}`),
};

// Push
export const pushApi = {
  subscribe: (subscription: PushSubscriptionJSON) =>
    request('/push/subscribe', {
      method: 'POST',
      body: JSON.stringify({ subscription }),
    }),
  unsubscribe: (endpoint: string) =>
    request('/push/unsubscribe', {
      method: 'POST',
      body: JSON.stringify({ endpoint }),
    }),
};
