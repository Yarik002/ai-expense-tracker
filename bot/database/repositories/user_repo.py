from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from bot.database.models import User, Expense

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, telegram_id: int, username: Optional[str], first_name: str, 
                     last_name: Optional[str], language_code: str, is_admin: bool = False) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_admin=is_admin
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        user = await self.session.merge(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = select(User).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_premium_users(self) -> List[User]:
        stmt = select(User).where(User.subscription_type == "premium")
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_count(self) -> int:
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_premium_count(self) -> int:
        stmt = select(func.count(User.id)).where(User.subscription_type == "premium")
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_active_users(self, days: int = 30) -> List[User]:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = select(User).join(Expense).where(Expense.created_at >= cutoff_date).distinct()
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def block_user(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            user.is_blocked = True
            await self.session.commit()
            return True
        return False

    async def unblock_user(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            user.is_blocked = False
            await self.session.commit()
            return True
        return False
