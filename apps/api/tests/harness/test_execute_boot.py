"""하네스 부팅 거부 계약 — 잘못된 phase 상태에서는 실행을 시작하지 않는다."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[4] / "tools" / "harness" / "execute.py"
_SPEC = importlib.util.spec_from_file_location("qb_harness_execute", _SRC)
assert _SPEC is not None
assert _SPEC.loader is not None
ex = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ex)


def _step(
    number: int,
    *,
    ac: list[str] | None = None,
    status: str = "pending",
) -> dict[str, object]:
    step: dict[str, object] = {
        "step": number,
        "name": f"step-{number}",
        "status": status,
    }
    if ac is not None:
        step["ac"] = ac
    return step


def _write_phase(
    root: Path,
    *,
    phase_name: str = "test-phase",
    steps: list[dict[str, object]] | None = None,
) -> Path:
    phase_dir = root / "phases" / phase_name
    phase_dir.mkdir(parents=True)
    payload = {
        "project": "QuantBridge",
        "phase": phase_name,
        "steps": steps or [_step(0, ac=["true"])],
    }
    (phase_dir / "index.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return phase_dir


def _write_guardrails(root: Path) -> None:
    for relative_path in ex.GUARDRAIL_FILES:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test guardrail", encoding="utf-8")


def test_init_refuses_missing_phase_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """존재하지 않는 phase는 경로를 남기고 즉시 거부한다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    missing_path = tmp_path / "phases" / "missing-phase"

    with pytest.raises(SystemExit) as exc_info:
        ex.StepExecutor("missing-phase")

    assert str(missing_path) in str(exc_info.value)


def test_init_refuses_missing_index_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """phase 디렉터리만 있고 index가 없으면 시작하지 않는다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    phase_dir = tmp_path / "phases" / "missing-index"
    phase_dir.mkdir(parents=True)

    with pytest.raises(SystemExit) as exc_info:
        ex.StepExecutor("missing-index")

    assert str(phase_dir / "index.json") in str(exc_info.value)


@pytest.mark.parametrize(
    ("invalid_ac", "step_number"),
    [
        (None, 7),
        ([], 8),
    ],
)
def test_init_refuses_missing_or_empty_ac(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    invalid_ac: list[str] | None,
    step_number: int,
) -> None:
    """AC 키 누락과 빈 배열 모두 해당 step 번호를 남기고 거부한다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    _write_phase(
        tmp_path,
        steps=[_step(0, ac=["true"]), _step(step_number, ac=invalid_ac)],
    )

    with pytest.raises(SystemExit) as exc_info:
        ex.StepExecutor("test-phase")

    assert str(step_number) in str(exc_info.value)


def test_init_allows_steps_with_nonempty_ac(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """음성 대조: 모든 step에 AC가 있으면 부팅 검사가 통과한다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    _write_phase(tmp_path, steps=[_step(0, ac=["true"]), _step(1, ac=["echo ok"])])

    executor = ex.StepExecutor("test-phase")

    assert executor._total == 2


@pytest.mark.parametrize("missing_path", ex.GUARDRAIL_FILES)
def test_load_guardrails_refuses_each_missing_required_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    missing_path: str,
) -> None:
    """가드레일 네 축은 하나라도 빠지면 각각 시작을 막는다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    _write_phase(tmp_path)
    _write_guardrails(tmp_path)
    executor = ex.StepExecutor("test-phase")
    (tmp_path / missing_path).unlink()

    with pytest.raises(SystemExit) as exc_info:
        executor._load_guardrails()

    assert missing_path in str(exc_info.value)


@pytest.mark.parametrize("status", ["error", "blocked"])
def test_run_refuses_uninspected_step_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
) -> None:
    """선행 step이 error 또는 blocked면 Codex와 AC 실행 전에 중단한다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    _write_phase(tmp_path, steps=[_step(3, ac=["true"], status=status)])
    executor = ex.StepExecutor("test-phase")

    with pytest.raises(SystemExit) as exc_info:
        executor.run()

    assert "3" in str(exc_info.value)
    assert status in str(exc_info.value)


def test_stamp_uses_kst_iso8601_format(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """실행 원장의 타임스탬프는 KST 오프셋을 가진 ISO 8601 초 단위다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    _write_phase(tmp_path)
    executor = ex.StepExecutor("test-phase")

    stamp = executor._stamp()

    assert stamp.endswith("+0900")
    datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S%z")


def test_write_json_preserves_korean_indentation_and_trailing_newline(tmp_path: Path) -> None:
    """JSON 산출물은 한글·2칸 들여쓰기·끝 개행을 보존한다."""
    output_file = tmp_path / "payload.json"
    payload = {"요약": "한글 산출물", "중첩": {"시도": 2}}

    ex.StepExecutor._write_json(output_file, payload)

    content = output_file.read_text(encoding="utf-8")
    assert content == '{\n  "요약": "한글 산출물",\n  "중첩": {\n    "시도": 2\n  }\n}\n'
    assert ex.StepExecutor._read_json(output_file) == payload


def test_load_guardrails_includes_each_distinct_required_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """가드레일 조립은 네 파일을 경로 제목과 각자 내용으로 한 번씩 포함한다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    _write_phase(tmp_path)
    guardrail_contents = {
        relative_path: f"guardrail-{position}-{relative_path}"
        for position, relative_path in enumerate(ex.GUARDRAIL_FILES, start=1)
    }
    for relative_path, content in guardrail_contents.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    executor = ex.StepExecutor("test-phase")

    guardrails = executor._load_guardrails()

    for relative_path, content in guardrail_contents.items():
        assert f"## 프로젝트 규칙 ({relative_path})" in guardrails
        assert guardrails.count(content) == 1


def test_save_run_creates_runs_directory_and_uses_step_attempt_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """run 산출물은 격리 phase의 runs 아래 step·attempt 이름으로 저장한다."""
    monkeypatch.setattr(ex, "ROOT", tmp_path)
    phase_dir = _write_phase(tmp_path)
    executor = ex.StepExecutor("test-phase")
    payload = {"summary": "한글 run 산출물"}
    expected_file = phase_dir / "runs" / "step4-attempt2.json"

    assert not expected_file.parent.exists()

    executor._save_run(4, 2, payload)

    assert expected_file.exists()
    assert ex.StepExecutor._read_json(expected_file) == payload
