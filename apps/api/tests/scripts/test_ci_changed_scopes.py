"""CI 경로 스코프 판정을 고정한다 — 이 스크립트가 틀리면 미검증 코드가 조용히 머지된다.

★이 테스트가 지키는 것은 **속도가 아니라 fail-safe** 다. 「덜 돌린다」는 이득이고
「돌려야 할 것을 안 돌린다」는 사고다. 그래서 음성 대조(건너뛰어야 하는 것)보다
양성 대조(반드시 돌아야 하는 것)의 케이스가 더 많다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "ci-changed-scopes.sh"


def classify(*paths: str) -> tuple[bool, bool]:
    """파일 목록을 stdin 으로 넣고 (backend, frontend) 판정을 받는다."""
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--stdin"],
        input="\n".join(paths),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"스크립트가 죽었다: rc={proc.returncode}\n{proc.stderr}"
    out = dict(line.split("=", 1) for line in proc.stdout.strip().splitlines() if "=" in line)
    assert set(out) == {"backend", "frontend"}, f"출력 키가 계약과 다르다: {out}"
    return out["backend"] == "true", out["frontend"] == "true"


def test_script_exists_and_is_executable() -> None:
    """판정 대상이 실재하는지 먼저 본다 — 빈 입력이 초록으로 새는 것을 막는 첫 단추."""
    assert SCRIPT.is_file(), f"{SCRIPT} 가 없다"


# ── 음성 대조: 건너뛰어야 하는 것 ────────────────────────────────────────
@pytest.mark.parametrize(
    "paths",
    [
        ("docs/status.md",),
        ("docs/status.md", "docs/backlog.md", "docs/lessons.md"),
        ("README.md",),
        ("phases/index.json",),
        ("CONTEXT.md", "AGENTS.md"),
    ],
)
def test_docs_only_skips_both(paths: tuple[str, ...]) -> None:
    """문서·회차 정의만 바뀌면 BE·FE 둘 다 건너뛴다 — 이 회차의 이득 본체."""
    assert classify(*paths) == (False, False)


# ── 양성 대조: 반드시 돌아야 하는 것 ─────────────────────────────────────
@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (("apps/api/src/strategy/pine_v2/parser_adapter.py",), (True, False)),
        (("apps/api/AGENTS.md",), (True, False)),
        (("apps/web/src/app/page.tsx",), (False, True)),
        (("apps/web/AGENTS.md",), (False, True)),
        (("apps/api/src/x.py", "apps/web/src/y.ts"), (True, True)),
    ],
)
def test_app_paths_select_their_job(paths: tuple[str, ...], expected: tuple[bool, bool]) -> None:
    assert classify(*paths) == expected


@pytest.mark.parametrize(
    "shared",
    [
        ".github/workflows/ci.yml",
        "tools/scripts/ci-changed-scopes.sh",
        "infra/compose/docker-compose.yml",
        "mise.toml",
        "package.json",
        "pnpm-workspace.yaml",
        ".husky/pre-push",
    ],
)
def test_shared_paths_run_both(shared: str) -> None:
    """공유 경로는 어느 한쪽만 돌리면 안 된다 — 도구 버전·컨테이너·훅은 양쪽에 걸린다."""
    assert classify(shared) == (True, True)


# ── fail-safe: 모르면 둘 다 ──────────────────────────────────────────────
def test_unknown_path_forces_both() -> None:
    """분류표에 없는 새 경로가 조용히 미검증으로 새면 안 된다."""
    assert classify("some-new-thing/x.py") == (True, True)


def test_unknown_path_wins_over_docs_only() -> None:
    """★판별력 검사 — 문서 5건에 미지 경로 1건이 섞이면 전량 실행으로 뒤집혀야 한다.

    이 단언이 없으면 「다수결」로 구현해도 위 음성 대조가 전부 통과한다.
    """
    assert classify("docs/a.md", "docs/b.md", "docs/c.md", "docs/d.md", "newdir/e.py") == (
        True,
        True,
    )


def test_empty_input_is_not_a_pass() -> None:
    """빈 입력을 「변경 없음」으로 읽지 않는다 — 이 레포가 5회 이상 밟은 함정이다."""
    assert classify() == (True, True)


def test_missing_sha_args_fail_safe() -> None:
    """base/head sha 가 없는 트리거(merge_group·workflow_dispatch)는 전량 실행이다."""
    proc = subprocess.run(["bash", str(SCRIPT), "", ""], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0
    assert "backend=true" in proc.stdout
    assert "frontend=true" in proc.stdout


def test_verdict_is_always_explained_on_stderr() -> None:
    """무엇을 왜 건너뛰는지 항상 남긴다 — 'CI 가 안 돌았다' 를 두 번 겪은 레포다."""
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--stdin"],
        input="docs/status.md",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "판정:" in proc.stderr
    assert "docs/status.md" in proc.stderr, "변경 목록이 로그에 안 남는다"
