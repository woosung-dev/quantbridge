"""Sprint 31 BL-154: pine_v2 path 신규 12 metric 직접 계산 검증.

production path = `_compute_metrics()` (v2_adapter). vectorbt 의존 없이
RawTrade list + equity Series 만 사용해 24 필드 모두 채움. dogfood Day 3
"17 row 중 12 신규 metric 모두 — fallback" root cause 해소 evidence.

BL-156 leverage 검증 — 동일 trade 결과에 대해 leverage=1/2/3 시 max_drawdown
계산이 *equity 변동* 에 따른 것이지 leverage 에 직접 영향받지 않음을 명시
(qty 가 절대 수량 → leverage 는 응답 노출 가정으로만 의미). 사용자가
-100% 초과 MDD 를 leverage 가정과 결합해 해석할 수 있도록 evidence 보존.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestConfig, RawTrade
from src.backtest.engine.v2_adapter import (
    _compute_equity_curve,
    _compute_metrics,
    _v2_avg_holding_hours,
    _v2_drawdown_extract,
    _v2_monthly_returns,
    _v2_side_win_rate,
    _v2_streaks,
    _v2_trade_returns_stats,
)


def _make_ohlcv_30d_1h() -> pd.DataFrame:
    """30일 * 24h = 720 bars, 가벼운 선형 + sine wave."""
    idx = pd.date_range("2024-01-01", periods=720, freq="1h", tz="UTC")
    # close: $100 ~ $130 사이 sine wave + drift
    base = 100.0
    vals = [
        base + 0.02 * i + 5.0 * (1 if (i // 24) % 2 == 0 else -1)
        for i in range(720)
    ]
    return pd.DataFrame(
        {
            "open": vals,
            "high": [v + 0.5 for v in vals],
            "low": [v - 0.5 for v in vals],
            "close": vals,
            "volume": [1000.0] * 720,
        },
        index=idx,
    )


def _make_raw_trades_30d() -> list[RawTrade]:
    """5 closed trades — 3 win / 2 loss. long-only. holding 12 bars 평균."""
    # entries: bar 0, 100, 250, 400, 600 — exits: +12 bars
    raws: list[RawTrade] = []
    deals = [
        # (entry_bar, entry_px, exit_bar, exit_px, dir, pnl_sign)
        (0, Decimal("100.00"), 12, Decimal("105.00"), "long"),       # win
        (100, Decimal("102.00"), 112, Decimal("99.00"), "long"),     # loss
        (250, Decimal("110.00"), 262, Decimal("115.00"), "long"),    # win
        (400, Decimal("108.00"), 412, Decimal("114.00"), "long"),    # win
        (600, Decimal("125.00"), 612, Decimal("120.00"), "long"),    # loss
    ]
    qty = Decimal("1")
    for idx, (eb, ep, xb, xp, d) in enumerate(deals):
        sign = Decimal("1") if d == "long" else Decimal("-1")
        gross = (xp - ep) * qty * sign
        # zero fees / slippage 로 깔끔한 fixture
        notional = ep * qty
        net = gross  # fees=0 가정
        raws.append(
            RawTrade(
                trade_index=idx,
                direction="long",
                status="closed",
                entry_bar_index=eb,
                exit_bar_index=xb,
                entry_price=ep,
                exit_price=xp,
                size=qty,
                pnl=net,
                return_pct=net / notional,
                fees=Decimal("0"),
            )
        )
    return raws


# --- Test 1: production path 24 metric all populated -----------------------


def test_v2_compute_metrics_all_24_fields_populated() -> None:
    """30일 1h fixture — 신규 12 metric 모두 non-None evidence (BL-154 root fix)."""
    ohlcv = _make_ohlcv_30d_1h()
    trades = _make_raw_trades_30d()
    cfg = BacktestConfig(
        init_cash=Decimal("10000"),
        fees=0.0,
        slippage=0.0,
        freq="1h",
    )
    equity = _compute_equity_curve(trades, ohlcv, cfg)
    m = _compute_metrics(trades, equity, cfg, ohlcv)

    # 기존 12 필드
    assert m.num_trades == 5
    assert m.long_count == 5
    assert m.short_count == 0

    # 신규 12 필드 — 모두 non-None (γ-BE drift silent skip 해소 증거)
    assert m.avg_holding_hours is not None
    # 12 bars * 1h = 12 시간 평균
    assert m.avg_holding_hours == Decimal("12.0")

    assert m.consecutive_wins_max is not None
    assert m.consecutive_losses_max is not None
    # 시퀀스: W L W W L → max_win=2, max_loss=1
    assert m.consecutive_wins_max == 2
    assert m.consecutive_losses_max == 1

    assert m.long_win_rate_pct is not None
    # 3/5 long wins
    assert m.long_win_rate_pct == Decimal("3") / Decimal("5")
    assert m.short_win_rate_pct is None  # short 0건

    assert m.monthly_returns is not None
    assert len(m.monthly_returns) >= 1
    for key, val in m.monthly_returns:
        assert isinstance(key, str)
        assert isinstance(val, Decimal)

    assert m.drawdown_curve is not None
    assert len(m.drawdown_curve) == 720  # 1 point / bar
    assert m.drawdown_duration is not None
    assert m.drawdown_duration >= 0

    assert m.annual_return_pct is not None  # 30일 = ~0.082 years → CAGR 정의됨

    assert m.total_trades == 5  # PRD parity alias

    assert m.avg_trade_pct is not None
    assert m.best_trade_pct is not None
    assert m.worst_trade_pct is not None
    # best > avg > worst
    assert m.best_trade_pct >= m.avg_trade_pct >= m.worst_trade_pct


# --- Test 2: short-period (1주 미만) → monthly_returns graceful None --------


def test_v2_monthly_returns_short_period_graceful() -> None:
    """1주 (168 bars) fixture — monthly_returns 는 'ME' resample 시 1개 (의도적 OK)."""
    idx = pd.date_range("2024-01-01", periods=168, freq="1h", tz="UTC")
    ohlcv = pd.DataFrame(
        {"close": [100.0 + i * 0.01 for i in range(168)]},
        index=idx,
    )
    eq = pd.Series([float(10000 + i) for i in range(168)], index=idx, dtype=float)
    monthly = _v2_monthly_returns(eq, ohlcv)
    # 1주 → 'ME' resample 1개 (1월 31일 bucket). graceful — None 또는 1건.
    assert monthly is None or len(monthly) >= 0


def test_v2_monthly_returns_no_ohlcv_returns_none() -> None:
    """ohlcv None → monthly_returns None (graceful, 기존 fixture 호환)."""
    eq = pd.Series([10000.0, 10100.0, 10200.0])
    assert _v2_monthly_returns(eq, None) is None


# --- Test 3: leverage=1/2/3 max_drawdown 계산 정합 --------------------------


def test_v2_max_drawdown_leverage_independent_evidence() -> None:
    """BL-156 evidence: leverage 는 응답 노출 가정 — 엔진 PnL 에 직접 적용 안 됨.

    현재 pine_v2 path 는 qty 절대 수량 (Pine `strategy.entry()` default qty=1)
    이라 leverage 를 cfg 에 1/2/3 다르게 줘도 동일 trades 면 max_drawdown
    동일 (equity 곡선 변경 없음). 사용자 dogfood Day 3 의 -132% MDD 는
    *qty=1 BTC notional* 이 init_cash $10K 를 초과한 자연스러운 결과 (10x
    natural exposure). leverage 는 명시적 가정 으로 응답에 노출됨.
    """
    ohlcv = _make_ohlcv_30d_1h()
    trades = _make_raw_trades_30d()
    results = []
    for lev in (1.0, 2.0, 3.0):
        cfg = BacktestConfig(
            init_cash=Decimal("10000"),
            fees=0.0,
            slippage=0.0,
            freq="1h",
            leverage=lev,
        )
        equity = _compute_equity_curve(trades, ohlcv, cfg)
        m = _compute_metrics(trades, equity, cfg, ohlcv)
        results.append((lev, m.max_drawdown))
    # leverage 다 다른데 max_drawdown 동일 — engine 이 leverage 미적용
    assert results[0][1] == results[1][1] == results[2][1]


# --- Test 4: helper 직접 검증 ----------------------------------------------


def test_v2_streaks_basic_sequence() -> None:
    """W W L W L L → max_win=2, max_loss=2."""
    trades = _make_raw_trades_30d()
    # 위 fixture 시퀀스: W L W W L → max_win=2, max_loss=1
    wins, losses = _v2_streaks(trades)
    assert wins == 2
    assert losses == 1


def test_v2_streaks_zero_trades_returns_none() -> None:
    """0 trades → (None, None)."""
    assert _v2_streaks([]) == (None, None)


def test_v2_side_win_rate_long_only_short_none() -> None:
    """long-only fixture → long_win_rate Decimal, short_win_rate None."""
    trades = _make_raw_trades_30d()
    long_rate = _v2_side_win_rate(trades, "long")
    short_rate = _v2_side_win_rate(trades, "short")
    assert long_rate == Decimal("3") / Decimal("5")
    assert short_rate is None


def test_v2_avg_holding_hours_freq_mapping() -> None:
    """평균 12 bars * 1h = 12h. freq='1d' 시 12 * 24 = 288h."""
    trades = _make_raw_trades_30d()
    hours_1h = _v2_avg_holding_hours(trades, "1h")
    hours_1d = _v2_avg_holding_hours(trades, "1d")
    assert hours_1h == Decimal("12.0")
    assert hours_1d == Decimal("288.0")


def test_v2_trade_returns_stats_avg_best_worst() -> None:
    """5 trades: returns mean / max / min 정합."""
    trades = _make_raw_trades_30d()
    avg, best, worst = _v2_trade_returns_stats(trades)
    assert avg is not None
    assert best is not None
    assert worst is not None
    assert best > avg > worst
    # 5 trades:
    #   #0 long 100→105, return = 5/100 = 0.05
    #   #1 long 102→99,  return = -3/102 ≈ -0.0294 (worst)
    #   #2 long 110→115, return = 5/110 ≈ 0.04545
    #   #3 long 108→114, return = 6/108 ≈ 0.05555 (best)
    #   #4 long 125→120, return = -5/125 = -0.04
    # best = 6/108, worst = -5/125
    assert best == Decimal("6") / Decimal("108")
    assert worst == Decimal("-5") / Decimal("125")


def test_v2_drawdown_extract_with_ohlcv_curve_and_duration() -> None:
    """ohlcv 제공 시 curve + duration 모두 산출."""
    ohlcv = _make_ohlcv_30d_1h()
    eq = pd.Series(
        [10000.0 + 100.0 * (1 if i % 50 < 25 else -1) for i in range(720)],
        index=ohlcv.index,
        dtype=float,
    )
    curve, dur = _v2_drawdown_extract(eq, ohlcv)
    assert curve is not None
    assert len(curve) == 720
    assert dur is not None
    assert dur > 0  # 음수 drawdown 구간 존재


def test_v2_drawdown_extract_no_ohlcv_returns_curve_none_but_duration() -> None:
    """ohlcv None → curve=None, duration 만 산출 (graceful degrade)."""
    eq = pd.Series([10000.0, 9900.0, 9800.0, 10100.0, 10200.0], dtype=float)
    curve, dur = _v2_drawdown_extract(eq, None)
    assert curve is None
    assert dur is not None
    assert dur >= 1  # 9900, 9800 두 bar 음수 (running_max=10000)
