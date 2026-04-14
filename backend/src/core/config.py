from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "QuantBridge"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: SecretStr = SecretStr("change-me")

    # Clerk
    clerk_secret_key: SecretStr = SecretStr("")
    clerk_publishable_key: str = ""
    clerk_webhook_secret: SecretStr = SecretStr("")

    # Database
    database_url: str = "postgresql+asyncpg://quantbridge:password@db:5432/quantbridge"
    timescale_url: str = "postgresql+asyncpg://quantbridge:password@timescaledb:5432/quantbridge_ts"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Encryption (거래소 API Key AES-256)
    encryption_key: SecretStr = SecretStr("")

    # CORS / URLs
    frontend_url: str = "http://localhost:3000"

    # Exchange
    default_exchange: str = "bybit"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
