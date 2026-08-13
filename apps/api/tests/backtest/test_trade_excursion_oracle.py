# TV Trades-parity — per-trade MAE/MFE(run-up/drawdown)·fee split·bars·comment·누적 손계산 오라클
"""_build_raw_trades 의 RawTrade 확장 필드 hand-oracle (anti-circular, LESSON-039).

윈도 규약 (엔진 = bar-close 체결 전제):
- excursion 스캔 = (entry_bar, exit_bar] — entry bar 는 체결(종가) 이전 고저가
  포지션 미보유 구간이라 제외, exit bar 는 full high/low 포함(트리거 후 극값 포함
  = 낙관/보수 혼합 bar 근사, TV next-bar-open 체결과 완전 일치 불가 — "TV 근사").
- open trade = (entry_bar, last_bar].
- runup/drawdown 은 gross(수수료 미차감) 가격 excursion. pct 분모 = entry notional.
- cumulative_pnl = trade_index(entry 순) 누적 net pnl.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import _build_raw_trades
from src.strategy.pine_v2.strategy_state import StrategyState, Trade

_ZERO_CFG = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="1D")
_FEE_CFG = BacktestConfig(init_cash=Decimal("1000"), fees=0.001, slippage=0.0005, freq="1D")

# 5 bars — close/high/low 를 excursion 판별 가능하게 비대칭 구성.
_CLOSES = [100.0, 103.0, 108.0, 104.0, 106.0]
_HIGHS = [105.0, 112.0, 109.0, 107.0, 108.0]
_LOWS = [95.0, 99.0, 101.0, 98.0, 103.0]


def _ohlcv() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=5, freq="1D")
    return pd.DataFrame(
        {
            "open": [c - 1.0 for c in _CLOSES],
            "high": _HIGHS,
            "low": _LOWS,
            "close": _CLOSES,
            "volume": [1000.0] * 5,
        },
        index=dates,
    )


def _state(*trades: Trade) -> StrategyState:
    state = StrategyState()
    state.closed_trades = [t for t in trades if t.exit_bar is not None]
    for t in trades:
        if t.exit_bar is None:
            state.open_trades[t.id] = t
    return state


def test_long_closed_excursion_hand_oracle() -> None:
    """X1: long qty=2, entry bar1@100, exit bar3@104. 윈도 (1,3] = bar2,3.
    max high = max(109,107)=109 → runup = (109-100)*2 = 18 (pct 18/200 = 0.09)
    min low  = min(101, 98)= 98 → drawdown = (100-98)*2 = 4 (pct 0.02)
    bars_in_trade = 3-1 = 2.
    """
    t = Trade(id="X1", direction="long", qty=2.0, entry_bar=1, entry_price=100.0,
              exit_bar=3, exit_price=104.0)
    [raw] = _build_raw_trades(_state(t), _ZERO_CFG, ohlcv=_ohlcv())
    assert raw.runup_abs == Decimal("18")
    assert raw.runup_pct == Decimal("0.09")
    assert raw.drawdown_abs == Decimal("4")
    assert raw.drawdown_pct == Decimal("0.02")
    assert raw.bars_in_trade == 2


def test_short_closed_excursion_hand_oracle() -> None:
    """X2: short qty=1, entry bar0@100, exit bar2@108. 윈도 (0,2] = bar1,2.
    favorable(하락) = min low = 99 → runup = (100-99)*1 = 1 (pct 0.01)
    adverse(상승) = max high = 112 → drawdown = (112-100)*1 = 12 (pct 0.12)
    """
    t = Trade(id="X2", direction="short", qty=1.0, entry_bar=0, entry_price=100.0,
              exit_bar=2, exit_price=108.0)
    [raw] = _build_raw_trades(_state(t), _ZERO_CFG, ohlcv=_ohlcv())
    assert raw.runup_abs == Decimal("1")
    assert raw.runup_pct == Decimal("0.01")
    assert raw.drawdown_abs == Decimal("12")
    assert raw.drawdown_pct == Decimal("0.12")
    assert raw.bars_in_trade == 2


def test_open_trade_scans_to_last_bar() -> None:
    """X3: open long entry bar3@104. 윈도 (3,4] = bar4 (high 108 / low 103).
    runup = 108-104 = 4, drawdown = 104-103 = 1. bars_in_trade = None (open).
    """
    t = Trade(id="X3", direction="long", qty=1.0, entry_bar=3, entry_price=104.0)
    [raw] = _build_raw_trades(_state(t), _ZERO_CFG, ohlcv=_ohlcv())
    assert raw.status == "open"
    assert raw.runup_abs == Decimal("4")
    assert raw.drawdown_abs == Decimal("1")
    assert raw.bars_in_trade is None


def test_excursion_clamped_at_zero() -> None:
    """X5: long entry@120 (전 구간 high 미만) → runup = 0 (음수 excursion 없음)."""
    t = Trade(id="X5", direction="long", qty=2.0, entry_bar=1, entry_price=120.0,
              exit_bar=3, exit_price=104.0)
    [raw] = _build_raw_trades(_state(t), _ZERO_CFG, ohlcv=_ohlcv())
    assert raw.runup_abs == Decimal("0")
    assert raw.runup_pct == Decimal("0")
    assert raw.drawdown_abs == Decimal("44")  # (120-98)*2


def test_same_bar_close_has_zero_excursion() -> None:
    """X6: entry_bar == exit_bar → 윈도 공집합 → excursion 0, bars_in_trade 0."""
    t = Trade(id="X6", direction="long", qty=1.0, entry_bar=2, entry_price=108.0,
              exit_bar=2, exit_price=108.0)
    [raw] = _build_raw_trades(_state(t), _ZERO_CFG, ohlcv=_ohlcv())
    assert raw.runup_abs == Decimal("0")
    assert raw.drawdown_abs == Decimal("0")
    assert raw.bars_in_trade == 0


def test_without_ohlcv_excursion_is_none_but_rest_filled() -> None:
    """X4: ohlcv 미전달(기존 8개 테스트 파일 호환 경로) → excursion 만 None."""
    t = Trade(id="X4", direction="long", qty=2.0, entry_bar=1, entry_price=100.0,
              exit_bar=3, exit_price=104.0, comment="Long")
    [raw] = _build_raw_trades(_state(t), _FEE_CFG)
    assert raw.runup_abs is None
    assert raw.runup_pct is None
    assert raw.drawdown_abs is None
    assert raw.drawdown_pct is None
    # 나머지 신규 필드는 ohlcv 무관하게 채워짐
    assert raw.bars_in_trade == 2
    assert raw.comment == "Long"
    assert raw.cumulative_pnl is not None


def test_fee_slippage_split_hand_oracle() -> None:
    """fee_paid/slippage_paid 분리 + 불변식 fee+slip == fees(결합).
    entry 100*2 + exit 104*2 = 408 notional → fee 0.408 / slip 0.204 / 결합 0.612.
    """
    t = Trade(id="XF", direction="long", qty=2.0, entry_bar=1, entry_price=100.0,
              exit_bar=3, exit_price=104.0)
    [raw] = _build_raw_trades(_state(t), _FEE_CFG, ohlcv=_ohlcv())
    assert raw.fee_paid == Decimal("0.408")
    assert raw.slippage_paid == Decimal("0.204")
    assert raw.fees == raw.fee_paid + raw.slippage_paid


def test_comment_empty_becomes_none() -> None:
    t = Trade(id="XC", direction="long", qty=1.0, entry_bar=0, entry_price=100.0,
              exit_bar=1, exit_price=103.0, comment="")
    [raw] = _build_raw_trades(_state(t), _ZERO_CFG, ohlcv=_ohlcv())
    assert raw.comment is None


def test_cumulative_pnl_in_trade_index_order() -> None:
    """누적 = trade_index(entry 순) net pnl 누적.
    idx0 = short bar0: (108-100)*1*(-1) = -8 → 누적 -8
    idx1 = long bar1: (104-100)*2 = +8 → 누적 0
    """
    t_short = Trade(id="XS", direction="short", qty=1.0, entry_bar=0, entry_price=100.0,
                    exit_bar=2, exit_price=108.0)
    t_long = Trade(id="XL", direction="long", qty=2.0, entry_bar=1, entry_price=100.0,
                   exit_bar=3, exit_price=104.0)
    raws = _build_raw_trades(_state(t_short, t_long), _ZERO_CFG, ohlcv=_ohlcv())
    assert [r.cumulative_pnl for r in raws] == [Decimal("-8"), Decimal("0")]
