import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.deps import get_current_user
from app.models import Profile, Conversation
from app.schemas import ProfileOut, ProfileAnswerItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileOut])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).order_by(desc(Profile.created_at))
    )
    profiles = result.scalars().all()

    out = []
    for p in profiles:
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == p.conversation_id)
        )
        conv = conv_result.scalar_one_or_none()

        answers = [ProfileAnswerItem(**a) for a in (p.answers or [])]
        out.append(ProfileOut(
            id=p.id,
            conversation_id=p.conversation_id,
            instagram_username=conv.instagram_username if conv else None,
            profile_pic_url=conv.profile_pic_url if conv else None,
            answers=answers,
            summary=p.summary,
            created_at=p.created_at,
        ))

    return out


@router.get("/{profile_id}", response_model=ProfileOut)
async def get_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == p.conversation_id)
    )
    conv = conv_result.scalar_one_or_none()

    answers = [ProfileAnswerItem(**a) for a in (p.answers or [])]
    return ProfileOut(
        id=p.id,
        conversation_id=p.conversation_id,
        instagram_username=conv.instagram_username if conv else None,
        profile_pic_url=conv.profile_pic_url if conv else None,
        answers=answers,
        summary=p.summary,
        created_at=p.created_at,
    )
