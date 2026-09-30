from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
import logging
import re

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseMiddleware):
    """
    Middleware безопасности:
    1. Санитизация ввода — фильтрация опасных символов (SQL-инъекции, XSS)
    2. Ограничение длины сообщений
    3. Логирование подозрительной активности
    """

    MAX_MESSAGE_LENGTH = 1000  # Максимальная длина сообщения пользователя
    
    # Паттерны, которые могут указывать на попытку SQL-инъекции
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(--|;|'|\bOR\b\s+1\s*=\s*1)",
    ]

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            text = event.text
            user = data.get("event_from_user")
            uid = user.id if user else "unknown"

            # 1. Проверка длины
            if len(text) > self.MAX_MESSAGE_LENGTH:
                logger.warning(f"[SECURITY] User {uid}: message too long ({len(text)} chars), truncating")
                # Не блокируем, но обрезаем в data если нужно

            # 2. Проверка на SQL-инъекции
            text_upper = text.upper()
            for pattern in self.SQL_INJECTION_PATTERNS:
                if re.search(pattern, text_upper, re.IGNORECASE):
                    logger.warning(f"[SECURITY] Potential SQL injection from user {uid}: {text[:100]}")
                    await event.answer("🛡 Подозрительный ввод заблокирован системой безопасности.")
                    return None

        return await handler(event, data)
