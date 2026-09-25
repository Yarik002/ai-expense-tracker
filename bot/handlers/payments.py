from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.filters import Command
from bot.database.engine import async_session
from bot.database.models import User
from bot.config import settings
from bot.services.subscription_service import SubscriptionService
from bot.keyboards.inline import premium_keyboard

router = Router()

@router.callback_query(F.data == 'premium')
async def show_premium(callback: CallbackQuery, db_user: User):
    text = (
        "<b>Premium подписка</b>\n\n"
        "• Безлимитное сканирование чеков\n"
        "• Кастомные категории\n"
        "• Бюджетирование\n"
    )
    await callback.message.edit_text(text, reply_markup=premium_keyboard())
    await callback.answer()

@router.callback_query(F.data == 'buy_monthly')
async def buy_monthly(callback: CallbackQuery, bot: Bot, db_user: User):
    prices = [LabeledPrice(label='Premium Monthly', amount=settings.MONTHLY_STARS_PRICE)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title='Premium подписка (месяц)',
        description='Безлимитные чеки, кастомные категории и бюджеты на 1 месяц',
        payload='premium_monthly',
        provider_token='',
        currency='XTR',
        prices=prices
    )
    await callback.answer()

@router.callback_query(F.data == 'buy_yearly')
async def buy_yearly(callback: CallbackQuery, bot: Bot, db_user: User):
    prices = [LabeledPrice(label='Premium Yearly', amount=settings.YEARLY_STARS_PRICE)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title='Premium подписка (год)',
        description='Безлимитные чеки, кастомные категории и бюджеты на 1 год',
        payload='premium_yearly',
        provider_token='',
        currency='XTR',
        prices=prices
    )
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, db_user: User):
    payment = message.successful_payment
    payload = payment.invoice_payload
    plan = "monthly" if payload == "premium_monthly" else "yearly"
    charge_id = payment.telegram_payment_charge_id
    amount_stars = payment.total_amount
    
    async with async_session() as session:
        sub_service = SubscriptionService(session)
        sub = await sub_service.activate_subscription(
            user_id=db_user.id,
            plan=plan,
            charge_id=charge_id,
            amount_stars=amount_stars,
        )
        days = (sub.expires_at - sub.starts_at).days
        
    await message.answer(
        f"🎉 <b>Спасибо за оплату!</b>\n\n"
        f"Premium подписка активирована на <b>{days} дней</b>.\n"
        f"Теперь вам доступны все функции бота!"
    )

@router.message(Command("status"))
async def status_command(message: Message, db_user: User):
    if db_user.subscription_type == 'premium':
        await message.answer(f"Ваш план: Premium\nИстекает: {db_user.subscription_expires_at}")
    else:
        await message.answer("Ваш план: Free plan\n/premium для улучшения.")
