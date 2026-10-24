"""같은 session interface로 초기화·의도·중단·회수와 언어 선택을 검증한다."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.strategy.code_runtime.models import CodeRuntimeError
from src.strategy.code_runtime.session import (
    CodeExecutionSession,
    CodeSessionProtocolError,
    create_code_transport,
)
from src.strategy.python_runtime.protocol import PythonRunnerTimeout
from src.strategy.python_runtime.serialization import bars_payload
from tests.strategy.code_runtime.test_backtest import frame


def transport(*replies):
    result = Mock()
    result.exchange.side_effect = replies or [{"ready": 1}, {"intent": {"action": "hold"}}]
    return result


def test_session_is_lazy_and_injected_transport_owns_the_whole_exchange():
    adapter = transport()
    factory = Mock(return_value=adapter)
    session = CodeExecutionSession("source", "python", {"length": 3}, [], transport_factory=factory)
    factory.assert_not_called()
    with patch("src.strategy.code_runtime.session.create_code_transport") as native:
        with session as active:
            assert active.action({"index": 0}, {"direction": "flat"}) == "hold"
        native.assert_not_called()
    assert adapter.exchange.call_args_list[0].args[0] == {
        "type": "init",
        "protocol": 1,
        "source": "source",
        "params": {"length": 3},
    }
    assert adapter.exchange.call_args_list[1].args[0] == {
        "type": "bar",
        "bar": {"index": 0},
        "position": {"direction": "flat"},
    }
    factory.assert_called_once_with()
    adapter.close.assert_called_once_with()


@pytest.mark.parametrize(
    ("replies", "phase"),
    [
        ([{"ready": 2}], "init"),
        ([{"ready": 1, "extra": True}], "init"),
        ([{"ready": 1}, {"intent": {"action": "hold"}, "pnl": "1"}], "bar"),
    ],
)
def test_protocol_failures_close_transport(replies, phase):
    adapter = transport(*replies)
    with (
        pytest.raises(CodeSessionProtocolError) as raised,
        CodeExecutionSession(
            "source", "python", {}, [], transport_factory=lambda: adapter
        ) as session,
    ):
        session.action({}, {})
    assert raised.value.phase == phase
    adapter.close.assert_called_once_with()


@pytest.mark.parametrize("intent", [{"action": "buy"}, {"action": "long", "stop_loss": "1"}])
def test_action_only_contract_is_unchanged(intent):
    adapter = transport({"ready": 1}, {"intent": intent})
    with (
        pytest.raises(CodeRuntimeError) as raised,
        CodeExecutionSession(
            "source", "python", {}, [], transport_factory=lambda: adapter
        ) as session,
    ):
        session.action({}, {})
    assert type(raised.value) is CodeRuntimeError
    adapter.close.assert_called_once_with()


@pytest.mark.parametrize("phase", ["init", "bar"])
@pytest.mark.parametrize("error", [PythonRunnerTimeout("timeout"), KeyboardInterrupt()])
def test_timeout_and_interruption_close_and_preserve_the_original_error(phase, error):
    replies = [error] if phase == "init" else [{"ready": 1}, error]
    adapter = transport(*replies)
    with (
        pytest.raises(type(error)) as raised,
        CodeExecutionSession(
            "source", "python", {}, [], transport_factory=lambda: adapter
        ) as session,
    ):
        session.action({}, {})
    assert raised.value is error
    adapter.close.assert_called_once_with()


def test_cleanup_failure_does_not_replace_an_execution_failure():
    original = PythonRunnerTimeout("timeout")
    adapter = transport(original)
    adapter.close.side_effect = OSError("cleanup failed")
    with (
        pytest.raises(PythonRunnerTimeout) as raised,
        CodeExecutionSession("source", "python", {}, [], transport_factory=lambda: adapter),
    ):
        pytest.fail("init must fail")
    assert raised.value is original
    assert raised.value.__notes__ == ["격리 실행기 회수 실패: OSError"]


def test_cleanup_failure_after_success_is_not_hidden():
    adapter = transport({"ready": 1})
    adapter.close.side_effect = OSError("cleanup failed")
    with (
        pytest.raises(OSError, match="cleanup failed"),
        CodeExecutionSession("source", "python", {}, [], transport_factory=lambda: adapter),
    ):
        pass


@pytest.mark.parametrize(("language", "timeout"), [("python", 900), ("typescript", 30)])
def test_factory_keeps_language_and_caller_deadline(language, timeout):
    adapter = transport()
    with patch(
        "src.strategy.code_runtime.sandbox.create_transport", return_value=adapter
    ) as create:
        assert create_code_transport(language, [], timeout=timeout) is adapter
    create.assert_called_once_with(language, timeout=timeout)


@pytest.mark.parametrize("use_payload", [False, True])
def test_pine_factory_loads_the_entire_frame_with_the_caller_deadline(use_payload):
    data = frame([(100, 110, 90, 100)] * 4)
    adapter = transport()
    with patch(
        "src.strategy.code_runtime.pine.PineSignalTransport", return_value=adapter
    ) as create:
        assert (
            create_code_transport("pine", bars_payload(data) if use_payload else data, timeout=30)
            is adapter
        )
    loaded = create.call_args.args[0]
    pd.testing.assert_frame_equal(
        loaded, data, check_dtype=False, check_names=False, check_freq=False
    )
    assert create.call_args.kwargs == {"timeout": 30}


def test_invalid_source_fails_before_creating_transport():
    factory = Mock()
    with (
        pytest.raises(ValueError),
        CodeExecutionSession(" ", "python", {}, [], transport_factory=factory),
    ):
        pytest.fail("source must fail")
    factory.assert_not_called()
