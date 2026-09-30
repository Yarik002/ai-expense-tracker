import re
from decimal import Decimal
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database.engine import async_session
from bot.database.models import User
from bot.database.repositories import ExpenseRepository, CategoryRepository
from bot.services.expense_service import ExpenseService
from bot.services.gemini_service import GeminiService
from bot.keyboards.inline import categories_keyboard, back_keyboard
from bot.utils.formatters import format_amount, format_date
from bot.handlers.settings import SettingsStates

router = Router()

gemini = GeminiService()


class ExpenseStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_category = State()
    waiting_for_delete_range = State()


@router.callback_query(F.data == "add_expense")
@router.message(F.text == "➕ Расход")
async def start_add_expense(event: Message | CallbackQuery, state: FSMContext, db_user: User):
    message = event if isinstance(event, Message) else event.message
    text = (
        "✏️ Введите расход в свободной форме:\n\n"
        "Примеры:\n"
        "• <i>Кофе 300</i>\n"
        "• <i>Такси 500 руб</i>\n"
        "• <i>Lunch 15 dollars</i>"
    )
    await state.set_state(ExpenseStates.waiting_for_text)
    
    markup = back_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
        await event.answer()
    else:
        await message.answer(text, reply_markup=markup)


@router.message(ExpenseStates.waiting_for_text, F.text)
async def process_text_expense(message: Message, state: FSMContext, db_user: User):
    text = message.text
    if not text:
        await message.answer("Пожалуйста, отправьте текст с описанием расхода.")
        return
        
    REPLY_BUTTONS = ["➕ Расход", "📸 Чек", "📋 Мои расходы", "⚙️ Настройки", "🏠 Главное меню", "❌ Отмена"]
    if text in REPLY_BUTTONS:
        await state.clear()
        if text == "📸 Чек":
            from bot.handlers.receipts import prompt_receipt_photo
            await prompt_receipt_photo(message, db_user)
            return
        elif text == "📋 Мои расходы":
            await _show_expenses(message, state, db_user)
            return
        elif text == "⚙️ Настройки":
            from bot.handlers.settings import show_settings
            await show_settings(message, db_user)
            return
        elif text == "🏠 Главное меню":
            from bot.handlers.start import cmd_start
            await cmd_start(message, db_user)
            return
        else:
            await message.answer("Действие отменено.")
            return

    # Check weekly limits
    async with async_session() as session:
        from bot.services.subscription_service import SubscriptionService
        sub_service = SubscriptionService(session)
        can_add = await sub_service.can_add_manual_expense(db_user)
        if not can_add:
            await message.answer(
                "⚠️ <b>Превышен лимит ручных записей!</b>\n\n"
                "В бесплатной версии доступно 50 записей в неделю.\n"
                "⭐ Перейдите на Premium для <b>безлимитного</b> добавления расходов и чеков!\n"
                "👉 /premium"
            )
            await state.clear()
            return
            
        rem_manual = await sub_service.get_remaining_manual_expenses(db_user)

    # Пробуем распарсить через Gemini
    parsed = await gemini.parse_text_expense(text)
    
    # Если Gemini не справился — фоллбэк на regex
    if not parsed or "error" in parsed:
        # Пытаемся найти число в тексте
        match = re.search(r"(\d+[\.,]?\d*)", text)
        if match:
            amount_str = match.group(1).replace(",", ".")
            description = text.replace(match.group(0), "").strip() or "Расход"
            parsed = {
                "amount": float(amount_str),
                "description": description,
                "currency": db_user.currency,
            }
        else:
            await message.answer("❌ Не удалось распознать сумму. Попробуйте ещё раз.")
            return

    await state.update_data(parsed=parsed)
    
    # Показываем категории
    async with async_session() as session:
        cat_repo = CategoryRepository(session)
        categories = await cat_repo.get_user_categories(db_user.id)
    
    amount_val = parsed.get("amount", 0)
    desc = parsed.get("description", "") or "Расход"
    currency = parsed.get("currency", db_user.currency)
    
    # Очистка суммы от запятых и пробелов для безопасной конвертации
    amount_str = str(amount_val).replace(",", ".").replace(" ", "")
    try:
        amount_dec = Decimal(amount_str)
    except:
        amount_dec = Decimal("0")
    
    parsed["amount"] = str(amount_dec)
    
    # Авто-определение категории через OpenRouter
    status_msg = await message.answer("🤖 <i>ИИ распознает категорию...</i>")
    
    from bot.services.openrouter_service import OpenRouterService
    openrouter = OpenRouterService()
    best_cat = await openrouter.categorize_expense(desc, categories)
    
    if best_cat:
        # Успешно определили
        async with async_session() as session:
            expense_service = ExpenseService(session)
            expense = await expense_service.add_manual_expense(
                user_id=db_user.id,
                amount=amount_dec,
                description=desc,
                category_id=best_cat.id,
                currency=currency,
            )
            
            sub_service = SubscriptionService(session)
            rem = await sub_service.get_remaining_manual_expenses(db_user)
        
        msg_text = (
            f"✅ <b>Расход сохранён!</b>\n\n"
            f"📝 {expense.description}\n"
            f"💰 {format_amount(expense.amount, expense.currency)}\n"
            f"📂 Авто-категория: {best_cat.emoji} {best_cat.name}\n\n"
        )
        if db_user.subscription_type != 'premium':
            msg_text += f"<i>Осталось записей на этой неделе: {rem} из 50</i>"
            
        await status_msg.edit_text(msg_text)
        await state.clear()
        
    else:
        # Fallback если не удалось
        await status_msg.delete()
        await state.update_data(parsed=parsed)
        
        await message.answer(
            f"💰 <b>Сумма:</b> {format_amount(amount_dec, currency)}\n"
            f"📝 <b>Описание:</b> {desc}\n\n"
            f"Выберите категорию:",
            reply_markup=categories_keyboard(categories),
        )
        await state.set_state(ExpenseStates.waiting_for_category)


@router.callback_query(F.data.startswith("cat:"), ExpenseStates.waiting_for_category)
async def process_category(callback: CallbackQuery, state: FSMContext, db_user: User):
    category_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    parsed = data["parsed"]
    
    async with async_session() as session:
        expense_service = ExpenseService(session)
        expense = await expense_service.add_manual_expense(
            user_id=db_user.id,
            amount=Decimal(str(parsed["amount"])),
            description=parsed["description"],
            category_id=category_id,
            currency=parsed.get("currency", db_user.currency),
        )
        
        from bot.services.subscription_service import SubscriptionService
        sub_service = SubscriptionService(session)
        rem = await sub_service.get_remaining_manual_expenses(db_user)
    
    msg_text = (
        f"✅ <b>Расход сохранён!</b>\n\n"
        f"📝 {expense.description}\n"
        f"💰 {format_amount(expense.amount, expense.currency)}\n\n"
    )
    if db_user.subscription_type != 'premium':
        msg_text += f"<i>Осталось записей на этой неделе: {rem} из 50</i>"
        
    await callback.message.edit_text(msg_text)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel", StateFilter("*"))
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()


@router.message(Command("expenses"))
async def show_expenses_command(message: Message, state: FSMContext, db_user: User):
    await _show_expenses(message, state, db_user)



@router.callback_query(F.data.startswith("exp_page:"))
async def process_expenses_page(callback: CallbackQuery, state: FSMContext, db_user: User):
    page = int(callback.data.split(":")[1])
    await _show_expenses(callback, state, db_user, page=page)

@router.callback_query(F.data == "my_expenses")
async def show_expenses_callback(callback: CallbackQuery, state: FSMContext, db_user: User):
    await _show_expenses(callback, state, db_user)

@router.message(F.text == "📋 Мои расходы")
async def show_expenses_reply_button(message: Message, state: FSMContext, db_user: User):
    await _show_expenses(message, state, db_user)



async def _show_expenses(event: Message | CallbackQuery, state: FSMContext, db_user: User, page: int = 1):
    """Показывает последние 20 расходов."""
    import math
    async with async_session() as session:
        repo = ExpenseRepository(session)
        
        limit = 15
        offset = (page - 1) * limit
        total_count = await repo.get_expense_count(db_user.id)
        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
        if page > total_pages:
            page = total_pages
            offset = (page - 1) * limit
            
        expenses = await repo.get_user_expenses(db_user.id, limit=limit, offset=offset)
        
        if not expenses:
            text = "📭 У вас пока нет расходов.\n\nОтправьте текст или фото чека, чтобы добавить первый!"
            reply_markup = back_keyboard()
        else:
            theme = db_user.design_theme or "standard"
            expense_ids = []
            
            start_idx = offset + 1
            if theme == "standard":
                text = f"<b>📋 ИСТОРИЯ РАСХОДОВ (Стр. {page}/{total_pages})</b>\n\n"
                for i, exp in enumerate(expenses, start_idx):
                    date_str = exp.created_at.strftime("%d.%m %H:%M") if exp.created_at else ""
                    cat_emoji = exp.category.emoji if exp.category else "🌀"
                    amount_str = format_amount(exp.amount, exp.currency)
                    text += f"<b>{i}.</b> {cat_emoji} <b>{amount_str}</b>  |  {exp.description} <code>{date_str}</code>\n"
                    expense_ids.append(exp.id)
            
            elif theme == "business":
                text = f"📊 <b>ФИНАНСОВАЯ ВЫПИСКА (Стр. {page}/{total_pages})</b>\n\n"
                for i, exp in enumerate(expenses, start_idx):
                    date_str = exp.created_at.strftime("%Y-%m-%d %H:%M") if exp.created_at else ""
                    amount_str = format_amount(exp.amount, exp.currency)
                    text += f"<b>{i}.</b> ID:{exp.id} | <b>{amount_str}</b> | {exp.description} | {date_str}\n"
                    expense_ids.append(exp.id)
            
            elif theme == "minimal":
                text = f"<b>Траты (Стр. {page}/{total_pages}):</b>\n\n"
                for i, exp in enumerate(expenses, start_idx):
                    amount_str = format_amount(exp.amount, exp.currency)
                    text += f"<b>{i}.</b> ▫️ {exp.description} — <b>{amount_str}</b>\n"
                    expense_ids.append(exp.id)
                    
            text += "\n<i>Для удаления введите номер (например: 1 или 1-3)</i>"
            
            await state.update_data(last_shown_expenses=expense_ids, last_shown_offset=offset)
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            
            # Pagination row
            if total_pages > 1:
                prev_cb = f"exp_page:{page - 1}" if page > 1 else "ignore"
                next_cb = f"exp_page:{page + 1}" if page < total_pages else "ignore"
                prev_text = "⬅️" if page > 1 else " "
                next_text = "➡️" if page < total_pages else " "
                
                builder.button(text=prev_text, callback_data=prev_cb)
                builder.button(text=f"{page}/{total_pages}", callback_data="ignore")
                builder.button(text=next_text, callback_data=next_cb)
            
            builder.button(text="🗑 Удалить", callback_data="start_delete_expenses")
            builder.button(text="◀️ Назад", callback_data="back_menu")
            
            if total_pages > 1:
                builder.adjust(3, 2)
            else:
                builder.adjust(2)
                
            reply_markup = builder.as_markup()
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=reply_markup)
        await event.answer()
    else:
        await event.answer(text, reply_markup=reply_markup)


@router.callback_query(F.data == "start_delete_expenses")
async def start_delete_expenses(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🗑 <b>Удаление расходов</b>\n\n"
        "Отправьте мне порядковый номер расхода из списка выше, чтобы удалить его.\n"
        "Если хотите удалить сразу несколько, введите диапазон через дефис (например: <code>1-5</code>).",
        reply_markup=back_keyboard("my_expenses")
    )
    await state.set_state(ExpenseStates.waiting_for_delete_range)
    await callback.answer()


@router.message(ExpenseStates.waiting_for_delete_range, F.text)
async def process_delete_range(message: Message, state: FSMContext, db_user: User):
    text = message.text.strip()
    
    REPLY_BUTTONS = ["➕ Расход", "📸 Чек", "📋 Мои расходы", "⚙️ Настройки", "🏠 Главное меню", "❌ Отмена"]
    if text in REPLY_BUTTONS:
        await state.clear()
        if text == "📸 Чек":
            from bot.handlers.receipts import prompt_receipt_photo
            await prompt_receipt_photo(message, db_user)
            return
        elif text == "📋 Мои расходы":
            await _show_expenses(message, state, db_user)
            return
        elif text == "⚙️ Настройки":
            from bot.handlers.settings import show_settings
            await show_settings(message, db_user)
            return
        elif text == "🏠 Главное меню":
            from bot.handlers.start import cmd_start
            await cmd_start(message, db_user)
            return
        else:
            await message.answer("Действие отменено.")
            return

    data = await state.get_data()
    expense_ids = data.get("last_shown_expenses", [])
    offset = data.get("last_shown_offset", 0)
    
    if not expense_ids:
        await message.answer("Список устарел. Пожалуйста, откройте /expenses заново.")
        await state.clear()
        return

    to_delete_indices = set()
    
    if re.match(r"^\d+$", text):
        to_delete_indices.add(int(text))
    elif re.match(r"^\d+\-\d+$", text):
        start, end = map(int, text.split("-"))
        if start <= end:
            to_delete_indices.update(range(start, end + 1))
        else:
            to_delete_indices.update(range(end, start + 1))
    else:
        await message.answer("❌ Неверный формат. Введите число (например: 1) или диапазон (например: 1-3).")
        return
        
    ids_to_delete = []
    for idx in to_delete_indices:
        relative_idx = idx - offset
        if 1 <= relative_idx <= len(expense_ids):
            ids_to_delete.append(expense_ids[relative_idx - 1])
            
    if not ids_to_delete:
        await message.answer("❌ Номера выходят за рамки списка. Проверьте список расходов и попробуйте снова.")
        return
        
    async with async_session() as session:
        repo = ExpenseRepository(session)
        deleted_count = 0
        for exp_id in ids_to_delete:
            if await repo.delete(exp_id, db_user.id):
                deleted_count += 1
                
    await message.answer(f"✅ Успешно удалено записей: {deleted_count}")
    await state.clear()
    
    # Show updated list
    await _show_expenses(message, state, db_user)


# Обработчик свободного текста с числом — авто-ввод расхода
# Регистрируется ПОСЛЕДНИМ чтобы не перехватывать другие handlers
@router.message(
    F.text.regexp(r"\d"),
    ~StateFilter(ExpenseStates),
    ~StateFilter(SettingsStates),
)
async def handle_plain_text_expense(message: Message, state: FSMContext, db_user: User):
    """Если пользователь просто пишет текст с числом — считаем это расходом."""
    await state.set_state(ExpenseStates.waiting_for_text)
    await process_text_expense(message, state, db_user)
