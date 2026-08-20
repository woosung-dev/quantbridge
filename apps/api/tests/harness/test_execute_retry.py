# codex 호출 결과와 재시도 한도를 고립된 임시 phase에서 검증한다.
"""하네스 codex 호출 및 재시도 회귀 테스트."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

_SRC = Path(__file__).resolve().parents[4] / "tools" / "harness" / "execute.py"


def _make_executor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, steps: list[dict] | None = None
):
    """실제 저장소와 분리된 최소 phase용 executor를 만든다."""
    spec = importlib.util.spec_from_file_location("qb_harness_execute", _SRC)
    if spec is None or spec.loader is None:
        raise RuntimeError("harness execute module을 불러올 수 없다")
    ex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)

    phase_dir = tmp_path / "phases" / "retry"
    phase_dir.mkdir(parents=True)
    (phase_dir / "index.json").write_text(
        json.dumps(
            {
                "project": "QuantBridge",
                "phase": "retry",
                "steps": steps
                or [
                    {
                        "step": 0,
                        "name": "codex-invoke-and-retry",
                        "status": "pending",
                        "ac": ["true"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "phases" / "index.json").write_text(
        json.dumps({"phases": [{"dir": "retry", "status": "pending"}]}),
        encoding="utf-8",
    )
    (phase_dir / "step0.md").write_text("# Step 0\n", encoding="utf-8")

    monkeypatch.setattr(ex, "ROOT", tmp_path)
    return ex, ex.StepExecutor("retry")


def test_invoke_codex_records_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """정상 종료는 성공 tuple과 표준 run 산출물로 남긴다."""
    ex, executor = _make_executor(monkeypatch, tmp_path)
    monkeypatch.setattr(
        ex,
        "CODEX_CMD",
        [
            sys.executable,
            "-c",
            "import sys; print('fake stdout'); print('fake stderr', file=sys.stderr)",
        ],
    )

    result = executor._invoke_codex(executor._steps[0], "preamble\n", attempt=1)

    assert result == (True, "")
    payload = json.loads((tmp_path / "phases/retry/runs/step0-attempt1.json").read_text())
    assert payload == {"exitCode": 0, "stdout": "fake stdout\n", "stderr": "fake stderr\n"}


def test_invoke_codex_returns_reason_for_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """비정상 종료 코드는 호출자에게 실패 사유로 전달한다."""
    ex, executor = _make_executor(monkeypatch, tmp_path)
    monkeypatch.setattr(
        ex,
        "CODEX_CMD",
        [sys.executable, "-c", "import sys; print('failed', file=sys.stderr); sys.exit(17)"],
    )

    ok, reason = executor._invoke_codex(executor._steps[0], "preamble\n", attempt=1)

    assert not ok
    assert "rc=17" in reason


def test_invoke_codex_catches_timeout_and_records_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """시간 초과는 runner 밖으로 전파되지 않고 error 산출물로 남긴다."""
    ex, executor = _make_executor(monkeypatch, tmp_path)
    monkeypatch.setattr(ex, "CODEX_TIMEOUT", 0.1)
    monkeypatch.setattr(ex, "CODEX_CMD", [sys.executable, "-c", "import time; time.sleep(1)"])

    ok, reason = executor._invoke_codex(executor._steps[0], "preamble\n", attempt=1)

    assert not ok
    assert "TimeoutExpired" in reason
    payload = json.loads((tmp_path / "phases/retry/runs/step0-attempt1.json").read_text())
    assert "error" in payload


def test_execute_step_retries_exactly_maximum_times(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """계속 실패하는 codex 호출은 MAX_RETRIES번만 시도한다."""
    _, executor = _make_executor(monkeypatch, tmp_path)
    invoke = Mock(return_value=(False, "intentional failure"))
    monkeypatch.setattr(executor, "_invoke_codex", invoke)
    monkeypatch.setattr(
        executor,
        "_run_git",
        lambda *args: subprocess.CompletedProcess(args=args, returncode=0),
    )

    with pytest.raises(SystemExit) as exc_info:
        executor._execute_step(executor._steps[0], "guardrails")

    assert exc_info.value.code == 1
    assert executor.MAX_RETRIES == 3
    assert invoke.call_count == executor.MAX_RETRIES
    assert [call.args[2] for call in invoke.call_args_list] == [1, 2, 3]


def test_execute_step_marks_error_and_exits_one_after_all_retries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """3회 실패는 step·phase 상태를 error로 남기고 종료 코드 1을 낸다."""
    _, executor = _make_executor(monkeypatch, tmp_path)
    monkeypatch.setattr(executor, "_invoke_codex", Mock(return_value=(False, "AC diagnostic")))
    monkeypatch.setattr(
        executor,
        "_run_git",
        lambda *args: subprocess.CompletedProcess(args=args, returncode=0),
    )

    with pytest.raises(SystemExit) as exc_info:
        executor._execute_step(executor._steps[0], "guardrails")

    assert exc_info.value.code == 1
    step = json.loads((tmp_path / "phases/retry/index.json").read_text())["steps"][0]
    assert step["status"] == "error"
    assert "[3회 시도 후 실패]" in step["error_message"]
    phase = json.loads((tmp_path / "phases/index.json").read_text())["phases"][0]
    assert phase["status"] == "error"


def test_execute_step_honors_blocked_before_running_ac(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """codex의 blocked 선언은 AC 없이 종료 코드 2로 끝낸다."""
    _, executor = _make_executor(monkeypatch, tmp_path)

    def declare_blocked(*_args) -> tuple[bool, str]:
        executor._update_step(0, status="blocked", blocked_reason="manual API key required")
        return True, ""

    run_ac = Mock(return_value=(True, ""))
    monkeypatch.setattr(executor, "_invoke_codex", declare_blocked)
    monkeypatch.setattr(executor, "_run_ac", run_ac)
    monkeypatch.setattr(executor, "_commit", Mock(return_value=True))

    with pytest.raises(SystemExit) as exc_info:
        executor._execute_step(executor._steps[0], "guardrails")

    assert exc_info.value.code == 2
    run_ac.assert_not_called()
    step = json.loads((tmp_path / "phases/retry/index.json").read_text())["steps"][0]
    assert step["status"] == "blocked"
    assert step["blocked_reason"] == "manual API key required"


def test_execute_step_passes_previous_failure_to_retry_preamble(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """첫 실패 사유는 가짜 codex가 받은 두 번째 프리앰블에 포함된다."""
    _, executor = _make_executor(monkeypatch, tmp_path)
    received_prompts = tmp_path / "fake-codex-prompts"

    def fake_invoke(_step: dict, preamble: str, attempt: int) -> tuple[bool, str]:
        received_prompts.mkdir(exist_ok=True)
        (received_prompts / f"attempt{attempt}.txt").write_text(preamble, encoding="utf-8")
        return (False, "first attempt diagnostic") if attempt == 1 else (True, "")

    monkeypatch.setattr(executor, "_invoke_codex", fake_invoke)
    monkeypatch.setattr(executor, "_commit", Mock(return_value=True))

    executor._execute_step(executor._steps[0], "guardrails")

    second_preamble = (received_prompts / "attempt2.txt").read_text(encoding="utf-8")
    assert "## ⚠ 이전 시도 실패" in second_preamble
    assert "first attempt diagnostic" in second_preamble


def test_step_context_includes_only_completed_steps_with_summaries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """이전 산출물은 completed이면서 summary가 있는 step만 누적한다."""
    steps = [
        {"step": 0, "name": "included", "status": "completed", "summary": "done", "ac": ["true"]},
        {"step": 1, "name": "no-summary", "status": "completed", "ac": ["true"]},
        {"step": 2, "name": "pending", "status": "pending", "summary": "not yet", "ac": ["true"]},
    ]
    _, executor = _make_executor(monkeypatch, tmp_path, steps=steps)

    context = executor._step_context(executor._read_json(executor._index_file))

    assert "- Step 0 (included): done" in context
    assert "no-summary" not in context
    assert "pending" not in context
