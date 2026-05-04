"""market_data backfill task — ts.ohlcv hypertable 사전 채우기 (BL-141 Slice 2).

목적: dogfood Day 4-7 D.1 finding (ts.ohlcv 비어있음) 해결. Backtest UI 활성화 시
첫 실행이 60s+ CCXT fetch 대기 없이 cache hit 으로 빠르게 응답.

패턴:
- Celery prefork-safe (Sprint 18 BL-080) — `run_in_worker_loop` + per-task engine + dispose
- 기존 TimescaleProvider 의 advisory lock + gap 재조회 + insert_bulk 패턴 활용
- 신규 코드 최소 — 얇은 wrapper

사용:
    celery -A src.tasks call market_data.backfill_ohlcv \\
        --kwargs '{"symbol": "BTC/USDT", "timeframe": "1h", "period_days": 60}'

또는 `python -m src.tasks.market_data_backfill BTC/USDT 1h 60` (script 실행).
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="market_data.backfill_ohlcv", max_retries=0)  # type: ignore[untyped-decorator]
def backfill_ohlcv_task(
    symbol: str,
    timeframe: str,
    period_days: int,
) -> dict[str, object]:
    """Sync Celery task — Sprint 28 Slice 2 BL-141.

    Args:
        symbol: 거래쌍 (예: "BTC/USDT").
        timeframe: 타임프레임 (예: "1h", "5m").
        period_days: now 부터 거슬러 올라갈 일수 (예: 60 = 60일치).

    Returns:
        dict — symbol/timeframe/rows_written/duration_s/period_start/period_end.

    Worker pool 제약: prefork only (§2.4). gevent/eventlet 비호환.

    P1 fix (idempotency): TimescaleProvider 의 PRIMARY KEY (time, symbol, timeframe)
    가 자연 dedup. 동일 task 두 번 실행 시 두 번째 호출은 0 row 추가 (gap 0).

    P1 fix (lock contention): TimescaleProvider 의 advisory lock 은 트랜잭션
    종료 시 자동 해제. LiveSession dispatch 가 동시 동일 (symbol, tf) fetch 시 lock 대기 →
    backfill 완료 후 다음 주기에서 정상 진행. (Sprint 11 LESSON-008 Beat scheduler skip
    pattern 정합)
    """
    from src.tasks._worker_loop import run_in_worker_loop

    started = time.monotonic()
    result = run_in_worker_loop(_async_backfill(symbol, timeframe, period_days))
    result["duration_s"] = round(time.monotonic() - started, 2)
    return result


async def _async_backfill(
    symbol: str,
    timeframe: str,
    period_days: int,
) -> dict[str, object]:
    """Worker entry — TimescaleProvider.get_ohlcv() wrapping.

    engine + sessionmaker 는 task 단위로 생성 + finally dispose (Sprint 17 패턴).
    """
    from src.tasks.backtest import create_worker_engine_and_sm  # 재사용

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            from src.market_data.providers.ccxt import CCXTProvider
            from src.market_data.providers.timescale import TimescaleProvider
            from src.market_data.repository import OHLCVRepository

            repo = OHLCVRepository(session)

            # row count BEFORE
            from sqlalchemy import func, select

            from src.market_data.models import OHLCV

            count_stmt = (
                select(func.count())
                .select_from(OHLCV)
                .where(
                    OHLCV.symbol == symbol,  # type: ignore[arg-type]
                    OHLCV.timeframe == timeframe,  # type: ignore[arg-type]
                )
            )
            rows_before = (await session.execute(count_stmt)).scalar_one()

            # Period: [now - period_days, now]
            now = datetime.now(UTC)
            period_start = now - timedelta(days=period_days)
            period_end = now

            ccxt = CCXTProvider()  # default settings
            provider = TimescaleProvider(repo, ccxt, exchange_name="bybit")

            # cache-first fetch — gap 만 CCXT fetch + insert_bulk + commit
            df = await provider.get_ohlcv(symbol, timeframe, period_start, period_end)

            # row count AFTER
            rows_after = (await session.execute(count_stmt)).scalar_one()
            rows_written = rows_after - rows_before

            logger.info(
                "backfill_complete symbol=%s tf=%s period_days=%s rows_written=%s df_len=%s",
                symbol,
                timeframe,
                period_days,
                rows_written,
                len(df),
            )

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "rows_written": rows_written,
                "df_len": len(df),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            }
    finally:
        await engine.dispose()
