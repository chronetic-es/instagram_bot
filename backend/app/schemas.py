from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from app.models import ConversationState, MessageDirection, SenderType


# --- Auth ---

class LoginRequest(BaseModel):
    username: str
    password: str


class AuthMeResponse(BaseModel):
    username: str


# --- Messages ---

class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    instagram_mid: Optional[str] = None
    direction: MessageDirection
    sender_type: SenderType
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    text: str


# --- Conversations ---

class ConversationOut(BaseModel):
    id: UUID
    instagram_user_id: str
    instagram_username: Optional[str] = None
    profile_pic_url: Optional[str] = None
    state: ConversationState
    last_message_at: Optional[datetime] = None
    unread_count: int
    needs_attention: bool = False
    created_at: datetime
    updated_at: datetime
    last_message: Optional[MessageOut] = None

    class Config:
        from_attributes = True


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class UpdateConversationRequest(BaseModel):
    state: ConversationState


# --- Settings ---

class SettingsOut(BaseModel):
    bot_enabled: bool


class UpdateSettingsRequest(BaseModel):
    bot_enabled: bool


# --- Profiles ---

class ProfileAnswerItem(BaseModel):
    question: str
    answer: str


class ProfileOut(BaseModel):
    id: UUID
    conversation_id: UUID
    instagram_username: Optional[str] = None
    profile_pic_url: Optional[str] = None
    answers: list[ProfileAnswerItem]
    summary: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Push ---

class PushSubscribeRequest(BaseModel):
    subscription: dict[str, Any]


class PushUnsubscribeRequest(BaseModel):
    endpoint: str
