"""메인 체크아웃 전용 가드의 Git 기반 판정을 검증한다.

공유 컨테이너·앱 DB를 건드리는 mise task는 워크트리에서 거부돼야 한다.
단, Git으로 판정할 수 없는 CI·컨테이너 환경까지 막으면 안 된다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "assert-main-checkout.sh"
_BASH = Path("/bin/bash")


def run(
    cwd: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """가드는 원본 그대로 두고 cwd만 바꿔 실제 Git 판정을 실행한다."""
    return subprocess.run(
        [str(_BASH), str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    """메인 체크아웃과 연결 워크트리를 가진 임시 Git 저장소를 만든다."""
    main = tmp_path / "main"
    main.mkdir()

    def git(*args: str, cwd: Path = main) -> None:
        subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (main / "f.txt").write_text("x", encoding="utf-8")
    git("add", "f.txt")
    git("commit", "-qm", "init")

    worktree = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "side", str(worktree))
    return main, worktree


def test_main_checkout_succeeds_silently(tmp_path: Path) -> None:
    """메인 체크아웃은 성공하며 표준 출력과 표준 오류가 모두 비어 있다."""
    main, _ = _repo(tmp_path)

    result = run(main, "up")

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_worktree_is_rejected_but_main_checkout_is_allowed(tmp_path: Path) -> None:
    """같은 저장소에서 메인은 통과하고 워크트리만 복구 안내와 함께 거부된다."""
    main, worktree = _repo(tmp_path)

    main_result = run(main, "migrate")
    worktree_result = run(worktree, "migrate")

    assert main_result.returncode == 0
    assert worktree_result.returncode == 1
    assert "'migrate'" in worktree_result.stderr
    assert "mise run migrate" in worktree_result.stderr
    assert str(main) in worktree_result.stderr
    assert "docs/development/worktree-parallel.md §2.1" in worktree_result.stderr


def test_worktree_without_target_uses_default_target_name(tmp_path: Path) -> None:
    """인자를 생략하면 워크트리 거부 메시지가 기본 타깃 이름을 사용한다."""
    _, worktree = _repo(tmp_path)

    result = run(worktree)

    assert result.returncode == 1
    assert "'이 타깃'" in result.stderr
    assert "mise run 이 타깃" in result.stderr


def test_non_git_directory_is_allowed(tmp_path: Path) -> None:
    """음성 대조: Git 저장소가 아닌 곳에서는 판정 불가이므로 통과시킨다."""
    plain = tmp_path / "plain"
    plain.mkdir()
    probe = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=str(plain),
        capture_output=True,
        text=True,
    )

    assert probe.returncode != 0
    assert run(plain, "seed").returncode == 0


def test_missing_git_binary_is_allowed_in_a_worktree(tmp_path: Path) -> None:
    """음성 대조: PATH에 Git이 없으면 워크트리여도 판정 불가로 통과시킨다."""
    _, worktree = _repo(tmp_path)
    no_git_path = tmp_path / "no-git-path"
    no_git_path.mkdir()

    result = run(worktree, "seed", env={"PATH": str(no_git_path)})

    assert result.returncode == 0
