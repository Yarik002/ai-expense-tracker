from typing import Optional, List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import joinedload
from bot.database.models import Expense, Category

class ExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, amount: Decimal, currency: str, description: str, 
                     source: str, category_id: Optional[int] = None, receipt_file_id: Optional[str] = None, 
                     raw_text: Optional[str] = None) -> Expense:
        expense = Expense(
            user_id=user_id,
            amount=amount,
            currency=currency,
            description=description,
            source=source,
            category_id=category_id,
            receipt_file_id=receipt_file_id,
            raw_text=raw_text
        )
        self.session.add(expense)
        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def get_by_id(self, expense_id: int) -> Optional[Expense]:
        stmt = select(Expense).options(joinedload(Expense.category)).where(Expense.id == expense_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_expenses(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Expense]:
        stmt = select(Expense).options(joinedload(Expense.category)).where(Expense.user_id == user_id).order_by(desc(Expense.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_expenses_by_period(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Expense]:
        stmt = select(Expense).options(joinedload(Expense.category)).where(
            and_(Expense.user_id == user_id, Expense.created_at >= start_date, Expense.created_at <= end_date)
        ).order_by(desc(Expense.created_at))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_expenses_by_category(self, user_id: int, category_id: int, start_date: datetime, end_date: datetime) -> List[Expense]:
        stmt = select(Expense).options(joinedload(Expense.category)).where(
            and_(
                Expense.user_id == user_id, 
                Expense.category_id == category_id,
                Expense.created_at >= start_date, 
                Expense.created_at <= end_date
            )
        ).order_by(desc(Expense.created_at))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_by_period(self, user_id: int, start_date: datetime, end_date: datetime) -> Decimal:
        stmt = select(func.sum(Expense.amount)).where(
            and_(Expense.user_id == user_id, Expense.created_at >= start_date, Expense.created_at <= end_date)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or Decimal('0.00')

    async def get_totals_by_category(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Tuple[Category, Decimal]]:
        stmt = (
            select(Category, func.sum(Expense.amount).label("total"))
            .join(Expense, Category.id == Expense.category_id)
            .where(
                and_(
                    Expense.user_id == user_id,
                    Expense.created_at >= start_date,
                    Expense.created_at <= end_date
                )
            )
            .group_by(Category.id)
            .order_by(desc("total"))
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def delete(self, expense_id: int, user_id: int) -> bool:
        stmt = select(Expense).where(and_(Expense.id == expense_id, Expense.user_id == user_id))
        result = await self.session.execute(stmt)
        expense = result.scalar_one_or_none()
        if expense:
            await self.session.delete(expense)
            await self.session.commit()
            return True
        return False

    async def get_expense_count(self, user_id: int) -> int:
        stmt = select(func.count(Expense.id)).where(Expense.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
