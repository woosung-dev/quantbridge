"""vectorbt Portfolio → BacktestMetrics 추출."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

import pandas as pd

from src.backtest.engine.types import BacktestMetrics

# Sprint 30 gamma-BE: pandas freq alias → 시간 단위
# duration.mean()이 bar 수를 반환하므로, bar 1개 당 시간으로 변환.
# 정의되지 않은 freq 는 default 24h (안전 fallback, "1d"와 동치).
_FREQ_HOURS: dict[str, float] = {
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


def _freq_to_hours(freq: str) -> float:
    """pandas offset alias → bar 1개 당 시간. 매핑 없으면 24h fallback."""
    return _FREQ_HOURS.get(freq, 24.0)


def extract_metrics(pf: Any, freq: str = "1D") -> BacktestMetrics:
    """vectorbt.Portfolio 인스턴스에서 24 metric 추출.

    Sprint 30 gamma-BE: 신규 12 필드 추가. 모든 신규 호출은 try/except → None fallback
    (vectorbt API drift 방어). NaN/Inf → None.

    Args:
        pf: vectorbt Portfolio 인스턴스
        freq: pandas offset alias ("1m"/"5m"/"15m"/"1h"/"4h"/"1d") — duration → 시간 변환용
    """
    trades = pf.trades
    num_trades = int(trades.count())

    total_return = _as_decimal(pf.total_return())
    sharpe_ratio = _as_decimal(pf.sharpe_ratio())
    max_drawdown = _as_decimal(pf.max_drawdown())
    win_rate = _as_decimal(trades.win_rate()) if num_trades > 0 else Decimal("0")

    # 기존 확장 지표 — NaN → None 변환
    sortino_ratio = _as_optional_decimal(pf.sortino_ratio())
    calmar_ratio = _as_optional_decimal(pf.calmar_ratio())

    if num_trades > 0:
        profit_factor = _as_optional_decimal(trades.profit_factor())
        win_count = int(trades.winning.count())
        loss_count = int(trades.losing.count())
        avg_win = _as_optional_decimal(trades.winning.returns.mean()) if win_count > 0 else None
        avg_loss = _as_optional_decimal(trades.losing.returns.mean()) if loss_count > 0 else None
        long_count: int | None = int(trades.long.count())
        short_count: int | None = int(trades.short.count())
    else:
        profit_factor = None
        avg_win = None
        avg_loss = None
        long_count = 0
        short_count = 0

    # --- Sprint 30 gamma-BE 신규 12 필드 (모두 try/except → None fallback) ---
    avg_holding_hours = _safe_avg_holding_hours(trades, freq) if num_trades > 0 else None
    consecutive_wins_max, consecutive_losses_max = (
        _safe_streaks(trades) if num_trades > 0 else (None, None)
    )
    long_win_rate_pct = _safe_long_short_win_rate(trades, "long") if num_trades > 0 else None
    short_win_rate_pct = _safe_long_short_win_rate(trades, "short") if num_trades > 0 else None
    monthly_returns = _safe_monthly_returns(pf)
    drawdown_curve, drawdown_duration = _safe_drawdown_extract(pf)
    annual_return_pct = _safe_annual_return(pf)
    avg_trade_pct, best_trade_pct, worst_trade_pct = (
        _safe_trade_returns_stats(trades) if num_trades > 0 else (None, None, None)
    )
    total_trades_alias: int | None = num_trades  # PRD parity alias

    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
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


def _as_decimal(value: Any) -> Decimal:
    """vectorbt 지표 반환(스칼라 또는 단일 원소 Series) → Decimal.

    NaN은 Decimal('NaN')으로 보존 (zero가 아니라 명시적으로 표시).
    str(float(value)) 경유로 binary-float drift 방지.
    """
    if hasattr(value, "iloc"):  # Series 또는 DataFrame
        value = value.iloc[0] if len(value) > 0 else float("nan")
    return Decimal(str(float(value)))


def _as_optional_decimal(value: Any) -> Decimal | None:
    """NaN이면 None, 유한 값이면 Decimal 반환."""
    if hasattr(value, "iloc"):
        value = value.iloc[0] if len(value) > 0 else float("nan")
    f = float(value)
    if not math.isfinite(f):
        return None
    return Decimal(str(f))


# --- Sprint 30 gamma-BE 신규 추출 helper ---


def _safe_avg_holding_hours(trades: Any, freq: str) -> Decimal | None:
    """trades.duration.mean() (bars) * freq -> 시간 단위 Decimal. 실패 시 None."""
    try:
        mean_bars = float(trades.duration.mean())
        if not math.isfinite(mean_bars):
            return None
        hours_per_bar = _freq_to_hours(freq)
        return Decimal(str(mean_bars * hours_per_bar))
    except Exception:
        return None


def _safe_streaks(trades: Any) -> tuple[int | None, int | None]:
    """records_readable 의 PnL 부호로 win/loss 연속 streak 최대값 계산.

    PnL > 0 → win, PnL < 0 → loss, PnL == 0 → 둘 다 reset (중립).
    Status 'Open' 거래는 unrealized 라 streak 미반영 (Closed only).
    """
    try:
        recs = trades.records_readable
        if recs is None or len(recs) == 0:
            return (None, None)
        # vectorbt records_readable 컬럼 후보: "PnL", "Status"
        pnl_col = "PnL" if "PnL" in recs.columns else None
        status_col = "Status" if "Status" in recs.columns else None
        if pnl_col is None:
            return (None, None)
        max_win = 0
        max_loss = 0
        cur_win = 0
        cur_loss = 0
        for _, row in recs.iterrows():
            if status_col is not None and str(row[status_col]) != "Closed":
                continue
            pnl_val = float(row[pnl_col])
            if not math.isfinite(pnl_val):
                continue
            if pnl_val > 0:
                cur_win += 1
                cur_loss = 0
                max_win = max(max_win, cur_win)
            elif pnl_val < 0:
                cur_loss += 1
                cur_win = 0
                max_loss = max(max_loss, cur_loss)
            else:  # 0 — break-even, reset 양쪽
                cur_win = 0
                cur_loss = 0
        return (int(max_win), int(max_loss))
    except Exception:
        return (None, None)


def _safe_long_short_win_rate(trades: Any, side: str) -> Decimal | None:
    """trades.long.win_rate() / trades.short.win_rate() — 거래 0건 또는 NaN 시 None."""
    try:
        sub = trades.long if side == "long" else trades.short
        if int(sub.count()) == 0:
            return None
        return _as_optional_decimal(sub.win_rate())
    except Exception:
        return None


def _safe_monthly_returns(pf: Any) -> list[tuple[str, Decimal]] | None:
    """pf.returns().resample('ME') → list[("YYYY-MM", Decimal ratio)]. 실패 시 None."""
    try:
        returns = pf.returns()
        if returns is None or len(returns) == 0:
            return None
        # 'ME' (Month End) — 'M' deprecated in pandas 2.2+
        monthly = returns.resample("ME").apply(lambda r: (1.0 + r).prod() - 1.0)
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


def _safe_drawdown_extract(pf: Any) -> tuple[list[tuple[str, Decimal]] | None, int | None]:
    """pf.drawdown() Series → (curve list, max duration bars). 실패 시 (None, None)."""
    try:
        dd = pf.drawdown()
        if dd is None or len(dd) == 0:
            return (None, None)
        curve: list[tuple[str, Decimal]] = []
        max_dur = 0
        cur_dur = 0
        for ts, val in dd.items():
            f = float(val)
            if not math.isfinite(f):
                continue
            ts_obj = pd.Timestamp(str(ts)) if not isinstance(ts, pd.Timestamp) else ts
            iso = ts_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
            curve.append((iso, Decimal(str(f))))
            if f < 0:
                cur_dur += 1
                if cur_dur > max_dur:
                    max_dur = cur_dur
            else:
                cur_dur = 0
        return (curve if curve else None, int(max_dur))
    except Exception:
        return (None, None)


def _safe_annual_return(pf: Any) -> Decimal | None:
    """CAGR = (1 + total_return)^(1/years) - 1. period < 1d 시 None."""
    try:
        total = float(pf.total_return())
        if not math.isfinite(total):
            return None
        idx = pf.wrapper.index
        if idx is None or len(idx) < 2:
            return None
        start = pd.Timestamp(str(idx[0]))
        end = pd.Timestamp(str(idx[-1]))
        days = (end - start).total_seconds() / 86400.0
        if days <= 0:
            return None
        years = days / 365.25
        if years <= 0:
            return None
        # (1+total) 음수 방어 — total ≤ -1 (전손) 시 CAGR 정의 불가
        base = 1.0 + total
        if base <= 0:
            return None
        cagr = base ** (1.0 / years) - 1.0
        if not math.isfinite(cagr):
            return None
        return Decimal(str(cagr))
    except Exception:
        return None


def _safe_trade_returns_stats(
    trades: Any,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """trades.returns 의 mean / max / min — 빈 Series / NaN 시 None."""
    try:
        rets = trades.returns
        # ReturnsAccessor / ndarray 둘 다 지원
        avg = _as_optional_decimal(rets.mean())
        best = _as_optional_decimal(rets.max())
        worst = _as_optional_decimal(rets.min())
        return (avg, best, worst)
    except Exception:
        return (None, None, None)
