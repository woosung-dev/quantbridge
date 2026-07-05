"""pine_v2 → BacktestOutcome 어댑터.

`parse_and_run_v2` 가 반환하는 `V2RunResult` (Track S/A/M) 의 `StrategyState`
를 기존 엔진이 기대하는 `BacktestOutcome(BacktestResult(metrics, equity,
trades))` 형태로 변환한다. vectorbt 는 사용하지 않으며, bar-by-bar 누적 PnL
방식으로 equity curve 를 재구성한다.

Decimal-first 합산 규칙 (CLAUDE.md LESSON) 준수 — 금융 수치는 float 공간에서
합산 후 Decimal 로 바꾸지 않는다. equity 시리즈는 dtype=object 로 Decimal 을
보관하고, Sharpe/DD 같은 근사 지표만 float 으로 변환해 계산한다.
"""

from __future__ import annotations

import bisect
import logging
import math
import re
from decimal import Decimal
from typing import Literal

import pandas as pd

from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
    RawTrade,
)
from src.backtest.exceptions import TradingSessionTzNaiveReject
from src.strategy.pine.types import ParseOutcome, SignalResult
from src.strategy.pine_v2.compat import V2RunResult, parse_and_run_v2
from src.strategy.pine_v2.exit_orders import fill_type_for
from src.strategy.pine_v2.interpreter import PineRuntimeError
from src.strategy.pine_v2.strategy_state import StrategyState, Trade

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)", re.MULTILINE)


def run_backtest_v2(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
    funding_rates: pd.Series | None = None,
) -> BacktestOutcome:
    """pine_v2 엔진으로 Pine 을 실행한 뒤 `BacktestOutcome` 으로 변환.

    실패 분기
    ---------
    - `PineRuntimeError` (bar-level 실행 오류) → status="error". "부분 실행 금지"
      규칙에 따라 silent skip 하지 않는다.
    - `SyntaxError` (pynescript 파싱 실패) → status="parse_failed"
    - `ValueError` (_validate_ohlcv 같은 데이터 오류) → status="error"
    - classify 가 unknown track 반환 (`ValueError` 에 포함) → status="error"
    """
    cfg = config if config is not None else BacktestConfig()

    # Sprint 38 BL-188 v3 A2 — tz-naive sessions-only fail-closed (422).
    # sessions 비어있으면 reject 안 함 (회귀 0). DatetimeIndex 아님 또는 tz=None 시 reject.
    # Live `is_allowed` 가 tz-aware 강제하므로 backtest 도 동일 invariant 유지.
    if cfg.trading_sessions:
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TradingSessionTzNaiveReject(
                detail=(
                    "trading_sessions 활성 시 OHLCV index 가 DatetimeIndex 필수 — "
                    "현재 type: " + type(ohlcv.index).__name__
                )
            )
        if ohlcv.index.tz is None:
            raise TradingSessionTzNaiveReject(
                detail=(
                    "trading_sessions 활성 시 OHLCV index 가 tz-aware 필수 — "
                    "naive index 를 silent UTC 가정으로 처리 시 Live `is_allowed` 와 "
                    "결과 불일치 risk."
                )
            )

    try:
        # strict=True — bar-level PineRuntimeError 를 raise 시켜 상위에서 status=error 로 변환.
        # Sprint 37 BL-185: cfg.init_cash 를 initial_capital 로 전달 → configure_sizing 호출.
        # Sprint 37 BL-188a: cfg.default_qty_type/value (폼 입력) 도 전달.
        # Sprint 38 BL-188 v3 A2: cfg.live_position_size_pct + cfg.trading_sessions 를
        # compat 으로 propagate. priority chain (Pine > form > Live > None) 은
        # compat.parse_and_run_v2 안에서 결정.
        v2 = parse_and_run_v2(
            source,
            ohlcv,
            strict=True,
            initial_capital=float(cfg.init_cash),
            live_position_size_pct=cfg.live_position_size_pct,
            form_default_qty_type=cfg.default_qty_type,
            form_default_qty_value=cfg.default_qty_value,
            sessions_allowed=cfg.trading_sessions,
            # Sprint 51 BL-220 — pine_v2 input override (Param Stability grid sweep).
            # cfg.input_overrides=None 일 때 = 회귀 0 (기존 backtest path 변경 X).
            input_overrides=cfg.input_overrides,
            # TV parity — 시장가 체결 타이밍 (기본 bar_close = 회귀 0).
            fill_timing=cfg.fill_timing,
        )
    except PineRuntimeError as exc:
        logger.info("v2_adapter_runtime_error: %s", exc)
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )
    except SyntaxError as exc:
        logger.info("v2_adapter_parse_failed (syntax): %s", exc)
        return BacktestOutcome(
            status="parse_failed",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )
    except ValueError as exc:
        # 데이터 오류 (empty OHLCV 등) 또는 classify unknown — parse 자체는 성공했을 가능성이 높다.
        logger.info("v2_adapter_data_error: %s", exc)
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )
    except Exception as exc:
        logger.exception("v2_adapter_parse_failed_unexpected")
        return BacktestOutcome(
            status="parse_failed",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )

    state, _errors = _extract_state_and_errors(v2)
    if state is None:
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=f"pine_v2: strategy state 수집 실패 (track={v2.track})",
        )

    try:
        trades = _build_raw_trades(state, cfg)
        # C6 funding accrual 배선 — funding_rates 제공 시 8h 정산 경계 차감 + 결측 flag.
        # flag 는 경량 헬퍼로 1회만 계산(cost 재계산 회피, _compute_equity_curve 시그니처
        # 불변). None = 회귀 0 (기존 동작 byte-identical).
        funding_incomplete = (
            _funding_coverage_incomplete(trades, ohlcv, funding_rates)
            if funding_rates is not None
            else None
        )
        equity = _compute_equity_curve(trades, ohlcv, cfg, funding_rates=funding_rates)
        metrics = _compute_metrics(
            trades, equity, cfg, ohlcv, funding_data_incomplete=funding_incomplete
        )
    except Exception as exc:
        logger.exception("v2_adapter_build_failed")
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )

    result = BacktestResult(
        metrics=metrics,
        equity_curve=equity,
        trades=trades,
        config_used=cfg,
    )
    logger.info(
        "v2_adapter_ok",
        extra={
            "track": v2.track,
            "num_trades": metrics.num_trades,
            "total_return": str(metrics.total_return),
        },
    )
    return BacktestOutcome(
        status="ok",
        # Sprint 23 codex G.2 P1 #2 — strategy.exit NOP 등 state.warnings 전파.
        # 사용자가 silent success 받지 않도록 BacktestOutcome.parse.warnings 노출.
        parse=_stub_parse_outcome(
            source, status="ok", warnings=list(state.warnings) if state else None
        ),
        result=result,
        error=None,
    )


# --- extraction ----------------------------------------------------------


def _extract_state_and_errors(
    v2: V2RunResult,
) -> tuple[StrategyState | None, list[tuple[int, str]]]:
    if v2.track in ("S", "M") and v2.historical is not None:
        return v2.historical.strategy_state, list(v2.historical.errors)
    if v2.track == "A" and v2.virtual is not None:
        return v2.virtual.strategy_state, list(v2.virtual.errors)
    return None, []


# --- cost model ----------------------------------------------------------


def _leg_cost(
    notional: Decimal,
    *,
    fill_type: Literal["taker", "maker"],
    taker_fee: Decimal,
    slippage: Decimal,
    maker_fee: Decimal = Decimal("0"),
) -> tuple[Decimal, Decimal]:
    """단일 체결(leg)의 (수수료, 슬리피지) 비용 — C8 선물형 비용모델 SSOT.

    - taker(시장가·트리거 체결): taker_fee 적용 + slippage 적용.
    - maker(resting post-only limit 체결): maker_fee 적용 + slippage 면제(limit 제외).

    grounding: pine_v2 엔진의 모든 실제 체결은 taker 이다(strategy.entry/close/
    close_all = 시장가 current_close, stop= = 트리거; limit/strategy.exit 은 H2
    NOP, BL-098/BL-104). 따라서 엔진 caller 는 항상 fill_type="taker" 이며 maker_fee
    인자를 전달하지 않는다. maker 분기 + 비용모델은 resting-limit fill producer
    (BL-104) 도입 시 활성될 forward 모델로, 본 helper 단위 테스트가 정확성을 고정.
    본 helper 가 _build_raw_trades / _compute_metrics / _compute_equity_curve 3 경로의
    비용 공식 단일 출처(Slice 1 ponytail 중복 제거).
    """
    if fill_type == "maker":
        return notional * maker_fee, Decimal("0")
    return notional * taker_fee, notional * slippage


# --- trades --------------------------------------------------------------


def _build_raw_trades(state: StrategyState, cfg: BacktestConfig) -> list[RawTrade]:
    all_trades: list[Trade] = list(state.closed_trades) + list(state.open_trades.values())
    # 체결 순서 = entry_bar 오름차순 (같은 bar 면 기존 리스트 순서 유지)
    all_trades.sort(key=lambda t: (t.entry_bar, 0 if t.is_open else 1))

    raw: list[RawTrade] = []
    taker_fee = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    maker_fee = Decimal(str(cfg.maker_fee))
    for idx, t in enumerate(all_trades):
        entry_price = Decimal(str(t.entry_price))
        qty = Decimal(str(t.qty))
        exit_price: Decimal | None = (
            Decimal(str(t.exit_price)) if t.exit_price is not None else None
        )

        # 수수료/슬리피지 = _leg_cost SSOT 위임. 현재 모든 체결 taker (grounding
        # _leg_cost docstring). entry leg 항상 + exit leg 는 closed 만.
        entry_fee, entry_slip = _leg_cost(
            entry_price * qty,
            fill_type="taker",
            taker_fee=taker_fee,
            slippage=slip_rate,
        )
        if exit_price is not None:
            # BL-104 — exit leg fill_type 라우팅: TP=maker(slippage 면제), SL/Trail=taker.
            # exit_kind 미태그(market close/flip) → taker (byte-identical).
            exit_fill = fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"
            exit_fee, exit_slip = _leg_cost(
                exit_price * qty,
                fill_type=exit_fill,
                taker_fee=taker_fee,
                slippage=slip_rate,
                maker_fee=maker_fee,
            )
        else:
            exit_fee = exit_slip = Decimal("0")
        fees_total = entry_fee + exit_fee + entry_slip + exit_slip

        # PnL (수수료 차감 전 원시값 → 수수료 차감)
        if t.pnl is not None:
            gross_pnl = Decimal(str(t.pnl))
        elif exit_price is not None:
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            gross_pnl = (exit_price - entry_price) * qty * direction_sign
        else:
            gross_pnl = Decimal("0")
        net_pnl = gross_pnl - fees_total

        # return_pct = net_pnl / (entry_price * qty)
        notional = entry_price * qty
        return_pct = net_pnl / notional if notional != 0 else Decimal("0")

        raw.append(
            RawTrade(
                trade_index=idx,
                direction=t.direction,
                status="closed" if t.exit_bar is not None else "open",
                entry_bar_index=int(t.entry_bar),
                exit_bar_index=int(t.exit_bar) if t.exit_bar is not None else None,
                entry_price=entry_price,
                exit_price=exit_price,
                size=qty,
                pnl=net_pnl,
                return_pct=return_pct,
                fees=fees_total,
                exit_kind=t.exit_kind,
            )
        )
    return raw


# --- equity curve --------------------------------------------------------


def _funding_coverage_incomplete(
    trades: list[RawTrade], ohlcv: pd.DataFrame, funding_rates: pd.Series
) -> bool:
    """funding 데이터가 보유 구간을 완전히 포괄하는지 — 결측 시 True (0 묵살 금지).

    보유 구간 = [최초 entry bar, 최종 exit bar(또는 마지막 bar)]. funding_rates 의
    커버 범위가 이 구간을 못 덮으면(앞/뒤 결측) True → C14 배너에 "funding 데이터
    일부 결측" 고지 (C6 정직성). 포지션이 없으면 funding 무관 → False.
    """
    if not trades:
        return False
    if len(funding_rates) == 0:
        return True
    bar_ns = [t.value for t in pd.DatetimeIndex(ohlcv.index)]
    fund_ns = [t.value for t in pd.DatetimeIndex(funding_rates.index)]
    last_bar = len(ohlcv) - 1
    held_start_bar = min(t.entry_bar_index for t in trades)
    held_end_bar = max(
        (t.exit_bar_index if t.exit_bar_index is not None else last_bar) for t in trades
    )
    held_start = bar_ns[held_start_bar]
    held_end = bar_ns[min(held_end_bar, last_bar)]
    return min(fund_ns) > held_start or max(fund_ns) < held_end


def _funding_cost_by_bar(
    trades: list[RawTrade], ohlcv: pd.DataFrame, funding_rates: pd.Series
) -> tuple[list[Decimal], bool]:
    """각 bar 의 funding 비용(차감액 리스트) + 데이터 결측 여부 — C6 SSOT.

    funding 은 정산 경계(보통 8h)마다 보유 perp 포지션에 부과. settlement ts 는
    이를 포함하는 bar 에 귀속(searchsorted). cost = notional(close*qty) * rate *
    direction_sign (long=+1 → rate>0 시 지불 equity↓ / short=-1 → 수취).
    funding_rates index = tz-aware 정산 시각, value = Decimal rate.
    """
    n = len(ohlcv)
    costs = [Decimal("0")] * n
    # int64 ns 로 변환해 bisect — pandas searchsorted overload/Hashable 타입 마찰 회피.
    bar_ns: list[int] = [t.value for t in pd.DatetimeIndex(ohlcv.index)]
    funding_ns: list[int] = [t.value for t in pd.DatetimeIndex(funding_rates.index)]
    funding_vals = list(funding_rates)
    for ts_ns, rate_raw in zip(funding_ns, funding_vals, strict=True):
        rate = rate_raw if isinstance(rate_raw, Decimal) else Decimal(str(rate_raw))
        # ts 를 포함하는 bar (가장 가까운 이전/동일 bar). 첫 bar 이전 ts → skip.
        # 마지막 bar 시각 초과(백테스트 window 밖) 정산은 마지막 bar 오귀속 방지 위해 skip.
        if not bar_ns or ts_ns > bar_ns[-1]:
            continue
        pos = bisect.bisect_right(bar_ns, ts_ns) - 1
        if pos < 0:
            continue
        close_px = Decimal(str(ohlcv["close"].iloc[pos]))
        for t in trades:
            if t.entry_bar_index > pos:
                continue
            if t.exit_bar_index is not None and t.exit_bar_index <= pos:
                continue
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            costs[pos] += close_px * t.size * rate * direction_sign
    incomplete = _funding_coverage_incomplete(trades, ohlcv, funding_rates)
    return costs, incomplete


def _compute_equity_curve(
    trades: list[RawTrade],
    ohlcv: pd.DataFrame,
    cfg: BacktestConfig,
    funding_rates: pd.Series | None = None,
) -> pd.Series:
    """bar-by-bar equity 재구성.

    각 bar 에 대해:
      equity[bar] = init_cash
                  + Σ net_pnl (exit_bar_index <= bar)
                  + Σ unrealized_position_pnl (open/aboutToExit, entry 비용 차감 포함)

    unrealized_position_pnl = (close[bar] - entry_price) * qty * direction_sign
                            - entry_cost (fee + slip at entry)

    exit 비용은 실현 시점에 net_pnl 에 반영되므로 MTM 구간에서는 entry 비용만
    차감한다. 수수료/슬리피지 미반영 equity 로 Sharpe/DD 가 낙관 편향되는
    것을 방지 (Codex review P1).

    Decimal-first 합산을 위해 반환 Series 는 dtype=object 로 Decimal 을 보관한다.
    """
    n = len(ohlcv)
    init_cash = cfg.init_cash
    taker_fee = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))

    values: list[Decimal] = []

    # C6 funding accrual — funding_rates 제공 시 정산 경계마다 보유 포지션 funding
    # 누적 차감 (None = 회귀 0, 기존 동작 byte-identical).
    funding_by_bar = (
        _funding_cost_by_bar(trades, ohlcv, funding_rates)[0] if funding_rates is not None else None
    )

    # exit bar 별 realized pnl 누적
    exits_by_bar: dict[int, list[RawTrade]] = {}
    for t in trades:
        if t.exit_bar_index is not None:
            exits_by_bar.setdefault(t.exit_bar_index, []).append(t)

    realized_cum = Decimal("0")
    funding_cum = Decimal("0")
    for bar_idx in range(n):
        # 이 bar 에 exit 된 trade pnl 을 실현 누적에 추가 (bar 종료 시점 관점)
        for t in exits_by_bar.get(bar_idx, []):
            realized_cum += t.pnl
        if funding_by_bar is not None:
            funding_cum += funding_by_bar[bar_idx]

        # close price — numpy/float 소스라도 str() 경유로 Decimal 진입
        close_raw = ohlcv["close"].iloc[bar_idx]
        close_px = Decimal(str(close_raw))

        unrealized = Decimal("0")
        for t in trades:
            if t.entry_bar_index > bar_idx:
                continue
            # 아직 exit 안 된 포지션만 mark-to-market — open 이거나 (closed 이지만 이 bar 이후 exit)
            if t.status == "closed":
                assert t.exit_bar_index is not None
                if t.exit_bar_index <= bar_idx:
                    continue
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            price_pnl = (close_px - t.entry_price) * t.size * direction_sign
            # entry leg 비용 (taker fee + slippage) — _leg_cost SSOT 위임.
            entry_fee, entry_slip = _leg_cost(
                t.entry_price * t.size,
                fill_type="taker",
                taker_fee=taker_fee,
                slippage=slip_rate,
            )
            unrealized += price_pnl - (entry_fee + entry_slip)

        values.append(init_cash + realized_cum + unrealized - funding_cum)

    # object dtype 으로 Decimal 을 보관 — float drift 방지.
    return pd.Series(values, index=ohlcv.index, dtype=object)


# --- metrics -------------------------------------------------------------


def _compute_metrics(
    trades: list[RawTrade],
    equity: pd.Series,
    cfg: BacktestConfig,
    ohlcv: pd.DataFrame | None = None,
    funding_data_incomplete: bool | None = None,
) -> BacktestMetrics:
    """RawTrade list + equity curve → BacktestMetrics 24 필드.

    Sprint 31 BL-154: pine_v2 엔진 production path 에 신규 12 metric 직접
    계산 (vectorbt 의존 없이 RawTrade + equity Series 만 사용). vectorbt
    `extract_metrics` (engine/metrics.py) 와 알고리즘 정합:
      - avg_holding_hours: (exit_bar - entry_bar) * freq_to_hours
      - consecutive_*_max: closed PnL 부호 streak
      - long/short_win_rate_pct: direction 별 win_rate
      - monthly_returns: equity → daily returns → resample('ME') → cumprod
      - drawdown_curve / drawdown_duration: running_max 대비 % + 연속 음수 bars
      - annual_return_pct (CAGR): (1+total)^(1/years)-1
      - avg/best/worst_trade_pct: closed return_pct mean/max/min
      - total_trades: num_trades alias

    `ohlcv` 는 monthly_returns / drawdown_curve 의 timestamp 매핑용. None
    이면 monthly/drawdown_curve 는 None 반환 (graceful degrade — 기존
    fixture 호환).
    """
    closed = [t for t in trades if t.status == "closed"]
    num_trades = len(closed)
    init_cash = cfg.init_cash

    # equity 는 dtype=object 에 Decimal 을 보관. 마지막 원소를 Decimal 그대로 사용해
    # float drift 없이 total_return 을 계산한다.
    if len(equity) > 0:
        last = equity.iloc[-1]
        final_equity = last if isinstance(last, Decimal) else Decimal(str(last))
    else:
        final_equity = init_cash

    total_return = (final_equity - init_cash) / init_cash if init_cash != 0 else Decimal("0")
    if total_return.is_nan():
        total_return = Decimal("0")

    # Sharpe/MDD 는 근사 지표 — float 변환하여 numpy/pandas 연산 활용.
    equity_float = _as_float_series(equity)
    sharpe_ratio = _sharpe(equity_float)
    max_drawdown = _max_drawdown(equity_float)
    # Sprint 32-D BL-156: MDD 수학 정합 메타.
    # leverage=1 가정 하에서 MDD < -1.0 (= -100%) 는 수학적으로 자본 초과 손실
    # → 사용자 신뢰 quality 측면에서 명시적 표시 의무. pine_v2 엔진은 leverage
    # 를 PnL 에 직접 적용 안 함 (qty=절대 수량) → equity 음수 가능 → MDD 가
    # 자유롭게 -1.0 미만으로 갈 수 있음. 응답에 명시적 boolean 으로 노출하면
    # FE 가 "leverage Nx 가정" 라벨을 inline 으로 표시 가능.
    mdd_exceeds_capital = max_drawdown < Decimal("-1")

    win_count = sum(1 for t in closed if t.pnl > 0)
    win_rate = Decimal(win_count) / Decimal(num_trades) if num_trades > 0 else Decimal("0")

    long_count = sum(1 for t in closed if t.direction == "long") if num_trades > 0 else 0
    short_count = sum(1 for t in closed if t.direction == "short") if num_trades > 0 else 0

    if num_trades > 0:
        wins = [t.return_pct for t in closed if t.pnl > 0]
        losses = [t.return_pct for t in closed if t.pnl < 0]
        avg_win = _mean(wins) if wins else None
        avg_loss = _mean(losses) if losses else None
        gross_profit = sum((t.pnl for t in closed if t.pnl > 0), start=Decimal("0"))
        gross_loss_abs = sum((-t.pnl for t in closed if t.pnl < 0), start=Decimal("0"))
        profit_factor: Decimal | None = (
            gross_profit / gross_loss_abs if gross_loss_abs > 0 else None
        )
    else:
        avg_win = None
        avg_loss = None
        profit_factor = None

    # --- Sprint 31 BL-154: 신규 12 metric (RawTrade + equity 기반 직접 계산) ---
    avg_holding_hours = _v2_avg_holding_hours(closed, cfg.freq) if num_trades > 0 else None
    consecutive_wins_max, consecutive_losses_max = (
        _v2_streaks(closed) if num_trades > 0 else (None, None)
    )
    long_win_rate_pct = _v2_side_win_rate(closed, "long") if num_trades > 0 else None
    short_win_rate_pct = _v2_side_win_rate(closed, "short") if num_trades > 0 else None
    monthly_returns = _v2_monthly_returns(equity_float, ohlcv)
    drawdown_curve, drawdown_duration = _v2_drawdown_extract(equity_float, ohlcv)
    annual_return_pct = _v2_annual_return(total_return, ohlcv)
    avg_trade_pct, best_trade_pct, worst_trade_pct = (
        _v2_trade_returns_stats(closed) if num_trades > 0 else (None, None, None)
    )
    total_trades_alias: int | None = num_trades  # PRD parity alias
    # Sprint 34 BL-175: Buy & Hold curve (정확 OHLCV close 기반).
    buy_and_hold_curve = _v2_buy_and_hold_curve(ohlcv, init_cash)

    # C14 (정직성) — 총 수수료/슬리피지 분해 집계. C8 Slice 3: _leg_cost SSOT
    # 위임으로 _build_raw_trades 와의 cost 공식 중복 제거. 불변식 보존:
    #   total_fees + total_slippage == Σ RawTrade.fees.
    taker_fee = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    maker_fee = Decimal(str(cfg.maker_fee))
    total_fees = Decimal("0")
    total_slippage = Decimal("0")
    for t in trades:
        entry_fee, entry_slip = _leg_cost(
            t.entry_price * t.size,
            fill_type="taker",
            taker_fee=taker_fee,
            slippage=slip_rate,
        )
        total_fees += entry_fee
        total_slippage += entry_slip
        if t.exit_price is not None:
            # BL-104 — exit leg fill_type 라우팅 (_build_raw_trades 와 동일 SSOT).
            exit_fill = fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"
            exit_fee, exit_slip = _leg_cost(
                t.exit_price * t.size,
                fill_type=exit_fill,
                taker_fee=taker_fee,
                slippage=slip_rate,
                maker_fee=maker_fee,
            )
            total_fees += exit_fee
            total_slippage += exit_slip

    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
        sortino_ratio=None,  # pine_v2 경로 v1 — H2+
        calmar_ratio=None,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        long_count=long_count,
        short_count=short_count,
        avg_holding_hours=avg_holding_hours,
        consecutive_wins_max=consecutive_wins_max,
        consecutive_losses_max=consecutive_losses_max,
        long_win_rate_pct=long_win_rate_pct,
        short_win_rate_pct=short_win_rate_pct,
        monthly_returns=monthly_returns,
        drawdown_duration=drawdown_duration,
        annual_return_pct=annual_return_pct,
        total_trades=total_trades_alias,
        avg_trade_pct=avg_trade_pct,
        best_trade_pct=best_trade_pct,
        worst_trade_pct=worst_trade_pct,
        drawdown_curve=drawdown_curve,
        # Sprint 32-D BL-156: MDD 수학 정합 메타 (FE 카드 inline 표시용).
        mdd_unit="equity_ratio",
        mdd_exceeds_capital=mdd_exceeds_capital,
        # Sprint 34 BL-175: Buy & Hold curve (정확 OHLCV 기반).
        buy_and_hold_curve=buy_and_hold_curve,
        # C14 (정직성) — 총 수수료/슬리피지 분해 (헤드라인 net 표시용).
        total_fees=total_fees,
        total_slippage=total_slippage,
        # C6 (정직성) — funding 차감 시 보유 구간 일부가 funding 데이터 범위 밖이면 True.
        funding_data_incomplete=funding_data_incomplete,
    )


# --- Sprint 31 BL-154: pine_v2 path 신규 12 metric helper ---

# pandas offset alias → bar 1개 당 시간 (engine/metrics.py 와 정합).
# P1-5 (2026-05-30 정검): config_mapper.timeframe_to_freq 는 1m/5m/15m 을
# pandas 표준 alias '1min'/'5min'/'15min' 로 산출하므로 'min' alias 키도 필수.
# 누락 시 24h fallback 으로 avg_holding_hours 가 1440x/288x/96x 과대 계산.
_FREQ_HOURS_V2: dict[str, float] = {
    "1m": 1.0 / 60.0,
    "1min": 1.0 / 60.0,
    "5m": 5.0 / 60.0,
    "5min": 5.0 / 60.0,
    "15m": 15.0 / 60.0,
    "15min": 15.0 / 60.0,
    "30m": 30.0 / 60.0,
    "30min": 30.0 / 60.0,
    "1h": 1.0,
    "2h": 2.0,
    "4h": 4.0,
    "8h": 8.0,
    "12h": 12.0,
    "1d": 24.0,
    "1D": 24.0,
    "D": 24.0,
}


def _freq_to_hours_v2(freq: str) -> float:
    """매핑 없으면 24h fallback (engine/metrics.py 와 동일)."""
    return _FREQ_HOURS_V2.get(freq, 24.0)


def _v2_buy_and_hold_curve(
    ohlcv: pd.DataFrame | None, init_cash: Decimal
) -> list[tuple[str, Decimal]] | None:
    """Buy & Hold benchmark curve — OHLCV 첫 close 가격에 init_cash 매수 후 보유.

    공식: bh[i] = init_cash * close[i] / close[0]
    timestamp 형식: equity_curve / drawdown_curve 와 동일 ISO ("YYYY-MM-DDTHH:MM:SSZ").

    **fail-closed 정책 (P1-3, Sprint 34 BL-175):**
    - ohlcv None 또는 "close" 컬럼 부재 → None
    - len(ohlcv) < 2 (1 bar 이하 → BH 의미 없음) → None
    - DatetimeIndex 가 아닌 경우 → None
    - 첫 close NaN 또는 <=0 → None (zero division 차단)
    - **임의 close NaN 또는 <=0 1건이라도 → None** (partial silent line = 거짓 trust 차단)

    full curve 가 valid 한 경우만 반환 → frontend BH series 미렌더 + ChartLegend
    BH 항목 자동 hide (Surface Trust ADR-019 정합).

    Decimal-first 합산: close 는 OHLCV 원본 dtype 이 float 이지만 Decimal(str(...))
    경유로 Decimal 공간에서 곱셈/나눗셈. equity_curve 와 동일 패턴.
    """
    if ohlcv is None or "close" not in ohlcv.columns:
        return None
    if len(ohlcv) < 2:
        return None
    if not isinstance(ohlcv.index, pd.DatetimeIndex):
        return None

    # 1차 fail-closed gate — 첫 close 검증.
    try:
        first_close = Decimal(str(ohlcv["close"].iloc[0]))
    except Exception:
        return None
    if first_close.is_nan() or first_close <= 0:
        return None

    # 2차 fail-closed gate — 모든 close 검증 (1건이라도 invalid → None 반환).
    closes_decimal: list[Decimal] = []
    for raw in ohlcv["close"]:
        try:
            c = Decimal(str(raw))
        except Exception:
            return None
        if c.is_nan() or c <= 0:
            return None  # partial silent line 차단
        closes_decimal.append(c)

    # 검증 통과 후만 curve 생성.
    curve: list[tuple[str, Decimal]] = []
    for ts, close_dec in zip(ohlcv.index, closes_decimal, strict=True):
        ts_obj = pd.Timestamp(str(ts)) if not isinstance(ts, pd.Timestamp) else ts
        iso = ts_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        bh_value = init_cash * close_dec / first_close
        curve.append((iso, bh_value))

    return curve


def _v2_avg_holding_hours(closed: list[RawTrade], freq: str) -> Decimal | None:
    """closed trade 의 (exit_bar - entry_bar) * freq_to_hours 평균."""
    if not closed:
        return None
    bars: list[int] = []
    for t in closed:
        if t.exit_bar_index is None:
            continue
        bars.append(int(t.exit_bar_index) - int(t.entry_bar_index))
    if not bars:
        return None
    avg_bars = sum(bars) / len(bars)
    if not math.isfinite(avg_bars):
        return None
    return Decimal(str(avg_bars * _freq_to_hours_v2(freq)))


def _v2_streaks(closed: list[RawTrade]) -> tuple[int | None, int | None]:
    """closed trade PnL 부호 streak 최대값. 0 → 양쪽 reset."""
    if not closed:
        return (None, None)
    max_win = 0
    max_loss = 0
    cur_win = 0
    cur_loss = 0
    for t in closed:
        pnl = t.pnl
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
            if cur_win > max_win:
                max_win = cur_win
        elif pnl < 0:
            cur_loss += 1
            cur_win = 0
            if cur_loss > max_loss:
                max_loss = cur_loss
        else:
            cur_win = 0
            cur_loss = 0
    return (int(max_win), int(max_loss))


def _v2_side_win_rate(closed: list[RawTrade], side: str) -> Decimal | None:
    """direction 별 win_rate. 해당 side 0건이면 None."""
    sub = [t for t in closed if t.direction == side]
    if not sub:
        return None
    win_count = sum(1 for t in sub if t.pnl > 0)
    return Decimal(win_count) / Decimal(len(sub))


def _v2_monthly_returns(
    equity_float: pd.Series, ohlcv: pd.DataFrame | None
) -> list[tuple[str, Decimal]] | None:
    """equity → daily returns → resample('ME') → ("YYYY-MM", Decimal). 1개월 미만 None."""
    if ohlcv is None or len(equity_float) < 2:
        return None
    try:
        # equity index 가 DatetimeIndex 라야 resample 가능. ohlcv.index 사용.
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            return None
        eq = pd.Series(equity_float.values, index=ohlcv.index, dtype=float)
        returns = eq.pct_change().dropna()
        if returns.empty:
            return None
        # 'ME' (Month End) — pandas 2.2+ deprecation 'M' → 'ME' 정합.
        monthly = returns.resample("ME").apply(lambda r: float((1.0 + r).prod() - 1.0))
        result: list[tuple[str, Decimal]] = []
        for ts, val in monthly.items():
            f = float(val)
            if not math.isfinite(f):
                continue
            ts_obj = pd.Timestamp(str(ts)) if not isinstance(ts, pd.Timestamp) else ts
            key = ts_obj.strftime("%Y-%m")
            result.append((key, Decimal(str(f))))
        return result if result else None
    except Exception:
        return None


def _v2_drawdown_extract(
    equity_float: pd.Series, ohlcv: pd.DataFrame | None
) -> tuple[list[tuple[str, Decimal]] | None, int | None]:
    """equity → (running_max - equity) / running_max → curve + 최대 연속 음수 bars.

    drawdown_curve 는 timestamp 가 필요하므로 ohlcv 가 None 이면 (None, max_dur)
    반환 (max_dur 는 무관계로 계산 가능).
    """
    if len(equity_float) == 0:
        return (None, None)
    try:
        running_max = equity_float.cummax()
        # ZeroDivisionError 방어 — running_max 0 시 NaN 후 0 으로 fallback (math.isfinite 체크).
        dd = (equity_float - running_max) / running_max.replace(0, float("nan"))
        max_dur = 0
        cur_dur = 0
        curve: list[tuple[str, Decimal]] | None = None
        if ohlcv is not None and isinstance(ohlcv.index, pd.DatetimeIndex):
            curve_list: list[tuple[str, Decimal]] = []
            for ts, f in zip(ohlcv.index, dd.values, strict=True):
                f_val = float(f) if math.isfinite(float(f)) else 0.0
                ts_obj = pd.Timestamp(str(ts)) if not isinstance(ts, pd.Timestamp) else ts
                iso = ts_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
                curve_list.append((iso, Decimal(str(f_val))))
                if f_val < 0:
                    cur_dur += 1
                    if cur_dur > max_dur:
                        max_dur = cur_dur
                else:
                    cur_dur = 0
            curve = curve_list if curve_list else None
        else:
            for f in dd.values:
                f_val = float(f) if math.isfinite(float(f)) else 0.0
                if f_val < 0:
                    cur_dur += 1
                    if cur_dur > max_dur:
                        max_dur = cur_dur
                else:
                    cur_dur = 0
        return (curve, int(max_dur))
    except Exception:
        return (None, None)


def _v2_annual_return(total_return: Decimal, ohlcv: pd.DataFrame | None) -> Decimal | None:
    """CAGR = (1+total)^(1/years)-1. period < 1d 또는 base ≤ 0 시 None."""
    if ohlcv is None or len(ohlcv.index) < 2:
        return None
    try:
        idx = ohlcv.index
        if not isinstance(idx, pd.DatetimeIndex):
            return None
        start = pd.Timestamp(str(idx[0]))
        end = pd.Timestamp(str(idx[-1]))
        days = (end - start).total_seconds() / 86400.0
        if days <= 0:
            return None
        years = days / 365.25
        if years <= 0:
            return None
        total_f = float(total_return)
        if not math.isfinite(total_f):
            return None
        base = 1.0 + total_f
        if base <= 0:
            return None
        cagr = base ** (1.0 / years) - 1.0
        if not math.isfinite(cagr):
            return None
        return Decimal(str(cagr))
    except Exception:
        return None


def _v2_trade_returns_stats(
    closed: list[RawTrade],
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """closed return_pct mean / max / min. 빈 list 시 (None, None, None)."""
    if not closed:
        return (None, None, None)
    rets = [t.return_pct for t in closed]
    if not rets:
        return (None, None, None)
    avg = sum(rets, start=Decimal("0")) / Decimal(len(rets))
    best = max(rets)
    worst = min(rets)
    return (avg, best, worst)


def _as_float_series(equity: pd.Series) -> pd.Series:
    """Sharpe/MDD 계산용 Decimal → float 변환. object dtype 이면 원소별 float 화."""
    if equity.dtype == object:
        return pd.Series([float(v) for v in equity], index=equity.index, dtype=float)
    return equity.astype(float)


def _sharpe(equity: pd.Series) -> Decimal:
    if len(equity) < 2:
        return Decimal("0")
    returns = equity.pct_change().dropna()
    if returns.empty:
        return Decimal("0")
    mean = float(returns.mean())
    std = float(returns.std(ddof=1))
    if std == 0 or not math.isfinite(std):
        return Decimal("0")
    sharpe = mean / std * math.sqrt(len(returns))
    if not math.isfinite(sharpe):
        return Decimal("0")
    return Decimal(str(sharpe))


def _max_drawdown(equity: pd.Series) -> Decimal:
    if len(equity) == 0:
        return Decimal("0")
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    min_dd = float(dd.min())
    if not math.isfinite(min_dd):
        return Decimal("0")
    return Decimal(str(min_dd))


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


# --- ParseOutcome stub ---------------------------------------------------


def _stub_parse_outcome(
    source: str,
    *,
    status: Literal["ok", "unsupported", "error"] = "ok",
    warnings: list[str] | None = None,
) -> ParseOutcome:
    """pine_v2 경로는 ParseOutcome 을 생성하지 않음. legacy 필드 호환용 최소 stub.

    BacktestOutcome.parse 필드가 non-optional 이라 최소 구조를 채워주되, 실패
    경로에서는 status="error" 를 넘겨 소비자가 파싱 상태를 오해하지 않도록 한다.
    entries/exits 시리즈는 구 엔진 SignalResult 용이라 pine_v2 경로에선 빈 값.
    실제 파싱 판정은 strategy service `_parse` 가 pine_v2 기반으로 수행한다.

    Sprint 23 codex G.2 P1 #2: warnings= 인자로 strategy_state.warnings (BL-098
    strategy.exit NOP 등) 를 BacktestOutcome.parse.warnings 로 전파. 사용자가
    silent success 받지 않도록.
    """
    version: Literal["v4", "v5"] = _detect_version(source)
    empty = SignalResult(
        entries=pd.Series(dtype=bool),
        exits=pd.Series(dtype=bool),
    )
    return ParseOutcome(
        status=status,
        source_version=version,
        result=empty,
        error=None,
        supported_feature_report={"functions_used": []},
        warnings=list(warnings) if warnings else [],
    )


def _detect_version(source: str) -> Literal["v4", "v5"]:
    m = _VERSION_RE.search(source)
    if m is None:
        return "v5"
    try:
        v = int(m.group(1))
    except ValueError:
        return "v5"
    return "v4" if v == 4 else "v5"


__all__ = ["run_backtest_v2"]
