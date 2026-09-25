from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from bot.database.models import Category

class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_default_categories(self) -> List[Category]:
        stmt = select(Category).where(Category.is_default == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_categories(self, user_id: int) -> List[Category]:
        stmt = select(Category).where(
            or_(Category.is_default == True, Category.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        stmt = select(Category).where(Category.id == category_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, user_id: Optional[int] = None) -> Optional[Category]:
        conditions = [Category.name == name]
        if user_id:
            conditions.append(or_(Category.is_default == True, Category.user_id == user_id))
        else:
            conditions.append(Category.is_default == True)
            
        stmt = select(Category).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_custom(self, user_id: int, name: str, name_en: str, emoji: str) -> Category:
        category = Category(
            user_id=user_id,
            name=name,
            name_en=name_en,
            emoji=emoji,
            is_default=False
        )
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def delete_custom(self, category_id: int, user_id: int) -> bool:
        stmt = select(Category).where(and_(Category.id == category_id, Category.user_id == user_id, Category.is_default == False))
        result = await self.session.execute(stmt)
        category = result.scalar_one_or_none()
        if category:
            await self.session.delete(category)
            await self.session.commit()
            return True
        return False

    async def seed_defaults(self, categories: List[Tuple[str, str, str]]) -> None:
        existing_defaults = await self.get_default_categories()
        existing_names = {c.name for c in existing_defaults}
        
        new_categories = []
        for name, name_en, emoji in categories:
            if name not in existing_names:
                new_categories.append(Category(name=name, name_en=name_en, emoji=emoji, is_default=True))
                
        if new_categories:
            self.session.add_all(new_categories)
            await self.session.commit()
