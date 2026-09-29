from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database.engine import async_session
from bot.database.models import User
from bot.database.repositories import UserRepository
from bot.services.category_service import CategoryService
from bot.keyboards.inline import settings_keyboard, currency_keyboard

router = Router()

class SettingsStates(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_emoji = State()
    waiting_for_budget_amount = State()

@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
@router.callback_query(F.data == 'settings')
async def show_settings(event: Message | CallbackQuery, db_user: User):
    is_premium = db_user.subscription_type == 'premium'
    markup = settings_keyboard(is_premium=is_premium)
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text("Настройки:", reply_markup=markup)
        await event.answer()
    else:
        await event.answer("Настройки:", reply_markup=markup)

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
    await state.update_data(category_name=message.text)
    await message.answer("Введите эмодзи для категории:")
    await state.set_state(SettingsStates.waiting_for_category_emoji)

@router.message(SettingsStates.waiting_for_category_emoji, F.text)
async def process_category_emoji(message: Message, state: FSMContext, db_user: User):
    data = await state.get_data()
    name = data['category_name']
    emoji = message.text
    
    async with async_session() as session:
        cat_service = CategoryService(session)
        await cat_service.create_custom_category(user_id=db_user.id, name=name, emoji=emoji)
        
    await message.answer(f"✅ Категория {emoji} {name} создана!")
    await state.clear()

from bot.utils.formatters import format_amount
from decimal import Decimal
from bot.keyboards.inline import back_keyboard

@router.callback_query(F.data == 'set_budgets')
async def set_budgets(callback: CallbackQuery, state: FSMContext, db_user: User):
    text = (
        f"💵 <b>Ваши финансы (Баланс)</b>\n\n"
        f"Текущий баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n"
        "Отправьте мне новую сумму (просто число), чтобы обновить ваш баланс. "
        "Эта сумма будет автоматически уменьшаться при каждом расходе!"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard("settings"))
    await state.set_state(SettingsStates.waiting_for_budget_amount)
    await callback.answer()

@router.message(SettingsStates.waiting_for_budget_amount, F.text)
async def process_budget_amount(message: Message, state: FSMContext, db_user: User):
    try:
        new_balance = Decimal(message.text.replace(',', '.').replace(' ', ''))
        async with async_session() as session:
            repo = UserRepository(session)
            db_user.balance = new_balance
            await repo.update(db_user)
        await message.answer(f"✅ Ваш баланс успешно обновлен: <b>{format_amount(new_balance, db_user.currency)}</b>")
        await state.clear()
    except Exception:
        await message.answer("❌ Пожалуйста, введите корректное число (например: 1500.50).")

from bot.keyboards.inline import appearance_keyboard

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
    # Перерисовываем меню
    text = (
        "🎨 <b>Оформление и Дизайн</b>\n\n"
        "Здесь вы можете выбрать стиль, в котором бот будет выводить ваши расходы и отчеты.\n\n"
        "Текущая тема: <b>" + new_theme.capitalize() + "</b>"
    )
    await callback.message.edit_text(text, reply_markup=appearance_keyboard(new_theme))
