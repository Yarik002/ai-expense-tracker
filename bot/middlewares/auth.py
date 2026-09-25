from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker
from bot.database.repositories.user_repo import UserRepository
from bot.config import settings

class AuthMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Get user from event
        user_tg = data.get("event_from_user")
        if not user_tg:
            return await handler(event, data)
        
        async with self.session_factory() as session:
            repo = UserRepository(session)
            db_user = await repo.get_by_telegram_id(user_tg.id)
            
            if not db_user:
                # Auto-register new user
                is_admin = user_tg.id in settings.ADMIN_IDS
                db_user = await repo.create(
                    telegram_id=user_tg.id,
                    username=user_tg.username,
                    first_name=user_tg.first_name or "User",
                    last_name=user_tg.last_name,
                    language_code=user_tg.language_code or "ru",
                    is_admin=is_admin,
                )
            
            # Check if blocked
            if db_user.is_blocked:
                if isinstance(event, Message):
                    await event.answer("⛔ Ваш аккаунт заблокирован.")
                return None
            
            # Update username if changed
            if db_user.username != user_tg.username:
                db_user.username = user_tg.username
                await repo.update(db_user)
            
            data["db_user"] = db_user
            data["session_factory"] = self.session_factory
        
        return await handler(event, data)
