import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.deps import get_current_user
from app.models import Setting
from app.schemas import SettingsOut, UpdateSettingsRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
async def get_settings_endpoint(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(select(Setting).where(Setting.key == "bot_enabled"))
    setting = result.scalar_one_or_none()
    bot_enabled = setting.value if setting else True
    return SettingsOut(bot_enabled=bool(bot_enabled))


@router.patch("", response_model=SettingsOut)
async def update_settings_endpoint(
    body: UpdateSettingsRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(select(Setting).where(Setting.key == "bot_enabled"))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = body.bot_enabled
    else:
        setting = Setting(key="bot_enabled", value=body.bot_enabled)
        db.add(setting)

    await db.commit()
    logger.info(f"bot_enabled set to {body.bot_enabled}")
    return SettingsOut(bot_enabled=body.bot_enabled)
