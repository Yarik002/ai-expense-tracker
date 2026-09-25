from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from bot.database.models import Subscription

class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, plan: str, starts_at: datetime, expires_at: datetime, 
                     charge_id: str, amount_stars: int) -> Subscription:
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            starts_at=starts_at,
            expires_at=expires_at,
            telegram_payment_charge_id=charge_id,
            amount_stars=amount_stars,
            is_active=True
        )
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription

    async def get_active(self, user_id: int) -> Optional[Subscription]:
        now = datetime.utcnow()
        stmt = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                Subscription.expires_at > now
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_subscriptions(self, user_id: int) -> List[Subscription]:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate(self, subscription_id: int) -> bool:
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.session.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.is_active = False
            await self.session.commit()
            return True
        return False

    async def get_total_revenue(self) -> int:
        stmt = select(func.sum(Subscription.amount_stars)).where(Subscription.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_subscription_count(self) -> int:
        stmt = select(func.count(Subscription.id)).where(Subscription.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
