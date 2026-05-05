"""Sprint 30 γ-BE: BacktestMetrics 12 → 24 확장 추출 검증.

PRD `backtests.results` JSONB 24 metric spec 정합. vectorbt API drift 방어
(try/except → None fallback) 검증 포함.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.metrics import (
    _freq_to_hours,
    _safe_annual_return,
    _safe_avg_holding_hours,
    _safe_drawdown_extract,
    _safe_long_short_win_rate,
    _safe_monthly_returns,
    _safe_streaks,
    _safe_trade_returns_stats,
    extract_metrics,
)
from src.backtest.engine.types import BacktestMetrics


def _make_pf_with_trades() -> object:
    """다거래 fixture — 2 closed trades (long), 명확한 PnL."""
    close = pd.Series(
        [10.0, 11.0, 12.0, 11.5, 13.0, 12.5, 14.0, 13.5, 15.0, 14.5],
        index=pd.date_range("2024-01-01", periods=10, freq="1D"),
    )
    entries = pd.Series(
        [False, True, False, False, True, False, True, False, False, False],
        index=close.index,
    )
    exits = pd.Series(
        [False, False, False, True, False, False, False, True, False, True],
        index=close.index,
    )
    return vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )


def _make_pf_zero_trades() -> object:
    """0 거래 fixture — entries/exits 모두 False."""
    close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0, 12.5])
    entries = pd.Series([False] * 6)
    exits = pd.Series([False] * 6)
    return vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )


# --- 1. 정상 fixture: 24 필드 모두 추출 + 타입 정합 ---


def test_extract_metrics_all_24_fields_present_and_typed() -> None:
    """다거래 fixture — 24 필드 모두 정상 추출, 신규 12 필드 타입 정합."""
    pf = _make_pf_with_trades()
    m = extract_metrics(pf, freq="1D")

    # 기존 12 필드는 baseline 과 동일
    assert isinstance(m, BacktestMetrics)
    assert isinstance(m.total_return, Decimal)
    assert isinstance(m.num_trades, int)

    # 신규 12 필드: 모두 추출되었어야 함
    assert m.avg_holding_hours is not None
    assert isinstance(m.avg_holding_hours, Decimal)
    assert m.avg_holding_hours > Decimal("0")  # 보유 시간 > 0

    assert m.consecutive_wins_max is not None
    assert isinstance(m.consecutive_wins_max, int)
    assert m.consecutive_losses_max is not None
    assert isinstance(m.consecutive_losses_max, int)

    assert m.long_win_rate_pct is not None  # long 거래만 있음
    assert isinstance(m.long_win_rate_pct, Decimal)
    # short 거래 0 → None
    assert m.short_win_rate_pct is None

    assert m.monthly_returns is not None
    assert len(m.monthly_returns) >= 1
    for key, val in m.monthly_returns:
        assert isinstance(key, str)
        assert len(key) == 7  # "YYYY-MM"
        assert key[4] == "-"
        assert isinstance(val, Decimal)

    assert m.drawdown_duration is not None
    assert isinstance(m.drawdown_duration, int)
    assert m.drawdown_duration >= 0

    assert m.annual_return_pct is not None
    assert isinstance(m.annual_return_pct, Decimal)

    assert m.total_trades == m.num_trades  # alias parity

    assert m.avg_trade_pct is not None
    assert m.best_trade_pct is not None
    assert m.worst_trade_pct is not None
    assert isinstance(m.avg_trade_pct, Decimal)

    assert m.drawdown_curve is not None
    assert len(m.drawdown_curve) >= 1
    for ts, val in m.drawdown_curve:
        assert isinstance(ts, str)
        assert ts.endswith("Z")
        assert isinstance(val, Decimal)


# --- 2. empty trades: 신규 12 필드 모두 None (또는 0/alias) ---


def test_extract_metrics_zero_trades_extended_fields_none() -> None:
    """num_trades=0 → 거래 의존 12 필드 모두 None. monthly/drawdown 은 returns 기반이라 추출 가능."""
    pf = _make_pf_zero_trades()
    m = extract_metrics(pf, freq="1D")

    assert m.num_trades == 0
    # 거래 의존 필드 — None
    assert m.avg_holding_hours is None
    assert m.consecutive_wins_max is None
    assert m.consecutive_losses_max is None
    assert m.long_win_rate_pct is None
    assert m.short_win_rate_pct is None
    assert m.avg_trade_pct is None
    assert m.best_trade_pct is None
    assert m.worst_trade_pct is None
    # total_trades alias 은 num_trades=0 이므로 0
    assert m.total_trades == 0


# --- 3. vectorbt API fail (mock raise) → None fallback ---


def test_extract_metrics_vectorbt_drift_returns_none_fallback() -> None:
    """vectorbt 신규 호출이 raise 시, 신규 필드는 None fallback (drift 방어)."""
    # fixture 자체 호출 — drift 검증은 후속 _safe_* helper 직접 검증으로 수행.
    _ = _make_pf_with_trades()

    # _safe_streaks 가 raise 하도록 mock — fallback 되어야 함
    with patch("src.backtest.engine.metrics._safe_streaks", side_effect=Exception("API drift")):
        # extract_metrics 가 _safe_streaks 호출 시 patched → side_effect 발화 전에
        # extract_metrics 자체는 caller 이므로 try 안에 호출되지 않음. 패턴 검증을 위해
        # 직접 _safe_streaks 호출 시 try/except 안 됨 — caller 가 try 함.
        # 대신 _safe_streaks 자체가 try/except 로 감싸져 있는지 검증:
        pass

    # 직접 helper 검증 — records_readable 접근이 raise 시 (None, None) 반환
    class FakeTrades:
        @property
        def records_readable(self) -> object:
            raise RuntimeError("vectorbt API removed")

    result = _safe_streaks(FakeTrades())
    assert result == (None, None)

    # _safe_monthly_returns 도 마찬가지
    class FakePf:
        def returns(self) -> object:
            raise RuntimeError("vectorbt API removed")

    assert _safe_monthly_returns(FakePf()) is None

    # _safe_drawdown_extract
    class FakePf2:
        def drawdown(self) -> object:
            raise RuntimeError("vectorbt API removed")

    assert _safe_drawdown_extract(FakePf2()) == (None, None)

    # _safe_annual_return
    class FakePf3:
        def total_return(self) -> object:
            raise RuntimeError("vectorbt API removed")

    assert _safe_annual_return(FakePf3()) is None

    # _safe_avg_holding_hours
    class FakeTrades2:
        @property
        def duration(self) -> object:
            raise RuntimeError("vectorbt API removed")

    assert _safe_avg_holding_hours(FakeTrades2(), "1D") is None

    # _safe_long_short_win_rate
    class FakeTrades3:
        @property
        def long(self) -> object:
            raise RuntimeError("API drift")

    assert _safe_long_short_win_rate(FakeTrades3(), "long") is None

    # _safe_trade_returns_stats
    class FakeTrades4:
        @property
        def returns(self) -> object:
            raise RuntimeError("API drift")

    assert _safe_trade_returns_stats(FakeTrades4()) == (None, None, None)


# --- 4. drawdown_curve len = equity_curve len ---


def test_drawdown_curve_length_matches_equity_curve() -> None:
    """drawdown_curve 길이는 pf.value() (equity) 길이와 동일."""
    pf = _make_pf_with_trades()
    m = extract_metrics(pf, freq="1D")

    assert m.drawdown_curve is not None
    equity_len = len(pf.value())
    # drawdown 가 0/NaN 일 수 있어 약간 적을 수 있지만, 정상 fixture 에서는 동일
    assert len(m.drawdown_curve) == equity_len


# --- 5. monthly_returns YYYY-MM 키 정합 ---


def test_monthly_returns_yyyymm_keys() -> None:
    """monthly_returns 의 키는 YYYY-MM 포맷, 값은 Decimal ratio."""
    pf = _make_pf_with_trades()
    m = extract_metrics(pf, freq="1D")

    assert m.monthly_returns is not None
    for key, val in m.monthly_returns:
        # YYYY-MM 정확히 7 자리, "-" 위치 4
        assert len(key) == 7
        assert key[4] == "-"
        year_part = key[:4]
        month_part = key[5:]
        assert year_part.isdigit()
        assert month_part.isdigit()
        month_int = int(month_part)
        assert 1 <= month_int <= 12
        # 값은 ratio (보통 -1 ~ +N)
        assert val > Decimal("-1")


# --- 6. _freq_to_hours 매핑 정합 ---


def test_freq_to_hours_known_values() -> None:
    """알려진 freq → 시간 매핑."""
    assert _freq_to_hours("1m") == 1.0 / 60.0
    assert _freq_to_hours("5m") == 5.0 / 60.0
    assert _freq_to_hours("15m") == 0.25
    assert _freq_to_hours("1h") == 1.0
    assert _freq_to_hours("4h") == 4.0
    assert _freq_to_hours("1d") == 24.0
    assert _freq_to_hours("1D") == 24.0


def test_freq_to_hours_unknown_default_24() -> None:
    """매핑 없는 freq → 24h fallback (안전)."""
    assert _freq_to_hours("unknown") == 24.0
    assert _freq_to_hours("") == 24.0


# --- 7. avg_holding_hours scaling — 1h freq 시 hours == bars ---


def test_avg_holding_hours_scales_with_freq() -> None:
    """동일 portfolio: freq='1h' 시 avg_holding_hours == duration_bars,
    freq='1d' 시 avg_holding_hours == duration_bars × 24."""
    pf = _make_pf_with_trades()

    m_hour = extract_metrics(pf, freq="1h")
    m_day = extract_metrics(pf, freq="1d")

    assert m_hour.avg_holding_hours is not None
    assert m_day.avg_holding_hours is not None
    # day = hour × 24
    ratio = float(m_day.avg_holding_hours) / float(m_hour.avg_holding_hours)
    assert abs(ratio - 24.0) < 0.01


# --- 8. _safe_streaks: 명시적 win/loss 패턴 ---


def test_safe_streaks_with_explicit_pattern() -> None:
    """records_readable mock — Win Win Loss Win Win Win Loss 패턴 → (3, 1)."""
    fake_recs = pd.DataFrame(
        {
            "PnL": [1.0, 2.0, -1.0, 1.5, 2.5, 0.5, -2.0],
            "Status": ["Closed"] * 7,
        }
    )

    class FakeTrades:
        @property
        def records_readable(self) -> pd.DataFrame:
            return fake_recs

    wins, losses = _safe_streaks(FakeTrades())
    assert wins == 3
    assert losses == 1


def test_safe_streaks_skips_open_trades() -> None:
    """Open status 거래는 streak 미반영 (Closed only)."""
    fake_recs = pd.DataFrame(
        {
            "PnL": [1.0, -1.0, 2.0, 3.0],
            "Status": ["Closed", "Closed", "Open", "Closed"],
        }
    )

    class FakeTrades:
        @property
        def records_readable(self) -> pd.DataFrame:
            return fake_recs

    wins, losses = _safe_streaks(FakeTrades())
    # Closed: Win, Loss, Win — wins=1 each side, but second Win after Loss = streak 1
    # Pattern: W L (skip Open) W → final wins streak = 1, losses streak = 1
    # 단, 마지막 W 는 reset 후 +1 → max_win = 1
    assert wins == 1
    assert losses == 1


# --- 9. annual_return_pct: 1년 미만 fixture 도 finite ---


def test_annual_return_pct_short_period_finite() -> None:
    """10일 fixture → CAGR 계산 가능 (years > 0). 결과 finite."""
    pf = _make_pf_with_trades()
    m = extract_metrics(pf, freq="1D")
    assert m.annual_return_pct is not None
    # 10일에 +N% → 연환산 시 매우 큰 수가 나올 수 있음. finite 만 검증.
    import math as _m

    assert _m.isfinite(float(m.annual_return_pct))


# --- 10. total_trades alias = num_trades ---


def test_total_trades_aliases_num_trades() -> None:
    """PRD parity: total_trades == num_trades 항상."""
    pf = _make_pf_with_trades()
    m = extract_metrics(pf, freq="1D")
    assert m.total_trades == m.num_trades

    pf_zero = _make_pf_zero_trades()
    m_zero = extract_metrics(pf_zero, freq="1D")
    assert m_zero.total_trades == 0
    assert m_zero.num_trades == 0
