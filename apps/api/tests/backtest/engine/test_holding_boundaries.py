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
    stats = out.result.metrics.excursion_stats
    assert stats.max_drawdown_intrabar_abs == -trade.pnl
    assert stats.max_runup_intrabar_abs == -trade.pnl


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


@pytest.mark.parametrize("direction", ["long", "short"])
@pytest.mark.parametrize("timing", ["bar_close", "next_bar_open"])
@pytest.mark.parametrize("wick_bar", [1, 2])
def test_public_equity_extremes_respect_market_fill_boundaries(direction, timing, wick_bar):
    frame = candles(4)
    frame.loc[frame.index[wick_bar], ["high", "low"]] = [120.0, 80.0]
    entry_signal, exit_signal = (1, 2) if timing == "bar_close" else (0, 1)
    source = (
        '//@version=5\nstrategy("Equity boundary")\n'
        f'if bar_index == {entry_signal}\n    strategy.entry("T", strategy.{direction})\n'
        f'if bar_index == {exit_signal}\n    strategy.close("T")\n'
    )
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(
            init_cash=Decimal("1000"), fees=0, slippage=0, freq="1h", fill_timing=timing
        ),
    )
    assert out.status == "ok", out.error
    result = out.result
    assert result is not None
    assert list(result.equity_curve) == [Decimal("1000")] * 4
    assert result.metrics.total_return == result.metrics.max_drawdown == 0
    assert all(value == 0 for _, value in result.metrics.drawdown_curve)
    held_wick = wick_bar == (2 if timing == "bar_close" else 1)
    expected = Decimal("40") if held_wick else Decimal("0")
    stats = result.metrics.excursion_stats
    assert stats.max_runup_intrabar_abs == expected
    assert stats.max_drawdown_intrabar_abs == expected


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("rate", [Decimal("0"), Decimal("0.01"), Decimal("-0.01")])
def test_exit_wick_uses_pre_exit_pnl_and_costs(reverse, rate):
    frame = candles(4)
    frame.loc[frame.index[2], ["high", "low", "close"]] = [120.0, 90.0, 110.0]
    frame.loc[frame.index[3], ["open", "high", "low", "close"]] = [110.0] * 4
    action = 'strategy.entry("S", strategy.short)' if reverse else 'strategy.close("L")'
    source = (
        '//@version=5\nstrategy("Exit costs")\n'
        'if bar_index == 1\n    strategy.entry("L", strategy.long)\n'
        f"if bar_index == 2\n    {action}\n"
    )
    funding = pd.Series([rate], index=frame.index[[2]])
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(init_cash=Decimal("1000"), fees=0.01, slippage=0, freq="1h"),
        funding_rates=funding,
    )
    assert out.status == "ok", out.error
    result = out.result
    assert result is not None
    cost = Decimal("110") * rate
    final = Decimal("1007.9") - cost - (Decimal("1.1") if reverse else 0)
    assert list(result.equity_curve) == [Decimal("1000"), Decimal("999"), final, final]
    assert result.metrics.net_profit_abs == Decimal("7.9")
    assert result.metrics.total_fees == (Decimal("3.2") if reverse else Decimal("2.1"))
    assert result.metrics.total_funding == cost
    assert result.metrics.total_return == (final - Decimal("1000")) / Decimal("1000")
    assert float(result.metrics.max_drawdown) == pytest.approx(-0.001)
    stats = result.metrics.excursion_stats
    # 청산 전 equity = high 1019 / low 989. 청산 수수료·새 short 진입 수수료는
    # wick에 소급하지 않으며 funding만 기존 봉 총액 근사대로 양쪽에 선차감한다.
    assert stats.max_runup_intrabar_abs == stats.max_drawdown_intrabar_abs == Decimal("30")
    assert stats.max_runup_intrabar_pct == Decimal("30") / (Decimal("989") - cost)
    assert stats.max_drawdown_intrabar_pct == Decimal("30") / (Decimal("1019") - cost)


@pytest.mark.parametrize("kind", ["entry", "exit", "reversal"])
def test_unknown_intrabar_exposure_uses_only_known_equity_points(kind):
    frame = candles(3)
    frame.loc[frame.index[1], ["high", "low"]] = [120.0, 80.0]
    if kind == "entry":
        frame.loc[frame.index[1], "close"] = 110.0
        frame.loc[frame.index[2], ["open", "high", "low", "close"]] = [110.0] * 4
        orders = 'strategy.entry("L", strategy.long, stop=105)'
        expected_up, expected_down, final = "5", "5", "1005"
    elif kind == "exit":
        orders = 'strategy.entry("L", strategy.long)\n    strategy.exit("X", "L", stop=95)'
        expected_up, expected_down, final = "5", "5", "995"
    else:
        orders = (
            'strategy.entry("L", strategy.long)\n    strategy.entry("S", strategy.short, stop=95)'
        )
        expected_up, expected_down, final = "10", "10", "990"
    source = f'//@version=5\nstrategy("Unknown exposure")\nif bar_index == 0\n    {orders}\n'
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(init_cash=Decimal("1000"), fees=0, slippage=0, freq="1h"),
    )
    assert out.status == "ok", out.error
    result = out.result
    assert result is not None
    assert result.equity_curve.iloc[-1] == Decimal(final)
    stats = result.metrics.excursion_stats
    # 실제 순서가 아니라 확인한 봉 시작/마감 equity의 양방향 범위 근사다.
    assert stats.max_runup_intrabar_abs == Decimal(expected_up)
    assert stats.max_drawdown_intrabar_abs == Decimal(expected_down)
    assert any("확실한 가격점" in warning for warning in out.parse.warnings)


def test_next_open_gap_exit_preserves_price_loss_and_both_leg_costs():
    frame = candles(3)
    frame.loc[frame.index[2], ["open", "high", "low", "close"]] = [90.0, 120.0, 20.0, 90.0]
    source = (
        '//@version=5\nstrategy("Gap exit")\n'
        'if bar_index == 0\n    strategy.entry("L", strategy.long)\n'
        'if bar_index == 1\n    strategy.close("L")\n'
    )
    out = run_backtest_v2(
        source,
        frame,
        BacktestConfig(
            init_cash=Decimal("1000"), fees=0.01, slippage=0, freq="1h", fill_timing="next_bar_open"
        ),
    )
    assert out.status == "ok", out.error
    result = out.result
    assert result is not None
    assert list(result.equity_curve) == [Decimal("1000"), Decimal("999"), Decimal("988.1")]
    assert result.metrics.net_profit_abs == Decimal("-11.9")
    assert result.metrics.total_fees == Decimal("1.9")
    assert result.metrics.excursion_stats.max_drawdown_intrabar_abs == Decimal("11.9")
    # 동일 봉 비용 차이도 기존 양방향 범위 근사에 포함된다. 실제 회복 순서가 아니다.
    assert result.metrics.excursion_stats.max_runup_intrabar_abs == Decimal("1")
