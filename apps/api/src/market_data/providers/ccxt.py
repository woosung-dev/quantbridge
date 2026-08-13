"""CCXTProvider — raw OHLCV fetch from exchange (pagination + tenacity 재시도)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import ccxt.async_support as ccxt_async
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.market_data.constants import TIMEFRAME_SECONDS

logger = logging.getLogger(__name__)


class CCXTProvider:
    """CCXT raw OHLCV fetch — pagination + tenacity 재시도 + lifecycle 관리.

    TimescaleProvider가 gap 구간을 채울 때 내부 호출. FastAPI lifespan 또는
    Celery worker_shutdown에서 close()로 리소스 해제.

    Event loop 인식: Celery prefork worker 는 task 마다 `asyncio.run()` 으로 새 loop 를
    만들기 때문에 한 번 생성된 exchange(aiohttp ClientSession)는 이전 loop 에 bound 되어
    다음 task 에서 "Event loop is closed" 로 실패한다. 매 호출 시점에 현재 loop 을 확인해
    loop 변경을 감지하면 exchange 를 투명하게 재생성한다 (Sprint 9-2 D1 후속 fix).
    """

    def __init__(self, exchange_name: str = "bybit") -> None:
        self.exchange_name = exchange_name
        self._exchange: Any | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _build_exchange(self) -> Any:
        cls = getattr(ccxt_async, self.exchange_name)
        return cls(
            {
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {"defaultType": "spot"},
            }
        )

    @property
    def exchange(self) -> Any:
        """현재 event loop 에 bound 된 exchange 반환. loop 변경 시 재생성.

        이전 loop 에 bound 된 exchange 는 close() 호출이 불가능하므로 그대로 폐기.
        aiohttp 가 "Unclosed client session" 경고를 낼 수 있으나 loop 가 이미 닫힌
        상태라 session cleanup 자체가 무의미.
        """
        current_loop = asyncio.get_event_loop()
        if self._exchange is None or self._loop is not current_loop:
            self._exchange = self._build_exchange()
            self._loop = current_loop
        return self._exchange

    async def close(self) -> None:
        """리소스 해제 — lifespan 종료 또는 worker_shutdown에서 호출.

        현재 loop 에 bound 된 exchange 만 close. 이전 loop 에 bound 된 exchange 는
        loop 자체가 닫혔으므로 close 호출 불가 — skip.
        """
        if self._exchange is None:
            return
        try:
            current_loop = asyncio.get_event_loop()
        except RuntimeError:
            return
        if self._loop is current_loop:
            await self._exchange.close()
        self._exchange = None
        self._loop = None

    @retry(
        retry=retry_if_exception_type(
            (
                ccxt_async.NetworkError,
                ccxt_async.RateLimitExceeded,
                ccxt_async.ExchangeNotAvailable,
            )
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _fetch_page(
        self, symbol: str, timeframe: str, since_ms: int, limit: int
    ) -> list[list[Any]]:
        result = await self.exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        return list(result)  # ccxt는 list[list[float|int]] 반환 (type stub 없음)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: datetime | None = None,
        until: datetime | None = None,
        max_pages: int = 1000,
        *,
        limit_bars: int | None = None,
    ) -> list[list[Any]]:
        """전체 범위 fetch — pagination + 중복 제거 + closed bar 필터.

        반환: [[timestamp_ms, open, high, low, close, volume], ...]
        진행 중인 현재 bar는 제외 (last_closed_ts 기준).

        모드:
        - 범위 모드 (legacy): `since` + `until` 직접 지정. backtest gap 채우기 등.
        - limit_bars 모드 (Sprint 26 B.3, codex P1 #6): 최근 N 개 closed bar.
          ccxt `since=None` 동작이 exchange-specific 이고 현재 진행 bar 가
          섞일 수 있어 `since = now - (limit_bars + 2) * tf` 로 자동 계산하고
          마지막 `limit_bars` 개만 slice 반환. `since`/`until` 동시 지정 시
          무시 + WARN log.
        """
        tf_sec = TIMEFRAME_SECONDS[timeframe]

        # limit_bars 모드 — since/until 자동 계산 (codex P1 #6)
        if limit_bars is not None:
            if since is not None or until is not None:
                logger.warning(
                    "ccxt_fetch_limit_bars_overrides_since_until",
                    extra={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "limit_bars": limit_bars,
                    },
                )
            now = datetime.now(UTC)
            # +2 buffer: 진행 중 bar 1개 + exchange clock skew safety 1개
            since = now - timedelta(seconds=(limit_bars + 2) * tf_sec)
            until = now

        if since is None or until is None:
            raise ValueError(
                "fetch_ohlcv: 'since'+'until' 또는 'limit_bars' 중 하나는 필수"
            )

        now_ts = int(datetime.now(UTC).timestamp())
        last_closed_ts = (now_ts // tf_sec) * tf_sec - tf_sec
        actual_until_ms = min(int(until.timestamp() * 1000), last_closed_ts * 1000)

        since_ms = int(since.timestamp() * 1000)
        all_bars: list[list[Any]] = []
        seen_timestamps: set[int] = set()
        page_count = 0
        limit = 1000

        while since_ms <= actual_until_ms and page_count < max_pages:
            page = await self._fetch_page(symbol, timeframe, since_ms, limit)
            if not page:
                break

            new_bars = [b for b in page if b[0] not in seen_timestamps and b[0] <= actual_until_ms]
            if not new_bars:
                break

            all_bars.extend(new_bars)
            seen_timestamps.update(b[0] for b in new_bars)

            last_ts = new_bars[-1][0]
            since_ms = last_ts + tf_sec * 1000
            page_count += 1

            # 보수적 throttle (exchange 정책 대응, 테스트에서는 mock)
            await asyncio.sleep(0.1)

        if page_count >= max_pages:
            logger.warning(
                "ccxt_fetch_max_pages_reached",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "pages": page_count,
                },
            )

        # limit_bars 모드 — 마지막 N 개만 slice (over-fetch 정상화)
        if limit_bars is not None and len(all_bars) > limit_bars:
            all_bars = all_bars[-limit_bars:]

        return all_bars
