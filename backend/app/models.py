import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Column, String, Integer, Text, DateTime, Enum, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class ConversationState(str, enum.Enum):
    bot_managed = "bot_managed"
    self_managed = "self_managed"


class MessageDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class SenderType(str, enum.Enum):
    user = "user"
    bot = "bot"
    owner = "owner"


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instagram_user_id = Column(String, nullable=False, unique=True, index=True)
    instagram_username = Column(String, nullable=True)
    profile_pic_url = Column(String, nullable=True)
    state = Column(
        Enum(ConversationState, name="conversation_state"),
        nullable=False,
        default=ConversationState.bot_managed,
    )
    last_message_at = Column(DateTime, nullable=True)
    unread_count = Column(Integer, nullable=False, default=0)
    needs_attention = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    profile = relationship("Profile", back_populates="conversation", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    instagram_mid = Column(String, nullable=True, unique=True)
    direction = Column(
        Enum(MessageDirection, name="message_direction"),
        nullable=False,
    )
    sender_type = Column(
        Enum(SenderType, name="sender_type"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(JSONB, nullable=False)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, unique=True)
    answers = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    conversation = relationship("Conversation", back_populates="profile")
