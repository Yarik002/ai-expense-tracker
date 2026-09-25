import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.config import settings
from bot.database.engine import engine, async_session
from bot.database.models import Base
from bot.handlers import (
    start_router,
    expenses_router,
    receipts_router,
    analytics_router,
    admin_router,
    payments_router,
    settings_router,
)
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.services.category_service import seed_default_categories


async def on_startup(bot: Bot):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await seed_default_categories(async_session)
    logging.info("Bot started successfully")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    
    dp.startup.register(on_startup)
    
    auth_middleware = AuthMiddleware(async_session)
    throttling_middleware = ThrottlingMiddleware()
    
    dp.message.middleware(throttling_middleware)
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(throttling_middleware)
    dp.callback_query.middleware(auth_middleware)
    
    dp.include_routers(
        start_router,
        expenses_router,
        receipts_router,
        analytics_router,
        admin_router,
        payments_router,
        settings_router,
    )
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
