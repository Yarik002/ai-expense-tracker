from pydantic import field_validator
from pydantic_settings import BaseSettings
import sys
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/expense_tracker"
    
    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_VISION_MODEL: str = "gemini-3.8-flash"
    
    # OpenRouter API (for auto-categorization)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    
    # Subscription pricing (Telegram Stars)
    MONTHLY_STARS_PRICE: int = 150
    YEARLY_STARS_PRICE: int = 1500
    FREE_RECEIPT_LIMIT: int = 3
    
    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v
    
    def validate_secrets(self):
        """Проверка что все секреты заданы и не являются плейсхолдерами."""
        errors = []
        
        if not self.BOT_TOKEN or self.BOT_TOKEN == "your_bot_token_here":
            errors.append("BOT_TOKEN не задан!")
            
        if not self.GEMINI_API_KEY or self.GEMINI_API_KEY == "your_gemini_api_key_here":
            logger.warning("⚠️  GEMINI_API_KEY не задан — ИИ-функции будут недоступны.")
            
        if not self.OPENROUTER_API_KEY or self.OPENROUTER_API_KEY == "your_openrouter_api_key_here":
            logger.warning("⚠️  OPENROUTER_API_KEY не задан — авто-категоризация будет недоступна.")
            
        if "postgres:postgres@" in self.DATABASE_URL:
            logger.warning("⚠️  ВНИМАНИЕ: Используется дефолтный пароль БД 'postgres'. Смените его в .env!")
            
        if not self.ADMIN_IDS:
            logger.warning("⚠️  ADMIN_IDS пуст — никто не сможет использовать /admin панель.")
            
        if errors:
            for e in errors:
                logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            logger.error("Бот не может запуститься без правильных секретов. Проверьте файл .env")
            sys.exit(1)
        
        logger.info("✅ Все секреты проверены и загружены.")
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
settings.validate_secrets()
