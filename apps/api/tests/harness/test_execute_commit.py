"""하네스의 코드·상태 2단 커밋 계약을 실제 격리 Git 저장소에서 검증한다."""

import importlib.util
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[4] / "tools" / "harness" / "execute.py"
_SPEC = importlib.util.spec_from_file_location("qb_harness_execute", _SRC)
assert _SPEC is not None
assert _SPEC.loader is not None
ex = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ex)

_PHASE_DIR_NAME = "commit-contract"
_STATE_PATHS = {
    f"phases/{_PHASE_DIR_NAME}/index.json",
    "phases/index.json",
}


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _commit_hash(root: Path, message: str) -> str:
    for line in _git(root, "log", "--format=%H%x09%s").splitlines():
        commit_hash, subject = line.split("\t", maxsplit=1)
        if subject == message:
            return commit_hash
    raise AssertionError(f"커밋 메시지를 찾지 못했다: {message}")


def _changed_paths(root: Path, commit_hash: str) -> set[str]:
    return {
        path
        for path in _git(root, "show", "--format=", "--name-only", commit_hash).splitlines()
        if path
    }


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def executor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """최초 커밋을 가진 최소 phase 저장소와 StepExecutor를 만든다."""
    phase_dir = tmp_path / "phases" / _PHASE_DIR_NAME
    phase_dir.mkdir(parents=True)
    _write_json(
        phase_dir / "index.json",
        {
            "project": "QuantBridge",
            "phase": _PHASE_DIR_NAME,
            "steps": [{"step": 0, "name": "contract", "status": "pending", "ac": ["true"]}],
        },
    )
    _write_json(tmp_path / "phases" / "index.json", {"phases": [{"dir": _PHASE_DIR_NAME}]})
    (tmp_path / "baseline.txt").write_text("baseline\n", encoding="utf-8")

    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "harness-test@example.com")
    _git(tmp_path, "config", "user.name", "Harness Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "test: baseline")

    monkeypatch.setattr(ex, "ROOT", tmp_path)
    yield ex.StepExecutor(_PHASE_DIR_NAME)


def _change_code_and_state(executor: object) -> None:
    root = executor._root
    (root / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
    _write_json(executor._index_file, {"phase": "updated"})
    _write_json(executor._top_index_file, {"phases": [{"dir": "updated"}]})


def _change_state(executor: object) -> None:
    _write_json(executor._index_file, {"phase": "updated"})
    _write_json(executor._top_index_file, {"phases": [{"dir": "updated"}]})


def test_code_commit_excludes_harness_state_files(executor: object) -> None:
    """코드 커밋에는 각 phase와 최상위 index.json이 들어가지 않는다."""
    _change_code_and_state(executor)

    assert executor._commit("feat: x") is True

    paths = _changed_paths(executor._root, _commit_hash(executor._root, "feat: x"))
    assert paths == {"feature.py"}
    assert paths.isdisjoint(_STATE_PATHS)


def test_state_files_follow_in_harness_state_commit(executor: object) -> None:
    """코드 뒤 상태 파일은 phase 이름을 가진 별도 상태 커밋으로 남는다."""
    _change_code_and_state(executor)

    assert executor._commit("feat: x") is True

    state_message = f"chore({_PHASE_DIR_NAME}): harness state"
    assert _git(executor._root, "log", "-2", "--format=%s").splitlines() == [
        state_message,
        "feat: x",
    ]
    state_paths = _changed_paths(executor._root, _commit_hash(executor._root, state_message))
    assert state_paths == _STATE_PATHS


def test_state_only_commit_preserves_caller_message(executor: object) -> None:
    """상태만 바뀌면 blocked/completed 의미가 담긴 호출자 메시지를 보존한다."""
    _change_state(executor)

    assert executor._commit("chore: mark blocked") is True

    assert _git(executor._root, "log", "-1", "--format=%s").strip() == "chore: mark blocked"
    assert _changed_paths(executor._root, "HEAD") == _STATE_PATHS


def test_commit_returns_false_when_nothing_changed(executor: object) -> None:
    """커밋할 코드와 상태가 모두 없으면 실패가 아닌 False를 반환한다."""
    assert executor._commit("chore: no changes") is False
