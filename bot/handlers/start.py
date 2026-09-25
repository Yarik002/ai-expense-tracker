from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from bot.database.models import User
from bot.keyboards.reply import main_reply_keyboard
from bot.keyboards.inline import main_menu_keyboard

router = Router()

@router.message(CommandStart())
@router.message(F.text == "🏠 Главное меню")
async def cmd_start(message: Message, db_user: User):
    welcome_text = (
        "🧠 <b>AI Expense Tracker</b>\n\n"
        "Я помогу тебе вести учёт финансов без боли!\n\n"
        "📝 Просто напиши расход: <i>Кофе 300</i>\n"
        "📸 Сфотографируй чек — я сам всё распознаю\n"
        "📊 Получай аналитику по своим тратам\n\n"
        "Нажми кнопку ниже или используй команды:\n"
        "/menu — главное меню\n"
        "/help — список команд\n"
        "/stats — статистика за месяц\n"
        "/premium — премиум подписка"
    )
    await message.answer(welcome_text, reply_markup=main_reply_keyboard())
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User):
    help_text = (
        "<b>Доступные команды:</b>\n"
        "/start - Перезапустить бота\n"
        "/menu - Открыть главное меню\n"
        "/help - Список команд\n"
        "/expenses - Ваши расходы\n"
        "/stats - Статистика\n"
        "/settings - Настройки\n"
        "/premium - Премиум подписка (дополнительные лимиты и сканирование чеков)\n"
    )
    await message.answer(help_text)

@router.message(Command("menu"))
async def cmd_menu(message: Message, db_user: User):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())

from aiogram.fsm.context import FSMContext

@router.callback_query(F.data == 'back_menu')
async def back_to_menu(callback: CallbackQuery, state: FSMContext, db_user: User):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()

from aiogram.utils.keyboard import InlineKeyboardBuilder

@router.message(F.text == "ℹ️ О боте")
async def cmd_about_message(message: Message, db_user: User):
    await send_about_info(message, db_user)

@router.callback_query(F.data == 'about_bot')
async def cmd_about_callback(callback: CallbackQuery, db_user: User):
    await send_about_info(callback.message, db_user, is_callback=True)
    await callback.answer()

async def send_about_info(message: Message, db_user: User, is_callback: bool = False):
    about_text = (
        "🚀 <b>AI Expense Tracker — Умный учет твоих финансов</b>\n\n"
        "Хватит тратить время на ручной ввод и скучные таблицы! "
        "Нейросеть сделает всю рутину за тебя. Просто отправь текст, голос или сфоткай чек.\n\n"
        
        "🟢 <b>БАЗОВЫЙ ДОСТУП (Бесплатно)</b>\n"
        "└ 📝 <b>50 ручных записей</b> в неделю <i>(«Кофе 300», «Такси 500»)</i>\n"
        "└ 📸 <b>3 сканирования чеков</b> в месяц <i>(ИИ сам найдет все товары)</i>\n"
        "└ 🤖 <b>Авто-распределение</b> по категориям\n"
        "└ 📊 <b>Базовая статистика</b> расходов\n\n"
        
        "👑 <b>PREMIUM ДОСТУП (Полный контроль)</b>\n"
        "└ 📸 <b>Безлимитные чеки:</b> Фоткай любые чеки без ограничений!\n"
        "└ 📝 <b>Безлимитный ввод:</b> Записывай каждую мелочь.\n"
        "└ 📈 <b>Smart Charts:</b> Профессиональная визуализация трат.\n"
        "└ 📄 <b>Excel Отчеты:</b> Выгрузка красивых .xlsx таблиц в 1 клик.\n"
        "└ 🎯 <b>Кастомные категории:</b> Настрой учет полностью под себя.\n\n"
        
        "💡 <i>Контроль над деньгами — это свобода. Управляй своим бюджетом профессионально!</i> 👇"
    )
    
    builder = InlineKeyboardBuilder()
    if db_user.subscription_type != 'premium':
        builder.button(text="🔥 Получить PREMIUM", callback_data="premium")
    builder.button(text="◀️ Назад", callback_data="back_menu")
    builder.adjust(1)
    
    if is_callback:
        await message.edit_text(about_text, reply_markup=builder.as_markup())
    else:
        await message.answer(about_text, reply_markup=builder.as_markup())
