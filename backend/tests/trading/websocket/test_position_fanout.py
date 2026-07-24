# Bybit private position 팬아웃과 캐시 무효화 계약을 검증한다.
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import src.trading.websocket.position_fanout as position_fanout
from src.trading.websocket.position_fanout import PositionFanoutHandler, PrivateTopicRouter


class _RecordingRedis:
    def __init__(self, error: Exception | None = None) -> None:
        self.deleted: list[str] = []
        self._error = error

    async def delete(self, key: str) -> None:
        if self._error is not None:
            raise self._error
        self.deleted.append(key)


def _session_factory():
    @asynccontextmanager
    async def _session():
        yield object()

    return _session


def _install_sessions(monkeypatch: pytest.MonkeyPatch, sessions: list[object]) -> None:
    class _SessionRepo:
        def __init__(self, _session: object) -> None:
            pass

        async def list_active_by_account(self, _account_id: object) -> list[object]:
            return sessions

    monkeypatch.setattr(position_fanout, "LiveSignalSessionRepository", _SessionRepo)


def _handler(
    monkeypatch: pytest.MonkeyPatch,
    sessions: list[object],
    redis: _RecordingRedis | None = None,
    *,
    min_interval_s: float = 2.0,
    clock=None,
) -> tuple[PositionFanoutHandler, _RecordingRedis, AsyncMock]:
    _install_sessions(monkeypatch, sessions)
    publisher = AsyncMock()
    monkeypatch.setattr(position_fanout, "publish_realtime", publisher)
    recorded_redis = redis or _RecordingRedis()
    return (
        PositionFanoutHandler(
            _session_factory(),
            recorded_redis,
            "user-1",
            uuid4(),
            min_interval_s=min_interval_s,
            clock=clock or position_fanout.time.monotonic,
        ),
        recorded_redis,
        publisher,
    )


@pytest.mark.asyncio
async def test_router_order_topic_dispatches_each_item() -> None:
    account_id = uuid4()
    state_handler = AsyncMock()
    position_handler = AsyncMock()
    router = PrivateTopicRouter(
        account_id=account_id,
        state_handler=state_handler,
        position_handler=position_handler,
    )
    items = [{"orderId": "one"}, {"orderId": "two"}]

    await router.handle_message({"topic": "order", "data": items})

    assert state_handler.handle_order_event.await_args_list[0].args == (account_id, items[0])
    assert state_handler.handle_order_event.await_args_list[1].args == (account_id, items[1])
    position_handler.handle_position_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_order_failure_does_not_block_next_item() -> None:
    account_id = uuid4()
    state_handler = AsyncMock()
    state_handler.handle_order_event = AsyncMock(side_effect=[RuntimeError("boom"), None])
    router = PrivateTopicRouter(
        account_id=account_id,
        state_handler=state_handler,
        position_handler=AsyncMock(),
    )

    await router.handle_message({"topic": "order", "data": [{"id": 1}, {"id": 2}]})

    assert state_handler.handle_order_event.await_count == 2


@pytest.mark.asyncio
async def test_position_event_publishes_frozen_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    session = SimpleNamespace(id=uuid4(), symbol="BTC/USDT")
    handler, redis, publisher = _handler(monkeypatch, [session])

    await handler.handle_position_event({"symbol": "BTCUSDT", "side": "Buy", "size": "1.25"})

    assert redis.deleted == [f"qb_pos_snapshot:{session.id}"]
    publisher.assert_awaited_once_with(
        "user-1",
        "position_update",
        {"symbol": "BTCUSDT", "side": "long", "size": "1.25"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reported_side", "size", "expected_side"),
    [("Buy", "1", "long"), ("Sell", "1", "short"), ("Sell", "0", "flat")],
)
async def test_position_side_normalization(
    monkeypatch: pytest.MonkeyPatch,
    reported_side: str,
    size: str,
    expected_side: str,
) -> None:
    handler, _, publisher = _handler(
        monkeypatch,
        [SimpleNamespace(id=uuid4(), symbol="BTC/USDT")],
        min_interval_s=0,
    )

    await handler.handle_position_event(
        {"symbol": "BTCUSDT", "side": reported_side, "size": size}
    )

    assert publisher.await_args.args[2]["side"] == expected_side


@pytest.mark.asyncio
async def test_position_debounce_does_not_skip_cache_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = SimpleNamespace(id=uuid4(), symbol="BTC/USDT")
    times = iter((10.0, 11.0, 12.0, 13.0))
    handler, redis, publisher = _handler(monkeypatch, [session], clock=lambda: next(times))
    item = {"symbol": "BTCUSDT", "side": "Buy", "size": "1"}

    await handler.handle_position_event(item)
    await handler.handle_position_event(item)

    assert redis.deleted == [f"qb_pos_snapshot:{session.id}"] * 2
    publisher.assert_awaited_once()


@pytest.mark.asyncio
async def test_position_deletes_only_matching_session_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    matching = SimpleNamespace(id=uuid4(), symbol="BTC/USDT")
    other = SimpleNamespace(id=uuid4(), symbol="ETH/USDT")
    handler, redis, _ = _handler(monkeypatch, [matching, other])

    await handler.handle_position_event({"symbol": "BTCUSDT", "side": "Buy", "size": "1"})

    assert redis.deleted == [f"qb_pos_snapshot:{matching.id}"]


@pytest.mark.asyncio
async def test_redis_delete_failure_does_not_skip_publish(monkeypatch: pytest.MonkeyPatch) -> None:
    handler, _, publisher = _handler(
        monkeypatch,
        [SimpleNamespace(id=uuid4(), symbol="BTC/USDT")],
        _RecordingRedis(RuntimeError("redis down")),
    )

    await handler.handle_position_event({"symbol": "BTCUSDT", "side": "Buy", "size": "1"})

    publisher.assert_awaited_once()


@pytest.mark.asyncio
async def test_router_ignores_acks_and_warns_on_rejected_subscribe(
    caplog: pytest.LogCaptureFixture,
) -> None:
    router = PrivateTopicRouter(
        account_id=uuid4(), state_handler=AsyncMock(), position_handler=AsyncMock()
    )

    with caplog.at_level(logging.WARNING, logger=position_fanout.__name__):
        await router.handle_message({"op": "subscribe", "success": True})
        await router.handle_message({"op": "subscribe", "success": False})
        await router.handle_message({"topic": "unknown", "data": []})

    assert "ws_subscribe_rejected" in caplog.text


@pytest.mark.asyncio
async def test_malformed_position_payloads_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    session = SimpleNamespace(id=uuid4(), symbol="BTC/USDT")
    handler, redis, publisher = _handler(monkeypatch, [session])
    router = PrivateTopicRouter(
        account_id=uuid4(), state_handler=AsyncMock(), position_handler=handler
    )

    await router.handle_message({"topic": "position"})
    await router.handle_message({"topic": "position", "data": None})
    await router.handle_message(
        {
            "topic": "position",
            "data": [
                None,
                {},
                {"symbol": "BTCUSDT", "size": "-1"},
                {"symbol": "BTCUSDT", "size": "NaN"},
            ],
        }
    )
    await handler.handle_position_event({"symbol": "BTCUSDT", "side": "Buy", "size": "0"})

    assert redis.deleted == [f"qb_pos_snapshot:{session.id}"]
    assert publisher.await_args.args[2]["side"] == "flat"


@pytest.mark.asyncio
async def test_position_event_with_no_active_sessions_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    handler, redis, publisher = _handler(monkeypatch, [])

    await handler.handle_position_event({"symbol": "BTCUSDT", "side": "Buy", "size": "1"})

    assert redis.deleted == []
    publisher.assert_not_awaited()


@pytest.mark.asyncio
async def test_stream_main_wires_private_topic_router(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.tasks import websocket_task
    from src.trading.models import ExchangeName

    captured: dict[str, object] = {}
    account_id = str(uuid4())
    account = MagicMock(
        exchange=ExchangeName.bybit,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
        mode=SimpleNamespace(value="demo"),
        user_id=uuid4(),
    )

    class _Engine:
        async def dispose(self) -> None:
            pass

    @asynccontextmanager
    async def _session():
        session = MagicMock()
        session.get = AsyncMock(return_value=account)
        yield session

    class _SessionFactory:
        def __call__(self):
            return _session()

    class _Stream:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)
            self.reconnect_count = 0

        async def __aenter__(self):
            captured["stop_event"].set()  # type: ignore[union-attr]
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(websocket_task, "create_worker_engine_and_sm", lambda: (_Engine(), _SessionFactory()))
    monkeypatch.setattr("src.trading.encryption.EncryptionService.decrypt", lambda *_: "plain")
    monkeypatch.setattr("src.trading.websocket.BybitPrivateStream", _Stream)
    monkeypatch.setattr("src.common.redis_client.get_redis_lock_pool", _RecordingRedis)

    await websocket_task._stream_main(account_id)

    assert captured["topics"] == ("order", "position")
    assert isinstance(captured["message_handler"], PrivateTopicRouter)
    assert "handler" not in captured
