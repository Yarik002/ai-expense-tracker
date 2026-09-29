from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

from bot.database.engine import async_session
from bot.database.models import User
from bot.config import settings
from bot.database.repositories import UserRepository, SubscriptionRepository
from bot.keyboards.inline import admin_keyboard

router = Router()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

@router.message(Command("admin"))
async def admin_panel(message: Message, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
    await message.answer("🛠 <b>Панель администратора</b>", reply_markup=admin_keyboard())

@router.callback_query(F.data == 'admin_stats')
async def admin_stats(callback: CallbackQuery, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
    async with async_session() as session:
        repo = UserRepository(session)
        total_users = await repo.get_user_count()
        premium_users = await repo.get_premium_count()
        active_users = len(await repo.get_active_users(days=30))
        
        text = (
            "📊 <b>Статистика бота:</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"⭐ Premium пользователей: {premium_users}\n"
            f"🔥 Активных за 30 дней: {active_users}\n"
        )
        await callback.message.edit_text(text, reply_markup=admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == 'admin_users')
async def admin_users(callback: CallbackQuery, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
    async with async_session() as session:
        repo = UserRepository(session)
        users = await repo.get_all_users(limit=50) # Увеличим лимит до 50
        total_count = await repo.get_user_count()
        
        text = f"👥 <b>Пользователи (показано {len(users)} из {total_count}):</b>\n\n"
        for u in users:
            plan = "⭐ Prem" if u.subscription_type == "premium" else "🆓 Free"
            name = u.first_name or ""
            if u.username:
                name += f" (@{u.username})"
            text += f"• <code>{u.telegram_id}</code> | {name} — {plan}\n"
            
        try:
            await callback.message.edit_text(text, reply_markup=admin_keyboard())
        except Exception as e:
            # Если текст слишком длинный, обрезаем
            if len(text) > 4000:
                text = text[:4000] + "...\n[Список обрезан]"
                await callback.message.edit_text(text, reply_markup=admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == 'admin_revenue')
async def admin_revenue(callback: CallbackQuery, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
    async with async_session() as session:
        sub_repo = SubscriptionRepository(session)
        total_stars = await sub_repo.get_total_revenue()
        active_subs = await sub_repo.get_subscription_count()
        
        text = (
            "💰 <b>Финансы (Telegram Stars):</b>\n\n"
            f"⭐️ Заработано всего: {total_stars} Stars\n"
            f"📌 Активных подписок: {active_subs}\n"
        )
        await callback.message.edit_text(text, reply_markup=admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == 'admin_broadcast')
async def admin_broadcast(callback: CallbackQuery, state: FSMContext, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\nОтправьте сообщение, которое получат все пользователи бота. Можно использовать форматирование, фото, видео.",
        reply_markup=admin_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.answer()

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
    
    async with async_session() as session:
        repo = UserRepository(session)
        users = await repo.get_all_users(limit=100000) # Get all users
        
    sent, failed = 0, 0
    await message.answer("⏳ Рассылка началась...")
    
    for u in users:
        try:
            await message.copy_to(chat_id=u.telegram_id)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            
    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Успешно доставлено: {sent}\n"
        f"Ошибок (заблокировали бота): {failed}"
    )
    await state.clear()

from datetime import datetime, timedelta

@router.message(Command("give_premium"))
async def give_premium(message: Message, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
        
    args = message.text.split()
    target_id = db_user.telegram_id
    days = 30
    
    if len(args) > 1:
        if args[1].isdigit():
            target_id = int(args[1])
    if len(args) > 2:
        if args[2].isdigit():
            days = int(args[2])
            
    async with async_session() as session:
        repo = UserRepository(session)
        target_user = await repo.get_by_telegram_id(target_id)
        
        if not target_user:
            await message.answer(f"❌ Пользователь с Telegram ID {target_id} не найден в базе.")
            return
            
        target_user.subscription_type = "premium"
        
        current_expiry = target_user.subscription_expires_at
        if current_expiry and current_expiry > datetime.now():
            target_user.subscription_expires_at = current_expiry + timedelta(days=days)
        else:
            target_user.subscription_expires_at = datetime.now() + timedelta(days=days)
            
        await repo.update(target_user)
        
    await message.answer(f"✅ Успех! Пользователю {target_user.first_name} (ID: {target_id}) выдан Premium на {days} дней.")


@router.message(Command("remove_premium"))
async def remove_premium(message: Message, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS and not db_user.is_admin:
        return
        
    args = message.text.split()
    target_id = db_user.telegram_id
    
    if len(args) > 1:
        if args[1].isdigit():
            target_id = int(args[1])
            
    async with async_session() as session:
        repo = UserRepository(session)
        target_user = await repo.get_by_telegram_id(target_id)
        
        if not target_user:
            await message.answer(f"❌ Пользователь с Telegram ID {target_id} не найден в базе.")
            return
            
        target_user.subscription_type = "free"
        target_user.subscription_expires_at = None
        
        await repo.update(target_user)
        
    await message.answer(f"✅ Успех! У пользователя {target_user.first_name} (ID: {target_id}) отключена Premium подписка.")


@router.message(Command("give_admin"))
async def give_admin(message: Message, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS:
        return
        
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("ℹ️ Использование: /give_admin <Telegram ID>")
        return
        
    target_id = int(args[1])
    async with async_session() as session:
        repo = UserRepository(session)
        target_user = await repo.get_by_telegram_id(target_id)
        if not target_user:
            await message.answer(f"❌ Пользователь {target_id} не найден.")
            return
            
        target_user.is_admin = True
        await repo.update(target_user)
        await message.answer(f"✅ Пользователь {target_user.first_name} назначен администратором.")


@router.message(Command("remove_admin"))
async def remove_admin(message: Message, db_user: User):
    if db_user.telegram_id not in settings.ADMIN_IDS:
        return
        
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("ℹ️ Использование: /remove_admin <Telegram ID>")
        return
        
    target_id = int(args[1])
    async with async_session() as session:
        repo = UserRepository(session)
        target_user = await repo.get_by_telegram_id(target_id)
        if not target_user:
            await message.answer(f"❌ Пользователь {target_id} не найден.")
            return
            
        target_user.is_admin = False
        await repo.update(target_user)
        await message.answer(f"✅ Пользователь {target_user.first_name} лишен прав администратора.")

