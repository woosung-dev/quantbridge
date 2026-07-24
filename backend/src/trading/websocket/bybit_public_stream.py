# Bybit 공개 ticker 스트림의 delta 병합과 Redis 팬아웃을 담당한다.
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from src.trading.realtime_publisher import publish_ticker
from src.trading.websocket.bybit_private_stream import BybitPrivateStream

# Bybit 공식 문서: demo 계정도 공개 시세는 mainnet public linear endpoint를 공유한다.
_BYBIT_PUBLIC_WS_ENDPOINT = "wss://stream.bybit.com/v5/public/linear"
_PUBLIC_STREAM_ACCOUNT_ID = "public-ticker"


class TickerFanoutHandler:
    """Bybit ticker snapshot/delta를 심볼별 완전한 현재값으로 병합한다."""

    def __init__(self, *, min_interval_s: float = 1.0) -> None:
        self._min_interval_s = min_interval_s
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._last_published_at: dict[str, float] = {}

    async def handle_message(self, msg: dict[str, Any]) -> None:
        data = msg.get("data")
        if not isinstance(data, dict):
            return
        symbol = data.get("symbol")
        if not isinstance(symbol, str):
            return

        snapshot = self._snapshots.setdefault(symbol, {})
        snapshot.update(data)
        mark_price = snapshot.get("markPrice")
        if not isinstance(mark_price, str):
            return

        now = time.monotonic()
        if now - self._last_published_at.get(symbol, float("-inf")) < self._min_interval_s:
            return
        self._last_published_at[symbol] = now
        last_price = snapshot.get("lastPrice")
        await publish_ticker(
            symbol,
            {
                "symbol": symbol,
                "mark_price": mark_price,
                "last_price": last_price if isinstance(last_price, str) else None,
            },
        )


class BybitPublicTickerStream:
    """공개 ticker를 기존 supervisor에 조립하는 async context manager."""

    def __init__(
        self,
        *,
        symbols: set[str],
        stop_event: asyncio.Event | None = None,
        handler: TickerFanoutHandler | None = None,
        heartbeat_interval: float = 20.0,
        connect_func: Any = None,
    ) -> None:
        self._symbols = set(symbols)
        self._stream = BybitPrivateStream(
            endpoint=_BYBIT_PUBLIC_WS_ENDPOINT,
            api_key=None,
            api_secret=None,
            account_id=_PUBLIC_STREAM_ACCOUNT_ID,
            stop_event=stop_event,
            heartbeat_interval=heartbeat_interval,
            connect_func=connect_func,
            topics=self._topics_for(self._symbols),
            auth_required=False,
            message_handler=handler or TickerFanoutHandler(),
        )

    @property
    def stop_event(self) -> asyncio.Event:
        return self._stream.stop_event

    @staticmethod
    def _topics_for(symbols: set[str]) -> tuple[str, ...]:
        return tuple(f"tickers.{symbol}" for symbol in sorted(symbols))

    async def __aenter__(self) -> BybitPublicTickerStream:
        await self._stream.__aenter__()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self._stream.__aexit__(*exc_info)

    async def update_symbols(self, new: set[str]) -> None:
        """현재 연결에서는 diff만 보내고 재연결용 topics도 즉시 교체한다."""
        new_symbols = set(new)
        removed = self._symbols - new_symbols
        added = new_symbols - self._symbols
        ws = self._stream._ws
        if self._stream.connected and ws is not None:
            if removed:
                await ws.send(
                    json.dumps({"op": "unsubscribe", "args": list(self._topics_for(removed))})
                )
            if added:
                await ws.send(
                    json.dumps({"op": "subscribe", "args": list(self._topics_for(added))})
                )
        self._symbols = new_symbols
        self._stream._topics = self._topics_for(new_symbols)
