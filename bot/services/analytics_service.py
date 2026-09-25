from decimal import Decimal
from datetime import datetime, timedelta
import calendar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload
from bot.database.models import Expense, Category
from bot.database.repositories import ExpenseRepository


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.expense_repo = ExpenseRepository(session)

    async def _get_expenses_with_categories(
        self, user_id: int, start_date: datetime, end_date: datetime
    ) -> list[Expense]:
        """Получает расходы с подгруженными категориями."""
        stmt = (
            select(Expense)
            .options(joinedload(Expense.category))
            .where(
                Expense.user_id == user_id,
                Expense.created_at >= start_date,
                Expense.created_at <= end_date,
            )
            .order_by(desc(Expense.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_monthly_summary(self, user_id: int, year: int, month: int) -> dict:
        """Месячная сводка: итого, по категориям, среднее в день."""
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        expenses = await self._get_expenses_with_categories(user_id, start_date, end_date)
        
        total = sum(e.amount for e in expenses)
        by_category: dict[str, dict] = {}
        for e in expenses:
            cat_name = e.category.name if e.category else "Другое"
            emoji = e.category.emoji if e.category else "❓"
            if cat_name not in by_category:
                by_category[cat_name] = {"name": cat_name, "emoji": emoji, "total": Decimal(0)}
            by_category[cat_name]["total"] += e.amount
            
        category_list = []
        for cat in by_category.values():
            cat["percentage"] = round(float(cat["total"] / total * 100), 1) if total > 0 else 0
            category_list.append(cat)
            
        category_list.sort(key=lambda x: x["total"], reverse=True)
        
        avg_per_day = total / last_day if last_day > 0 else Decimal(0)
        
        return {
            "total": total,
            "by_category": category_list,
            "expense_count": len(expenses),
            "avg_per_day": avg_per_day,
        }

    async def get_weekly_summary(self, user_id: int) -> dict:
        """Недельная сводка (с понедельника по сегодня)."""
        now = datetime.now()
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        
        expenses = await self._get_expenses_with_categories(user_id, start_date, end_date)
        total = sum(e.amount for e in expenses)
        
        by_category: dict[str, dict] = {}
        for e in expenses:
            cat_name = e.category.name if e.category else "Другое"
            emoji = e.category.emoji if e.category else "❓"
            if cat_name not in by_category:
                by_category[cat_name] = {"name": cat_name, "emoji": emoji, "total": Decimal(0)}
            by_category[cat_name]["total"] += e.amount
            
        category_list = []
        for cat in by_category.values():
            cat["percentage"] = round(float(cat["total"] / total * 100), 1) if total > 0 else 0
            category_list.append(cat)
            
        category_list.sort(key=lambda x: x["total"], reverse=True)
        days = (now - start_date).days + 1
        avg_per_day = total / days if days > 0 else Decimal(0)
        
        return {
            "total": total,
            "by_category": category_list,
            "expense_count": len(expenses),
            "avg_per_day": avg_per_day,
        }

    async def compare_with_previous_month(self, user_id: int) -> dict:
        """Сравнение текущего месяца с предыдущим."""
        now = datetime.now()
        curr_summary = await self.get_monthly_summary(user_id, now.year, now.month)
        
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        prev_summary = await self.get_monthly_summary(user_id, prev_year, prev_month)
        
        curr_total = curr_summary["total"]
        prev_total = prev_summary["total"]
        difference = curr_total - prev_total
        percentage_change = round(
            float(difference / prev_total * 100), 1
        ) if prev_total > 0 else (100 if curr_total > 0 else 0)
        
        prev_cats = {c["name"]: c["total"] for c in prev_summary["by_category"]}
        
        category_changes = []
        for cat in curr_summary["by_category"]:
            name = cat["name"]
            curr_val = cat["total"]
            prev_val = prev_cats.get(name, Decimal(0))
            change = curr_val - prev_val
            pct = round(float(change / prev_val * 100), 1) if prev_val > 0 else (100 if curr_val > 0 else 0)
            category_changes.append({
                "name": name,
                "current": curr_val,
                "previous": prev_val,
                "change_percent": pct,
            })
            
        return {
            "current_total": curr_total,
            "previous_total": prev_total,
            "difference": difference,
            "percentage_change": percentage_change,
            "category_changes": category_changes,
        }

    async def get_top_expenses(self, user_id: int, year: int, month: int, limit: int = 5) -> list[Expense]:
        """Топ расходов за месяц по сумме."""
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, last_day, 23, 59, 59)
        expenses = await self._get_expenses_with_categories(user_id, start_date, end_date)
        expenses.sort(key=lambda x: x.amount, reverse=True)
        return expenses[:limit]

    async def get_daily_average(self, user_id: int, year: int, month: int) -> Decimal:
        """Средний расход в день за месяц."""
        summary = await self.get_monthly_summary(user_id, year, month)
        return summary["avg_per_day"]
