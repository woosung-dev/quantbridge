"""Python 신뢰 경계·체결·재현 계약. DB/Celery 를 사용하지 않는다."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import threading
import uuid
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.backtest.engine.python_adapter import run_python_backtest
from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.python_runtime.gateway import create_app
from src.strategy.python_runtime.protocol import (
    PythonRunnerUnavailable,
    PythonRuntimeError,
    validate_intent,
)
from src.strategy.python_runtime.sandbox import DockerPythonTransport, sandbox_command
from src.strategy.python_runtime.serialization import (
    bars_payload,
    json_value,
    result_from_payload,
    result_payload,
)

SOURCE = "def on_bar(ctx, state): return {'action': 'hold'}"
TOKEN = "test-runner-token-with-at-least-32-characters"
HEADERS = {"Authorization": "Bearer " + TOKEN}


def bars(count: int = 6) -> pd.DataFrame:
    prices = list(range(100, 100 + count))
    return pd.DataFrame(
        {
            "open": prices,
            "high": [p + 1 for p in prices],
            "low": [p - 1 for p in prices],
            "close": prices,
            "volume": [100] * count,
        },
        index=pd.date_range("2025-01-01", periods=count, freq="1h", tz="UTC"),
    )


def config(**changes: Any) -> BacktestConfig:
    return replace(
        BacktestConfig(freq="1h", default_qty_type="strategy.fixed", default_qty_value=1), **changes
    )


class ScriptedTransport:
    image_id = "sha256:" + "1" * 64

    def __init__(self, actions: dict[int, dict[str, Any]] | None = None):
        self.actions = actions or {}
        self.messages: list[dict[str, Any]] = []
        self.closed = False

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        self.messages.append(copy.deepcopy(message))
        if message["type"] == "init":
            return {"ready": 1}
        return {"intent": self.actions.get(message["bar"]["index"], {"action": "hold"})}

    def close(self) -> None:
        self.closed = True


def test_python_and_pine_share_next_open_fees_equity_and_funding() -> None:
    frame = bars()
    rates = pd.Series([Decimal("0.001")] * 3, index=frame.index[[0, 2, 5]])
    cfg = config(fill_timing="next_bar_open", include_funding=True)
    python = run_python_backtest(
        SOURCE,
        frame,
        cfg,
        rates,
        transport_factory=lambda: ScriptedTransport(
            {0: {"action": "long"}, 3: {"action": "close"}}
        ),
    )
    pine = run_backtest_v2(
        '//@version=5\nstrategy("Parity")\nif bar_index == 0\n    strategy.entry("L", strategy.long, qty=1)\nif bar_index == 3\n    strategy.close("L")\n',
        frame,
        cfg,
        rates,
    )
    assert pine.status == "ok" and pine.result is not None
    assert python.trades == pine.result.trades
    assert python.metrics == pine.result.metrics
    pd.testing.assert_series_equal(python.equity_curve, pine.result.equity_curve)
    assert python.trades[0].entry_bar_index == 1
    assert python.trades[0].exit_bar_index == 4
    assert python.metrics.total_funding == Decimal("0.1020")


def test_controller_streams_only_current_bar_and_appending_future_keeps_prefix() -> None:
    short = ScriptedTransport({0: {"action": "long"}, 2: {"action": "close"}})
    long = ScriptedTransport(short.actions)
    first = run_python_backtest(SOURCE, bars(4), config(), transport_factory=lambda: short)
    extended = run_python_backtest(SOURCE, bars(8), config(), transport_factory=lambda: long)
    assert short.messages == long.messages[: len(short.messages)]
    assert set(short.messages[0]) == {"type", "source", "protocol", "params"}
    for index, message in enumerate(short.messages[1:]):
        assert set(message) == {"type", "bar", "position"}
        assert message["bar"]["index"] == index
    assert first.trades == extended.trades
    assert short.closed and long.closed


def test_warmup_signals_do_not_trade_or_enter_metrics() -> None:
    fake = ScriptedTransport({0: {"action": "long"}, 2: {"action": "long"}, 3: {"action": "close"}})
    result = run_python_backtest(
        SOURCE, bars(), config(), warmup_bars=2, transport_factory=lambda: fake
    )
    assert list(result.equity_curve.index) == list(bars().index[2:])
    assert result.trades[0].entry_bar_index == 1
    assert result.trades[0].entry_price == Decimal("103.0")
    assert result.trades[0].exit_bar_index == 2
    assert fake.messages[3]["position"]["direction"] == "flat"


def test_entry_bracket_is_active_on_next_open_bar_and_stop_wins() -> None:
    fake = ScriptedTransport({0: {"action": "long", "stop_loss": "100", "take_profit": "102"}})
    result = run_python_backtest(SOURCE, bars(), config(), transport_factory=lambda: fake)
    trade = result.trades[0]
    assert trade.entry_bar_index == trade.exit_bar_index == 1
    assert trade.exit_price == Decimal("100.0")
    assert trade.exit_kind == "stop_loss"
    assert trade.pnl < 0


def test_reverse_signal_has_one_position_and_last_signal_is_unfilled() -> None:
    fake = ScriptedTransport({0: {"action": "long"}, 1: {"action": "short"}, 5: {"action": "long"}})
    result = run_python_backtest(SOURCE, bars(), config(), transport_factory=lambda: fake)
    assert len(result.trades) == 2
    assert [t.direction for t in result.trades] == ["long", "short"]
    assert result.trades[0].exit_bar_index == result.trades[1].entry_bar_index == 2
    assert result.trades[1].status == "open"


@pytest.mark.parametrize(
    "intent",
    [
        {"action": "buy"},
        {"action": "hold", "pnl": "100"},
        {"action": "long", "stop_loss": "NaN"},
        {"action": "long", "stop_loss": 90},
        {"action": "long", "take_profit": "-1"},
    ],
)
def test_untrusted_intent_validation_rejects_authority_or_nonfinite_values(intent: Any) -> None:
    with pytest.raises(PythonRuntimeError):
        validate_intent(intent)


def test_invalid_intent_closes_transport_and_discards_partial_results() -> None:
    fake = ScriptedTransport({0: {"action": "long"}, 2: {"action": "hold", "pnl": "1"}})
    with pytest.raises(PythonRuntimeError):
        run_python_backtest(SOURCE, bars(), config(), transport_factory=lambda: fake)
    assert fake.closed


def test_missing_bars_or_missing_funding_fail_before_source_runs() -> None:
    def forbidden() -> Any:
        raise AssertionError("잘못된 데이터에서 실행기를 시작했습니다")

    with pytest.raises(PythonRuntimeError, match="빈 구간"):
        run_python_backtest(
            SOURCE, bars().drop(bars().index[2]), config(), transport_factory=forbidden
        )
    with pytest.raises(PythonRuntimeError, match="펀딩"):
        run_python_backtest(
            SOURCE, bars(), config(include_funding=True), transport_factory=forbidden
        )


def test_result_wire_round_trip_preserves_decimals_and_nested_metrics() -> None:
    result = run_python_backtest(
        SOURCE,
        bars(),
        config(),
        transport_factory=lambda: ScriptedTransport(
            {0: {"action": "long"}, 2: {"action": "close"}}
        ),
    )
    decoded = result_from_payload(json.loads(json.dumps(result_payload(result))))
    assert decoded.metrics == result.metrics
    assert decoded.trades == result.trades
    assert decoded.config_used == result.config_used
    pd.testing.assert_series_equal(decoded.equity_curve, result.equity_curve, check_freq=False)


def test_sandbox_command_has_no_host_mount_or_secret_and_requires_gvisor() -> None:
    command = sandbox_command("sha256:" + "1" * 64, "qb-python-test")
    for flag in (
        "--runtime=runsc",
        "--network=none",
        "--read-only",
        "--user=10001:10001",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=64",
        "--cpus=1",
        "--memory=1g",
        "--memory-swap=1g",
    ):
        assert flag in command
    assert not any(
        flag in command for flag in ("--mount", "-v", "--volume", "--env-file", "--privileged")
    )


def test_missing_runsc_fails_closed_without_starting_host_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args[0], 0, b'{"runc":{}}', b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *a, **kw: pytest.fail("runsc 미등록인데 프로세스를 시작했습니다"),
    )
    with pytest.raises(PythonRunnerUnavailable, match="runsc"):
        DockerPythonTransport()


def test_host_modules_do_not_execute_python_source() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src"
    paths = [
        *(source_root / "strategy/python_runtime").glob("*.py"),
        source_root / "backtest/engine/python_adapter.py",
    ]
    for path in paths:
        calls = [
            node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.Call)
        ]
        assert not any(
            isinstance(call.func, ast.Name) and call.func.id in {"exec", "eval", "compile"}
            for call in calls
        ), path


def request_body(job_id: str | None = None) -> dict[str, Any]:
    return {
        "job_id": job_id or str(uuid.uuid4()),
        "source": SOURCE,
        "bars": bars_payload(bars()),
        "config": json_value(config()),
        "params": {},
        "warmup_bars": 0,
    }


def test_gateway_auth_cancel_before_submission_and_provenance() -> None:
    with TestClient(create_app(TOKEN, transport_factory=ScriptedTransport)) as client:
        assert client.post("/v1/backtests", json=request_body()).status_code == 401
        cancelled_id = str(uuid.uuid4())
        assert (
            client.post(f"/v1/backtests/{cancelled_id}/cancel", headers=HEADERS).json()["status"]
            == "cancelled"
        )
        assert (
            client.post(
                "/v1/backtests", json=request_body(cancelled_id), headers=HEADERS
            ).status_code
            == 409
        )
        response = client.post("/v1/backtests", json=request_body(), headers=HEADERS)
        assert response.status_code == 200, response.text
        record = response.json()
        assert len(record["provenance"]["environment_digest"]) == 64
        assert len(record["provenance"]["source_hash"]) == 64
        assert record["config_used"]["fill_timing"] == "next_bar_open"


def test_gateway_cancels_active_process_and_rejects_second_job() -> None:
    entered = threading.Event()
    released = threading.Event()

    class BlockingTransport(ScriptedTransport):
        def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
            if message["type"] == "bar":
                entered.set()
                assert released.wait(timeout=10)
                raise PythonRuntimeError("취소됨")
            return super().exchange(message)

        def close(self) -> None:
            released.set()
            super().close()

    with TestClient(create_app(TOKEN, transport_factory=BlockingTransport)) as client:
        job_id = str(uuid.uuid4())
        responses = []
        thread = threading.Thread(
            target=lambda: responses.append(
                client.post("/v1/backtests", json=request_body(job_id), headers=HEADERS)
            )
        )
        thread.start()
        assert entered.wait(timeout=10)
        assert client.post("/v1/backtests", json=request_body(), headers=HEADERS).status_code == 503
        assert (
            client.post(f"/v1/backtests/{job_id}/cancel", headers=HEADERS).json()["status"]
            == "cancelled"
        )
        thread.join(timeout=10)
        assert not thread.is_alive()
        assert responses[0].status_code == 422


@pytest.mark.integration
def test_real_gvisor_has_no_network_secret_host_files_or_future_bars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--run-integration 과 실제 runsc 이미지가 필요하다. 호스트 대체 실행은 없다."""
    monkeypatch.setenv("QB_PYTHON_RUNTIME_TEST_SECRET", "must-not-enter-the-container")
    source = """
import os
import socket
import numpy as np
import pandas as pd
from quantbridge_sdk import Intent

def on_bar(ctx, state):
    assert os.getuid() == 10001
    assert "QB_PYTHON_RUNTIME_TEST_SECRET" not in os.environ
    assert "DATABASE_URL" not in os.environ
    assert not os.path.exists("/var/run/docker.sock")
    assert len(ctx["history"]) == ctx["bar"]["index"] + 1
    assert ctx["history"][-1] == ctx["bar"]
    assert all(bar["index"] <= ctx["bar"]["index"] for bar in ctx["history"])
    if not state.get("checked"):
        assert pd.Series(np.array([1, 2])).sum() == 3
        for path in ("/forbidden-probe", "/runner/forbidden-probe"):
            try:
                with open(path, "w") as handle:
                    handle.write("forbidden")
            except OSError:
                pass
            else:
                raise AssertionError("root filesystem is writable")
        with socket.socket() as connection:
            connection.settimeout(0.2)
            try:
                connection.connect(("1.1.1.1", 443))
            except OSError:
                pass
            else:
                raise AssertionError("network is available")
        state["checked"] = True
    return {"action": "long" if ctx["bar"]["index"] == 0 else "hold"}
"""
    result = run_python_backtest(source, bars(4), config())
    assert result.trades[0].entry_bar_index == 1
    assert result.trades[0].entry_phase == "bar_open"
