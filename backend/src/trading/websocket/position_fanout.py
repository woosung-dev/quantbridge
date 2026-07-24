# Bybit private position 이벤트를 캐시 무효화와 사용자 실시간 힌트로 전달한다.
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from src.common.metrics import qb_ws_subscribe_rejected_total
from src.market_data.constants import to_bybit_raw_symbol
from src.trading.realtime_publisher import publish_realtime
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.websocket.bybit_private_stream import MessageEventHandler
from src.trading.websocket.state_handler import StateHandler

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Any]


class PositionFanoutHandler:
    """Bybit position 이벤트로 관련 position snapshot만 무효화한다."""

    def __init__(
        self,
        session_factory: SessionFactory,
        redis: Any,
        user_id: str,
        account_id: UUID,
        min_interval_s: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis
        self._user_id = user_id
        self._account_id = account_id
        self._min_interval_s = min_interval_s
        self._clock = clock
        self._last_published_at: dict[str, float] = {}

    async def handle_position_event(self, item: dict[str, Any]) -> None:
        if not isinstance(item, dict):
            return
        symbol = item.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            return
        try:
            size = Decimal(str(item.get("size")))
        except (InvalidOperation, TypeError, ValueError):
            return
        if not size.is_finite() or size < 0:
            return

        reported_side = item.get("side")
        side = {"Buy": "long", "Sell": "short"}.get(
            reported_side if isinstance(reported_side, str) else "", "flat"
        )
        if size == 0:
            side = "flat"

        async with self._session_factory() as session:
            sessions = await LiveSignalSessionRepository(session).list_active_by_account(
                self._account_id
            )
        if not sessions:
            return

        for live_session in sessions:
            if to_bybit_raw_symbol(live_session.symbol) != symbol:
                continue
            try:
                await self._redis.delete(f"qb_pos_snapshot:{live_session.id}")
            except Exception as exc:
                logger.warning(
                    "position_snapshot_cache_delete_failed session=%s err=%s",
                    live_session.id,
                    exc,
                )

        now = self._clock()
        if now - self._last_published_at.get(symbol, float("-inf")) < self._min_interval_s:
            return
        self._last_published_at[symbol] = now
        await publish_realtime(
            self._user_id,
            "position_update",
            {"symbol": symbol, "side": side, "size": str(size)},
        )


class PrivateTopicRouter(MessageEventHandler):
    """private stream topic별 handler를 분리한다."""

    def __init__(
        self,
        *,
        account_id: UUID,
        state_handler: StateHandler,
        position_handler: PositionFanoutHandler,
    ) -> None:
        self._account_id = account_id
        self._state_handler = state_handler
        self._position_handler = position_handler

    async def handle_message(self, msg: dict[str, Any]) -> None:
        topic = msg.get("topic")
        data = msg.get("data")
        items = data if isinstance(data, list) else []
        if topic == "order":
            for item in items:
                try:
                    await self._state_handler.handle_order_event(self._account_id, item)
                except Exception as exc:
                    logger.warning("ws_handler_failed account=%s err=%s", self._account_id, exc)
            return
        if topic == "position":
            for item in items:
                try:
                    await self._position_handler.handle_position_event(item)
                except Exception as exc:
                    logger.warning("position_handler_failed account=%s err=%s", self._account_id, exc)
            return
        if msg.get("op") == "subscribe" and msg.get("success") is False:
            logger.warning("ws_subscribe_rejected account=%s msg=%s", self._account_id, msg)
            qb_ws_subscribe_rejected_total.labels(account_id=str(self._account_id)).inc()
