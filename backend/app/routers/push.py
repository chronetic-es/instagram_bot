import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.deps import get_current_user
from app.models import PushSubscription
from app.schemas import PushSubscribeRequest, PushUnsubscribeRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/push", tags=["push"])


@router.post("/subscribe")
async def subscribe(
    body: PushSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    endpoint = body.subscription.get("endpoint", "")

    # Check if already subscribed
    result = await db.execute(select(PushSubscription))
    existing = result.scalars().all()
    for sub in existing:
        if sub.subscription_json.get("endpoint") == endpoint:
            logger.info(f"Push subscription already exists for {endpoint[:50]}")
            return {"status": "already_subscribed"}

    new_sub = PushSubscription(subscription_json=body.subscription)
    db.add(new_sub)
    await db.commit()
    logger.info(f"New push subscription: {endpoint[:50]}")
    return {"status": "subscribed"}


@router.post("/unsubscribe")
async def unsubscribe(
    body: PushUnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await db.execute(select(PushSubscription))
    subs = result.scalars().all()
    deleted = 0
    for sub in subs:
        if sub.subscription_json.get("endpoint") == body.endpoint:
            await db.delete(sub)
            deleted += 1
    await db.commit()
    logger.info(f"Removed {deleted} push subscription(s) for {body.endpoint[:50]}")
    return {"status": "unsubscribed", "deleted": deleted}
