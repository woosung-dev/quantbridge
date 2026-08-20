"""하네스 부팅 거부 계약 — 잘못된 phase 상태에서는 실행을 시작하지 않는다."""

from __future__ import annotations

import importlib.util
import json
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
