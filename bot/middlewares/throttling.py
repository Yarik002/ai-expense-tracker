from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import time
from collections import defaultdict


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.last_request: Dict[int, float] = defaultdict(float)
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            current_time = time.monotonic()
            last_time = self.last_request.get(user.id, 0)
            
            if current_time - last_time < self.rate_limit:
                return None  # Skip if too fast
            
            self.last_request[user.id] = current_time
        
        return await handler(event, data)
