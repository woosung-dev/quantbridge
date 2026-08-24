# 실시간 Redis 발행의 envelope 직렬화와 실패 격리를 검증한다.
from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.common.metrics import qb_rt_publish_failed_total, qb_rt_publish_invalid_total
from src.realtime.schemas import ticker_channel, user_channel
from src.trading import realtime_publisher


class _RecordingPool:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self._error = error

    async def publish(self, channel: str, message: str) -> None:
        self.calls.append((channel, message))
        if self._error is not None:
            raise self._error


@pytest.mark.asyncio
async def test_publish_realtime_serializes_envelope_and_decimal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)

    await realtime_publisher.publish_realtime(
        "user-1",
        "order_update",
        {
            "order_id": "order-1",
            "state": "filled",
            "symbol": "BTC/USDT",
            "side": "buy",
            "source": "rest",
            "price": Decimal("123.45"),
        },
    )

    assert len(pool.calls) == 1
    channel, message = pool.calls[0]
    assert channel == user_channel("user-1")
    envelope = json.loads(message)
    assert envelope["v"] == 1
    assert envelope["type"] == "order_update"
    assert isinstance(envelope["ts"], int)
    assert envelope["payload"] == {
        "order_id": "order-1",
        "state": "filled",
        "symbol": "BTC/USDT",
        "side": "buy",
        "source": "rest",
        "price": "123.45",
    }


@pytest.mark.asyncio
async def test_publish_realtime_swallows_redis_error_and_counts_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = _RecordingPool(RuntimeError("redis unavailable"))
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)
    before = qb_rt_publish_failed_total._value.get()

    await realtime_publisher.publish_realtime(
        "user-1", "session_state", {"session_id": "session-1"}
    )

    assert qb_rt_publish_failed_total._value.get() == before + 1


@pytest.mark.asyncio
async def test_publish_realtime_swallows_metric_mutation_failure_after_redis_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """모양 B: except 본문의 metric 고장도 이미 잡은 Redis 오류를 다시 누출시키지 않는다."""
    pool = _RecordingPool(RuntimeError("redis unavailable"))
    mutation = MagicMock(side_effect=OSError("metric mmap is read-only"))
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)
    monkeypatch.setattr(realtime_publisher.qb_rt_publish_failed_total, "inc", mutation)

    await realtime_publisher.publish_realtime(
        "user-1", "session_state", {"session_id": "session-1"}
    )

    assert len(pool.calls) == 1
    mutation.assert_called_once_with()


@pytest.mark.asyncio
async def test_publish_ticker_uses_symbol_channel_and_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)

    await realtime_publisher.publish_ticker(
        "BTCUSDT",
        {"symbol": "BTCUSDT", "mark_price": "67000", "last_price": "66999"},
    )

    assert pool.calls[0][0] == ticker_channel("BTCUSDT")
    assert json.loads(pool.calls[0][1])["type"] == "ticker"


@pytest.mark.asyncio
async def test_publish_ticker_uses_shared_payload_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)
    counter = qb_rt_publish_invalid_total.labels(event_type="ticker")
    before = counter._value.get()

    await realtime_publisher.publish_ticker("BTCUSDT", {"symbol": "BTCUSDT"})

    assert pool.calls == []
    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_publish_position_update_serializes_registered_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)

    await realtime_publisher.publish_realtime(
        "user-1",
        "position_update",
        {"symbol": "BTCUSDT", "side": "long", "size": "1.25"},
    )

    assert json.loads(pool.calls[0][1])["type"] == "position_update"


@pytest.mark.asyncio
async def test_publish_realtime_skips_unregistered_type_and_counts_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)
    counter = qb_rt_publish_invalid_total.labels(event_type="unregistered")
    before = counter._value.get()

    await realtime_publisher.publish_realtime("user-1", "unregistered", {})

    assert pool.calls == []
    assert counter._value.get() == before + 1
