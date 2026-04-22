"""백테스트 엔진 공개 API.

pine_v2 엔진 기반으로 마이그레이션됨 — `run_backtest` 는 `v2_adapter.run_backtest_v2`
로 위임한다. 구 Pine 인터프리터 + vectorbt 경로는 제거.

Trading session 헬퍼 (`_build_session_hour_mask` / `_apply_trading_sessions`) 는
기존 test/호환성을 위해 legacy 모듈로 유지된다 — 하지만 v2 경로 실행 흐름엔
사용되지 않는다. 다음 sprint 에서 pine_v2 경로에도 동일 필터 로직을 통합
예정.
"""

from __future__ import annotations

import pandas as pd

from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
    RawTrade,
)
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine.types import SignalResult
from src.strategy.trading_sessions import SESSION_UTC_HOURS, TradingSession

run_backtest = run_backtest_v2


def _build_session_hour_mask(index: pd.DatetimeIndex, sessions: tuple[str, ...]) -> pd.Series:
    """True인 바만 entry 허용. UTC hour로 평가.

    입력 index가 naïve면 UTC로 간주 (localize). tz-aware면 UTC로 convert.
    알 수 없는 세션 이름은 무시 (schema 레이어에서 이미 검증).

    Legacy — pine_v2 경로로 마이그레이션된 이후 v1 은 사용하지 않는다.
    다음 sprint 에서 Trade 사후 필터로 재도입 예정.
    """
    hours = index.tz_localize("UTC").hour if index.tz is None else index.tz_convert("UTC").hour

    allowed = [False] * 24
    for name in sessions:
        try:
            session = TradingSession(name)
        except ValueError:
            continue
        start, end = SESSION_UTC_HOURS[session]
        for h in range(start, end):
            allowed[h] = True
    mask_values = [allowed[h] for h in hours]
    return pd.Series(mask_values, index=index)


def _apply_trading_sessions(signal: SignalResult, sessions: tuple[str, ...]) -> None:
    """Mask signal.entries in place by the session hour-of-day filter.

    exits는 그대로 둔다 — 세션 밖에도 청산은 허용해야 포지션 관리가 깨지지 않는다.

    Legacy — pine_v2 경로로 마이그레이션된 이후 v1 은 사용하지 않는다.
    """
    if not isinstance(signal.entries.index, pd.DatetimeIndex):
        return
    mask = _build_session_hour_mask(signal.entries.index, sessions)
    signal.entries = signal.entries & mask


__all__ = [
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestResult",
    "RawTrade",
    "run_backtest",
]
