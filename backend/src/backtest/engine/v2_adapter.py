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
from src.strategy.pine.types import ParseOutcome, SignalResult
from src.strategy.pine_v2.compat import V2RunResult, parse_and_run_v2
from src.strategy.pine_v2.interpreter import PineRuntimeError
from src.strategy.pine_v2.strategy_state import StrategyState, Trade

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)", re.MULTILINE)


def run_backtest_v2(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
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

    if cfg.trading_sessions:
        # Sprint 7d 의 bar-hour 마스킹은 pine_v2 경로에서 아직 미구현. corpus/기본 경로엔 무관.
        logger.warning("v2_adapter: trading_sessions filter not yet implemented for pine_v2 path")

    try:
        # strict=True — bar-level PineRuntimeError 를 raise 시켜 상위에서 status=error 로 변환.
        v2 = parse_and_run_v2(source, ohlcv, strict=True)
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
        equity = _compute_equity_curve(trades, ohlcv, cfg)
        metrics = _compute_metrics(trades, equity, cfg, ohlcv)
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


# --- trades --------------------------------------------------------------


def _build_raw_trades(state: StrategyState, cfg: BacktestConfig) -> list[RawTrade]:
    all_trades: list[Trade] = list(state.closed_trades) + list(state.open_trades.values())
    # 체결 순서 = entry_bar 오름차순 (같은 bar 면 기존 리스트 순서 유지)
    all_trades.sort(key=lambda t: (t.entry_bar, 0 if t.is_open else 1))

    raw: list[RawTrade] = []
    fee_rate = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    for idx, t in enumerate(all_trades):
        entry_price = Decimal(str(t.entry_price))
        qty = Decimal(str(t.qty))
        exit_price: Decimal | None = (
            Decimal(str(t.exit_price)) if t.exit_price is not None else None
        )

        # 수수료 = (entry + exit) * qty * fee_rate. slippage 는 entry/exit 두 번 모두 적용.
        entry_fee = entry_price * qty * fee_rate
        entry_slip = entry_price * qty * slip_rate
        exit_fee = exit_price * qty * fee_rate if exit_price is not None else Decimal("0")
        exit_slip = exit_price * qty * slip_rate if exit_price is not None else Decimal("0")
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
            )
        )
    return raw


# --- equity curve --------------------------------------------------------


def _compute_equity_curve(
    trades: list[RawTrade], ohlcv: pd.DataFrame, cfg: BacktestConfig
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
    fee_rate = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    entry_cost_rate = fee_rate + slip_rate

    values: list[Decimal] = []

    # exit bar 별 realized pnl 누적
    exits_by_bar: dict[int, list[RawTrade]] = {}
    for t in trades:
        if t.exit_bar_index is not None:
            exits_by_bar.setdefault(t.exit_bar_index, []).append(t)

    realized_cum = Decimal("0")
    for bar_idx in range(n):
        # 이 bar 에 exit 된 trade pnl 을 실현 누적에 추가 (bar 종료 시점 관점)
        for t in exits_by_bar.get(bar_idx, []):
            realized_cum += t.pnl

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
            entry_cost = t.entry_price * t.size * entry_cost_rate
            unrealized += price_pnl - entry_cost

        values.append(init_cash + realized_cum + unrealized)

    # object dtype 으로 Decimal 을 보관 — float drift 방지.
    return pd.Series(values, index=ohlcv.index, dtype=object)


# --- metrics -------------------------------------------------------------


def _compute_metrics(
    trades: list[RawTrade],
    equity: pd.Series,
    cfg: BacktestConfig,
    ohlcv: pd.DataFrame | None = None,
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
    )


# --- Sprint 31 BL-154: pine_v2 path 신규 12 metric helper ---

# pandas offset alias → bar 1개 당 시간 (engine/metrics.py 와 정합).
_FREQ_HOURS_V2: dict[str, float] = {
    "1m": 1.0 / 60.0,
    "5m": 5.0 / 60.0,
    "15m": 15.0 / 60.0,
    "30m": 30.0 / 60.0,
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
