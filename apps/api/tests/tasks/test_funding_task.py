"""Funding rate Celery 태스크의 prefork-safe 엔진 수명 계약을 고정한다."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.models import ExchangeName


class _RecordingEngine:
    """dispose() await 횟수를 기록한다."""

    def __init__(self) -> None:
        self.dispose_calls = 0

    async def dispose(self) -> None:
        self.dispose_calls += 1


def _fake_create_worker_engine_and_sm() -> tuple[
    Callable[[], tuple[_RecordingEngine, object]],
    _RecordingEngine,
    MagicMock,
]:
    """엔진 수명과 저장 함수 인자를 관측하는 worker factory fake를 만든다."""
    engine = _RecordingEngine()
    session = MagicMock()

    @asynccontextmanager
    async def _session_ctx():
        yield session

    class _SessionMaker:
        def __call__(self):
            return _session_ctx()

    def _factory() -> tuple[_RecordingEngine, object]:
        return engine, _SessionMaker()

    return _factory, engine, session


@pytest.mark.asyncio
async def test_async_fetch_returns_contract_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """정상 fetch는 저장 반환값 계약과 dispose 1회를 함께 보장한다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    factory, engine, session = _fake_create_worker_engine_and_sm()
    store = AsyncMock(return_value=7)
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "fetch_and_store_funding_rates", store)

    result = await funding_module._async_fetch("binance", "ETH/USDT:USDT", 2)

    assert result == {"exchange": "binance", "symbol": "ETH/USDT:USDT", "inserted": 7}
    assert engine.dispose_calls == 1
    store.assert_awaited_once()
    kwargs = store.await_args.kwargs
    assert type(kwargs["exchange_name"]) is ExchangeName
    assert kwargs["exchange_name"] is ExchangeName.binance
    assert kwargs["symbol"] == "ETH/USDT:USDT"
    assert kwargs["session"] is session


@pytest.mark.asyncio
async def test_async_fetch_disposes_engine_when_store_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """저장 실패가 밖으로 전파돼도 finally가 엔진을 정확히 한 번 처분한다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    factory, engine, _session = _fake_create_worker_engine_and_sm()
    store = AsyncMock(side_effect=RuntimeError("store failed"))
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "fetch_and_store_funding_rates", store)

    with pytest.raises(RuntimeError, match="store failed"):
        await funding_module._async_fetch("bybit", "BTC/USDT:USDT", 2)

    store.assert_awaited_once()
    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_async_fetch_creates_worker_engine_for_each_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """두 fetch 호출은 factory를 두 번 불러 module-level 엔진 캐시를 막는다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    first_factory, first_engine, _first_session = _fake_create_worker_engine_and_sm()
    second_factory, second_engine, _second_session = _fake_create_worker_engine_and_sm()
    factory = MagicMock(side_effect=[first_factory(), second_factory()])
    store = AsyncMock(return_value=1)
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "fetch_and_store_funding_rates", store)

    await funding_module._async_fetch("bybit", "BTC/USDT:USDT", 2)
    await funding_module._async_fetch("bybit", "BTC/USDT:USDT", 2)

    assert factory.call_count == 2
    assert first_engine.dispose_calls == 1
    assert second_engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_async_fetch_passes_utc_since_for_requested_lookback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fetch의 since는 호출 경계 안에서 계산한 UTC now - lookback_hours다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    factory, _engine, _session = _fake_create_worker_engine_and_sm()
    store = AsyncMock(return_value=1)
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "fetch_and_store_funding_rates", store)
    before = datetime.now(UTC)

    await funding_module._async_fetch("bybit", "BTC/USDT:USDT", 5)

    after = datetime.now(UTC)
    since = store.await_args.kwargs["since"]
    assert since.tzinfo is UTC
    assert before - timedelta(hours=5) <= since <= after - timedelta(hours=5)


@pytest.mark.asyncio
async def test_async_fetch_invalid_exchange_creates_then_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """알 수 없는 거래소는 엔진 생성 뒤 ValueError가 나며 finally가 dispose한다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    factory, engine, _session = _fake_create_worker_engine_and_sm()
    store = AsyncMock()
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "fetch_and_store_funding_rates", store)

    with pytest.raises(ValueError):
        await funding_module._async_fetch("kraken", "BTC/USDT:USDT", 2)

    store.assert_not_awaited()
    assert engine.dispose_calls == 1


def test_funding_module_has_no_global_worker_engine_cache() -> None:
    """prefork loop mismatch를 일으킨 과거 엔진·sessionmaker 캐시 재도입을 막는다."""
    from src.tasks import funding as funding_module

    assert not hasattr(funding_module, "_worker_engine")
    assert not hasattr(funding_module, "_sessionmaker_cache")
    assert hasattr(funding_module, "create_worker_engine_and_sm")


@pytest.mark.asyncio
async def test_async_backfill_parses_dates_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """backfill은 ISO 문자열을 datetime으로 넘기고 정상 path에서 엔진을 처분한다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    factory, engine, session = _fake_create_worker_engine_and_sm()
    store = AsyncMock(return_value=11)
    start_iso = "2026-01-02T03:04:05+00:00"
    end_iso = "2026-01-03T04:05:06+00:00"
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "backfill_funding_rate_history", store)

    result = await funding_module._async_backfill("okx", "BTC/USDT:USDT", start_iso, end_iso)

    assert result == {"exchange": "okx", "symbol": "BTC/USDT:USDT", "inserted": 11}
    assert engine.dispose_calls == 1
    store.assert_awaited_once()
    kwargs = store.await_args.kwargs
    assert type(kwargs["start"]) is datetime
    assert type(kwargs["end"]) is datetime
    assert kwargs["start"] == datetime.fromisoformat(start_iso)
    assert kwargs["end"] == datetime.fromisoformat(end_iso)
    assert kwargs["session"] is session


@pytest.mark.asyncio
async def test_async_backfill_disposes_engine_when_store_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """backfill 저장 실패도 finally에서 엔진을 정확히 한 번 처분한다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    factory, engine, _session = _fake_create_worker_engine_and_sm()
    store = AsyncMock(side_effect=RuntimeError("backfill failed"))
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "backfill_funding_rate_history", store)

    with pytest.raises(RuntimeError, match="backfill failed"):
        await funding_module._async_backfill(
            "bybit", "BTC/USDT:USDT", "2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00"
        )

    store.assert_awaited_once()
    assert engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_async_backfill_invalid_iso_fails_before_engine_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """못 읽는 ISO 문자열은 엔진 생성·dispose 전 ValueError로 끝난다."""
    from src.tasks import funding as funding_module
    from src.trading import funding as funding_service

    factory = MagicMock()
    store = AsyncMock()
    monkeypatch.setattr(funding_module, "create_worker_engine_and_sm", factory)
    monkeypatch.setattr(funding_service, "backfill_funding_rate_history", store)

    with pytest.raises(ValueError):
        await funding_module._async_backfill(
            "bybit", "BTC/USDT:USDT", "not-an-iso-date", "2026-01-02T00:00:00+00:00"
        )

    factory.assert_not_called()
    store.assert_not_awaited()


def test_funding_tasks_keep_beat_registration_names_and_retry_contract() -> None:
    """beat가 찾는 태스크 이름과 fetch 재시도 횟수를 고정한다."""
    from src.tasks import funding as funding_module

    assert funding_module.fetch_funding_rates_task.name == "trading.fetch_funding_rates"
    assert funding_module.fetch_funding_rates_task.max_retries == 2
    assert funding_module.backfill_funding_rates_task.name == "trading.backfill_funding_rates"
