"""부모봉 내부 펀딩과 정확한 분봉 범위를 공통 원장으로 검증한다."""

from decimal import Decimal

import pandas as pd
import pytest

from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.python_runtime.protocol import PythonRuntimeError
from tests.strategy.code_runtime.test_backtest import Tape, cfg, frame


def inputs():
    parent = frame([(100, 101, 99, 100)] * 3)
    child = pd.DataFrame(
        {"open": "100", "high": "101", "low": "99", "close": "100", "volume": "1"},
        index=pd.date_range(parent.index[0], periods=180, freq="1min", tz="UTC"),
    )
    return parent, child


def test_funding_inside_parent_bar_uses_actual_remaining_position():
    parent, child = inputs()
    tape = Tape({1: {"action": "long"}})
    trace = []
    result = run_code_backtest(
        "test",
        "python",
        parent,
        cfg(include_funding=True),
        pd.Series([Decimal("0.001")], index=child.index[[150]]),
        transport_factory=lambda: tape,
        trace=trace,
        execution_ohlcv=child,
    )
    assert len(result.equity_curve) == 180
    assert result.equity_curve.iloc[-1] == result.config_used.init_cash - Decimal("1")
    funding = [event for event in trace if event["type"] == "funding"]
    assert funding[0]["timestamp"] == child.index[150].isoformat()
    assert Decimal(funding[0]["amount"]) == Decimal("1")


@pytest.mark.parametrize("change", ["missing", "different_high"])
def test_child_data_cannot_silently_replace_parent_or_leave_gaps(change):
    parent, child = inputs()
    if change == "missing":
        child = child.drop(child.index[70])
    else:
        child.loc[child.index[70], "high"] = "102"
    with pytest.raises(PythonRuntimeError):
        run_code_backtest(
            "test",
            "python",
            parent,
            cfg(),
            execution_ohlcv=child,
            transport_factory=lambda: Tape({}),
        )
