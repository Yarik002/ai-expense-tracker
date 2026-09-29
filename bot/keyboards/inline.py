from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.models import Category

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить расход", callback_data="add_expense")
    builder.button(text="📊 Аналитика", callback_data="analytics")
    builder.button(text="📋 Мои расходы", callback_data="my_expenses")
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.button(text="⭐ Премиум", callback_data="premium")
    builder.button(text="ℹ️ О боте", callback_data="about_bot")
    builder.adjust(1, 2, 2, 1)
    return builder.as_markup()

def categories_keyboard(categories: list[Category], action: str = 'cat') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"{cat.emoji} {cat.name}", callback_data=f"{action}:{cat.id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_menu"))
    return builder.as_markup()

def confirm_expense_keyboard(expense_id: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_exp:{expense_id}")
    builder.button(text="✏️ Изменить", callback_data=f"edit_exp:{expense_id}")
    builder.button(text="❌ Удалить", callback_data=f"delete_exp:{expense_id}")
    builder.adjust(1, 2)
    return builder.as_markup()

def analytics_keyboard(is_premium: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Эта неделя", callback_data="analytics_week")
    builder.button(text="📆 Этот месяц", callback_data="analytics_month")
    builder.button(text="📊 Сравнение", callback_data="analytics_compare")
    builder.button(text="🔝 Топ расходов", callback_data="analytics_top")
    
    if is_premium:
        builder.button(text="🤖 Финансовый ИИ-Советник", callback_data="ai_advice")
        builder.button(text="📄 Выгрузить Excel (CSV)", callback_data="export_csv")
        builder.button(text="📈 Умный график (ИИ)", callback_data="smart_chart")
        builder.button(text="◀️ Назад", callback_data="back_menu")
        builder.adjust(2, 2, 1, 1, 1, 1)
    else:
        builder.button(text="⭐ ИИ-Советник и Графики (Premium)", callback_data="premium")
        builder.button(text="◀️ Назад", callback_data="back_menu")
        builder.adjust(2, 2, 1, 1)
        
    return builder.as_markup()

def premium_keyboard(is_premium: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_premium:
        builder.button(text="⭐ Месяц (150 Stars)", callback_data="buy_monthly")
        builder.button(text="⭐ Год (1500 Stars)", callback_data="buy_yearly")
        builder.button(text="◀️ Назад", callback_data="back_menu")
        builder.adjust(1, 1, 1)
    else:
        builder.button(text="⭐ Продлить на год (1500 Stars)", callback_data="buy_yearly")
        builder.button(text="◀️ Назад", callback_data="back_menu")
        builder.adjust(1, 1)
    return builder.as_markup()

def settings_keyboard(is_premium: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💱 Валюта", callback_data="set_currency")
    builder.button(text="💵 Мои финансы", callback_data="set_budgets")
    
    if is_premium:
        builder.button(text="🏷 Мои категории", callback_data="set_categories")
        builder.button(text="🎨 Оформление", callback_data="set_appearance")
        builder.adjust(1, 1, 1, 1)
    else:
        builder.button(text="🔒 Категории (Premium)", callback_data="premium")
        builder.button(text="🔒 Оформление (Premium)", callback_data="premium")
        builder.adjust(1, 1, 1, 1)
        
    builder.button(text="◀️ Назад", callback_data="back_menu")
    return builder.as_markup()

def appearance_keyboard(current_theme: str = "standard") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    t_std = "✅ Стандартная" if current_theme == "standard" else "Стандартная"
    t_biz = "✅ Бизнес (Строгая)" if current_theme == "business" else "Бизнес (Строгая)"
    t_min = "✅ Минимализм" if current_theme == "minimal" else "Минимализм"
    
    builder.button(text=t_std, callback_data="theme:standard")
    builder.button(text=t_biz, callback_data="theme:business")
    builder.button(text=t_min, callback_data="theme:minimal")
    
    builder.button(text="◀️ Назад", callback_data="settings")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def currency_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇧🇾 BYN", callback_data="currency:BYN")
    builder.button(text="🇷🇺 RUB", callback_data="currency:RUB")
    builder.button(text="🇺🇸 USD", callback_data="currency:USD")
    builder.button(text="🇪🇺 EUR", callback_data="currency:EUR")
    builder.adjust(2, 2)
    return builder.as_markup()

def back_keyboard(callback_data: str = 'back_menu') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=callback_data)
    return builder.as_markup()

def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="💰 Доходы", callback_data="admin_revenue")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.adjust(2, 2)
    return builder.as_markup()

def pagination_keyboard(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if current_page > 1:
        builder.button(text="◀️", callback_data=f"{prefix}:page:{current_page - 1}")
    else:
        builder.button(text=" ", callback_data="ignore")
        
    builder.button(text=f"{current_page}/{total_pages}", callback_data="ignore")
    
    if current_page < total_pages:
        builder.button(text="▶️", callback_data=f"{prefix}:page:{current_page + 1}")
    else:
        builder.button(text=" ", callback_data="ignore")
        
    builder.adjust(3)
    return builder.as_markup()
