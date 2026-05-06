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
    fees: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    freq: str = "1D"  # pandas offset alias
    # Sprint 7d: 빈 리스트면 24h. 값은 {"asia","london","ny"} 부분집합.
    # 엔진은 entries를 바 timestamp의 UTC hour로 필터링한다.
    trading_sessions: tuple[str, ...] = ()
    # Sprint 31 BL-156: 응답 노출용 가정 — 현재 pine_v2 엔진 PnL 계산엔 미적용.
    # leverage=1.0 default = 현물 가정. >1.0 시 사용자가 자본 대비 손실 한계
    # 를 100% 초과로 해석할 수 있도록 응답에 노출.
    leverage: float = 1.0
    # 무기한 선물 funding 비용 — 현재 미반영 (future hook).
    include_funding: bool = False
    # Sprint 37 BL-188a — 폼 입력 default_qty (Pine 미명시 시 사용).
    # priority chain: Pine strategy(default_qty_type=...) > 폼 입력 > None (qty=1.0 fallback).
    # None 시 기존 동작 (qty=1.0 hardcode 호환).
    default_qty_type: str | None = None
    default_qty_value: float | None = None
    # Sprint 38 BL-188 v3 — Live Settings mirror (1x equity-basis only) 결과 입력.
    # codex G.0 iter 1+2 [P1] must-fix 1 (canonical 단일화) + #4 (D2 manual override).
    # service.py:_resolve_sizing_canonical 이 결정한 4-tier chain 결과:
    #   Pine 명시 > 폼 manual > Live mirror (1x only) > fallback (qty=1.0)
    # live_position_size_pct 명시 시 compat.parse_and_run_v2 가
    # `("strategy.percent_of_equity", live_pct)` 로 configure_sizing 호출.
    # leverage_basis 는 항상 1.0 (Sprint 38 = Nx reject. BL-186 후 unlock).
    live_position_size_pct: float | None = None
    sizing_source: Literal["pine", "live", "form", "fallback"] = "fallback"
    sizing_basis: Literal[
        "pine_native",
        "live_available_balance_approx_equity",
        "form_equity",
        "fallback_qty1",
    ] = "fallback_qty1"
    leverage_basis: float = 1.0


@dataclass(frozen=True)
class BacktestMetrics:
    """표준 지표. 금융 수치는 Decimal. 신규 필드는 None=미추출 또는 NaN.

    Sprint 30 gamma-BE: 12 → 24 필드 확장 (PRD `backtests.results` JSONB 정합).
    신규 12 필드는 모두 Optional default None → backward-compat
    (Sprint 28 이전 backtest round-trip 안전).

    Sprint 32-D BL-156 — MDD 수학 정합 메타 추가:
      - max_drawdown 의미: equity 시리즈 기준 ratio. 분모 = running peak equity,
        분자 = (현재 equity - peak). leverage=1.0 (현물) 가정 하에서는 수학적으로
        [-1.0, 0.0] 범위. 그러나 pine_v2 엔진은 leverage 를 PnL 에 직접 적용하지
        않고 (qty 가 절대 수량), 사용자가 큰 size 거래 시 equity 가 음수 → MDD
        < -1.0 (자본 100% 초과 손실) 시나리오 발생 가능. 이 경우 leverage 가정
        없이는 수학 모순 → 응답에 명시적으로 표시 (mdd_exceeds_capital).
    """

    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal  # 음수 (-0.25 = -25%). leverage=1 시 [-1.0, 0.0].
    win_rate: Decimal  # 0.0 ~ 1.0
    num_trades: int
    # 확장 지표 (vectorbt에서 추출; 기존 완료 백테스트는 None)
    sortino_ratio: Decimal | None = None
    calmar_ratio: Decimal | None = None
    profit_factor: Decimal | None = None
    avg_win: Decimal | None = None  # 평균 수익거래 수익률
    avg_loss: Decimal | None = None  # 평균 손실거래 수익률 (음수)
    long_count: int | None = None
    short_count: int | None = None
    # Sprint 30 gamma-BE 신규 12 필드 (PRD spec 정합)
    avg_holding_hours: Decimal | None = None  # 평균 보유 시간 (시간 단위)
    consecutive_wins_max: int | None = None  # 최대 연속 승 횟수
    consecutive_losses_max: int | None = None  # 최대 연속 패 횟수
    long_win_rate_pct: Decimal | None = None  # 0.0 ~ 1.0
    short_win_rate_pct: Decimal | None = None  # 0.0 ~ 1.0
    monthly_returns: list[tuple[str, Decimal]] | None = None  # ("YYYY-MM", return ratio)
    drawdown_duration: int | None = None  # 최대 DD bar 수
    annual_return_pct: Decimal | None = None  # CAGR
    total_trades: int | None = None  # PRD parity (num_trades alias)
    avg_trade_pct: Decimal | None = None
    best_trade_pct: Decimal | None = None
    worst_trade_pct: Decimal | None = None
    drawdown_curve: list[tuple[str, Decimal]] | None = None  # ("YYYY-MM-DDTHH:MM:SSZ", dd_pct)
    # Sprint 32-D BL-156 — MDD 수학 정합 메타.
    # max_drawdown 단위 ("equity 기준 %"). 향후 다른 단위 (USDT 등) 추가 시 변경.
    mdd_unit: str | None = None
    # MDD 가 -100% (= -1.0) 미만 = 자본 100% 초과 손실 시나리오. leverage > 1.0
    # 가정 하에서만 수학적으로 가능. False = 정상 [-1.0, 0.0] 범위.
    mdd_exceeds_capital: bool | None = None
    # Sprint 34 BL-175 — Buy & Hold benchmark curve (정확 OHLCV 가격 기반).
    #
    # 정의: init_cash * (close[i] / close[0]) — Backtest 의 initial_capital 을
    # 첫 bar close 가격에 매수 후 끝 bar close 가격까지 보유 시의 자본 곡선.
    # equity_curve 와 timestamp 1:1 align. ("YYYY-MM-DDTHH:MM:SSZ", value).
    #
    # **fail-closed 정책 (P1-3):** OHLCV close 1건이라도 NaN/<=0 시 None 반환
    # → frontend BH series 미렌더 + ChartLegend BH 항목 자동 hide. 거짓 trust
    # 차단 (Surface Trust ADR-019). partial silent line 금지.
    #
    # vectorbt 경로 (extract_metrics) 는 ohlcv 미수신 → 항상 None.
    buy_and_hold_curve: list[tuple[str, Decimal]] | None = None


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
    trades: list[RawTrade] = field(default_factory=list)  # Sprint 4 신규
    config_used: BacktestConfig = field(default_factory=BacktestConfig)


@dataclass
class BacktestOutcome:
    """run_backtest() 공개 반환 타입. ParseOutcome을 래핑."""

    status: Literal["ok", "unsupported", "error", "parse_failed"]
    parse: ParseOutcome
    result: BacktestResult | None = None
    error: PineError | str | None = None
