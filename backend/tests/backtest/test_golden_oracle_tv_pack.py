# TV parity 요약 메트릭 팩 hand-oracle — sortino/calmar/excursion/per-side/abs (anti-circular)
"""TV Strategy Tester convention 손계산 오라클 (LESSON-039).

TV 문서 ground (2026-07-05 doc spike):
- Sortino = (MR − RFR) / DD — 달력 월 단위 수익률, RFR 기본 2%/년(월 2%/12),
  DD = 모집단 sqrt(mean(max(0, RFR − Xi)²)), 연율화 없음. 데이터 2개월 미만 시
  daily 기간(RFR 2%/365) fallback (RiskMetrics 라이브러리 규칙).
- Calmar = CAGR / |MDD| (둘 다 ratio).
- 에피소드 정의는 TV 미공개 → 본 오라클이 우리 규약을 고정("TV 근사"):
  drawdown 에피소드 = running peak 아래로 내려간 연속 bar 구간(회복 bar 미포함),
  run-up 에피소드 = running trough 위 연속 bar 구간(신저점 bar 에서 종료).
- intrabar 근사: max_runup_intrabar = max(equity_high − runmin(equity_low)),
  max_drawdown_intrabar = max(runmax(equity_high) − equity_low). pct 분모 =
  각 시점 trough/peak.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.metrics import (
    calmar_ratio,
    compute_excursion_stats,
    compute_side_metrics,
    sharpe_ratio,
    sortino_ratio,
)
from src.backtest.engine.types import BacktestConfig, RawTrade
from src.backtest.engine.v2_adapter import (
    _build_raw_trades,
    _compute_equity_curve,
    _compute_metrics,
)
from src.strategy.pine_v2.strategy_state import StrategyState, Trade
from tests.fixtures.backtest_golden_minimal import make_s2_ohlcv, make_s2_state

_ZERO_CFG = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="1D")


# ── sortino ──────────────────────────────────────────────────────────────────


def _monthly_equity() -> pd.Series:
    """3 달력월 equity — 월말값 [110, 99, 108.9], 시작 100.
    월간 수익률 = [+0.10, -0.10, +0.10] (TV 예시와 동일 방식: (110-100)/100).
    """
    idx = pd.date_range("2024-01-01", "2024-03-31", freq="D")
    values: list[float] = []
    for ts in idx:
        if ts == idx[0]:
            values.append(100.0)
        elif ts.month == 1:
            values.append(110.0)
        elif ts.month == 2:
            values.append(99.0)
        else:
            values.append(108.9)
    return pd.Series(values, index=idx, dtype=float)


def test_sortino_monthly_hand_oracle() -> None:
    """returns [0.1, -0.1, 0.1], RFR_m = 0.02/12:
    mean = 0.0333333 / excess = 0.0316667
    DD = sqrt(((0.02/12 + 0.1)^2)/3) = 0.0586973
    sortino = 0.539492...
    """
    result = sortino_ratio(_monthly_equity())
    assert result is not None
    assert float(result) == pytest.approx(0.539492, abs=1e-4)


def test_sortino_daily_fallback_under_two_months() -> None:
    """5 일치 → 월 구간 <2 → daily fallback (RFR 2%/365).
    equity [100,110,99] → returns [0.1, -0.1], mean 0, rfr_d = 0.02/365
    DD = sqrt(((rfr_d+0.1)^2)/2) = 0.0707490 → sortino = -0.000775 근방.
    """
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    eq = pd.Series([100.0, 110.0, 99.0], index=idx, dtype=float)
    result = sortino_ratio(eq)
    assert result is not None
    assert float(result) == pytest.approx(-0.000775, abs=2e-4)


def test_sortino_no_downside_returns_none() -> None:
    """하방 편차 0 (전 구간 RFR 이상 수익) → None (0 나눗셈 금지)."""
    idx = pd.date_range("2024-01-01", "2024-03-31", freq="D")
    values = [
        100.0 if ts == idx[0] else 100.0 * (1.1 ** ts.month)  # 월간 수익률 전부 +10%
        for ts in idx
    ]
    eq = pd.Series(values, index=idx, dtype=float)
    assert sortino_ratio(eq) is None


# ── sharpe ───────────────────────────────────────────────────────────────────


def test_sharpe_monthly_hand_oracle() -> None:
    """rfr_m = 0.02/12 = 0.00166667, mean = 0.03333333, excess = 0.03166667.
    popSD = sqrt((0.06666667^2 + 0.13333333^2 + 0.06666667^2)/3) = 0.09428090.
    sharpe = 0.03166667 / 0.09428090 = 0.335876.
    """
    value, convention = sharpe_ratio(_monthly_equity())
    assert float(value) == pytest.approx(0.335876, abs=1e-5)
    assert convention == "tv_monthly_rfr2"


def test_sharpe_daily_fallback_hand_oracle() -> None:
    """returns [0.1, -0.1], mean = 0, popSD = 0.1, rfr_d = 0.02/365.
    sharpe = -0.0000547945 / 0.1 = -0.000547945.
    """
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    eq = pd.Series([100.0, 110.0, 99.0], index=idx, dtype=float)
    value, convention = sharpe_ratio(eq)
    assert float(value) == pytest.approx(-0.000548, abs=1e-6)
    assert convention == "tv_daily_rfr2"


def test_sharpe_zero_sd_returns_zero_not_none() -> None:
    idx = pd.date_range("2024-01-01", "2024-03-31", freq="D")
    eq = pd.Series([100.0] * len(idx), index=idx, dtype=float)
    # Sortino와 의도적 비대칭으로 Sharpe는 unavailable convention과 함께 0을 반환한다.
    assert sharpe_ratio(eq) == (Decimal("0"), "unavailable")


def test_sharpe_non_datetime_index_unavailable() -> None:
    # golden fixture ema_cross_atr_sltp_v5/ohlcv.csv는 timestamp 컬럼이 없어 RangeIndex라 이 경로를 탄다는 계약을 고정한다.
    assert sharpe_ratio(pd.Series([100.0, 110.0, 99.0])) == (Decimal("0"), "unavailable")


# ── calmar ───────────────────────────────────────────────────────────────────


def test_calmar_hand_oracle() -> None:
    assert calmar_ratio(Decimal("0.30"), Decimal("-0.15")) == Decimal("2")


def test_calmar_none_when_mdd_zero_or_cagr_none() -> None:
    assert calmar_ratio(Decimal("0.30"), Decimal("0")) is None
    assert calmar_ratio(None, Decimal("-0.15")) is None


# ── excursion stats ──────────────────────────────────────────────────────────

_EQ_CLOSES = [100.0, 105.0, 103.0, 108.0, 96.0, 98.0, 101.0, 110.0]


def _eq_series() -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=8, freq="D")
    return pd.Series([Decimal(str(v)) for v in _EQ_CLOSES], index=idx, dtype=object)


def test_excursion_stats_close_hand_oracle() -> None:
    """손유도 (docstring 에피소드 규약):
    drawdown 에피소드: [bar2] depth 2 dur 1 / [bar4..6] depth 12 dur 3
      → avg_abs 7, avg_dur 2 bars = 2 days, max_abs 12, recovery bar4→bar7 = 3
    run-up 에피소드: [bar1..3] peak 108 runup 8 dur 3 / [bar5..7] peak 110 runup 14 dur 3
      → max_abs 14 (pct 14/96), avg_abs 11, avg_dur 3 bars = 3 days
    """
    stats = compute_excursion_stats(_eq_series(), None, None)
    assert stats is not None
    assert stats.max_runup_abs == Decimal("14")
    assert float(stats.max_runup_pct) == pytest.approx(14 / 96, abs=1e-9)
    assert stats.avg_runup_abs == Decimal("11")
    assert stats.avg_runup_duration_bars == Decimal("3")
    assert stats.avg_runup_duration_days == Decimal("3")
    assert stats.avg_drawdown_abs == Decimal("7")
    assert stats.avg_drawdown_duration_bars == Decimal("2")
    assert stats.avg_drawdown_duration_days == Decimal("2")
    assert stats.max_drawdown_abs == Decimal("12")
    assert stats.max_drawdown_recovery_bars == 3
    assert stats.max_drawdown_recovery_days == Decimal("3")
    # intrabar 커브 미전달 → intrabar 필드 None
    assert stats.max_runup_intrabar_abs is None
    assert stats.max_drawdown_intrabar_abs is None


def test_excursion_stats_intrabar_hand_oracle() -> None:
    """high = close+2 / low = close-3:
    max_runup_intrabar = max(high − runmin(low)) = 112 − 93 = 19 (pct 19/93)
    max_drawdown_intrabar = max(runmax(high) − low) = 110 − 93 = 17 (pct 17/110)
    """
    highs = [Decimal(str(v + 2.0)) for v in _EQ_CLOSES]
    lows = [Decimal(str(v - 3.0)) for v in _EQ_CLOSES]
    stats = compute_excursion_stats(_eq_series(), highs, lows)
    assert stats is not None
    assert stats.max_runup_intrabar_abs == Decimal("19")
    assert float(stats.max_runup_intrabar_pct) == pytest.approx(19 / 93, abs=1e-9)
    assert stats.max_drawdown_intrabar_abs == Decimal("17")
    assert float(stats.max_drawdown_intrabar_pct) == pytest.approx(17 / 110, abs=1e-9)


def test_excursion_unrecovered_mdd_has_none_recovery() -> None:
    """끝까지 회복 못 한 MDD → recovery None."""
    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    eq = pd.Series([Decimal("100"), Decimal("120"), Decimal("90"), Decimal("95")],
                   index=idx, dtype=object)
    stats = compute_excursion_stats(eq, None, None)
    assert stats is not None
    assert stats.max_drawdown_abs == Decimal("30")
    assert stats.max_drawdown_recovery_bars is None
    assert stats.max_drawdown_recovery_days is None


# ── per-side ─────────────────────────────────────────────────────────────────


def _raw(direction: str, pnl: str, idx: int) -> RawTrade:
    return RawTrade(
        trade_index=idx,
        direction=direction,  # type: ignore[arg-type]
        status="closed",
        entry_bar_index=idx,
        exit_bar_index=idx + 1,
        entry_price=Decimal("100"),
        exit_price=Decimal("100"),
        size=Decimal("1"),
        pnl=Decimal(pnl),
        return_pct=Decimal("0"),
        fees=Decimal("0"),
    )


def test_per_side_metrics_hand_oracle() -> None:
    """long: [+20, +10, -5] → net 25, gp 30, gl 5, PF 6, avg 25/3
    short: [-8] → net -8, gp 0, gl 8, PF 0, avg -8
    """
    closed = [
        _raw("long", "20", 0), _raw("long", "10", 1), _raw("long", "-5", 2),
        _raw("short", "-8", 3),
    ]
    ps = compute_side_metrics(closed)
    assert ps is not None
    assert ps.long is not None and ps.short is not None
    assert ps.long.net_profit_abs == Decimal("25")
    assert ps.long.gross_profit_abs == Decimal("30")
    assert ps.long.gross_loss_abs == Decimal("5")
    assert ps.long.profit_factor == Decimal("6")
    assert ps.long.avg_trade_abs == Decimal("25") / Decimal("3")
    assert ps.short.net_profit_abs == Decimal("-8")
    assert ps.short.profit_factor == Decimal("0")
    assert ps.short.avg_trade_abs == Decimal("-8")


def test_per_side_missing_side_is_none() -> None:
    ps = compute_side_metrics([_raw("long", "20", 0)])
    assert ps is not None
    assert ps.long is not None
    assert ps.short is None
    assert compute_side_metrics([]) is None


# ── abs 팩 + integration (_compute_metrics 경유) ─────────────────────────────


def test_abs_pack_integration_s2() -> None:
    """S2 (zero-fee): T1 long +20 bars=1 / T2 short +10 bars=2.
    net 30, gp 30, gl 0, largest_win 20, largest_loss None, avg_trade 15,
    avg_win 15, avg_loss None, ratio None, open 0건 → open_pnl 0,
    avg_bars 1.5 / winning 1.5 / losing None. per_side.long.net 20 / short.net 10.
    """
    state = make_s2_state()
    ohlcv = make_s2_ohlcv()
    trades = _build_raw_trades(state, _ZERO_CFG, ohlcv=ohlcv)
    equity = _compute_equity_curve(trades, ohlcv, _ZERO_CFG)
    m = _compute_metrics(trades, equity, _ZERO_CFG, ohlcv)
    assert m.net_profit_abs == Decimal("30")
    assert m.gross_profit_abs == Decimal("30")
    assert m.gross_loss_abs == Decimal("0")
    assert m.largest_win_abs == Decimal("20")
    assert m.largest_loss_abs is None
    assert m.avg_trade_abs == Decimal("15")
    assert m.avg_win_abs == Decimal("15")
    assert m.avg_loss_abs is None
    assert m.ratio_avg_win_loss is None
    assert m.total_open_trades == 0
    assert m.open_pnl == Decimal("0")
    assert m.avg_bars_in_trade == Decimal("1.5")
    assert m.avg_bars_in_winning_trades == Decimal("1.5")
    assert m.avg_bars_in_losing_trades is None
    assert m.per_side is not None
    assert m.per_side.long is not None and m.per_side.long.net_profit_abs == Decimal("20")
    assert m.per_side.short is not None and m.per_side.short.net_profit_abs == Decimal("10")
    assert m.excursion_stats is not None
    # sortino: 6 daily bars → daily fallback 로 값 존재 / calmar: MDD 0 → None 허용
    assert m.sortino_ratio is not None


def test_zero_trades_sortino_gated_to_none() -> None:
    """trades 0건 = flat equity → sortino 무의미(-1 고정) → None 게이트."""
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    ohlcv = pd.DataFrame(
        {
            "open": [100.0] * 5, "high": [101.0] * 5, "low": [99.0] * 5,
            "close": [100.0] * 5, "volume": [1000.0] * 5,
        },
        index=idx,
    )
    equity = _compute_equity_curve([], ohlcv, _ZERO_CFG)
    m = _compute_metrics([], equity, _ZERO_CFG, ohlcv)
    assert m.sortino_ratio is None
    assert m.total_open_trades == 0
    assert m.open_pnl == Decimal("0")


def test_open_pnl_integration() -> None:
    """open long entry 104@bar3 (zero-fee), 마지막 close 106 → open_pnl = 2."""
    state = StrategyState()
    state.open_trades["O1"] = Trade(
        id="O1", direction="long", qty=1.0, entry_bar=3, entry_price=104.0
    )
    closes = [100.0, 103.0, 108.0, 104.0, 106.0]
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    ohlcv = pd.DataFrame(
        {
            "open": [c - 1.0 for c in closes],
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [1000.0] * 5,
        },
        index=idx,
    )
    trades = _build_raw_trades(state, _ZERO_CFG, ohlcv=ohlcv)
    equity = _compute_equity_curve(trades, ohlcv, _ZERO_CFG)
    m = _compute_metrics(trades, equity, _ZERO_CFG, ohlcv)
    assert m.open_pnl == Decimal("2")
    assert m.total_open_trades == 1
    assert m.net_profit_abs == Decimal("0")  # closed 없음 → net(closed 기준) 0
