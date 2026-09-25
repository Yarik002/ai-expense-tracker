from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import Category
from bot.database.repositories import CategoryRepository

DEFAULT_CATEGORIES = [
    ("Еда", "food", "🍕"),
    ("Продукты", "groceries", "🛒"),
    ("Транспорт", "transport", "🚕"),
    ("Жильё", "housing", "🏠"),
    ("Развлечения", "entertainment", "🎮"),
    ("Одежда", "clothing", "👕"),
    ("Здоровье", "health", "💊"),
    ("Быт", "household", "🧴"),
    ("Рестораны", "restaurants", "🍽"),
    ("Кофе", "coffee", "☕"),
    ("Связь", "telecom", "📱"),
    ("Образование", "education", "🎓"),
    ("Подарки", "gifts", "🎁"),
    ("Работа", "work", "💼"),
    ("Другое", "other", "❓"),
]


async def seed_default_categories(session_factory) -> None:
    """Заполняет БД категориями по умолчанию при старте бота."""
    async with session_factory() as session:
        repo = CategoryRepository(session)
        await repo.seed_defaults(DEFAULT_CATEGORIES)


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CategoryRepository(session)

    async def get_categories_for_user(self, user_id: int) -> list[Category]:
        """Получает все категории (дефолтные + пользовательские)."""
        return await self.repo.get_user_categories(user_id)

    async def create_custom_category(self, user_id: int, name: str, emoji: str) -> Category:
        """Создаёт кастомную категорию для пользователя."""
        return await self.repo.create_custom(
            user_id=user_id,
            name=name,
            name_en="custom",
            emoji=emoji,
        )

    async def delete_custom_category(self, category_id: int, user_id: int) -> bool:
        """Удаляет кастомную категорию пользователя."""
        return await self.repo.delete_custom(category_id, user_id)

    async def find_category_by_name(self, name: str, user_id: int) -> Optional[Category]:
        """Ищет категорию по имени."""
        return await self.repo.get_by_name(name, user_id)
