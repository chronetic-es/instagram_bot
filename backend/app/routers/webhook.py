import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.config import get_settings
from app.database import get_db
from app.models import Conversation, ConversationState, Message, MessageDirection, SenderType, Setting, utcnow
from app.schemas import MessageOut, ConversationOut
from app.services import instagram as instagram_service
from app.services import llm as llm_service
from app.services import push as push_service
from app.services.websocket import manager

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/webhook", tags=["webhook"])


def verify_hub_signature(body: bytes, signature_header: str) -> bool:
    """Validate X-Hub-Signature-256 from Meta."""
    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning(f"Missing or malformed signature header: {repr(signature_header)}")
        return False
    expected_sig = signature_header[len("sha256="):]
    computed = hmac.new(
        settings.meta_app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    logger.info(f"Signature check — received: {expected_sig[:16]}... computed: {computed[:16]}...")
    match = hmac.compare_digest(computed, expected_sig)
    if not match:
        logger.warning(f"Signature mismatch. Header: {expected_sig[:20]}... Computed: {computed[:20]}...")
    return match


@router.get("/instagram")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        logger.info("Webhook verified successfully")
        return int(hub_challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post("/instagram")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()

    # Validate signature
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if settings.meta_app_secret and not verify_hub_signature(body, sig_header):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"status": "ok"}

    if data.get("object") != "instagram":
        return {"status": "ok"}

    for entry in data.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id = messaging.get("sender", {}).get("id")
            recipient_id = messaging.get("recipient", {}).get("id")
            msg_data = messaging.get("message", {})

            # Skip messages sent by the page itself
            if sender_id == settings.instagram_account_id:
                continue

            mid = msg_data.get("mid")
            text = msg_data.get("text")

            if not sender_id:
                continue

            # Determine content (handle media)
            if not text:
                if "attachments" in msg_data:
                    attachment_type = msg_data["attachments"][0].get("type", "archivo")
                    type_map = {
                        "image": "[Imagen]",
                        "video": "[Video]",
                        "audio": "[Audio]",
                        "sticker": "[Sticker]",
                    }
                    content = type_map.get(attachment_type, "[Archivo adjunto]")
                else:
                    continue
            else:
                content = text

            background_tasks.add_task(
                process_incoming_message,
                sender_id=sender_id,
                mid=mid,
                content=content,
                is_media=(text is None),
            )

    return {"status": "ok"}


async def process_incoming_message(
    sender_id: str,
    mid: str,
    content: str,
    is_media: bool,
):
    """Background task: store message, call LLM if needed, send response."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Deduplication: check if mid already exists
            if mid:
                existing = await db.execute(
                    select(Message).where(Message.instagram_mid == mid)
                )
                if existing.scalar_one_or_none():
                    logger.info(f"Duplicate message {mid}, skipping")
                    return

            # Get or create conversation
            result = await db.execute(
                select(Conversation).where(Conversation.instagram_user_id == sender_id)
            )
            conversation = result.scalar_one_or_none()

            if not conversation:
                # Fetch user info from Instagram
                user_info = await instagram_service.get_user_info(sender_id)
                conversation = Conversation(
                    instagram_user_id=sender_id,
                    instagram_username=user_info.get("name"),
                    profile_pic_url=user_info.get("profile_pic"),
                    state=ConversationState.bot_managed,
                )
                db.add(conversation)
                await db.flush()

            # Store the incoming message
            message = Message(
                conversation_id=conversation.id,
                instagram_mid=mid,
                direction=MessageDirection.inbound,
                sender_type=SenderType.user,
                content=content,
            )
            db.add(message)

            # Update conversation metadata
            conversation.last_message_at = utcnow()
            conversation.unread_count = (conversation.unread_count or 0) + 1
            await db.flush()

            await db.commit()

            # Emit WebSocket event
            await manager.broadcast({
                "type": "new_message",
                "conversation_id": str(conversation.id),
                "message": {
                    "id": str(message.id),
                    "conversation_id": str(conversation.id),
                    "direction": message.direction.value,
                    "sender_type": message.sender_type.value,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                },
            })
            await manager.broadcast({
                "type": "conversation_updated",
                "conversation": {
                    "id": str(conversation.id),
                    "instagram_user_id": conversation.instagram_user_id,
                    "instagram_username": conversation.instagram_username,
                    "unread_count": conversation.unread_count,
                    "state": conversation.state.value,
                    "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                },
            })

            # If media message, send notice to user and skip LLM
            if is_media:
                notice = "No puedo procesar imágenes o archivos adjuntos, por favor escríbeme tu consulta."
                await instagram_service.send_message(sender_id, notice)
                notice_msg = Message(
                    conversation_id=conversation.id,
                    direction=MessageDirection.outbound,
                    sender_type=SenderType.bot,
                    content=notice,
                )
                async with AsyncSessionLocal() as db2:
                    db2.add(notice_msg)
                    await db2.commit()
                return

            # Check if bot should respond
            async with AsyncSessionLocal() as db2:
                conv_result = await db2.execute(
                    select(Conversation).where(Conversation.id == conversation.id)
                )
                conv = conv_result.scalar_one_or_none()
                if not conv or conv.state != ConversationState.bot_managed:
                    logger.info(f"Conversation {conversation.id} is self_managed, skipping LLM")
                    return

                setting_result = await db2.execute(
                    select(Setting).where(Setting.key == "bot_enabled")
                )
                setting = setting_result.scalar_one_or_none()
                bot_enabled = setting.value if setting else True

                if not bot_enabled:
                    logger.info("Bot is disabled, skipping LLM")
                    return

                # Get conversation history
                history_result = await db2.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.created_at)
                )
                history_msgs = history_result.scalars().all()

                # Build history for LLM (exclude the current message which is last)
                history = [
                    {"direction": m.direction.value, "sender_type": m.sender_type.value, "content": m.content}
                    for m in history_msgs[:-1]  # exclude the just-added message
                ]

            # Send typing indicator
            await instagram_service.send_typing_indicator(sender_id)

            # Prepare push notify callback
            async def notify_callback(reason: str):
                from app.models import PushSubscription
                already_notified = False
                async with AsyncSessionLocal() as db3:
                    conv_result = await db3.execute(
                        select(Conversation).where(Conversation.id == conversation.id)
                    )
                    conv_obj = conv_result.scalar_one_or_none()
                    if conv_obj:
                        already_notified = conv_obj.needs_attention
                        conv_obj.needs_attention = True

                    subs_result = await db3.execute(select(PushSubscription))
                    subs = subs_result.scalars().all()
                    sub_list = [s.subscription_json for s in subs]
                    await db3.commit()

                # Broadcast needs_attention flag so the frontend shows the bell indicator
                await manager.broadcast({
                    "type": "conversation_updated",
                    "conversation": {
                        "id": str(conversation.id),
                        "instagram_user_id": conversation.instagram_user_id,
                        "instagram_username": conversation.instagram_username,
                        "unread_count": conversation.unread_count,
                        "needs_attention": True,
                        "state": conversation.state.value,
                        "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                    },
                })

                if already_notified:
                    logger.info(f"Skipping push for {conversation.id}: owner already notified")
                    return

                username = conversation.instagram_username or sender_id
                to_delete = await push_service.send_push_notification(
                    subscriptions=sub_list,
                    title="DM del Gimnasio",
                    body=f"{username} desea hablar contigo!",
                    url=f"/conversaciones/{conversation.id}",
                    conversation_id=str(conversation.id),
                )

                # Delete expired subscriptions
                if to_delete:
                    async with AsyncSessionLocal() as db4:
                        from app.models import PushSubscription
                        for endpoint in to_delete:
                            subs_to_del = await db4.execute(
                                select(PushSubscription)
                            )
                            for sub in subs_to_del.scalars().all():
                                if sub.subscription_json.get("endpoint") == endpoint:
                                    await db4.delete(sub)
                        await db4.commit()

            # Prepare profile callback
            async def profile_callback(answers: list, summary: str):
                from app.models import Profile
                async with AsyncSessionLocal() as db_p:
                    # Upsert: skip if profile already exists for this conversation
                    existing = await db_p.execute(
                        select(Profile).where(Profile.conversation_id == conversation.id)
                    )
                    if existing.scalar_one_or_none():
                        logger.info(f"Profile already exists for conversation {conversation.id}, skipping")
                        return

                    profile = Profile(
                        conversation_id=conversation.id,
                        answers=answers,
                        summary=summary,
                    )
                    db_p.add(profile)

                    # Hand off to human
                    conv_result = await db_p.execute(
                        select(Conversation).where(Conversation.id == conversation.id)
                    )
                    conv_obj = conv_result.scalar_one_or_none()
                    if conv_obj:
                        conv_obj.state = ConversationState.self_managed
                        conv_obj.updated_at = utcnow()

                    await db_p.commit()

                # Send push notification to trainer
                from app.models import PushSubscription
                async with AsyncSessionLocal() as db_p2:
                    subs_result = await db_p2.execute(select(PushSubscription))
                    subs = subs_result.scalars().all()
                    sub_list = [s.subscription_json for s in subs]

                username = conversation.instagram_username or sender_id
                to_delete = await push_service.send_push_notification(
                    subscriptions=sub_list,
                    title="Perfil completo",
                    body=f"{username} completó el perfil!",
                    url=f"/conversaciones/{conversation.id}",
                    conversation_id=str(conversation.id),
                )

                if to_delete:
                    async with AsyncSessionLocal() as db_p3:
                        for endpoint in to_delete:
                            subs_to_del = await db_p3.execute(select(PushSubscription))
                            for sub in subs_to_del.scalars().all():
                                if sub.subscription_json.get("endpoint") == endpoint:
                                    await db_p3.delete(sub)
                        await db_p3.commit()

                # Broadcast state change to frontend
                await manager.broadcast({
                    "type": "conversation_updated",
                    "conversation": {
                        "id": str(conversation.id),
                        "instagram_user_id": conversation.instagram_user_id,
                        "instagram_username": conversation.instagram_username,
                        "unread_count": conversation.unread_count,
                        "needs_attention": conversation.needs_attention,
                        "state": ConversationState.self_managed.value,
                        "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                    },
                })

                logger.info(f"Profile saved and trainer notified for conversation {conversation.id}")

            # Call LLM
            response_text = await llm_service.process_message(
                conversation_history=history,
                new_message=content,
                notify_callback=notify_callback,
                profile_callback=profile_callback,
            )

            # Send response via Instagram
            send_result = await instagram_service.send_message(sender_id, response_text)

            # Check for 24h window error
            if "error" in send_result:
                error_code = send_result.get("error", {}).get("code")
                if error_code in (10, 100, 200):
                    logger.warning(f"24h window expired for {sender_id}")
                    return

            # Store bot response
            async with AsyncSessionLocal() as db5:
                bot_msg = Message(
                    conversation_id=conversation.id,
                    direction=MessageDirection.outbound,
                    sender_type=SenderType.bot,
                    content=response_text,
                )
                db5.add(bot_msg)

                # Update last_message_at
                conv_update = await db5.execute(
                    select(Conversation).where(Conversation.id == conversation.id)
                )
                conv_obj = conv_update.scalar_one_or_none()
                if conv_obj:
                    conv_obj.last_message_at = utcnow()

                await db5.commit()

                # Emit WS event for bot response
                await manager.broadcast({
                    "type": "new_message",
                    "conversation_id": str(conversation.id),
                    "message": {
                        "id": str(bot_msg.id),
                        "conversation_id": str(conversation.id),
                        "direction": bot_msg.direction.value,
                        "sender_type": bot_msg.sender_type.value,
                        "content": bot_msg.content,
                        "created_at": bot_msg.created_at.isoformat(),
                    },
                })

        except Exception as e:
            logger.error(f"Error processing message from {sender_id}: {e}", exc_info=True)
