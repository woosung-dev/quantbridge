"""[BL-820] 공유 `phases/index.json` 을 lane 이 만지지 않는다 · 충돌을 충돌이라 보고한다.

n7·n8·n9 세 회차 연속으로 병렬 lane 이 같은 자리에서 병합 충돌했다. 원인은 둘이다.

⑴ lane 러너가 `phases/index.json`(모든 lane 이 자기 항목을 **인접 줄**에 쓰는 유일한 공유
   파일)을 상태 커밋에 넣었다. 첫 lane 이 머지되면 나머지가 전부 CONFLICTING 이 된다.
⑵ 그 충돌 PR 은 CI 가 아예 돌지 않아 `statusCheckRollup` 이 영원히 비는데, 러너가
   `mergeable` 을 **요청해 놓고 읽지 않아** 45분을 태운 뒤 「CI 대기 시간 초과」로 적었다.
"""

import importlib.util
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[4] / "tools" / "harness" / "execute.py"
_SPEC = importlib.util.spec_from_file_location("qb_harness_shared_index", _SRC)
assert _SPEC is not None
assert _SPEC.loader is not None
ex = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ex)

_TOP_INDEX = "phases/index.json"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[Path]:
    """메인 체크아웃 하나 + 거기서 판 워크트리 하나."""
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-b", "main")
    _git(main, "config", "user.email", "t@t.local")
    _git(main, "config", "user.name", "t")
    (main / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(main, "add", "-A")
    _git(main, "commit", "-m", "seed")
    yield main


def test_main_checkout_is_not_a_linked_worktree(repo: Path) -> None:
    assert ex._in_linked_worktree(repo) is False


def test_linked_worktree_is_detected(repo: Path) -> None:
    wt = repo.parent / "wt1"
    _git(repo, "worktree", "add", "-b", "lane", str(wt))

    assert ex._in_linked_worktree(wt) is True


def test_unreadable_root_falls_back_to_main(tmp_path: Path) -> None:
    """판정 실패는 **메인이다**로 떨어뜨린다 — 모를 때 동작을 바꾸지 않는 방향이다."""
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()

    assert ex._in_linked_worktree(not_a_repo) is False


def _state_files_for(root: Path, *, owns: bool) -> list[str]:
    exe = ex.StepExecutor.__new__(ex.StepExecutor)
    exe._root = root
    exe._index_file = root / "phases" / "lane-a" / "index.json"
    exe._top_index_file = root / _TOP_INDEX
    exe._owns_top_index = owns
    return exe._state_files()


def test_lane_in_worktree_excludes_the_shared_index(repo: Path) -> None:
    """★이것이 [BL-820] 의 수리다 — 워크트리 lane 은 공유 파일을 커밋하지 않는다."""
    files = _state_files_for(repo, owns=False)

    assert _TOP_INDEX not in files
    assert "phases/lane-a/index.json" in files, "자기 lane 파일까지 빠지면 진행이 안 남는다"


def test_main_checkout_still_commits_the_shared_index(repo: Path) -> None:
    """음성 대조 — 순차 모드는 종전대로 공유 파일을 쓴다. 거기엔 경합이 없다."""
    files = _state_files_for(repo, owns=True)

    assert _TOP_INDEX in files


def test_update_top_index_is_a_noop_without_ownership(repo: Path, tmp_path: Path) -> None:
    top = repo / _TOP_INDEX
    top.parent.mkdir(parents=True, exist_ok=True)
    top.write_text('{"phases": [{"dir": "lane-a", "status": "pending"}]}\n', encoding="utf-8")
    before = top.read_text(encoding="utf-8")

    exe = ex.StepExecutor.__new__(ex.StepExecutor)
    exe._root = repo
    exe._top_index_file = top
    exe._phase_dir_name = "lane-a"
    exe._owns_top_index = False
    exe._update_top_index("completed")

    assert top.read_text(encoding="utf-8") == before, "워크트리에서 공유 파일을 건드렸다"


class _Res:
    def __init__(self) -> None:
        self.pr = "https://example.invalid/pr/1"
        self.merged = False
        self.detail = ""


def test_conflicting_pr_is_reported_as_conflict_not_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★충돌은 기다려서 안 풀린다 — 즉시 사실대로 보고하고 나가야 한다."""
    calls: list[tuple[str, ...]] = []

    def fake_sh(*args: str, **_kw: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=0,
            stdout='{"statusCheckRollup": [], "mergeable": "CONFLICTING", "state": "OPEN"}',
            stderr="",
        )

    monkeypatch.setattr(ex, "_sh", fake_sh)
    monkeypatch.setattr(ex.time, "sleep", lambda _s: pytest.fail("충돌인데 대기에 들어갔다"))
    res = _Res()

    ex._wait_ci_and_merge(res)

    assert "충돌" in res.detail
    assert "시간 초과" not in res.detail
    assert res.merged is False
    assert not any("merge" in c for c in calls), "충돌 PR 에 머지를 시도했다"


def test_clean_pr_still_waits_when_checks_are_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """음성 대조 — 충돌이 아니면 종전대로 기다린다. 넓게 잡아 정상 대기를 죽이면 안 된다."""
    slept: list[int] = []

    def fake_sh(*args: str, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=0,
            stdout='{"statusCheckRollup": [{"status": "IN_PROGRESS"}],'
            ' "mergeable": "MERGEABLE", "state": "OPEN"}',
            stderr="",
        )

    def fake_sleep(_s: int) -> None:
        slept.append(_s)
        if len(slept) >= 2:
            raise TimeoutError("stop")

    monkeypatch.setattr(ex, "_sh", fake_sh)
    monkeypatch.setattr(ex.time, "sleep", fake_sleep)

    with pytest.raises(TimeoutError):
        ex._wait_ci_and_merge(_Res())

    assert slept, "MERGEABLE 인데 기다리지 않았다"
