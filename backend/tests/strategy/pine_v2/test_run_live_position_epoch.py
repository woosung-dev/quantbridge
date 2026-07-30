"""position epoch 이 warmup 재생 포지션을 outbox 상태에서 격리하는지 검증한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical, run_live


def _ohlcv(closes: list[float], *, start: datetime | None = None) -> pd.DataFrame:
    """timestamp를 포함한 결정론적 OHLCV 프레임을 만든다."""
    if start is None:
        start = datetime(2026, 5, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=index) for index in range(len(closes))],
            "open": [closes[0], *closes[:-1]],
            "high": [close * 1.02 for close in closes],
            "low": [close * 0.98 for close in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


_BUY_ON_GREEN = """//@version=5
strategy("buy on green bar")
if close > open
    strategy.entry("L", strategy.long, qty=1.0)
"""


_BUY_AND_CLOSE = """//@version=5
strategy("buy and close")
if close > open
    strategy.entry("L", strategy.long, qty=1.0)
if close < open
    strategy.close("L")
"""


_BUY_WITH_TRAILING_EXIT = """//@version=5
strategy("buy with trailing exit")
if close > open
    strategy.entry("L", strategy.long, qty=1.0)
strategy.exit("X", "L", trail_offset=3.0)
"""


def test_position_epoch_none_keeps_warmup_position_as_control() -> None:
    """epoch 미지정 대조군은 재생 구간의 long을 그대로 남긴다."""
    result = run_live(
        _BUY_ON_GREEN,
        _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0, 95.0]),
        position_epoch=None,
    )

    assert result.strategy_state_report["position_size"] == 1.0


def test_position_epoch_at_last_bar_discards_warmup_position() -> None:
    """마지막 bar epoch은 그 전 재생에서 열린 포지션을 폐기한다."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0, 95.0])

    result = run_live(_BUY_ON_GREEN, ohlcv, position_epoch=ohlcv.iloc[-1]["timestamp"])

    assert result.strategy_state_report["position_size"] == 0.0
    assert result.strategy_state_report["open_trades"] == []


def test_epoch_discard_does_not_disguise_a_close_or_keep_pnl() -> None:
    """epoch 이전의 실현손익은 폐기되고, epoch 미지정 대조군에는 남는다."""
    ohlcv = _ohlcv([100.0, 99.0, 101.0, 99.0, 101.0, 95.0])

    control_live_result = run_live(
        _BUY_AND_CLOSE,
        ohlcv,
        initial_capital=1000.0,
        position_epoch=None,
    )
    control_historical_result = run_historical(
        _BUY_AND_CLOSE,
        ohlcv,
        strict=True,
        initial_capital=1000.0,
        position_epoch_bar=None,
    )
    control_state = control_historical_result.strategy_state

    live_result = run_live(
        _BUY_AND_CLOSE,
        ohlcv,
        initial_capital=1000.0,
        position_epoch=ohlcv.iloc[-1]["timestamp"],
    )
    historical_result = run_historical(
        _BUY_AND_CLOSE,
        ohlcv,
        strict=True,
        initial_capital=1000.0,
        position_epoch_bar=len(ohlcv) - 1,
    )
    state = historical_result.strategy_state

    assert control_state is not None
    assert control_live_result.strategy_state_report["closed_trades"] != []
    assert control_state.closed_trades != []
    assert control_state.running_equity is not None
    assert control_state.initial_capital is not None
    assert control_state.running_equity != control_state.initial_capital
    assert state is not None
    assert live_result.signals == []
    assert live_result.strategy_state_report["closed_trades"] == []
    assert live_result.strategy_state_report["total_pnl"] == 0
    assert state.closed_trades == []
    assert state.to_report()["total_pnl"] == 0
    assert state.running_equity == state.initial_capital == 1000.0


def test_position_opened_on_epoch_bar_survives() -> None:
    """epoch bar 자신이 여는 포지션은 버리지 않아 off-by-one을 막는다."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0, 95.0])

    result = run_live(_BUY_ON_GREEN, ohlcv, position_epoch=ohlcv.iloc[4]["timestamp"])

    assert result.strategy_state_report["position_size"] == 1.0


def test_catchup_entry_signal_keeps_its_open_trade_after_epoch_clamp() -> None:
    """발행한 catch-up entry는 epoch 폐기 뒤에도 실제 엔진 포지션으로 남는다."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0, 95.0])

    result = run_live(
        _BUY_ON_GREEN,
        ohlcv,
        emit_from_bar_time=ohlcv.iloc[3]["timestamp"],
        position_epoch=ohlcv.iloc[3]["timestamp"],
    )

    assert [(signal.action, signal.trade_id, signal.bar_time) for signal in result.signals] == [
        ("entry", "L", ohlcv.iloc[4]["timestamp"])
    ]
    assert result.strategy_state_report["position_size"] == 1.0
    open_trades = result.strategy_state_report["open_trades"]
    assert len(open_trades) == 1
    assert open_trades[0]["id"] == "L"
    assert open_trades[0]["entry_bar"] == 4


def test_epoch_discards_pending_exit_levels_for_removed_trade() -> None:
    """폐기된 거래의 trailing exit leg는 이후 같은 id를 오염시키지 않는다."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0, 95.0])
    result = run_historical(
        _BUY_WITH_TRAILING_EXIT,
        ohlcv,
        strict=True,
        position_epoch_bar=len(ohlcv) - 1,
    )
    state = result.strategy_state

    assert state is not None
    assert state.exit_levels_for("L") == (None, None, None)


def test_position_epoch_after_all_bars_clamps_to_last_bar() -> None:
    """창보다 미래의 epoch은 마지막 bar에서 warmup 상태를 폐기한다."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0, 95.0])

    result = run_live(
        _BUY_ON_GREEN,
        ohlcv,
        position_epoch=ohlcv.iloc[-1]["timestamp"] + timedelta(days=1),
    )

    assert result.strategy_state_report["position_size"] == 0.0


def test_epoch_preserves_intent_until_close_all_applies_existing_contract() -> None:
    """epoch은 pending order를 직접 지우지 않지만 close_all 인텐트는 기존대로 지운다."""
    source = """//@version=5
strategy("close all clears pending order")
if bar_index == 0
    strategy.entry("P", strategy.long, qty=1.0, stop=999.0)
if bar_index == 1
    strategy.close_all()
"""
    ohlcv = _ohlcv([100.0, 100.0, 100.0])
    before_epoch = run_historical(
        source,
        ohlcv.iloc[:2],
        strict=True,
        fill_timing="next_bar_open",
    )
    at_epoch = run_historical(
        source,
        ohlcv,
        strict=True,
        fill_timing="next_bar_open",
        position_epoch_bar=2,
    )

    assert before_epoch.strategy_state is not None
    assert "P" in before_epoch.strategy_state.pending_orders
    assert at_epoch.strategy_state is not None
    assert at_epoch.strategy_state.pending_orders == {}
