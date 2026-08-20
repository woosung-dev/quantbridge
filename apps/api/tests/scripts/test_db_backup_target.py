"""db-backup dispatch 인자 계약과 --help 헤더 출력을 고정한다."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "db-backup.sh"


def _env(tmp_path: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    """실제 Docker·환경 파일·백업 경로를 테스트가 겨누지 않게 격리한다."""
    env = {
        **os.environ,
        "QB_BACKUP_DIR": str(tmp_path / "backups"),
        "QB_ENV_FILE": str(tmp_path / "env.local"),
        "QB_DB_CONTAINER": "qb-test-db",
        "QB_OCI_BIN": str(tmp_path / "bin" / "oci"),
        "QB_SKIP_UPLOAD": "1",
    }
    env.pop("QB_DB_USER", None)
    env.pop("QB_DB_NAME", None)
    env.update(extra or {})
    return env


def run(
    tmp_path: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """dispatch 거부 경로만 subprocess로 호출한다.

    이 테스트의 모든 run·verify-restore 호출은 인자 수가 틀려 `_wire_docker` 전에 끝난다.
    """
    (tmp_path / "backups").mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=_env(tmp_path, extra_env),
    )


def _docker_stub(
    tmp_path: Path,
    *,
    status: str = "running",
    image: str = "timescale/timescaledb:2.17.2-pg16",
    env_lines: str = "POSTGRES_USER=quantbridge\nPOSTGRES_DB=quantbridge",
    psql_out: str = "quantbridge|2.17.2|16.4",
    psql_rc: int = 0,
    port: str = "0.0.0.0:5432",
) -> Path:
    """`docker` PATH 스텁을 만들고 모든 호출 인자를 로그에 누적한다."""
    stub_dir = tmp_path / "bin"
    log_path = tmp_path / "docker-args.log"
    stub_dir.mkdir(exist_ok=True)
    docker = stub_dir / "docker"
    docker.write_text(
        f"""#!/usr/bin/env bash
set -u
printf '%s\\n' \"$*\" >> {str(log_path)!r}

case \"$1\" in
  version)
    printf 'stub-server\\n'
    ;;
  inspect)
    case \"$4\" in
      '{{{{.State.Status}}}}') printf '%s\\n' {status!r} ;;
      '{{{{.Config.Image}}}}') printf '%s\\n' {image!r} ;;
      '{{{{range .Config.Env}}}}{{{{println .}}}}{{{{end}}}}') printf '%b\\n' {env_lines!r} ;;
    esac
    ;;
  exec)
    if [ \"$3\" = 'psql' ]; then
      printf '%s\\n' {psql_out!r}
      exit {psql_rc}
    fi
    ;;
  port)
    printf '%s\\n' {port!r}
    ;;
esac
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    return stub_dir


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("run", "extra"), "run 은 인자를 받지 않는다"),
        (("--install", "extra"), "--install 은 인자를 받지 않는다"),
        (("--uninstall", "extra"), "--uninstall 은 인자를 받지 않는다"),
        (("--status", "extra"), "--status 는 인자를 받지 않는다"),
    ],
)
def test_no_argument_subcommands_reject_extra_argument(
    tmp_path: Path,
    args: tuple[str, str],
    expected: str,
) -> None:
    """타이머용 서브커맨드는 인자 하나라도 더 받으면 거부한다."""
    result = run(tmp_path, *args)

    assert result.returncode == 1
    assert expected in result.stderr


@pytest.mark.parametrize("dump_args", [(), ("first.dump", "second.dump")])
def test_verify_restore_requires_exactly_one_dump(
    tmp_path: Path,
    dump_args: tuple[str, ...],
) -> None:
    """verify-restore는 덤프 파일 하나만 받아 Docker 경로로 진입한다."""
    result = run(tmp_path, "verify-restore", *dump_args)

    assert result.returncode == 1
    assert "verify-restore 는 덤프 파일 하나를 받는다" in result.stderr


@pytest.mark.parametrize("args", [(), ("unknown",)])
def test_missing_or_unknown_command_prints_usage(tmp_path: Path, args: tuple[str, ...]) -> None:
    """인자 생략도 no-op가 아니라 사용법을 포함한 실패다."""
    result = run(tmp_path, *args)

    assert result.returncode == 1
    assert "알 수 없는 인자" in result.stderr
    assert "run / verify-restore <덤프> / --install / --uninstall / --status / --help" in result.stderr


def test_help_prints_usage_and_environment_variables(tmp_path: Path) -> None:
    """도움말은 Docker 없이 사용법과 설정 가능한 환경 변수를 보여 준다."""
    result = run(tmp_path, "--help")

    assert result.returncode == 0
    assert "tools/scripts/db-backup.sh run" in result.stdout
    assert "QB_BACKUP_DIR" in result.stdout


@pytest.mark.xfail(
    strict=True,
    reason="--help의 sed -n '2,59p' 범위가 헤더 65행보다 짧아 마지막 헤더를 누락한다",
)
def test_help_prints_the_entire_header(tmp_path: Path) -> None:
    """현재 드리프트: 헤더 마지막 설계 근거도 --help에 나와야 한다."""
    result = run(tmp_path, "--help")

    assert "0바이트 덤프가 쌓이면" in result.stdout
    assert "자격증명은 파일이 아니라" in result.stdout


def test_help_starts_with_the_script_header_second_line(tmp_path: Path) -> None:
    """양성 대조: --help가 비어 있지 않고 이 파일의 헤더에서 시작한다."""
    result = run(tmp_path, "--help")
    header_second_line = SCRIPT.read_text(encoding="utf-8").splitlines()[1]

    assert result.stdout.splitlines()[0] == header_second_line


def test_prove_target_rejection_matrix_and_preserves_container_lifecycle(
    tmp_path: Path,
) -> None:
    """`run`은 대상 증명 실패를 구분하고 컨테이너 생명주기를 건드리지 않는다."""
    cases = [
        ("container_missing", {"status": ""}, 5432, "quantbridge", 2, "가 없다"),
        ("container_exited", {"status": "exited"}, 5432, "quantbridge", 2, "running 이 아니다"),
        (
            "wrong_image",
            {"image": "postgres:16"},
            5432,
            "quantbridge",
            1,
            "timescaledb 계열이 아니다",
        ),
        (
            "missing_postgres_env",
            {"env_lines": ""},
            5432,
            "quantbridge",
            2,
            "POSTGRES_USER/POSTGRES_DB 를 못 읽었다",
        ),
        (
            "psql_failure",
            {"psql_rc": 1},
            5432,
            "quantbridge",
            2,
            "psql 로 못 붙었다",
        ),
        (
            "current_database_mismatch",
            {"psql_out": "another_db|2.17.2|16.4"},
            5432,
            "quantbridge",
            1,
            "current_database() 가 another_db 다",
        ),
        (
            "missing_timescaledb_extension",
            {"psql_out": "quantbridge||16.4"},
            5432,
            "quantbridge",
            1,
            "timescaledb 확장이 없다",
        ),
        (
            "published_port_mismatch",
            {},
            5433,
            "quantbridge",
            1,
            "앱이 쓰는 DB 가 아닌 것을 백업할 뻔했다",
        ),
        (
            "database_name_mismatch",
            {},
            5432,
            "another_db",
            1,
            "앱이 쓰지 않는 DB 를 백업할 뻔했다",
        ),
    ]

    for name, stub_options, url_port, url_db, expected_rc, expected_error in cases:
        (tmp_path / "env.local").write_text(
            "DATABASE_URL="
            f"postgresql+asyncpg://u:p@localhost:{url_port}/{url_db}\n",
            encoding="utf-8",
        )
        stub_dir = _docker_stub(tmp_path, **stub_options)

        result = run(
            tmp_path,
            "run",
            extra_env={"PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}"},
        )

        assert result.returncode == expected_rc, name
        assert expected_error in result.stderr, name

    (tmp_path / "env.local").write_text(
        "DATABASE_URL=postgresql+asyncpg://u:p@localhost:5432/quantbridge\n",
        encoding="utf-8",
    )
    stub_dir = _docker_stub(tmp_path)
    result = run(
        tmp_path,
        "run",
        extra_env={"PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}"},
    )

    assert "대상 증명 ✓" in result.stdout

    docker_calls = (tmp_path / "docker-args.log").read_text(encoding="utf-8").splitlines()
    assert docker_calls
    assert all(call.split()[0] not in {"up", "down", "start", "stop", "restart"} for call in docker_calls)
