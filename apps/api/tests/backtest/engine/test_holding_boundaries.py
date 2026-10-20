"""체결 시점에 따른 실제 보유 구간을 결과 계산까지 보존한다."""

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2


def candles(count: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 1.0},
        index=pd.date_range("2026-01-01", periods=count, freq="h", tz="UTC"),
    )


def test_next_open_excursion_includes_entry_bar() -> None:
    frame = candles()
    frame.loc[frame.index[1], ["high", "low"]] = [120.0, 80.0]
    source = '// @version=5\nstrategy("Entry excursion")\nif bar_index == 0\n    strategy.entry("L", strategy.long)\nif bar_index == 1\n    strategy.close("L")\n'
    out = run_backtest_v2(
        source, frame, BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open")
    )
    assert out.status == "ok", out.error
    trade = out.result.trades[0]
    assert (trade.entry_bar_index, trade.exit_bar_index) == (1, 2)
    assert (trade.runup_abs, trade.drawdown_abs) == (Decimal("20"), Decimal("20"))


def test_bar_close_entry_cannot_pay_funding_at_its_open() -> None:
    frame = candles(10)
    source = '// @version=5\nstrategy("Funding time")\nif bar_index == 8\n    strategy.entry("L", strategy.long)\n'
    funding = pd.Series([Decimal("0.001")], index=frame.index[[8]])
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="bar_close"),
        funding_rates=funding,
    )
    assert out.status == "ok", out.error
    assert out.result.metrics.total_funding == Decimal("0")


def test_next_open_excursion_excludes_exit_bar_wicks() -> None:
    frame = candles()
    frame.loc[frame.index[2], ["high", "low"]] = [120.0, 80.0]
    source = '// @version=5\nstrategy("Exit excursion")\nif bar_index == 0\n    strategy.entry("L", strategy.long)\nif bar_index == 1\n    strategy.close("L")\n'
    out = run_backtest_v2(
        source, frame, BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open")
    )
    assert out.status == "ok", out.error
    trade = out.result.trades[0]
    assert (trade.entry_bar_index, trade.exit_bar_index) == (1, 2)
    assert (trade.runup_abs, trade.drawdown_abs) == (Decimal("0"), Decimal("0"))


@pytest.mark.parametrize("direction", ["long", "short"])
@pytest.mark.parametrize("timing", ["bar_close", "next_bar_open"])
def test_entry_and_exit_funding_uses_fill_phase(direction, timing) -> None:
    frame = candles(12)
    entry_signal = 7 if timing == "next_bar_open" else 8
    exit_signal = 8 if timing == "next_bar_open" else 9
    source = (
        '//@version=5\nstrategy("Funding boundary")\n'
        f'if bar_index == {entry_signal}\n    strategy.entry("T", strategy.{direction})\n'
        f'if bar_index == {exit_signal}\n    strategy.close("T")\n'
    )
    # 진입 봉 08시와 청산 봉 09시의 서로 다른 rate가 경계 뒤집기를 판별한다.
    funding = pd.Series([Decimal("0.001"), Decimal("0.002")], index=frame.index[[8, 9]])
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing=timing),
        funding_rates=funding,
    )
    assert out.status == "ok", out.error
    expected = Decimal("0.1") if timing == "next_bar_open" else Decimal("0.2")
    assert out.result.metrics.total_funding == (expected if direction == "long" else -expected)
    trade = out.result.trades[0]
    assert (trade.entry_bar_index, trade.exit_bar_index) == (8, 9)


def test_same_bar_liquidation_excursion_includes_realized_loss() -> None:
    frame = candles(2)
    frame.loc[frame.index[1], ["high", "low"]] = [120.0, 80.0]
    source = '//@version=5\nstrategy("Liquidation")\nif bar_index == 0\n    strategy.entry("L", strategy.long)\n'
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open", leverage=10),
    )
    assert out.status == "ok", out.error
    trade = out.result.trades[0]
    assert trade.liquidated
    assert trade.entry_bar_index == trade.exit_bar_index == 1
    assert trade.drawdown_abs == -trade.pnl
    assert trade.runup_abs == 0


def test_unknown_intrabar_entry_does_not_invent_funding() -> None:
    frame = candles(3)
    frame.loc[frame.index[1], ["high", "close"]] = [110.0, 110.0]
    frame.loc[frame.index[2], ["open", "high", "low", "close"]] = [110.0] * 4
    source = '//@version=5\nstrategy("Conditional")\nif bar_index == 0\n    strategy.entry("L", strategy.long, stop=105)\n'
    funding = pd.Series([Decimal("0.001"), Decimal("0.002")], index=frame.index[[1, 2]])
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h"),
        funding_rates=funding,
    )
    assert out.status == "ok", out.error
    assert out.result.trades[0].entry_phase == "intrabar_unknown"
    assert out.result.metrics.total_funding == Decimal("0.22")
    assert out.result.metrics.funding_data_incomplete is True
    assert any("봉 내부 체결 시각" in warning for warning in out.parse.warnings)


@pytest.mark.parametrize("freq", ["1h", "4h", "1D"])
@pytest.mark.parametrize("timing", ["bar_close", "next_bar_open"])
def test_settlement_inside_candle_respects_entry_phase(freq, timing) -> None:
    frame = candles(4)
    frame.index = pd.date_range("2026-01-01", periods=4, freq=freq, tz="UTC")
    signal_bar = 0 if timing == "next_bar_open" else 1
    source = (
        '//@version=5\nstrategy("Inside candle")\n'
        f'if bar_index == {signal_bar}\n    strategy.entry("L", strategy.long)\n'
    )
    settlement = frame.index[1] + (frame.index[2] - frame.index[1]) / 2
    funding = pd.Series([Decimal("0.001")], index=pd.DatetimeIndex([settlement]))
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq=freq, fill_timing=timing),
        funding_rates=funding,
    )
    assert out.status == "ok", out.error
    assert out.result.metrics.total_funding == (
        Decimal("0.1") if timing == "next_bar_open" else Decimal("0")
    )


@pytest.mark.parametrize("action", ["strategy.close_all()", 'strategy.entry("S", strategy.short)'])
def test_next_open_close_all_and_reversal_preserve_exit_phase(action) -> None:
    frame = candles(3)
    frame.loc[frame.index[2], ["high", "low"]] = [120.0, 80.0]
    source = (
        '//@version=5\nstrategy("Closing phase")\n'
        'if bar_index == 0\n    strategy.entry("L", strategy.long)\n'
        f"if bar_index == 1\n    {action}\n"
    )
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(fees=0, slippage=0, freq="1h", fill_timing="next_bar_open"),
    )
    assert out.status == "ok", out.error
    closed = next(trade for trade in out.result.trades if trade.status == "closed")
    assert closed.exit_phase == "bar_open"
    assert (closed.runup_abs, closed.drawdown_abs) == (Decimal("0"), Decimal("0"))
