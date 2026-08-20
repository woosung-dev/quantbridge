"""하네스 AC 판정 계약 회귀 테스트.

`execute.py`는 패키지가 아닌 레포 루트 스크립트이므로 파일 경로로 격리 로드한다.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

_SRC = Path(__file__).resolve().parents[4] / "tools" / "harness" / "execute.py"
_SPEC = importlib.util.spec_from_file_location("qb_harness_execute", _SRC)
assert _SPEC is not None and _SPEC.loader is not None
ex = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ex)


def _make_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    commands: list[str],
) -> tuple[Any, dict[str, Any]]:
    """각 테스트가 독립된 phase와 AC 배열을 갖게 한다."""
    phase_dir = tmp_path / "phases" / "ac-contract"
    phase_dir.mkdir(parents=True)
    step = {
        "step": 0,
        "name": "ac-contract",
        "status": "pending",
        "ac": commands,
    }
    (phase_dir / "index.json").write_text(
        json.dumps({"project": "QuantBridge", "phase": "ac-contract", "steps": [step]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    return ex.StepExecutor("ac-contract"), step


def test_run_ac_returns_success_when_every_command_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC 전건 rc=0이면 성공과 빈 실패 사유를 반환한다."""
    executor, step = _make_executor(tmp_path, monkeypatch, ["true", "printf passed"])

    assert executor._run_ac(step, attempt=1) == (True, "")


def test_run_ac_reports_failing_command_and_return_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """첫 rc≠0 AC의 원문과 종료 코드를 실패 사유에 남긴다."""
    failing_command = "printf failure; exit 7"
    executor, step = _make_executor(tmp_path, monkeypatch, ["true", failing_command])

    ok, reason = executor._run_ac(step, attempt=1)

    assert ok is False
    assert "rc=7" in reason
    assert failing_command in reason


def test_run_ac_executes_commands_from_executor_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC의 상대 경로는 executor의 Path root를 기준으로 해석한다."""
    marker = "ac-cwd-marker.txt"
    executor, step = _make_executor(tmp_path, monkeypatch, [f"printf rooted > {marker}"])

    assert executor._run_ac(step, attempt=1) == (True, "")
    assert (tmp_path / marker).read_text(encoding="utf-8") == "rooted"


def test_run_ac_persists_failure_forensics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """실패 AC는 검시 파일에 명령·rc·출력 tail을 남긴다."""
    failing_command = "printf stdout; printf stderr >&2; exit 23"
    executor, step = _make_executor(tmp_path, monkeypatch, [failing_command])

    ok, _ = executor._run_ac(step, attempt=3)

    assert ok is False
    run_file = tmp_path / "phases" / "ac-contract" / "runs" / "step0-attempt3.json"
    payload = json.loads(run_file.read_text(encoding="utf-8"))
    assert payload["acFailed"] == failing_command
    assert payload["rc"] == 23
    assert isinstance(payload["tail"], list)


def test_run_ac_stops_after_first_failing_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """두 번째 AC가 실패하면 세 번째 AC의 부작용은 발생하지 않는다."""
    first_marker = tmp_path / "first-ac-ran.txt"
    third_marker = tmp_path / "third-ac-ran.txt"
    commands = [
        f"touch {first_marker}",
        "exit 9",
        f"touch {third_marker}",
    ]
    executor, step = _make_executor(tmp_path, monkeypatch, commands)

    ok, _ = executor._run_ac(step, attempt=1)

    assert ok is False
    assert first_marker.exists()
    assert not third_marker.exists()


def test_run_ac_persists_only_last_forty_output_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """40줄 초과 실패 출력은 검시에 마지막 40줄만 저장한다."""
    command = "for i in $(seq 1 45); do printf 'line-%s\\n' \"$i\"; done; exit 1"
    executor, step = _make_executor(tmp_path, monkeypatch, [command])

    ok, _ = executor._run_ac(step, attempt=2)

    assert ok is False
    run_file = tmp_path / "phases" / "ac-contract" / "runs" / "step0-attempt2.json"
    payload = json.loads(run_file.read_text(encoding="utf-8"))
    assert payload["tail"] == [f"line-{number}" for number in range(6, 46)]


def test_run_ac_returns_timeout_failure_without_raising(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC 제한 시간을 넘기면 예외 대신 timeout 실패 튜플을 반환한다."""
    timeout = 0.1
    command = "exec sleep 1"
    monkeypatch.setattr(ex, "AC_TIMEOUT", timeout)
    executor, step = _make_executor(tmp_path, monkeypatch, [command])

    assert executor._run_ac(step, attempt=1) == (False, f"AC timeout {timeout}s: {command}")
