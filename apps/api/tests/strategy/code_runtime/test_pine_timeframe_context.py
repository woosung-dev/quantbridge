"""명시 주기 provenance가 host load→worker→BarContext까지 검증되어 전달된다."""

import io
import json
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

from src.strategy.code_runtime import pine_worker
from src.strategy.code_runtime.models import CodeRuntimeError
from src.strategy.code_runtime.pine import (
    PineSignalTransport,
    _PineInterpreterTransport,
    validated_timeframe,
)
from src.strategy.python_runtime.sandbox import DockerPythonTransport
from src.strategy.python_runtime.serialization import bars_payload

SOURCE = """//@version=5
strategy("explicit timeframe")
if timeframe.period == "60" and timeframe.multiplier == 60 and timeframe.isminutes
    strategy.entry("L", strategy.long)
"""


def frame(tf="1h", *, freq="h", start="2026-01-01T00:00Z", periods=3):
    data = pd.DataFrame(
        {k: [100.0] * periods for k in ("open", "high", "low", "close", "volume")},
        index=pd.date_range(start, periods=periods, freq=freq),
    )
    if tf is not None:
        data.attrs["timeframe"] = tf
    return data


@pytest.mark.parametrize(
    "tf,freq,start",
    [
        ("1s", "s", "2026-01-01T00:00Z"),
        ("45s", "45s", "2026-01-01T00:00Z"),
        ("3m", "3min", "2026-01-01T00:00Z"),
        ("1h", "h", "2026-01-01T00:00Z"),
        ("4h", "4h", "2026-01-01T00:00Z"),
        ("1d", "D", "2026-01-01T00:00Z"),
        ("1w", "7D", "2026-01-05T00:00Z"),
    ],
)
def test_explicit_context_matches_actual_utc_grid_without_mutating_frame(tf, freq, start):
    data = frame(tf, freq=freq, start=start)
    before = data.copy(deep=True)
    assert validated_timeframe(data) == tf
    pd.testing.assert_frame_equal(data, before)
    assert data.attrs == before.attrs


@pytest.mark.parametrize("tf", [None, True, "0h", "1M", "1D", "60", "2d", "2w", "5h", "7m"])
def test_invalid_explicit_context_fails_before_any_docker_start(tf):
    data = frame()
    data.attrs["timeframe"] = tf
    with patch.object(DockerPythonTransport, "__init__") as start:
        with pytest.raises(CodeRuntimeError):
            PineSignalTransport(data)
        start.assert_not_called()


@pytest.mark.parametrize(
    "change", ["single", "naive", "duplicate", "reverse", "gap", "spacing", "grid", "week_grid"]
)
def test_context_rejects_unproven_or_inconsistent_datetime_grid(change):
    data = frame()
    if change == "single":
        data = data.iloc[:1].copy()
    elif change == "naive":
        data.index = data.index.tz_localize(None)
    elif change == "duplicate":
        data.index = pd.DatetimeIndex([data.index[0], data.index[0], data.index[2]])
    elif change == "reverse":
        data = data.iloc[::-1].copy()
    elif change == "gap":
        data.index = pd.DatetimeIndex(
            [data.index[0], data.index[1], data.index[2] + pd.Timedelta(hours=1)]
        )
    elif change == "spacing":
        data.attrs["timeframe"] = "4h"
    elif change == "grid":
        data.index += pd.Timedelta(minutes=30)
    else:
        data = frame("1w", freq="7D", start="2026-01-01T00:00Z")
    with pytest.raises(CodeRuntimeError):
        validated_timeframe(data)


def test_load_message_carries_only_explicit_validated_context():
    for data, expected in [(frame(), "1h"), (frame(None), None)]:
        with (
            patch.object(DockerPythonTransport, "__init__", return_value=None),
            patch.object(
                DockerPythonTransport,
                "exchange",
                return_value=(
                    {"loaded": True, "timeframe": expected}
                    if expected is not None
                    else {"loaded": True}
                ),
            ) as exchange,
        ):
            PineSignalTransport(data)
        message = exchange.call_args.args[0]
        assert message["type"] == "load"
        assert len(message["bars"]) == 3
        if expected is None:
            assert "timeframe" not in message
        else:
            assert message["timeframe"] == expected


def test_host_adapter_uses_verified_context_but_does_not_clear_security_degradation():
    engine = _PineInterpreterTransport(frame())
    assert engine.exchange({"type": "init", "protocol": 1, "source": SOURCE, "params": {}}) == {
        "ready": 1
    }
    assert engine._interpreter.bar.timeframe == "1h"
    assert engine.exchange(
        {
            "type": "bar",
            "bar": {"index": 0},
            "position": {"direction": "flat", "size": "0", "average_price": None},
        }
    ) == {"intent": {"action": "long"}}
    assert engine._interpreter.bar.timeframe_attribute("timeframe.period") == "60"
    assert frame(None).attrs == {}
    with pytest.raises(CodeRuntimeError, match="context"):
        _PineInterpreterTransport(frame(None)).exchange(
            {"type": "init", "protocol": 1, "source": SOURCE, "params": {}}
        )
    source = '//@version=5\nstrategy("external request")\nx=request.security("BYBIT:BTCUSDT.P","D",close)\n'
    with pytest.raises(CodeRuntimeError, match="근사"):
        _PineInterpreterTransport(frame()).exchange(
            {"type": "init", "protocol": 1, "source": source, "params": {}}
        )


def worker(messages, monkeypatch):
    from src.core.config import settings

    output = io.StringIO()
    with monkeypatch.context() as scope:
        scope.setattr(sys, "stdin", io.StringIO("".join(json.dumps(m) + "\n" for m in messages)))
        scope.setattr(sys, "stdout", output)
        scope.setattr(sys, "path", list(sys.path))
        scope.setattr(settings, "pine_ast_cache_dir", settings.pine_ast_cache_dir)
        scope.setenv("TRADING_ENCRYPTION_KEYS", os.environ.get("TRADING_ENCRYPTION_KEYS", ""))
        pine_worker.main()
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_worker_protocol_load_reconstructs_explicit_timeframe_and_intent(monkeypatch):
    messages = [
        {"type": "load", "bars": bars_payload(frame()), "timeframe": "1h"},
        {"type": "init", "protocol": 1, "source": SOURCE, "params": {}},
        {
            "type": "bar",
            "bar": {"index": 0},
            "position": {"direction": "flat", "size": "0", "average_price": None},
        },
    ]
    assert worker(messages, monkeypatch) == [
        {"loaded": True, "timeframe": "1h"},
        {"ready": 1},
        {"intent": {"action": "long"}},
    ]


def test_worker_does_not_manufacture_utc_for_naive_context_timestamps(monkeypatch):
    bars = bars_payload(frame())
    for bar in bars:
        bar["timestamp"] = pd.Timestamp(bar["timestamp"]).tz_localize(None).isoformat()
    result = worker([{"type": "load", "bars": bars, "timeframe": "1h"}], monkeypatch)
    assert len(result) == 1 and "timezone-aware" in result[0]["error"]


def test_legacy_worker_without_timeframe_keeps_plain_strategy_compatible(monkeypatch):
    source = (
        '//@version=5\nstrategy("legacy")\nif bar_index==0\n    strategy.entry("L",strategy.long)\n'
    )
    messages = [
        {"type": "load", "bars": bars_payload(frame(None))},
        {"type": "init", "protocol": 1, "source": source, "params": {}},
        {
            "type": "bar",
            "bar": {"index": 0},
            "position": {"direction": "flat", "size": "0", "average_price": None},
        },
    ]
    assert worker(messages, monkeypatch) == [
        {"loaded": True},
        {"ready": 1},
        {"intent": {"action": "long"}},
    ]


def test_worker_verified_timeframe_reaches_calendar_and_boundary_functions(monkeypatch):
    source = '//@version=6\nstrategy("worker daily boundary")\nif timeframe.change("D") and year==2026 and hour==0\n    strategy.entry("L",strategy.long)\n'
    messages = [
        {"type": "load", "bars": bars_payload(frame("1d", freq="D")), "timeframe": "1d"},
        {"type": "init", "protocol": 1, "source": source, "params": {}},
    ]
    messages += [
        {
            "type": "bar",
            "bar": {"index": index},
            "position": {"direction": "flat", "size": "0", "average_price": None},
        }
        for index in range(3)
    ]
    assert worker(messages, monkeypatch) == [
        {"loaded": True, "timeframe": "1d"},
        {"ready": 1},
        {"intent": {"action": "hold"}},
        {"intent": {"action": "long"}},
        {"intent": {"action": "long"}},
    ]


def test_old_worker_cannot_silently_ignore_new_timeframe_field():
    with (
        patch.object(DockerPythonTransport, "__init__", return_value=None),
        patch.object(DockerPythonTransport, "exchange", return_value={"loaded": True}),
        patch.object(DockerPythonTransport, "close") as close,
    ):
        with pytest.raises(CodeRuntimeError, match="timeframe"):
            PineSignalTransport(frame())
        close.assert_called_once()
