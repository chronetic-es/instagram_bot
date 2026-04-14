import asyncio
import logging

import httpx
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Setting
from app.services.instagram import get_access_token, set_access_token

logger = logging.getLogger(__name__)

_DEFAULT_EXPIRES_IN = 5183944  # ~60 days in seconds


async def _get_db_token() -> str | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Setting).where(Setting.key == "instagram_access_token")
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None


async def _save_token(token: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Setting).where(Setting.key == "instagram_access_token")
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = token
        else:
            db.add(Setting(key="instagram_access_token", value=token))
        await db.commit()


async def initialize_token() -> None:
    """
    On startup, decide which token to use:
    - If .env token differs from DB token → manual override, save .env token to DB
    - If DB token exists → use it (may have been auto-refreshed since last restart)
    - Otherwise → first run, save .env token to DB
    """
    from app.config import get_settings
    env_token = get_settings().meta_page_access_token
    db_token = await _get_db_token()

    if env_token and env_token != db_token:
        logger.info("New token detected in .env — saving to DB as manual override")
        await _save_token(env_token)
        set_access_token(env_token)
    elif db_token:
        logger.info("Using Instagram token from DB")
        set_access_token(db_token)
    else:
        logger.info("First run: saving .env token to DB")
        if env_token:
            await _save_token(env_token)
        set_access_token(env_token or "")


async def _do_refresh() -> int:
    """
    Attempt to refresh the current Instagram token.
    Returns the number of seconds to sleep before the next attempt:
    - Success: 80% of expires_in (~48 days for a 60-day token)
    - Failure: 24 hours
    """
    current_token = get_access_token()
    if not current_token:
        logger.warning("No Instagram token configured, skipping refresh")
        return 24 * 3600

    url = "https://graph.instagram.com/refresh_access_token"
    params = {"grant_type": "ig_refresh_token", "access_token": current_token}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            new_token = data.get("access_token")
            if new_token:
                expires_in = data.get("expires_in", _DEFAULT_EXPIRES_IN)
                set_access_token(new_token)
                await _save_token(new_token)
                next_in_days = int(expires_in * 0.8) // 86400
                logger.info(
                    f"Instagram token refreshed successfully. "
                    f"Next refresh in ~{next_in_days} days."
                )
                return int(expires_in * 0.8)
            else:
                logger.error(f"Token refresh: unexpected response body: {data}")
        else:
            logger.error(
                f"Token refresh failed: {response.status_code} {response.text}"
            )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")

    logger.info("Token refresh failed — retrying in 24 hours")
    return 24 * 3600


async def token_refresh_loop() -> None:
    """Background task: refresh token on startup then sleep per expires_in."""
    while True:
        sleep_seconds = await _do_refresh()
        await asyncio.sleep(sleep_seconds)
