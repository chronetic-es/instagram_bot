import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.deps import get_current_user
from app.models import Conversation, ConversationState, Message, MessageDirection, SenderType, utcnow
from app.schemas import (
    ConversationOut, ConversationDetail, MessageOut,
    UpdateConversationRequest, SendMessageRequest,
)
from app.services import instagram as instagram_service
from app.services.websocket import manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def is_within_24h(last_user_message_at: datetime) -> bool:
    """Check if we're still within the 24-hour Instagram messaging window."""
    if not last_user_message_at:
        return False
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return (now - last_user_message_at) < timedelta(hours=24)


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).order_by(desc(Conversation.last_message_at))
    )
    conversations = result.scalars().all()

    out = []
    for conv in conversations:
        # Get last message
        last_msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none()

        conv_out = ConversationOut.model_validate(conv)
        if last_msg:
            conv_out.last_message = MessageOut.model_validate(last_msg)
        out.append(conv_out)

    return out


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()

    conv_out = ConversationOut.model_validate(conv, from_attributes=True)
    detail = ConversationDetail(
        **conv_out.model_dump(),
        messages=[MessageOut.model_validate(m, from_attributes=True) for m in messages],
    )
    return detail


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: UUID,
    body: UpdateConversationRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    conv.state = body.state
    if body.state.value == "bot_managed":
        conv.unread_count = 0
    conv.updated_at = utcnow()
    await db.commit()
    await db.refresh(conv)

    # Emit WS event
    await manager.broadcast({
        "type": "conversation_updated",
        "conversation": {
            "id": str(conv.id),
            "state": conv.state.value,
            "unread_count": conv.unread_count,
            "needs_attention": conv.needs_attention,
        },
    })

    return ConversationOut.model_validate(conv)


@router.post("/{conversation_id}/messages", response_model=MessageOut)
async def send_owner_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    # Send via Instagram API
    send_result = await instagram_service.send_message(conv.instagram_user_id, body.text)

    if "error" in send_result:
        error_msg = send_result.get("error", {}).get("message", "Error desconocido")
        error_code = send_result.get("error", {}).get("code")
        if error_code in (10, 100, 200):
            raise HTTPException(
                status_code=400,
                detail="No se puede responder. Han pasado más de 24 horas desde el último mensaje del usuario.",
            )
        raise HTTPException(status_code=400, detail=f"Error de Instagram: {error_msg}")

    # Store message
    message = Message(
        conversation_id=conversation_id,
        direction=MessageDirection.outbound,
        sender_type=SenderType.owner,
        content=body.text,
    )
    db.add(message)
    conv.last_message_at = utcnow()
    conv.updated_at = utcnow()

    # Auto-switch to self_managed when owner takes over
    if conv.state == ConversationState.bot_managed:
        conv.state = ConversationState.self_managed

    await db.commit()
    await db.refresh(message)

    msg_out = MessageOut.model_validate(message)

    # Emit WS events
    await manager.broadcast({
        "type": "new_message",
        "conversation_id": str(conversation_id),
        "message": {
            "id": str(message.id),
            "conversation_id": str(conversation_id),
            "direction": message.direction.value,
            "sender_type": message.sender_type.value,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
    })
    await manager.broadcast({
        "type": "conversation_updated",
        "conversation": {
            "id": str(conv.id),
            "instagram_user_id": conv.instagram_user_id,
            "instagram_username": conv.instagram_username,
            "unread_count": conv.unread_count,
            "needs_attention": conv.needs_attention,
            "state": conv.state.value,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        },
    })

    return msg_out


@router.post("/{conversation_id}/read")
async def mark_read(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    conv.unread_count = 0
    conv.needs_attention = False
    conv.updated_at = utcnow()
    await db.commit()

    await manager.broadcast({
        "type": "conversation_updated",
        "conversation": {
            "id": str(conv.id),
            "unread_count": 0,
            "needs_attention": False,
        },
    })

    return {"status": "ok"}
