"""Sprint 23 BL-103 — EXCHANGE_PROVIDER deprecation lifespan warning.

codex G.0 P2 #2: lifespan one-shot warning + app_env (staging/production) 조건.
development/test 는 silent (test_config.py 4건이 EXCHANGE_PROVIDER setenv 하므로
caplog noise 회피).
"""
from __future__ import annotations

import logging

import pytest

from src.main import lifespan


@pytest.mark.asyncio
async def test_exchange_provider_deprecation_warning_emitted_in_production(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """staging/production + exchange_provider!=fixture → DEPRECATED warning."""
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "app_env", "production")
    monkeypatch.setattr(main_settings, "exchange_provider", "bybit_demo")
    # ohlcv_provider fixture mode 로 강제 (CCXTProvider 호출 회피)
    monkeypatch.setattr(main_settings, "ohlcv_provider", "fixture")

    # healthcheck_redis_lock 도 mock (test 환경에서 Redis 의존 회피)
    async def _noop_healthcheck(_app) -> None:
        return None

    monkeypatch.setattr(
        "src.common.redis_client.healthcheck_redis_lock",
        _noop_healthcheck,
    )

    from fastapi import FastAPI

    app = FastAPI()
    caplog.set_level(logging.WARNING, logger="src.main")

    async with lifespan(app):
        pass

    deprecation_messages = [
        r.getMessage() for r in caplog.records
        if "DEPRECATED" in r.getMessage() and "BL-091" in r.getMessage()
    ]
    assert len(deprecation_messages) == 1
    assert "bybit_demo" in deprecation_messages[0]


@pytest.mark.asyncio
async def test_exchange_provider_silent_in_development(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """development app_env 면 warning silent (test 환경 noise 회피)."""
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "app_env", "development")
    monkeypatch.setattr(main_settings, "exchange_provider", "bybit_demo")
    monkeypatch.setattr(main_settings, "ohlcv_provider", "fixture")

    async def _noop_healthcheck(_app) -> None:
        return None

    monkeypatch.setattr(
        "src.common.redis_client.healthcheck_redis_lock",
        _noop_healthcheck,
    )

    from fastapi import FastAPI

    app = FastAPI()
    caplog.set_level(logging.WARNING, logger="src.main")

    async with lifespan(app):
        pass

    deprecation_messages = [
        r.getMessage() for r in caplog.records
        if "DEPRECATED" in r.getMessage() and "BL-091" in r.getMessage()
    ]
    assert len(deprecation_messages) == 0


@pytest.mark.asyncio
async def test_exchange_provider_default_fixture_silent_even_in_production(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """production 이어도 exchange_provider=fixture (default) 면 warning 없음."""
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "app_env", "production")
    monkeypatch.setattr(main_settings, "exchange_provider", "fixture")
    monkeypatch.setattr(main_settings, "ohlcv_provider", "fixture")

    async def _noop_healthcheck(_app) -> None:
        return None

    monkeypatch.setattr(
        "src.common.redis_client.healthcheck_redis_lock",
        _noop_healthcheck,
    )

    from fastapi import FastAPI

    app = FastAPI()
    caplog.set_level(logging.WARNING, logger="src.main")

    async with lifespan(app):
        pass

    deprecation_messages = [
        r.getMessage() for r in caplog.records
        if "DEPRECATED" in r.getMessage() and "BL-091" in r.getMessage()
    ]
    assert len(deprecation_messages) == 0
