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
from aiohttp import web
import os

async def health_check(request):
    return web.Response(text="Bot is alive!")

async def start_dummy_server():
    """Starts a dummy aiohttp server to satisfy cloud providers (Render, Koyeb, Hugging Face) that require binding to a PORT."""
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 7860))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Dummy web server started on port {port}")


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
    
    from bot.middlewares.security import SecurityMiddleware
    security_middleware = SecurityMiddleware()
    
    # Порядок: 1) Throttling (антиспам) -> 2) Security (защита от инъекций) -> 3) Auth (авторизация)
    dp.message.middleware(throttling_middleware)
    dp.message.middleware(security_middleware)
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(throttling_middleware)
    dp.callback_query.middleware(auth_middleware)
    
    dp.include_routers(
        start_router,
        settings_router,
        expenses_router,
        receipts_router,
        analytics_router,
        admin_router,
        payments_router,
    )
    
    # Start dummy server for health checks (if not using Gradio)
    if not os.environ.get("RUNNING_IN_GRADIO"):
        await start_dummy_server()
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
