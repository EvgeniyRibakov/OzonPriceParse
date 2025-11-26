"""Настройки приложения."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Ozon Seller API настройки
    ozon_client_id: Optional[str] = Field(default=None, env="OZON_CLIENT_ID")
    ozon_api_key: Optional[str] = Field(default=None, env="OZON_API_KEY")
    
    # Настройки логирования
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Настройки агента
    agent_timeout: int = Field(default=30, env="AGENT_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    
    # Настройки парсинга
    request_delay: float = Field(default=0.2, env="REQUEST_DELAY")  # Безопасная задержка для API
    batch_size: int = Field(default=1000, env="BATCH_SIZE")  # Максимум товаров за запрос
    max_requests_per_minute: int = Field(default=60, env="MAX_REQUESTS_PER_MINUTE")  # Rate limit
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        env="USER_AGENT"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

