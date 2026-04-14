export type ConversationState = 'bot_managed' | 'self_managed';
export type MessageDirection = 'inbound' | 'outbound';
export type SenderType = 'user' | 'bot' | 'owner';

export interface Message {
  id: string;
  conversation_id: string;
  instagram_mid?: string;
  direction: MessageDirection;
  sender_type: SenderType;
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  instagram_user_id: string;
  instagram_username?: string;
  profile_pic_url?: string;
  state: ConversationState;
  last_message_at?: string;
  unread_count: number;
  needs_attention: boolean;
  created_at: string;
  updated_at: string;
  last_message?: Message;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface Settings {
  bot_enabled: boolean;
}

export type WsEvent =
  | { type: 'new_message'; conversation_id: string; message: Message }
  | { type: 'conversation_updated'; conversation: Partial<Conversation> };

export interface ProfileAnswer {
  question: string;
  answer: string;
}

export interface Profile {
  id: string;
  conversation_id: string;
  instagram_username?: string;
  profile_pic_url?: string;
  answers: ProfileAnswer[];
  summary: string;
  created_at: string;
}
