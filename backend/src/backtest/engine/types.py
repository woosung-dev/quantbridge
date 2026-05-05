"""백테스트 엔진 타입 정의."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

import pandas as pd

from src.strategy.pine import ParseOutcome, PineError


@dataclass(frozen=True)
class BacktestConfig:
    """엔진 실행 설정 (pine_v2 path는 vectorbt 의존 없이 직접 PnL 계산).

    Sprint 31 BL-156: leverage / include_funding 추가 — 응답 노출 (FE
    AssumptionsCard) 와 PRD `backtests.config` JSONB 5 가정 정합. 현재
    pine_v2 엔진은 leverage 를 PnL 에 적용하지 않음 (qty 가 절대 수량 →
    notional / capital 비율로 자연 노출). leverage 는 *명시적 가정* 으로
    응답에 노출하여 사용자가 MDD/total_return 을 해석할 때 참고하도록 함.
    """

    init_cash: Decimal = Decimal("10000")
    fees: float = 0.001        # 0.1%
    slippage: float = 0.0005   # 0.05%
    freq: str = "1D"           # pandas offset alias
    # Sprint 7d: 빈 리스트면 24h. 값은 {"asia","london","ny"} 부분집합.
    # 엔진은 entries를 바 timestamp의 UTC hour로 필터링한다.
    trading_sessions: tuple[str, ...] = ()
    # Sprint 31 BL-156: 응답 노출용 가정 — 현재 pine_v2 엔진 PnL 계산엔 미적용.
    # leverage=1.0 default = 현물 가정. >1.0 시 사용자가 자본 대비 손실 한계
    # 를 100% 초과로 해석할 수 있도록 응답에 노출.
    leverage: float = 1.0
    # 무기한 선물 funding 비용 — 현재 미반영 (future hook).
    include_funding: bool = False


@dataclass(frozen=True)
class BacktestMetrics:
    """표준 지표. 금융 수치는 Decimal. 신규 필드는 None=미추출 또는 NaN.

    Sprint 30 gamma-BE: 12 → 24 필드 확장 (PRD `backtests.results` JSONB 정합).
    신규 12 필드는 모두 Optional default None → backward-compat
    (Sprint 28 이전 backtest round-trip 안전).
    """

    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal      # 음수 (-0.25 = -25%)
    win_rate: Decimal          # 0.0 ~ 1.0
    num_trades: int
    # 확장 지표 (vectorbt에서 추출; 기존 완료 백테스트는 None)
    sortino_ratio: Decimal | None = None
    calmar_ratio: Decimal | None = None
    profit_factor: Decimal | None = None
    avg_win: Decimal | None = None       # 평균 수익거래 수익률
    avg_loss: Decimal | None = None      # 평균 손실거래 수익률 (음수)
    long_count: int | None = None
    short_count: int | None = None
    # Sprint 30 gamma-BE 신규 12 필드 (PRD spec 정합)
    avg_holding_hours: Decimal | None = None      # 평균 보유 시간 (시간 단위)
    consecutive_wins_max: int | None = None        # 최대 연속 승 횟수
    consecutive_losses_max: int | None = None      # 최대 연속 패 횟수
    long_win_rate_pct: Decimal | None = None       # 0.0 ~ 1.0
    short_win_rate_pct: Decimal | None = None      # 0.0 ~ 1.0
    monthly_returns: list[tuple[str, Decimal]] | None = None  # ("YYYY-MM", return ratio)
    drawdown_duration: int | None = None           # 최대 DD bar 수
    annual_return_pct: Decimal | None = None       # CAGR
    total_trades: int | None = None                # PRD parity (num_trades alias)
    avg_trade_pct: Decimal | None = None
    best_trade_pct: Decimal | None = None
    worst_trade_pct: Decimal | None = None
    drawdown_curve: list[tuple[str, Decimal]] | None = None  # ("YYYY-MM-DDTHH:MM:SSZ", dd_pct)


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
