from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import User, Subscription
from bot.database.repositories import UserRepository, SubscriptionRepository
from bot.config import settings

class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.sub_repo = SubscriptionRepository(session)

    async def is_premium(self, user: User) -> bool:
        if user.subscription_type == 'premium' and user.subscription_expires_at:
            return user.subscription_expires_at > datetime.now()
        return False

    async def can_scan_receipt(self, user: User) -> bool:
        if await self.is_premium(user):
            return True
            
        now = datetime.now()
        if not user.receipt_count_reset_at or user.receipt_count_reset_at.month != now.month:
            user.monthly_receipt_count = 0
            user.receipt_count_reset_at = now
            await self.user_repo.update(user)
            
        return user.monthly_receipt_count < settings.FREE_RECEIPT_LIMIT

    async def get_remaining_receipts(self, user: User) -> int:
        if await self.is_premium(user):
            return 9999
        now = datetime.now()
        if not user.receipt_count_reset_at or user.receipt_count_reset_at.month != now.month:
            return settings.FREE_RECEIPT_LIMIT
        return max(0, settings.FREE_RECEIPT_LIMIT - user.monthly_receipt_count)

    async def increment_receipt_count(self, user: User) -> None:
        if await self.is_premium(user):
            return
            
        now = datetime.now()
        if not user.receipt_count_reset_at or user.receipt_count_reset_at.month != now.month:
            user.monthly_receipt_count = 1
            user.receipt_count_reset_at = now
        else:
            user.monthly_receipt_count += 1
        await self.user_repo.update(user)

    async def can_add_manual_expense(self, user: User) -> bool:
        if await self.is_premium(user):
            return True
            
        from sqlalchemy import select, func, and_
        from bot.database.models import Expense
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stmt = select(func.count(Expense.id)).where(
            and_(Expense.user_id == user.id, Expense.created_at >= start_of_week)
        )
        result = await self.session.execute(stmt)
        return (result.scalar_one() or 0) < 50

    async def get_remaining_manual_expenses(self, user: User) -> int:
        if await self.is_premium(user):
            return 9999
            
        from sqlalchemy import select, func, and_
        from bot.database.models import Expense
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stmt = select(func.count(Expense.id)).where(
            and_(Expense.user_id == user.id, Expense.created_at >= start_of_week)
        )
        result = await self.session.execute(stmt)
        return max(0, 50 - (result.scalar_one() or 0))

    async def activate_subscription(self, user_id: int, plan: str, charge_id: str, amount_stars: int) -> Subscription:
        days = 30 if plan == 'monthly' else 365
        now = datetime.now()
        expires_at = now + timedelta(days=days)
        
        sub = await self.sub_repo.create(
            user_id=user_id,
            plan=plan,
            starts_at=now,
            expires_at=expires_at,
            charge_id=charge_id,
            amount_stars=amount_stars,
        )
        
        user = await self.user_repo.get_by_id(user_id)
        if user:
            user.subscription_type = 'premium'
            if user.subscription_expires_at and user.subscription_expires_at > now:
                user.subscription_expires_at += timedelta(days=days)
            else:
                user.subscription_expires_at = expires_at
            await self.user_repo.update(user)
            
        return sub

    async def check_and_expire_subscriptions(self) -> int:
        """Find and expire overdue subscriptions."""
        from sqlalchemy import select, and_
        now = datetime.now()
        stmt = select(Subscription).where(
            and_(
                Subscription.is_active == True,
                Subscription.expires_at <= now,
            )
        )
        result = await self.session.execute(stmt)
        expired = list(result.scalars().all())
        count = 0
        for sub in expired:
            sub.is_active = False
            user = await self.user_repo.get_by_id(sub.user_id)
            if user and user.subscription_expires_at and user.subscription_expires_at <= now:
                user.subscription_type = 'free'
            count += 1
        await self.session.commit()
        return count

    async def get_subscription_info(self, user: User) -> dict:
        if not await self.is_premium(user):
            return {"plan": "free"}
            
        days_remaining = (user.subscription_expires_at - datetime.now()).days if user.subscription_expires_at else 0
        return {
            "plan": "premium",
            "expires_at": user.subscription_expires_at,
            "days_remaining": max(0, days_remaining)
        }
