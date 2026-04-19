"""백테스트 엔진 타입 정의."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

import pandas as pd

from src.strategy.pine import ParseOutcome, PineError


@dataclass(frozen=True)
class BacktestConfig:
    """vectorbt Portfolio.from_signals() 호출 파라미터."""

    init_cash: Decimal = Decimal("10000")
    fees: float = 0.001        # 0.1%
    slippage: float = 0.0005   # 0.05%
    freq: str = "1D"           # pandas offset alias
    # Sprint 7d: 빈 리스트면 24h. 값은 {"asia","london","ny"} 부분집합.
    # 엔진은 entries를 바 timestamp의 UTC hour로 필터링한다.
    trading_sessions: tuple[str, ...] = ()


@dataclass(frozen=True)
class BacktestMetrics:
    """5개 표준 지표. 금융 수치는 Decimal."""

    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal      # 음수 (-0.25 = -25%)
    win_rate: Decimal          # 0.0 ~ 1.0
    num_trades: int


@dataclass(frozen=True)
class RawTrade:
    """엔진 레벨 trade 레코드. vectorbt records_readable → 도메인 중립 DTO.

    bar_index는 유지 (service layer에서 ohlcv.index로 datetime 변환).
    """

    trade_index: int
    direction: Literal["long", "short"]
    status: Literal["open", "closed"]
    entry_bar_index: int
    exit_bar_index: int | None
    entry_price: Decimal
    exit_price: Decimal | None
    size: Decimal
    pnl: Decimal
    return_pct: Decimal
    fees: Decimal


@dataclass(frozen=True)
class BacktestResult:
    """백테스트 실행 결과."""

    metrics: BacktestMetrics
    equity_curve: pd.Series
    trades: list[RawTrade] = field(default_factory=list)    # Sprint 4 신규
    config_used: BacktestConfig = field(default_factory=BacktestConfig)


@dataclass
class BacktestOutcome:
    """run_backtest() 공개 반환 타입. ParseOutcome을 래핑."""

    status: Literal["ok", "unsupported", "error", "parse_failed"]
    parse: ParseOutcome
    result: BacktestResult | None = None
    error: PineError | str | None = None
