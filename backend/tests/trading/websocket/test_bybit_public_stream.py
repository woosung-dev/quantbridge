# Bybit 공개 ticker 스트림의 인증 생략·delta 병합·심볼 갱신을 검증한다.
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.trading.websocket.bybit_public_stream import (
    BybitPublicTickerStream,
    TickerFanoutHandler,
)


@pytest.mark.asyncio
async def test_public_stream_skips_auth_and_subscribes_topics(fake_ws, fake_connect) -> None:
    stream = BybitPublicTickerStream(
        symbols={"ETHUSDT", "BTCUSDT"}, connect_func=fake_connect
    )

    async with stream:
        assert fake_ws.sent == [
            {"op": "subscribe", "args": ["tickers.BTCUSDT", "tickers.ETHUSDT"]}
        ]


@pytest.mark.asyncio
async def test_public_stream_with_no_symbols_sends_no_subscribe(fake_ws, fake_connect) -> None:
    stream = BybitPublicTickerStream(symbols=set(), connect_func=fake_connect)

    async with stream:
        assert fake_ws.sent == []


@pytest.mark.asyncio
async def test_ticker_handler_merges_dict_delta_and_publishes(monkeypatch) -> None:
    published = AsyncMock()
    monkeypatch.setattr(
        "src.trading.websocket.bybit_public_stream.publish_ticker", published
    )
    handler = TickerFanoutHandler(min_interval_s=0)

    await handler.handle_message(
        {"topic": "tickers.BTCUSDT", "data": {"symbol": "BTCUSDT", "markPrice": "100"}}
    )
    await handler.handle_message(
        {"topic": "tickers.BTCUSDT", "data": {"symbol": "BTCUSDT", "lastPrice": "101"}}
    )

    assert published.await_args_list[1].args == (
        "BTCUSDT",
        {"symbol": "BTCUSDT", "mark_price": "100", "last_price": "101"},
    )


@pytest.mark.asyncio
async def test_ticker_handler_skips_data_without_merged_mark_price(monkeypatch) -> None:
    published = AsyncMock()
    monkeypatch.setattr(
        "src.trading.websocket.bybit_public_stream.publish_ticker", published
    )
    handler = TickerFanoutHandler()

    await handler.handle_message(
        {"topic": "tickers.BTCUSDT", "data": {"symbol": "BTCUSDT", "lastPrice": "101"}}
    )

    assert handler._snapshots["BTCUSDT"]["lastPrice"] == "101"
    published.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_price_absent_delta_keeps_snapshot_and_is_throttled(monkeypatch) -> None:
    published = AsyncMock()
    monkeypatch.setattr(
        "src.trading.websocket.bybit_public_stream.publish_ticker", published
    )
    handler = TickerFanoutHandler(min_interval_s=60.0)

    await handler.handle_message(
        {
            "topic": "tickers.BTCUSDT",
            "data": {"symbol": "BTCUSDT", "markPrice": "100", "lastPrice": "100"},
        }
    )
    await handler.handle_message(
        {"topic": "tickers.BTCUSDT", "data": {"symbol": "BTCUSDT", "lastPrice": "101"}}
    )

    assert handler._snapshots["BTCUSDT"]["markPrice"] == "100"
    assert handler._snapshots["BTCUSDT"]["lastPrice"] == "101"
    published.assert_awaited_once()


@pytest.mark.asyncio
async def test_ticker_handler_throttles_per_symbol(monkeypatch) -> None:
    published = AsyncMock()
    monkeypatch.setattr(
        "src.trading.websocket.bybit_public_stream.publish_ticker", published
    )
    handler = TickerFanoutHandler(min_interval_s=60.0)

    for last_price in ("100", "101"):
        await handler.handle_message(
            {
                "topic": "tickers.BTCUSDT",
                "data": {
                    "symbol": "BTCUSDT",
                    "markPrice": "99",
                    "lastPrice": last_price,
                },
            }
        )

    assert published.await_count == 1
    assert handler._snapshots["BTCUSDT"]["lastPrice"] == "101"


@pytest.mark.asyncio
async def test_update_symbols_sends_live_subscribe_and_unsubscribe(fake_ws, fake_connect) -> None:
    stream = BybitPublicTickerStream(symbols={"BTCUSDT"}, connect_func=fake_connect)

    async with stream:
        await stream.update_symbols({"ETHUSDT"})
        assert fake_ws.sent[1:] == [
            {"op": "unsubscribe", "args": ["tickers.BTCUSDT"]},
            {"op": "subscribe", "args": ["tickers.ETHUSDT"]},
        ]
        assert stream._stream._topics == ("tickers.ETHUSDT",)


@pytest.mark.asyncio
async def test_update_symbols_survives_send_failure_and_updates_topics(
    fake_ws, fake_connect, monkeypatch
) -> None:
    """supervisor 재연결과 경합해 send 가 죽어도 예외가 새지 않고 topics 는 교체된다.

    codex 최종 diff 리뷰 반영 — send 실패 시 태스크/refresh 루프가 죽으면 beat
    reconcile(5분)까지 ticker 공백. topics 선교체 + best-effort send 로 재연결 시
    최신 셋 재구독을 보장한다.
    """
    stream = BybitPublicTickerStream(symbols={"BTCUSDT"}, connect_func=fake_connect)

    async with stream:
        monkeypatch.setattr(
            stream._stream._ws, "send", AsyncMock(side_effect=RuntimeError("socket dead"))
        )
        await stream.update_symbols({"ETHUSDT"})
        assert stream._stream._topics == ("tickers.ETHUSDT",)
        assert stream._symbols == {"ETHUSDT"}
