from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Продвинутая защита от спама и DDoS:
    1. Rate limiting — ограничение частоты запросов (не чаще чем раз в rate_limit секунд)
    2. Burst protection — если пользователь шлёт > burst_limit сообщений за burst_window секунд, он блокируется
    3. Auto-ban — после ban_threshold нарушений пользователь получает временный бан на ban_duration секунд
    4. Memory cleanup — автоматическая очистка старых записей чтобы не утекала память
    """

    def __init__(
        self,
        rate_limit: float = 0.5,       # Минимальный интервал между сообщениями (секунды)
        burst_limit: int = 5,           # Макс. сообщений за burst_window
        burst_window: float = 3.0,      # Окно в секундах для подсчёта burst
        ban_threshold: int = 10,        # Кол-во нарушений до временного бана
        ban_duration: float = 60.0,     # Длительность бана (секунды)
    ):
        self.rate_limit = rate_limit
        self.burst_limit = burst_limit
        self.burst_window = burst_window
        self.ban_threshold = ban_threshold
        self.ban_duration = ban_duration

        self.last_request: Dict[int, float] = defaultdict(float)
        self.request_timestamps: Dict[int, list] = defaultdict(list)
        self.violations: Dict[int, int] = defaultdict(int)
        self.banned_until: Dict[int, float] = defaultdict(float)
        self._last_cleanup = time.monotonic()
        super().__init__()

    def _cleanup_old_data(self):
        """Очистка старых записей раз в 5 минут чтобы не утекала память."""
        now = time.monotonic()
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now

        expired_bans = [uid for uid, until in self.banned_until.items() if until < now]
        for uid in expired_bans:
            del self.banned_until[uid]
            self.violations.pop(uid, None)

        stale = [uid for uid, ts in self.last_request.items() if now - ts > 600]
        for uid in stale:
            self.last_request.pop(uid, None)
            self.request_timestamps.pop(uid, None)
            self.violations.pop(uid, None)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        uid = user.id
        now = time.monotonic()

        self._cleanup_old_data()

        # 1. Проверка бана
        if self.banned_until.get(uid, 0) > now:
            remaining = int(self.banned_until[uid] - now)
            logger.warning(f"BLOCKED spam attempt from user {uid}, ban remaining: {remaining}s")
            if isinstance(event, Message):
                await event.answer(
                    f"🛡 <b>Антиспам:</b> Вы временно заблокированы за спам.\n"
                    f"Подождите {remaining} сек.",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(f"🛡 Антиспам: подождите {remaining} сек.", show_alert=True)
            return None

        # 2. Rate limit — слишком частые запросы
        last_time = self.last_request.get(uid, 0)
        if now - last_time < self.rate_limit:
            self.violations[uid] += 1

            # Если нарушений слишком много — баним
            if self.violations[uid] >= self.ban_threshold:
                self.banned_until[uid] = now + self.ban_duration
                logger.warning(f"BANNED user {uid} for {self.ban_duration}s (violations: {self.violations[uid]})")
                if isinstance(event, Message):
                    await event.answer(
                        f"🛡 <b>Антиспам:</b> Слишком много запросов!\n"
                        f"Вы заблокированы на {int(self.ban_duration)} секунд."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("🛡 Слишком много запросов! Бан на 60 сек.", show_alert=True)
            return None

        # 3. Burst protection — проверяем всплеск запросов
        timestamps = self.request_timestamps[uid]
        timestamps.append(now)
        # Убираем старые записи за окном
        self.request_timestamps[uid] = [t for t in timestamps if now - t < self.burst_window]

        if len(self.request_timestamps[uid]) > self.burst_limit:
            self.violations[uid] += 2  # Burst — более серьёзное нарушение
            logger.warning(f"BURST detected from user {uid}: {len(self.request_timestamps[uid])} requests in {self.burst_window}s")

            if self.violations[uid] >= self.ban_threshold:
                self.banned_until[uid] = now + self.ban_duration
                if isinstance(event, Message):
                    await event.answer(
                        f"🛡 <b>Антиспам:</b> Обнаружен спам!\n"
                        f"Вы заблокированы на {int(self.ban_duration)} секунд."
                    )
            return None

        # Всё ок — пропускаем
        self.last_request[uid] = now
        return await handler(event, data)
