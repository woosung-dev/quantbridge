"""실제 gVisor에서 Pine 파싱·반복·할당이 호스트를 막지 않는지 확인한다."""

from __future__ import annotations

import subprocess
import time
import unittest
from unittest.mock import patch

import pytest

from src.strategy.code_runtime.backtest import run_code_backtest
from src.strategy.code_runtime.models import CodeRuntimeError
from src.strategy.code_runtime.pine import DEFAULT_PINE_IMAGE, PineSignalTransport
from src.strategy.python_runtime.protocol import (
    PythonRunnerTimeout,
    PythonRunnerUnavailable,
    PythonRuntimeError,
)
from src.strategy.python_runtime.sandbox import _DOCKER, DockerPythonTransport
from tests.strategy.code_runtime import test_sandbox
from tests.strategy.code_runtime.test_backtest import cfg, frame


def require_pine_gvisor() -> None:
    try:
        test_sandbox.RealGvisorTests.setUpClass()
        subprocess.run(
            [_DOCKER, "image", "inspect", DEFAULT_PINE_IMAGE],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (unittest.SkipTest, subprocess.SubprocessError) as exc:
        pytest.skip(f"Pine gVisor 이미지가 필요합니다: {exc}")


def test_invalid_deadline_and_unavailable_image_never_use_host_interpreter() -> None:
    data = frame([(100, 101, 99, 100)] * 3)
    with patch.object(DockerPythonTransport, "__init__") as start:
        for timeout in (0, -1, float("inf"), float("nan")):
            with pytest.raises(CodeRuntimeError):
                PineSignalTransport(data, timeout=timeout)
        start.assert_not_called()
    with (
        patch.object(
            DockerPythonTransport, "__init__", side_effect=PythonRunnerUnavailable("missing")
        ),
        pytest.raises(PythonRunnerUnavailable, match="missing"),
    ):
        run_code_backtest('//@version=5\nstrategy("no fallback")', "pine", data, cfg())


@pytest.mark.integration
@pytest.mark.parametrize(
    ("body", "timeout"),
    [
        (
            "int total = 0\nfor i = 0 to 99999\n    for j = 0 to 99999\n        total := total + 1",
            4,
        ),
        ("values = array.new_float(2000000000, 1.0)", 15),
    ],
)
def test_large_nested_loop_and_allocation_fail_and_remove_container(body, timeout) -> None:
    require_pine_gvisor()
    data = frame([(100, 101, 99, 100)] * 3)
    transport = PineSignalTransport(data, timeout=timeout)
    name = transport.name
    started = time.monotonic()
    with pytest.raises(PythonRuntimeError) as raised:
        run_code_backtest(
            f'//@version=5\nstrategy("bounded")\n{body}\n',
            "pine",
            data,
            cfg(),
            transport_factory=lambda: transport,
        )
    if body.startswith("int total"):
        assert isinstance(raised.value, PythonRunnerTimeout)
    else:
        assert not isinstance(raised.value, PythonRunnerTimeout)
    assert time.monotonic() - started < timeout + 15
    assert transport._process is None
    inspected = subprocess.run(
        [_DOCKER, "container", "inspect", name],
        capture_output=True,
        timeout=10,
    )
    assert inspected.returncode != 0


@pytest.mark.integration
def test_real_pine_container_uses_external_position_and_closes_normally() -> None:
    require_pine_gvisor()
    data = frame([(100, 110, 90, 100)] * 4)
    trace = []
    result = run_code_backtest(
        """//@version=5
strategy("native external")
if bar_index == 1 or bar_index == 2
    strategy.entry("L", strategy.long)
if bar_index == 2 and strategy.position_size > 0
    strategy.close_all()
""",
        "pine",
        data,
        cfg(),
        trace=trace,
    )
    assert len(result.trades) == 1
    assert result.trades[0].exit_bar_index == 3
    assert [event["action"] for event in trace if event["type"] == "intent"] == [
        "hold",
        "long",
        "close",
        "hold",
    ]
