from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import Expense
from bot.database.repositories import ExpenseRepository, CategoryRepository
from bot.services.gemini_service import GeminiService


class ExpenseService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.expense_repo = ExpenseRepository(session)
        self.category_repo = CategoryRepository(session)

    async def add_expense_from_text(self, user_id: int, text: str, gemini: GeminiService) -> Expense:
        """Парсит текст через Gemini и создаёт расход."""
        parsed = await gemini.parse_text_expense(text)
        if "error" in parsed:
            raise ValueError(f"Failed to parse expense: {parsed['error']}")
            
        description = parsed.get("description", "Unknown")
        amount = Decimal(str(parsed.get("amount", 0)))
        currency = parsed.get("currency", "RUB")
        
        # Автокатегоризация
        categories = await self.category_repo.get_user_categories(user_id)
        cat_names = [c.name for c in categories]
        category_name = await gemini.categorize_expense(description, cat_names)
        
        category = await self.category_repo.get_by_name(category_name, user_id)
        category_id = category.id if category else None

        return await self.expense_repo.create(
            user_id=user_id,
            amount=amount,
            currency=currency,
            description=description,
            source="text",
            category_id=category_id,
            raw_text=text,
        )

    async def add_expense_from_receipt(
        self, user_id: int, image_bytes: bytes, file_id: str, gemini: GeminiService
    ) -> list[Expense]:
        """Парсит фото чека через Gemini Vision и создаёт расходы."""
        parsed = await gemini.parse_receipt(image_bytes)
        if "error" in parsed:
            raise ValueError(f"Failed to parse receipt: {parsed['error']}")
            
        expenses = []
        store = parsed.get("store", "Unknown Store")
        currency = parsed.get("currency", "RUB")
        
        categories = await self.category_repo.get_user_categories(user_id)
        cat_names = [c.name for c in categories]
        
        for item in parsed.get("items", []):
            name = item.get("name", "Товар")
            desc = f"{store} — {name}"
            
            # Очистка суммы
            price_val = item.get("price", 0)
            price_str = str(price_val).replace(",", ".").replace(" ", "")
            try:
                amount = Decimal(price_str)
            except:
                amount = Decimal("0")
            
            cat_name = await gemini.categorize_expense(name, cat_names)
            category = await self.category_repo.get_by_name(cat_name, user_id)
            
            exp = await self.expense_repo.create(
                user_id=user_id,
                amount=amount,
                currency=currency,
                description=desc,
                source="photo",
                category_id=category.id if category else None,
                receipt_file_id=file_id,
            )
            expenses.append(exp)
            
        return expenses

    async def add_manual_expense(
        self, user_id: int, amount: Decimal, description: str, 
        category_id: int, currency: str = "RUB"
    ) -> Expense:
        """Добавляет расход вручную."""
        return await self.expense_repo.create(
            user_id=user_id,
            amount=amount,
            currency=currency,
            description=description,
            source="text",
            category_id=category_id,
        )

    async def get_recent_expenses(self, user_id: int, limit: int = 10) -> list[Expense]:
        """Возвращает последние расходы пользователя."""
        return await self.expense_repo.get_user_expenses(user_id, limit=limit)

    async def delete_expense(self, expense_id: int, user_id: int) -> bool:
        """Удаляет расход, если он принадлежит пользователю."""
        return await self.expense_repo.delete(expense_id, user_id)
