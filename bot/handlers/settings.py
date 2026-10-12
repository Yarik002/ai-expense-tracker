from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decimal import Decimal
from bot.database.engine import async_session
from bot.database.models import User
from bot.database.repositories import UserRepository
from bot.services.category_service import CategoryService
from bot.keyboards.inline import (
    settings_keyboard,
    currency_keyboard,
    balance_keyboard,
    cancel_balance_keyboard,
    appearance_keyboard,
)
from bot.keyboards.reply import main_reply_keyboard
from bot.utils.formatters import format_amount

router = Router()

class SettingsStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_emoji = State()
    waiting_for_budget_amount = State()
    waiting_for_balance_add = State()
    waiting_for_balance_sub = State()

REPLY_BUTTONS = ["➕ Расход", "📸 Чек", "📋 Мои расходы", "⚙️ Настройки", "🏠 Главное меню", "❌ Отмена", "Отмена"]

async def handle_reply_button(message: Message, state: FSMContext, db_user: User) -> bool:
    text = message.text.strip() if message.text else ""
    if text in REPLY_BUTTONS:
        await state.clear()
        if text == "➕ Расход":
            from bot.handlers.expenses import start_add_expense
            await start_add_expense(message, state, db_user)
            return True
        elif text == "📸 Чек":
            from bot.handlers.receipts import prompt_receipt_photo
            await prompt_receipt_photo(message, db_user)
            return True
        elif text == "📋 Мои расходы":
            from bot.handlers.expenses import _show_expenses
            await _show_expenses(message, state, db_user)
            return True
        elif text == "⚙️ Настройки":
            await show_settings(message, db_user, state)
            return True
        elif text == "🏠 Главное меню":
            from bot.handlers.start import cmd_start
            await cmd_start(message, db_user)
            return True
        elif text in ["❌ Отмена", "Отмена"]:
            await message.answer("❌ Действие отменено.", reply_markup=main_reply_keyboard())
            return True
    return False

@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
@router.callback_query(F.data == 'settings')
async def show_settings(event: Message | CallbackQuery, db_user: User, state: FSMContext = None):
    if state:
        await state.clear()
    is_premium = db_user.subscription_type == 'premium'
    is_balance_enabled = getattr(db_user, 'is_balance_enabled', True)
    markup = settings_keyboard(is_premium=is_premium, is_balance_enabled=is_balance_enabled)
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text("⚙️ <b>Настройки:</b>", reply_markup=markup)
        await event.answer()
    else:
        await event.answer("⚙️ <b>Настройки:</b>", reply_markup=markup)

@router.callback_query(F.data == 'set_currency')
async def set_currency(callback: CallbackQuery, db_user: User):
    await callback.message.edit_text("Выберите валюту:", reply_markup=currency_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith('currency:'))
async def process_currency(callback: CallbackQuery, db_user: User):
    currency = callback.data.split(':')[1]
    async with async_session() as session:
        repo = UserRepository(session)
        db_user.currency = currency
        await repo.update(db_user)
        
    await callback.message.edit_text(f"Валюта изменена на {currency}.")
    await callback.answer()

@router.callback_query(F.data == 'set_categories')
async def set_categories(callback: CallbackQuery, db_user: User):
    if db_user.subscription_type != 'premium':
        await callback.answer("Только для Premium!", show_alert=True)
        return
    await callback.message.edit_text("Категории: (в разработке)")
    await callback.answer()

@router.callback_query(F.data == 'add_category')
async def add_category(callback: CallbackQuery, state: FSMContext, db_user: User):
    await callback.message.edit_text("Введите название категории:")
    await state.set_state(SettingsStates.waiting_for_category_name)
    await callback.answer()

@router.message(SettingsStates.waiting_for_category_name, F.text)
async def process_category_name(message: Message, state: FSMContext, db_user: User):
    if await handle_reply_button(message, state, db_user):
        return
    await state.update_data(category_name=message.text)
    await message.answer("Введите эмодзи для категории:")
    await state.set_state(SettingsStates.waiting_for_category_emoji)

@router.message(SettingsStates.waiting_for_category_emoji, F.text)
async def process_category_emoji(message: Message, state: FSMContext, db_user: User):
    if await handle_reply_button(message, state, db_user):
        return
    data = await state.get_data()
    name = data['category_name']
    emoji = message.text
    
    async with async_session() as session:
        cat_service = CategoryService(session)
        await cat_service.create_custom_category(user_id=db_user.id, name=name, emoji=emoji)
        
    await message.answer(f"✅ Категория {emoji} {name} создана!")
    await state.clear()

def _format_balance_menu_text(db_user: User) -> str:
    is_enabled = getattr(db_user, 'is_balance_enabled', True)
    status_icon = "🟢 <b>Включен</b>" if is_enabled else "🔴 <b>Отключен</b>"
    status_hint = "расходы автоматически списываются с баланса" if is_enabled else "расходы НЕ влияют на баланс"
    
    return (
        f"💵 <b>Управление балансом и финансами</b>\n\n"
        f"Статус учета: {status_icon} (<i>{status_hint}</i>)\n"
        f"Текущий баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
        f"💡 <b>Быстрые действия:</b>\n"
        f"• <b>➕ Пополнить</b> — прибавить сумму к балансу\n"
        f"• <b>➖ Уменьшить</b> — списать часть средств\n"
        f"• <b>✏️ Задать сумму</b> — установить точный баланс\n"
        f"• <b>🗑 Сбросить</b> — обнулить баланс до 0.00 (если случайно внесли)\n"
        f"• <b>Вкл/Выкл</b> — полностью включить или отключить учет баланса\n\n"
        f"<i>Или отправьте сумму сообщением (например: <code>+500</code>, <code>-200</code> или <code>1500</code>):</i>"
    )

@router.callback_query(F.data == 'set_budgets')
async def set_budgets(callback: CallbackQuery, state: FSMContext, db_user: User):
    await state.clear()
    await state.set_state(SettingsStates.waiting_for_budget_amount)
    is_enabled = getattr(db_user, 'is_balance_enabled', True)
    text = _format_balance_menu_text(db_user)
    await callback.message.edit_text(text, reply_markup=balance_keyboard(is_enabled=is_enabled))
    await callback.answer()

@router.callback_query(F.data == 'toggle_balance')
async def toggle_balance(callback: CallbackQuery, state: FSMContext, db_user: User):
    await state.clear()
    await state.set_state(SettingsStates.waiting_for_budget_amount)
    async with async_session() as session:
        repo = UserRepository(session)
        user_in_db = await repo.get_by_id(db_user.id)
        if user_in_db:
            new_status = not getattr(user_in_db, 'is_balance_enabled', True)
            user_in_db.is_balance_enabled = new_status
            await repo.update(user_in_db)
            db_user.is_balance_enabled = new_status
            
    is_enabled = getattr(db_user, 'is_balance_enabled', True)
    toast = "🟢 Учет баланса включен!" if is_enabled else "🔴 Учет баланса отключен!"
    await callback.answer(toast)
    
    text = _format_balance_menu_text(db_user)
    await callback.message.edit_text(text, reply_markup=balance_keyboard(is_enabled=is_enabled))

@router.callback_query(F.data == 'balance_reset')
async def balance_reset(callback: CallbackQuery, state: FSMContext, db_user: User):
    await state.clear()
    await state.set_state(SettingsStates.waiting_for_budget_amount)
    async with async_session() as session:
        repo = UserRepository(session)
        user_in_db = await repo.get_by_id(db_user.id)
        if user_in_db:
            user_in_db.balance = Decimal('0.00')
            await repo.update(user_in_db)
            db_user.balance = Decimal('0.00')
            
    is_enabled = getattr(db_user, 'is_balance_enabled', True)
    await callback.answer("🗑 Баланс сброшен до 0.00!")
    text = _format_balance_menu_text(db_user)
    await callback.message.edit_text(text, reply_markup=balance_keyboard(is_enabled=is_enabled))

@router.callback_query(F.data == 'balance_add')
async def balance_add_prompt(callback: CallbackQuery, state: FSMContext, db_user: User):
    text = (
        f"➕ <b>Пополнение баланса</b>\n\n"
        f"Текущий баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
        f"Отправьте сумму, которую хотите <b>прибавить</b> (например: <code>500</code> или <code>50.50</code>):"
    )
    await callback.message.edit_text(text, reply_markup=cancel_balance_keyboard())
    await state.set_state(SettingsStates.waiting_for_balance_add)
    await callback.answer()

@router.callback_query(F.data == 'balance_sub')
async def balance_sub_prompt(callback: CallbackQuery, state: FSMContext, db_user: User):
    text = (
        f"➖ <b>Уменьшение (списание) баланса</b>\n\n"
        f"Текущий баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
        f"Отправьте сумму, которую хотите <b>вычесть</b> (например: <code>200</code> или <code>25.00</code>):"
    )
    await callback.message.edit_text(text, reply_markup=cancel_balance_keyboard())
    await state.set_state(SettingsStates.waiting_for_balance_sub)
    await callback.answer()

@router.callback_query(F.data == 'balance_set')
async def balance_set_prompt(callback: CallbackQuery, state: FSMContext, db_user: User):
    text = (
        f"✏️ <b>Установка баланса</b>\n\n"
        f"Текущий баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
        f"Отправьте точную сумму нового баланса (например: <code>1500</code>):"
    )
    await callback.message.edit_text(text, reply_markup=cancel_balance_keyboard())
    await state.set_state(SettingsStates.waiting_for_budget_amount)
    await callback.answer()

@router.message(SettingsStates.waiting_for_balance_add, F.text)
async def process_balance_add(message: Message, state: FSMContext, db_user: User):
    if await handle_reply_button(message, state, db_user):
        return
        
    try:
        val_str = message.text.replace('+', '').replace(' ', '').replace(',', '.')
        amount = Decimal(val_str)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля. Попробуйте еще раз:", reply_markup=cancel_balance_keyboard())
            return
            
        async with async_session() as session:
            repo = UserRepository(session)
            user_in_db = await repo.get_by_id(db_user.id)
            if user_in_db:
                user_in_db.balance += amount
                await repo.update(user_in_db)
                db_user.balance = user_in_db.balance
                
        is_enabled = getattr(db_user, 'is_balance_enabled', True)
        await message.answer(
            f"✅ Баланс успешно пополнен на <b>+{format_amount(amount, db_user.currency)}</b>!\n"
            f"💳 Новый баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
            + _format_balance_menu_text(db_user),
            reply_markup=balance_keyboard(is_enabled=is_enabled)
        )
        await state.set_state(SettingsStates.waiting_for_budget_amount)
    except Exception:
        await message.answer("❌ Введите корректное число (например: 500 или 50.50):", reply_markup=cancel_balance_keyboard())

@router.message(SettingsStates.waiting_for_balance_sub, F.text)
async def process_balance_sub(message: Message, state: FSMContext, db_user: User):
    if await handle_reply_button(message, state, db_user):
        return
        
    try:
        val_str = message.text.replace('-', '').replace(' ', '').replace(',', '.')
        amount = Decimal(val_str)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля. Попробуйте еще раз:", reply_markup=cancel_balance_keyboard())
            return
            
        async with async_session() as session:
            repo = UserRepository(session)
            user_in_db = await repo.get_by_id(db_user.id)
            if user_in_db:
                user_in_db.balance -= amount
                await repo.update(user_in_db)
                db_user.balance = user_in_db.balance
                
        is_enabled = getattr(db_user, 'is_balance_enabled', True)
        await message.answer(
            f"✅ С баланса списано <b>-{format_amount(amount, db_user.currency)}</b>!\n"
            f"💳 Новый баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
            + _format_balance_menu_text(db_user),
            reply_markup=balance_keyboard(is_enabled=is_enabled)
        )
        await state.set_state(SettingsStates.waiting_for_budget_amount)
    except Exception:
        await message.answer("❌ Введите корректное число (например: 200 или 25.00):", reply_markup=cancel_balance_keyboard())

@router.message(SettingsStates.waiting_for_budget_amount, F.text)
async def process_budget_amount(message: Message, state: FSMContext, db_user: User):
    if await handle_reply_button(message, state, db_user):
        return
        
    raw_text = message.text.strip().replace(' ', '').replace(',', '.')
    try:
        async with async_session() as session:
            repo = UserRepository(session)
            user_in_db = await repo.get_by_id(db_user.id)
            if not user_in_db:
                user_in_db = db_user
                
            if raw_text.startswith('+'):
                add_val = Decimal(raw_text[1:])
                user_in_db.balance += add_val
                action_text = f"✅ Баланс пополнен на <b>+{format_amount(add_val, user_in_db.currency)}</b>!"
            elif raw_text.startswith('-'):
                sub_val = Decimal(raw_text[1:])
                user_in_db.balance -= sub_val
                action_text = f"✅ С баланса списано <b>-{format_amount(sub_val, user_in_db.currency)}</b>!"
            else:
                new_balance = Decimal(raw_text)
                user_in_db.balance = new_balance
                action_text = f"✅ Баланс успешно установлен: <b>{format_amount(new_balance, user_in_db.currency)}</b>!"
                
            await repo.update(user_in_db)
            db_user.balance = user_in_db.balance
            
        is_enabled = getattr(db_user, 'is_balance_enabled', True)
        await message.answer(
            f"{action_text}\n"
            f"💳 Текущий баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
            + _format_balance_menu_text(db_user),
            reply_markup=balance_keyboard(is_enabled=is_enabled)
        )
        await state.set_state(SettingsStates.waiting_for_budget_amount)
    except Exception:
        await message.answer("❌ Пожалуйста, введите корректное число (например: 1500, +500 или -200):", reply_markup=cancel_balance_keyboard())

@router.callback_query(F.data == 'set_appearance')
async def set_appearance(callback: CallbackQuery, db_user: User):
    if db_user.subscription_type != 'premium':
        await callback.answer("Только для Premium!", show_alert=True)
        return
        
    current_theme = db_user.design_theme or "standard"
    text = (
        "🎨 <b>Оформление и Дизайн</b>\n\n"
        "Здесь вы можете выбрать стиль, в котором бот будет выводить ваши расходы и отчеты.\n\n"
        "Текущая тема: <b>" + current_theme.capitalize() + "</b>"
    )
    await callback.message.edit_text(text, reply_markup=appearance_keyboard(current_theme))
    await callback.answer()

@router.callback_query(F.data.startswith('theme:'))
async def process_theme(callback: CallbackQuery, db_user: User):
    if db_user.subscription_type != 'premium':
        await callback.answer("Только для Premium!", show_alert=True)
        return
        
    new_theme = callback.data.split(':')[1]
    async with async_session() as session:
        repo = UserRepository(session)
        db_user.design_theme = new_theme
        await repo.update(db_user)
        
    await callback.answer("✅ Тема успешно обновлена!")
    text = (
        "🎨 <b>Оформление и Дизайн</b>\n\n"
        "Здесь вы можете выбрать стиль, в котором бот будет выводить ваши расходы и отчеты.\n\n"
        "Текущая тема: <b>" + new_theme.capitalize() + "</b>"
    )
    await callback.message.edit_text(text, reply_markup=appearance_keyboard(new_theme))
