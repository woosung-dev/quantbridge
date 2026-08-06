"""백테스트 엔진 타입 정의."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

import pandas as pd

from src.strategy.pine import ParseOutcome, PineError
from src.strategy.pine_v2.exit_orders import ExitOrderKind


@dataclass(frozen=True)
class BacktestConfig:
    """엔진 실행 설정 (pine_v2 가 bar-by-bar 로 PnL 을 직접 계산한다).

    Sprint 31 BL-156: leverage / include_funding 추가 — 응답 노출 (FE
    AssumptionsCard) 와 PRD `backtests.config` JSONB 5 가정 정합. 현재
    pine_v2 엔진은 leverage 를 PnL 에 적용하지 않음 (qty 가 절대 수량 →
    notional / capital 비율로 자연 노출). leverage 는 *명시적 가정* 으로
    응답에 노출하여 사용자가 MDD/total_return 을 해석할 때 참고하도록 함.
    """

    init_cash: Decimal = Decimal("10000")
    # C8 (선물형 비용모델): `fees` = taker 수수료. pine_v2 엔진의 모든 체결은
    # 시장가·트리거(taker)이므로 `fees` 가 전 체결에 적용된다(slippage 동일).
    # maker(resting post-only limit) 체결은 limit/strategy.exit H2 NOP(BL-098/BL-104)
    # 라 producer 가 없어 비용모델상 미존재 → `maker_fee` config 는 실 producer
    # (BL-104) 도입 시 추가. 비용 공식 SSOT 는 v2_adapter._leg_cost.
    fees: float = 0.001  # 0.1% (taker)
    slippage: float = 0.0005  # 0.05% (taker market/stop 에만 적용; limit 제외)
    # BL-104 — strategy.exit TP(resting limit) producer 도입 → maker 체결 활성.
    # maker_fee 는 TP exit leg 에만 적용 + slippage 면제(limit). taker(SL/Trail/
    # entry/market) 는 fees 사용. exit_kind 미태그 trade 는 전부 taker → 회귀 0.
    maker_fee: float = 0.0002  # 0.02% (maker; TP limit 체결)
    freq: str = "1D"  # pandas offset alias
    # Sprint 7d: 빈 리스트면 24h. 값은 {"asia","london","ny"} 부분집합.
    # 엔진은 entries를 바 timestamp의 UTC hour로 필터링한다.
    trading_sessions: tuple[str, ...] = ()
    # Sprint 31 BL-156: 응답 노출용 가정 — 현재 pine_v2 엔진 PnL 계산엔 미적용.
    # leverage=1.0 default = 현물 가정. >1.0 시 사용자가 자본 대비 손실 한계
    # 를 100% 초과로 해석할 수 있도록 응답에 노출.
    leverage: float = 1.0
    # 무기한 선물 funding 비용 — include_funding=True 이고 worker 경로가 funding_rates 를
    # 제공하면 8h 정산 경계마다 차감한다(SSOT: v2_adapter._funding_cost_by_bar).
    include_funding: bool = False
    # TV parity — 시장가 체결 타이밍. "bar_close"(기본, 신호 bar 종가 즉시 — 기존
    # 동작 byte-identical) | "next_bar_open"(다음 bar 시가 — TV
    # process_orders_on_close=false 기본. golden/trust-layer 는 기본값이라 무영향).
    fill_timing: Literal["bar_close", "next_bar_open"] = "bar_close"
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
    # Sprint 51 BL-220 — pine_v2 strategy input override (Param Stability grid sweep).
    # key = pine input declaration var_name (InputDecl.var_name, ast_extractor.py:60-65).
    # value = override value. type union = Decimal/int/bool/str (input.float/int/bool/string 4종).
    # None default = 회귀 0 (기존 backtest path 변경 X).
    # codex G.0 P1#4: frozen dataclass 만으론 runtime type reject 불가 → __post_init__ 검증.
    # codex Slice 1 review P1: frozen dataclass + mutable dict 는 caller mutation
    # 으로 stale validation bypass 가능 → __post_init__ 에서 방어 복사 + MappingProxyType lock.
    # Mapping (read-only interface) 으로 typed → 외부 mutation 차단.
    input_overrides: Mapping[str, Decimal | int | bool | str] | None = None

    def __post_init__(self) -> None:
        # Sprint 51 BL-220 codex G.0 P1#4 — input_overrides value type runtime reject.
        # codex Slice 1 review P1 — 검증 후 dict 방어 복사 + MappingProxyType lock.
        if self.input_overrides is not None:
            for key, value in self.input_overrides.items():
                # bool 은 int 의 subclass 라 isinstance(True, int) == True. 명시적 union 으로 가독성 확보.
                if not isinstance(value, (Decimal, bool, int, str)):
                    raise ValueError(
                        f"input_overrides[{key!r}] must be Decimal/int/bool/str, "
                        f"got {type(value).__name__}"
                    )
            # 방어 복사 + MappingProxyType lock (frozen dataclass 라 object.__setattr__ 우회).
            object.__setattr__(
                self,
                "input_overrides",
                MappingProxyType(dict(self.input_overrides)),
            )


@dataclass(frozen=True)
class SideMetrics:
    """long/short 한쪽 방향의 절대금액 통계 (closed only, TV parity)."""

    net_profit_abs: Decimal
    gross_profit_abs: Decimal
    gross_loss_abs: Decimal  # 양수 크기 (TV UI 음수 표기는 FE 책임)
    profit_factor: Decimal | None  # gross_loss 0 → None
    avg_trade_abs: Decimal | None


@dataclass(frozen=True)
class PerSideMetrics:
    """방향별 분리 팩 — 해당 방향 closed 0건이면 그 쪽 None."""

    long: SideMetrics | None
    short: SideMetrics | None


@dataclass(frozen=True)
class ExcursionStats:
    """equity run-up/drawdown 통계 팩 (TV "주식 시장의 상승과 하락" parity).

    에피소드 규약(우리 정의, hand-oracle 로 고정 — TV 미공개라 "TV 근사"):
    - drawdown 에피소드 = running peak 아래 연속 bar 구간(회복 bar 미포함).
    - run-up 에피소드 = running trough 위 연속 bar 구간(신저점 bar 에서 종료).
    - `_intrabar` 변형 = bar high/low 로 mark 한 equity 극값 근사(낙관 근사 —
      복수 포지션 동시 극값 미보장). FE 는 "(bar 근사)" 라벨 의무.
    - days = bars * bar 간격(equity index 중앙값 간격 기준).
    """

    max_runup_abs: Decimal | None = None
    max_runup_pct: Decimal | None = None  # 분모 = 에피소드 시작 trough equity
    avg_runup_abs: Decimal | None = None
    avg_runup_duration_bars: Decimal | None = None
    avg_runup_duration_days: Decimal | None = None
    avg_drawdown_abs: Decimal | None = None
    avg_drawdown_duration_bars: Decimal | None = None
    avg_drawdown_duration_days: Decimal | None = None
    max_drawdown_abs: Decimal | None = None  # 절대금액 (기존 max_drawdown ratio 보완)
    max_drawdown_recovery_bars: int | None = None  # MDD trough → 직전 peak 회복. 미회복 None
    max_drawdown_recovery_days: Decimal | None = None
    max_runup_intrabar_abs: Decimal | None = None
    max_runup_intrabar_pct: Decimal | None = None
    max_drawdown_intrabar_abs: Decimal | None = None
    max_drawdown_intrabar_pct: Decimal | None = None


@dataclass(frozen=True)
class BacktestMetrics:
    """표준 지표. 금융 수치는 Decimal. 신규 필드는 None=미추출 또는 NaN.

    필드 수의 SSOT 는 dataclass + `tests/backtest/test_metrics_field_parity.py`
    tripwire 이다. 선택 필드는 default None 으로 구 backtest round-trip 호환을
    유지한다.

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
    # 확장 지표 — **pine_v2 가 직접 계산해서 채운다**(`v2_adapter._build_metrics`).
    # `None` 은 죽은 경로라서가 아니라 **이 필드가 생기기 전에 완료된 백테스트 행**의
    # round-trip 호환용 기본값이다.
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
    # 구 vectorbt 경로 (extract_metrics) 는 ohlcv 미수신 → 항상 None 이었다.
    buy_and_hold_curve: list[tuple[str, Decimal]] | None = None
    # C14 (정직성 번들) — 헤드라인 net 표시용 총비용 분해. total_fees=순수 수수료,
    # total_slippage=순수 슬리피지. RawTrade.fees(결합) 와의 불변식:
    #   total_fees + total_slippage == Σ RawTrade.fees.
    # 기존 완료 backtest round-trip 호환 위해 None default.
    total_fees: Decimal | None = None
    total_slippage: Decimal | None = None
    # C6 (정직성 번들 Slice 4) — perp funding 차감 시 보유 구간 일부가 funding 데이터
    # 가용 범위(인제스션 forward-only) 밖이면 True. include_funding=false 또는 funding
    # 미전달 시 None(미반영) → 기존 완료 backtest round-trip 호환.
    funding_data_incomplete: bool | None = None
    # funding 총액. 양수=지불(equity 감소), 음수=수취. None=미반영, 0=반영했으나 정산 0건.
    total_funding: Decimal | None = None
    # --- TV Strategy Tester parity 팩 (전부 optional 꼬리 추가 — 구 backtest
    # round-trip 호환. 4-site 동시 수정은 test_metrics_field_parity tripwire 가 강제) ---
    # 절대금액 계열 (closed net pnl 기준, Decimal 정확 합산).
    net_profit_abs: Decimal | None = None
    gross_profit_abs: Decimal | None = None
    gross_loss_abs: Decimal | None = None  # 양수 크기
    # 미실현 PnL — open trades 의 (last_close - entry)*qty*sign - 비용. open 0건 = 0,
    # ohlcv 미전달 시 None.
    open_pnl: Decimal | None = None
    largest_win_abs: Decimal | None = None
    largest_loss_abs: Decimal | None = None  # 음수 그대로. 손실 0건 → None
    avg_trade_abs: Decimal | None = None  # TV "기대 수익(expectancy)" 와 동일값 — FE 라벨 처리
    avg_win_abs: Decimal | None = None
    avg_loss_abs: Decimal | None = None
    ratio_avg_win_loss: Decimal | None = None  # avg_win_abs / |avg_loss_abs|
    total_open_trades: int | None = None
    avg_bars_in_trade: Decimal | None = None  # closed only
    avg_bars_in_winning_trades: Decimal | None = None
    avg_bars_in_losing_trades: Decimal | None = None
    # nested 팩 2종 — site 당 1 key 로 4-site 부담 압축.
    per_side: PerSideMetrics | None = None
    excursion_stats: ExcursionStats | None = None
    # TV Sharpe 컨벤션. tv_monthly_rfr2 / tv_daily_rfr2 / unavailable /
    # None=구 실행.
    sharpe_convention: str | None = None
    # 격리 레버리지 모델 적용 결과. leverage<=1 이면 항상 None.
    liquidation_occurred: bool | None = None
    liquidation_count: int | None = None


@dataclass(frozen=True)
class RawTrade:
    """엔진 레벨 trade 레코드. 구 vectorbt records_readable 을 대체한 도메인 중립 DTO.

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
    # BL-104 — exit leg 종류 (TP/SL/Trailing). maker/taker 비용 라우팅 입력.
    # None = market close/flip/open → taker (byte-identical).
    exit_kind: ExitOrderKind | None = None
    # --- TV Trades parity 확장 (전부 optional 꼬리 추가 — frozen dataclass
    # additive-safe + trust-layer trades digest(명시적 11-필드) 불변) ---
    # run-up(MFE)/drawdown(MAE): 보유 구간 bar high/low 기반 gross(수수료 미차감)
    # 가격 excursion. 스캔 윈도 = (entry_bar, exit_bar] — entry bar 는 종가 체결
    # 이전 고저가 미보유 구간이라 제외, exit bar 는 full 포함(bar 근사, "TV 근사").
    # pct 분모 = entry notional (return_pct 규약 동일). ohlcv 미전달 시 None.
    runup_abs: Decimal | None = None
    runup_pct: Decimal | None = None
    drawdown_abs: Decimal | None = None
    drawdown_pct: Decimal | None = None
    bars_in_trade: int | None = None  # exit_bar - entry_bar (closed only)
    # 비용 분해 — 불변식: fee_paid + slippage_paid == fees (결합 필드 유지).
    fee_paid: Decimal | None = None
    slippage_paid: Decimal | None = None
    comment: str | None = None  # Pine strategy.entry comment ("" → None)
    cumulative_pnl: Decimal | None = None  # trade_index(entry 순) net pnl 누적
    liquidated: bool | None = None  # 격리 강제청산으로 종료된 거래.


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
