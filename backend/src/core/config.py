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
    trading_encryption_keys: SecretStr = Field(
        ...,
        description=(
            "Comma-separated Fernet keys (newest first) for MultiFernet. "
            "Rotation: prepend new key, keep old keys for grace period. "
            "ADR-006 결정 1 / autoplan CEO F3 + Eng E4."
        ),
    )
    exchange_provider: Literal["fixture", "bybit_demo", "bybit_futures", "okx_demo"] = Field(
        default="fixture",
        description=(
            "ExchangeProvider 선택. "
            "fixture=테스트, bybit_demo=Spot testnet, bybit_futures=Linear Perp testnet, "
            "okx_demo=Sprint 7d OKX Spot sandbox."
        ),
    )
    kill_switch_cumulative_loss_percent: Decimal = Field(
        default=Decimal("10.0"),
        description=(
            "Cumulative loss % of capital_base가 이 값 초과 시 strategy-scoped "
            "kill switch 발동. autoplan CEO F4: MddEvaluator → CumulativeLossEvaluator."
        ),
    )
    kill_switch_daily_loss_usd: Decimal = Field(
        default=Decimal("500.0"),
        description="당일 누적 손실(USD) 초과 시 account-scoped kill switch 발동.",
    )
    kill_switch_api_error_streak: int = Field(
        default=5,
        description="연속 API error N회 도달 시 account-scoped kill switch 발동.",
    )
    kill_switch_capital_base_usd: Decimal = Field(
        default=Decimal("10000"),
        description=(
            "cumulative loss % 산출용 기준 자본 fallback. Sprint 8+ (2026-04-20): "
            "ExchangeAccountService.fetch_balance_usdt() 동적 바인딩 완료 — 실제 "
            "계좌 USDT 잔고 우선, fetch 실패 시 본 값 fallback."
        ),
    )
    webhook_secret_grace_seconds: int = Field(
        default=3600,
        description="Webhook secret rotation 후 구 secret 수락 grace period (초).",
    )

    # --- Dogfood Daily Report ---
    dogfood_report_output_dir: str = Field(
        default="docs/reports/dogfood",
        description="Dogfood 일일 리포트 HTML 출력 디렉토리 (프로젝트 루트 상대 경로).",
    )

    # --- Sprint 7a Bybit Futures ---
    bybit_futures_max_leverage: int = Field(
        default=20,
        ge=1,
        le=125,
        description=(
            "OrderRequest.leverage 상한. 초과 시 422. "
            "Bybit USDT Perp 이론 상한 125x이나 리스크 관리로 20x 기본."
        ),
    )

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
