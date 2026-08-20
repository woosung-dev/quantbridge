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


def _make_executor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
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
                "steps": [
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
