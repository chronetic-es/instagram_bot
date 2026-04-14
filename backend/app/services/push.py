import json
import logging
from pywebpush import webpush, WebPushException
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_push_notification(
    subscriptions: list[dict],
    title: str,
    body: str,
    url: str = "/",
    conversation_id: str = None,
) -> list[str]:
    """
    Send a Web Push notification to all subscriptions.
    Returns list of endpoints to delete (expired/invalid subscriptions).
    """
    to_delete = []

    for sub in subscriptions:
        endpoint = sub.get("endpoint", "")
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({
                    "title": title,
                    "body": body,
                    "url": url,
                    "conversation_id": conversation_id,
                }),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_claim_email},
            )
            logger.info(f"Push notification sent to {endpoint[:50]}...")
        except WebPushException as e:
            logger.error(f"WebPushException for {endpoint[:50]}: {e}")
            # 410 Gone = subscription expired, should be deleted
            if e.response and e.response.status_code in (404, 410):
                to_delete.append(endpoint)
        except Exception as e:
            logger.error(f"Push notification error: {e}")

    return to_delete
