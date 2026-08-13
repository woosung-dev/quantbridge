"""position epoch 이 warmup 재생 포지션을 outbox 상태에서 격리하는지 검증한다."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical, run_live
from src.strategy.pine_v2.strategy_state import LedgerSeedLeg


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


# --- BL-544: 원장 seed (discard_state_before_epoch 의 대칭) --------------------

_LEDGER_LONG = (LedgerSeedLeg(trade_id="L", direction="long", qty=0.029, entry_price=64166.9),)


def test_ledger_seed_adopts_position_the_replay_never_made() -> None:
    """재생이 만들지 못한 포지션을 원장이 마지막 bar 에 들여온다 (BL-544)."""
    source = """//@version=5
strategy("never enters")
plot(close)
"""
    ohlcv = _ohlcv([100.0, 101.0, 102.0])

    without_seed = run_live(source, ohlcv)
    with_seed = run_live(source, ohlcv, ledger_seed_legs=_LEDGER_LONG)

    assert without_seed.strategy_state_report["position_size"] == 0.0
    assert without_seed.ledger_seed_applied == ()
    assert with_seed.ledger_seed_applied == ("L",)
    assert with_seed.strategy_state_report["position_size"] == 0.029
    seeded = with_seed.strategy_state_report["open_trades"][0]
    assert seeded["id"] == "L"
    assert seeded["entry_price"] == 64166.9
    assert seeded["entry_bar"] == len(ohlcv) - 1


def test_ledger_seed_is_idempotent_when_replay_already_holds_a_position() -> None:
    """★멱등 — 재생이 같은 포지션을 이미 열었으면 채택하지 않는다(이중 계상 금지).

    이 가드가 없으면 엔진이 거래소의 두 배를 들고, 그 값이 사이징과 청산 판정에 그대로 쓰인다.
    """
    ohlcv = _ohlcv([100.0, 101.0, 102.0])

    baseline = run_live(_BUY_ON_GREEN, ohlcv)
    seeded = run_live(_BUY_ON_GREEN, ohlcv, ledger_seed_legs=_LEDGER_LONG)

    assert baseline.strategy_state_report["position_size"] > 0.0
    assert seeded.ledger_seed_applied == ()
    assert (
        seeded.strategy_state_report["position_size"]
        == baseline.strategy_state_report["position_size"]
    )


def test_ledger_seed_is_visible_to_pine_on_the_last_bar() -> None:
    """채택한 포지션은 **그 bar 의 Pine 실행**이 본다 — 그래야 전략이 고아를 닫을 수 있다.

    seed 를 `interp.execute` 뒤나 중간 bar 에 두면 이 close 가 나오지 않는다.
    """
    source = """//@version=5
strategy("close whatever is open")
if strategy.position_size > 0
    strategy.close("L")
"""
    ohlcv = _ohlcv([100.0, 101.0, 102.0])

    without_seed = run_live(source, ohlcv)
    with_seed = run_live(source, ohlcv, ledger_seed_legs=_LEDGER_LONG)

    assert [signal.action for signal in without_seed.signals] == []
    assert [(s.action, s.direction, s.trade_id) for s in with_seed.signals] == [
        ("close", "long", "L")
    ]


def test_ledger_seed_default_leaves_run_historical_byte_identical() -> None:
    """기본값에서는 훅 자체가 돌지 않는다 — 기존 결과와 동일."""
    ohlcv = _ohlcv([100.0, 99.0, 101.0, 100.0])

    default = run_historical(_BUY_AND_CLOSE, ohlcv, strict=True)
    explicit = run_historical(_BUY_AND_CLOSE, ohlcv, strict=True, ledger_seed_legs=())

    assert default.strategy_state is not None
    assert explicit.strategy_state is not None
    default_report = default.strategy_state.to_report()
    explicit_report = explicit.strategy_state.to_report()
    # flat 이면 `position_avg_price` 가 NaN 이고 NaN != NaN 이라 통째 비교가 안 된다.
    assert math.isnan(default_report.pop("position_avg_price"))
    assert math.isnan(explicit_report.pop("position_avg_price"))
    assert default_report == explicit_report
    assert default.ledger_seed_applied == () == explicit.ledger_seed_applied
