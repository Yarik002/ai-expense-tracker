"""Handlers package."""
from bot.handlers.start import router as start_router
from bot.handlers.expenses import router as expenses_router
from bot.handlers.receipts import router as receipts_router
from bot.handlers.analytics import router as analytics_router
from bot.handlers.admin import router as admin_router
from bot.handlers.payments import router as payments_router
from bot.handlers.settings import router as settings_router

__all__ = [
    "start_router", "expenses_router", "receipts_router",
    "analytics_router", "admin_router", "payments_router", "settings_router",
]
