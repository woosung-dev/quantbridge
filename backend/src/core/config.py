from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
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

    # Database — TimescaleDB extension은 동일 DB의 ts schema에 위치 (M2)
    database_url: str = "postgresql+asyncpg://quantbridge:password@db:5432/quantbridge"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Backtest (Sprint 4)
    backtest_stale_threshold_seconds: int = Field(
        default=1800,
        description=(
            "running/cancelling 상태가 몇 초 초과 시 stale로 판정 "
            "(worker startup reclaim + GET /:id/progress의 stale 플래그). 기본 30분."
        ),
    )
    ohlcv_fixture_root: str = Field(
        default="backend/data/fixtures/ohlcv",
        description="FixtureProvider가 OHLCV CSV를 읽는 루트 경로. 프로세스 CWD 기준.",
    )

    # --- Sprint 6 Trading ---
    # autoplan CEO F3 + Eng E4: MultiFernet 기반 다중 키 지원 (comma-separated, newest first)
    trading_encryption_keys: SecretStr = Field(...)
    exchange_provider: Literal["fixture", "bybit_demo"] = Field(default="fixture")
    # autoplan CEO F4: MddEvaluator → CumulativeLossEvaluator rename 반영
    kill_switch_cumulative_loss_percent: Decimal = Field(default=Decimal("10.0"))
    kill_switch_daily_loss_usd: Decimal = Field(default=Decimal("500.0"))
    kill_switch_api_error_streak: int = Field(default=5)
    kill_switch_capital_base_usd: Decimal = Field(default=Decimal("10000"))
    webhook_secret_grace_seconds: int = Field(default=3600)

    @field_validator("trading_encryption_keys")
    @classmethod
    def _validate_keys(cls, v: SecretStr) -> SecretStr:
        """comma-separated Fernet keys — 1개 이상, 각각 44-char URL-safe base64."""
        from cryptography.fernet import Fernet
        raw = v.get_secret_value()
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys:
            raise ValueError("TRADING_ENCRYPTION_KEYS must contain at least 1 Fernet key")
        for k in keys:
            try:
                Fernet(k.encode())
            except ValueError as e:
                raise ValueError(f"Invalid Fernet key: {e}") from e
        return v

    # CORS / URLs
    frontend_url: str = "http://localhost:3000"

    # Exchange / OHLCV provider
    default_exchange: str = "bybit"
    ohlcv_provider: Literal["fixture", "timescale"] = Field(
        default="fixture",
        description=(
            "OHLCV 데이터 소스. 'fixture'=Sprint 4 CSV, "
            "'timescale'=CCXT+TimescaleDB cache (Sprint 5 M3+)."
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
