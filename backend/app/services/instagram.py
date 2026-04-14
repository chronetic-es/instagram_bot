import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GRAPH_API_URL = "https://graph.instagram.com/v25.0"

# Mutable token state — updated in-place by token_refresh service
_state = {"access_token": settings.meta_page_access_token}


def get_access_token() -> str:
    return _state["access_token"]


def set_access_token(token: str) -> None:
    _state["access_token"] = token


async def send_message(recipient_id: str, text: str) -> dict:
    """Send a DM via Instagram API."""
    url = f"{GRAPH_API_URL}/{settings.instagram_account_id}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {get_access_token()}"},
            )
        if response.status_code != 200:
            logger.error(f"Failed to send message to {recipient_id}: {response.status_code} {response.text}")
        else:
            logger.info(f"Sent message to {recipient_id}: {response.text}")
        return response.json()
    except Exception as e:
        logger.error(f"Network error sending message to {recipient_id}: {e}")
        return {"error": {"message": str(e), "code": -1}}


async def send_typing_indicator(recipient_id: str) -> None:
    """Send typing_on indicator to show the bot is typing."""
    url = f"{GRAPH_API_URL}/{settings.instagram_account_id}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": "typing_on",
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {get_access_token()}"},
            )
    except Exception as e:
        logger.warning(f"Failed to send typing indicator: {e}")


async def get_user_info(igsid: str) -> dict:
    """Fetch user name and profile pic from Instagram Graph API."""
    url = f"{GRAPH_API_URL}/{igsid}"
    params = {
        "fields": "name,profile_pic",
        "access_token": get_access_token(),
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to get user info for {igsid}: {e}")
    return {}
