from pydantic import field_validator
from pydantic_settings import BaseSettings


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
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
