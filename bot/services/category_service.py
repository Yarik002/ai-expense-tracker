from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import Category
from bot.database.repositories import CategoryRepository

DEFAULT_CATEGORIES = [
    ('Еда', 'food', '🍕'),
    ('Продукты', 'groceries', '🛒'),
    ('Транспорт', 'transport', '🚕'),
    ('Жильё', 'housing', '🏠'),
    ('Развлечения', 'entertainment', '🎮'),
    ('Одежда', 'clothing', '👕'),
    ('Здоровье', 'health', '💊'),
    ('Быт', 'household', '🧴'),
    ('Рестораны', 'restaurants', '🍽'),
    ('Кофе', 'coffee', '☕'),
    ('Связь', 'telecom', '📱'),
    ('Образование', 'education', '🎓'),
    ('Подарки', 'gifts', '🎁'),
    ('Работа', 'work', '💼'),
    ('Техника', 'electronics', '💻'),
    ('Игрушки', 'toys', '🧸'),
    ('Автомобиль', 'car', '🚗'),
    ('Питомцы', 'pets', '🐕'),
    ('Красота', 'beauty', '💅'),
    ('Спорт', 'sport', '🏋️'),
    ('Путешествия', 'travel', '✈️'),
    ('Хобби', 'hobby', '🎨'),
    ('Подписки', 'subscriptions', '📺'),
    ('Инвестиции', 'investments', '📈'),
    ('Благотворительность', 'charity', '🕊'),
    ('Дети', 'children', '👶'),
    ('Ремонт', 'repairs', '🛠'),
    ('Канцелярия', 'stationery', '📎'),
    ('Книги', 'books', '📚'),
    ('Мебель', 'furniture', '🛋'),
    ('Косметика', 'cosmetics', '💄'),
    ('Аптека', 'pharmacy', '🏥'),
    ('Топливо', 'fuel', '⛽'),
    ('Сладости', 'sweets', '🍬'),
    ('Обувь', 'shoes', '👟'),
    ('Алкоголь', 'alcohol', '🍷'),
    ('Семья', 'family', '👪'),
    ('Налоги', 'taxes', '🏛'),
    ('Страховка', 'insurance', '🛡'),
    ('Дача и Сад', 'garden', '🏡'),
    ('Услуги', 'services', '🛎'),
    ('Другое', 'other', '❓'),
]

async def seed_default_categories(session_factory) -> None:
    async with session_factory() as session:
        repo = CategoryRepository(session)
        await repo.seed_defaults(DEFAULT_CATEGORIES)

class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CategoryRepository(session)

    async def get_categories_for_user(self, user_id: int) -> list[Category]:
        return await self.repo.get_user_categories(user_id)

    async def create_custom_category(self, user_id: int, name: str, emoji: str) -> Category:
        return await self.repo.create_custom(
            user_id=user_id,
            name=name,
            name_en='custom',
            emoji=emoji,
        )

    async def delete_custom_category(self, category_id: int, user_id: int) -> bool:
        return await self.repo.delete_custom(category_id, user_id)

    async def find_category_by_name(self, name: str, user_id: int) -> Optional[Category]:
        return await self.repo.get_by_name(name, user_id)
