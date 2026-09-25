from decimal import Decimal
from datetime import datetime
from typing import Optional
from bot.database.models import Expense, Category

def get_currency_symbol(currency: str) -> str:
    symbols = {
        'RUB': '₽',
        'USD': '$',
        'EUR': '€'
    }
    return symbols.get(currency, currency)

def format_amount(amount: Decimal, currency: str = 'RUB') -> str:
    symbol = get_currency_symbol(currency)
    formatted = f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
    if currency in ['USD', 'EUR']:
        return f"{symbol}{formatted}"
    return f"{formatted} {symbol}"

def escape_html(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def format_expense(expense: Expense, category: Optional[Category] = None) -> str:
    emoji = category.emoji if category else "❓"
    desc = escape_html(expense.description)
    amount = format_amount(expense.amount, expense.currency)
    return f"{emoji} {desc}: {amount}"

def format_expense_list(expenses: list, include_id: bool = False) -> str:
    if not expenses:
        return "Нет расходов."
    
    lines = []
    for exp in expenses:
        base = format_expense(exp, exp.category)
        if include_id:
            base += f" (ID: {exp.id})"
        lines.append(base)
    return "\n".join(lines)

def format_monthly_report(summary: dict, currency: str = 'RUB') -> str:
    total = format_amount(summary["total"], currency)
    lines = [f"📊 <b>Отчет за месяц</b>\n", f"<b>Всего:</b> {total}\n"]
    
    if not summary["by_category"]:
        lines.append("Нет расходов в этом месяце.")
        return "\n".join(lines)
        
    lines.append("<b>По категориям:</b>")
    for cat in summary["by_category"]:
        amount = format_amount(cat['total'], currency)
        pct = f"{cat['percentage']:.1f}%"
        lines.append(f"{cat['emoji']} {cat['name']}: {amount} ({pct})")
        
    lines.append(f"\nСредний расход в день: {format_amount(summary['avg_per_day'], currency)}")
    return "\n".join(lines)

def format_comparison_report(comparison: dict, currency: str = 'RUB') -> str:
    curr = format_amount(comparison['current_total'], currency)
    prev = format_amount(comparison['previous_total'], currency)
    diff = format_amount(abs(comparison['difference']), currency)
    pct = abs(comparison['percentage_change'])
    
    direction = "больше 📈" if comparison['difference'] > 0 else "меньше 📉"
    if comparison['difference'] == 0:
        direction = "так же ➖"
        
    lines = [
        "📊 <b>Сравнение с прошлым месяцем</b>\n",
        f"Текущий месяц: {curr}",
        f"Прошлый месяц: {prev}",
        f"Разница: на {diff} {direction} ({pct:.1f}%)\n"
    ]
    
    if comparison['category_changes']:
        lines.append("<b>Изменения по категориям:</b>")
        for cat in comparison['category_changes']:
            c_curr = format_amount(cat['current'], currency)
            c_prev = format_amount(cat['previous'], currency)
            c_pct = f"{cat['change_percent']:+.1f}%"
            lines.append(f"• {cat['name']}: {c_curr} (было {c_prev}, {c_pct})")
            
    return "\n".join(lines)

def format_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y")

def format_datetime(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")
