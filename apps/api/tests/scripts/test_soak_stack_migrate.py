"""`soak-stack.sh migrate`의 DDL 승인·대상 증명 경계를 고정한다.

실제 소크 DB·레포 migration을 절대 읽지 않도록 대상 스크립트와 두 실행 파일을 가짜
레포에 둔다. 모든 사례는 PATH의 `docker`·`uv` 스텁만 호출한다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "soak-stack.sh"
CURRENT = "current"
HEAD = "head"
# `alembic history` 는 **`<부모> -> <자식> (head), 메시지`** 를 최신순으로 찍는다
# (2026-08-21 실측: `20260816_0001 -> 20260817_0002 (head), …`). 즉 첫 필드가 부모다.
# `-r cur:head` 는 cur **를 포함**하므로 맨 아래에 「cur 를 만든 전이」(= 이미 적용된 것)가
# 한 줄 끼어든다. 대기분은 `cur -> …` 줄까지이고 그 아래가 적용분이다.
PENDING_HISTORY = """pending -> head (head)
current -> pending
previous -> current
"""


def _fake_repo(
    tmp_path: Path,
    *,
    assertion_returncode: int = 0,
    database_port: int = 5433,
) -> Path:
    """대상과 `assert-main-checkout`을 가짜 레포 경로에만 둔다."""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "soak-stack.sh"
    shutil.copy2(REAL, script)

    (scripts / "assert-main-checkout.sh").write_text(
        f"""#!/usr/bin/env bash
exit {assertion_returncode}
""",
        encoding="utf-8",
    )
    (scripts / "assert-main-checkout.sh").chmod(0o755)

    api = tmp_path / "apps" / "api"
    api.mkdir(parents=True)
    (api / ".env.local").write_text(
        "DATABASE_URL=postgresql+asyncpg://user:password@127.0.0.1:"
        f"{database_port}/quantbridge\n",
        encoding="utf-8",
    )
    return script


def _write_stubs(tmp_path: Path) -> Path:
    """호출 argv와 revision 변화를 기록하는 `docker`·`uv` 스텁을 만든다."""
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    (stub_bin / "docker").write_text(
        """#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "${DOCKER_STUB_CALLS_FILE:?}"

case "$1" in
  exec)
    printf 'x\\n' >> "${DOCKER_STUB_PSQL_CALLS_FILE:?}"
    call_count=$(wc -l < "${DOCKER_STUB_PSQL_CALLS_FILE}")
    sed -n "${call_count}p" "${DOCKER_STUB_REVISIONS_FILE:?}"
    ;;
  port)
    printf '%s\\n' "${DOCKER_STUB_PORT:-127.0.0.1:5433}"
    ;;
esac
""",
        encoding="utf-8",
    )
    (stub_bin / "uv").write_text(
        """#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "${UV_STUB_CALLS_FILE:?}"

if [ "$1" = "run" ] && [ "$2" = "alembic" ] && [ "$3" = "heads" ]; then
  printf '%s\\n' "${UV_STUB_HEAD:-head}"
  exit 0
fi
if [ "$1" = "run" ] && [ "$2" = "alembic" ] && [ "$3" = "history" ]; then
  cat "${UV_STUB_HISTORY_FILE:?}"
  exit "${UV_STUB_HISTORY_RETURN_CODE:-0}"
fi
if [ "$1" = "run" ] && [ "$2" = "python" ] && [ "$3" = "-m" ] \\
  && [ "$4" = "src.scripts.run_alembic_with_lock" ]; then
  exit "${UV_STUB_UPGRADE_RETURN_CODE:-0}"
fi

printf 'unexpected uv command: %s\\n' "$*" >&2
exit 99
""",
        encoding="utf-8",
    )
    for executable in (stub_bin / "docker", stub_bin / "uv"):
        executable.chmod(0o755)
    return stub_bin


def _environment(
    tmp_path: Path,
    stub_bin: Path,
    *,
    revisions: tuple[str, ...] = (CURRENT,),
    history: str = PENDING_HISTORY,
    history_returncode: int = 0,
    head: str = HEAD,
) -> dict[str, str]:
    """가짜 레포의 정상/실패 응답을 환경 파일로 전달한다."""
    revisions_file = tmp_path / "docker-revisions"
    history_file = tmp_path / "uv-history"
    revisions_file.write_text("\n".join(revisions) + "\n", encoding="utf-8")
    history_file.write_text(history, encoding="utf-8")
    return {
        **os.environ,
        "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
        "DOCKER_STUB_CALLS_FILE": str(tmp_path / "docker-calls"),
        "DOCKER_STUB_PSQL_CALLS_FILE": str(tmp_path / "docker-psql-calls"),
        "DOCKER_STUB_REVISIONS_FILE": str(revisions_file),
        "DOCKER_STUB_PORT": "127.0.0.1:5433",
        "UV_STUB_CALLS_FILE": str(tmp_path / "uv-calls"),
        "UV_STUB_HISTORY_FILE": str(history_file),
        "UV_STUB_HISTORY_RETURN_CODE": str(history_returncode),
        "UV_STUB_HEAD": head,
        "UV_STUB_UPGRADE_RETURN_CODE": "0",
    }


def _run(
    script: Path,
    environment: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """실제 레포와 무관한 복사본의 `migrate` dispatch만 실행한다."""
    return subprocess.run(
        ["bash", str(script), "migrate", *args],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=10,
    )


def _calls(tmp_path: Path, name: str) -> list[str]:
    """호출하지 않은 실행 파일은 빈 목록으로 읽는다."""
    path = tmp_path / name
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (("--confirm", "--typo"), "인자가 너무 많다"),
        (("--typo",), "알 수 없는 인자"),
    ],
)
def test_migrate_rejects_extra_or_unknown_argument_before_any_query(
    tmp_path: Path,
    args: tuple[str, ...],
    message: str,
) -> None:
    """입력 가드는 Docker·uv 조회보다 먼저 실패해야 한다."""
    script = _fake_repo(tmp_path)
    stub_bin = _write_stubs(tmp_path)

    result = _run(script, _environment(tmp_path, stub_bin), *args)

    assert result.returncode == 1
    assert message in result.stderr
    assert _calls(tmp_path, "docker-calls") == []
    assert _calls(tmp_path, "uv-calls") == []


def test_migrate_checks_main_checkout_before_docker(tmp_path: Path) -> None:
    """main checkout 가드 실패는 전제 미충족(2)이며 DB를 조회하지 않는다."""
    script = _fake_repo(tmp_path, assertion_returncode=1)
    stub_bin = _write_stubs(tmp_path)

    result = _run(script, _environment(tmp_path, stub_bin))

    assert result.returncode == 2
    assert _calls(tmp_path, "docker-calls") == []
    assert _calls(tmp_path, "uv-calls") == []


def test_migrate_skips_history_and_upgrade_when_already_at_head(tmp_path: Path) -> None:
    """현재 revision이 head면 DDL wrapper까지 도달하지 않는다."""
    script = _fake_repo(tmp_path)
    stub_bin = _write_stubs(tmp_path)
    environment = _environment(tmp_path, stub_bin, revisions=(HEAD,))

    result = _run(script, environment)

    assert result.returncode == 0
    assert "이미 head 다" in result.stdout
    assert _calls(tmp_path, "uv-calls") == ["run alembic heads"]
    assert len(_calls(tmp_path, "docker-psql-calls")) == 1


@pytest.mark.parametrize(
    ("history", "history_returncode"),
    [
        ("history lookup failed\n", 1),
        ("", 0),
    ],
)
def test_migrate_fails_closed_when_history_cannot_be_measured(
    tmp_path: Path,
    history: str,
    history_returncode: int,
) -> None:
    """history 오류와 빈 결과는 모두 '대기 0'이 아니라 측정 실패다."""
    script = _fake_repo(tmp_path)
    stub_bin = _write_stubs(tmp_path)
    environment = _environment(
        tmp_path,
        stub_bin,
        history=history,
        history_returncode=history_returncode,
    )

    result = _run(script, environment)

    assert result.returncode == 2
    assert "alembic history 를 못 읽었다" in result.stderr
    assert all(
        "src.scripts.run_alembic_with_lock" not in call
        for call in _calls(tmp_path, "uv-calls")
    )


def test_migrate_rejects_database_url_for_another_published_port(tmp_path: Path) -> None:
    """대상 불일치는 history 이후이되 upgrade 전에 거부해야 한다."""
    script = _fake_repo(tmp_path, database_port=5432)
    stub_bin = _write_stubs(tmp_path)

    result = _run(script, _environment(tmp_path, stub_bin))

    assert result.returncode == 1
    assert "다른 DB 에 DDL 이 갈 뻔했다" in result.stderr
    assert all(
        "src.scripts.run_alembic_with_lock" not in call
        for call in _calls(tmp_path, "uv-calls")
    )


def test_migrate_dry_run_proves_target_without_running_upgrade(tmp_path: Path) -> None:
    """승인 없는 정상 경로는 target proof만 출력하고 DDL을 내지 않는다."""
    script = _fake_repo(tmp_path)
    stub_bin = _write_stubs(tmp_path)

    result = _run(script, _environment(tmp_path, stub_bin))

    assert result.returncode == 0
    assert "dry-run 이다" in result.stdout
    assert "적용 대상   : DATABASE_URL 이 :5433" in result.stdout
    assert all(
        "src.scripts.run_alembic_with_lock" not in call
        for call in _calls(tmp_path, "uv-calls")
    )
    assert _calls(tmp_path, "docker-calls") == [
        "exec quantbridge-db psql -U quantbridge -d quantbridge -Atc SELECT version_num FROM alembic_version;",
        "port quantbridge-db 5432/tcp",
    ]


def test_migrate_counts_only_revisions_pending_after_current(tmp_path: Path) -> None:
    """history 맨 아래의 「cur 를 만든 전이」는 대기 개수에 섞이면 안 된다."""
    script = _fake_repo(tmp_path)
    stub_bin = _write_stubs(tmp_path)

    result = _run(script, _environment(tmp_path, stub_bin))

    assert result.returncode == 0
    assert "적용 대기   : 2 항목" in result.stdout


@pytest.mark.parametrize(
    ("revisions", "expected_returncode", "expected_text"),
    [
        ((CURRENT, HEAD), 0, "✓ current → head"),
        ((CURRENT, "other"), 1, "다른 DB 에 적용됐다"),
    ],
)
def test_migrate_confirm_rechecks_the_same_database_after_upgrade(
    tmp_path: Path,
    revisions: tuple[str, str],
    expected_returncode: int,
    expected_text: str,
) -> None:
    """--confirm은 wrapper 실행 뒤 같은 컨테이너 revision을 다시 확인한다."""
    script = _fake_repo(tmp_path)
    stub_bin = _write_stubs(tmp_path)
    environment = _environment(tmp_path, stub_bin, revisions=revisions)

    result = _run(script, environment, "--confirm")

    assert result.returncode == expected_returncode
    assert expected_text in result.stdout or expected_text in result.stderr
    assert any(
        "src.scripts.run_alembic_with_lock" in call
        for call in _calls(tmp_path, "uv-calls")
    )
    assert _calls(tmp_path, "docker-calls") == [
        "exec quantbridge-db psql -U quantbridge -d quantbridge -Atc SELECT version_num FROM alembic_version;",
        "port quantbridge-db 5432/tcp",
        "exec quantbridge-db psql -U quantbridge -d quantbridge -Atc SELECT version_num FROM alembic_version;",
    ]


def test_help_range_contains_the_entire_comment_header_and_no_code(tmp_path: Path) -> None:
    """양성 대조: dispatch의 2~26행 범위는 실제 헤더와 정확히 맞는다."""
    script = _fake_repo(tmp_path)
    stub_bin = _write_stubs(tmp_path)
    environment = _environment(tmp_path, stub_bin)

    result = subprocess.run(
        ["bash", str(script), "--help"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=10,
    )
    lines = script.read_text(encoding="utf-8").splitlines()
    first_code_line = next(
        number
        for number, line in enumerate(lines, start=1)
        if line and not line.startswith("#")
    )

    assert result.returncode == 0
    assert first_code_line == 28
    assert first_code_line > 26
    assert result.stdout == "\n".join(lines[1:26]) + "\n"
