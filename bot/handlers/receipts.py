from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from bot.database.engine import async_session
from bot.database.models import User
from bot.services.subscription_service import SubscriptionService
from bot.services.gemini_service import GeminiService
from bot.services.expense_service import ExpenseService
from bot.utils.formatters import format_amount

router = Router()

gemini = GeminiService()

@router.message(F.text == "📸 Чек")
async def prompt_receipt_photo(message: Message, db_user: User):
    async with async_session() as session:
        sub_service = SubscriptionService(session)
        rem = await sub_service.get_remaining_receipts(db_user)
        
    text = (
        "📸 <b>Отправьте фото чека</b>\n\n"
        "Постарайтесь сделать фото чётким, при хорошем освещении и без бликов. "
        "ИИ автоматически распознает все позиции, цены и раскидает их по категориям!\n\n"
    )
    if db_user.subscription_type == 'premium':
        text += "💎 <b>Premium:</b> У вас безлимитное сканирование чеков."
    else:
        text += f"🆓 <b>Осталось бесплатных сканирований в этом месяце:</b> {rem} из {settings.FREE_RECEIPT_LIMIT}"
        
    await message.answer(text)

from aiogram.fsm.context import FSMContext
from bot.config import settings

@router.message(F.photo)
async def process_receipt_photo(message: Message, bot: Bot, db_user: User, state: FSMContext):
    """Обработка фото чека — парсинг через Gemini Vision."""
    await state.clear()
    async with async_session() as session:
        sub_service = SubscriptionService(session)
        
        # Проверяем лимит сканирований
        can_scan = await sub_service.can_scan_receipt(db_user)
        if not can_scan:
            await message.answer(
                "⚠️ Вы исчерпали лимит сканирования чеков "
                "в бесплатной версии (3/мес).\n\n"
                "⭐ Приобретите Premium для безлимитного доступа!\n"
                "/premium — подробнее о подписке"
            )
            return
        
        # Отправляем сообщение о процессе
        processing_msg = await message.answer("🔄 Обрабатываю чек... Это может занять около 5-10 секунд.")
        
        try:
            # Скачиваем фото
            file = await bot.get_file(message.photo[-1].file_id)
            file_data = await bot.download_file(file.file_path)
            image_bytes = file_data.read()
            
            # Парсим чек через Gemini Vision
            expense_service = ExpenseService(session)
            expenses = await expense_service.add_expense_from_receipt(
                user_id=db_user.id,
                image_bytes=image_bytes,
                file_id=message.photo[-1].file_id,
                gemini=gemini,
            )
            
            if not expenses:
                await processing_msg.edit_text("❌ Не удалось распознать товары в чеке. Попробуйте сфотографировать чётче.")
                return
            
            # Увеличиваем счётчик сканирований
            await sub_service.increment_receipt_count(db_user)
            rem = await sub_service.get_remaining_receipts(db_user)
            
            # Формируем ответ
            text = "✅ <b>Чек распознан!</b>\n\n"
            total = sum(exp.amount for exp in expenses)
            
            for exp in expenses:
                text += f"• {exp.description} — {format_amount(exp.amount, exp.currency)}\n"
            
            text += f"\n<b>Итого:</b> {format_amount(total, expenses[0].currency)}"
            text += f"\n📦 Добавлено позиций: {len(expenses)}\n\n"
            
            if db_user.subscription_type == 'premium':
                text += "💎 <i>Безлимитные сканирования (Premium)</i>"
            else:
                text += f"🆓 <i>Осталось бесплатных чеков: {rem}</i>"
            
            await processing_msg.edit_text(text)
            
        except ValueError as e:
            await processing_msg.edit_text(f"❌ Ошибка при распознавании чека: {str(e)}")
        except Exception as e:
            import logging
            logging.error(f"Error processing receipt: {e}", exc_info=True)
            await processing_msg.edit_text("❌ Произошла ошибка при обработке чека. Попробуйте ещё раз.")


@router.callback_query(F.data == "confirm_receipt")
async def confirm_receipt(callback: CallbackQuery, db_user: User):
    await callback.message.edit_text("✅ Чек подтверждён и сохранён.")
    await callback.answer()
