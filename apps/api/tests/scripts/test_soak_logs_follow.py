"""`soak-logs-follow.sh`의 설정·커서·회전 경계를 가짜 레포에서 고정한다.

실제 레포에서 실행하면 `.soak/logs`와 워커 Docker 로그를 건드린다. 모든 사례는
`tmp_path`에 대상 스크립트를 복사하고 PATH 선두의 docker 스텁만 호출한다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "soak-logs-follow.sh"
WORKER_CONTAINER = "worker-follow-test"
POLL_LIMIT_SECONDS = 15
POLL_INTERVAL_SECONDS = 0.05


def _fake_repo(tmp_path: Path) -> Path:
    """대상 스크립트의 ROOT와 `.soak/` 앵커를 tmp_path로 격리한다."""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    copied = scripts / "soak-logs-follow.sh"
    shutil.copy2(REAL, copied)
    return copied


def _write_docker_stub(tmp_path: Path, lines: str) -> tuple[Path, Path]:
    """argv를 기록하고 정해진 로그 줄을 낸 뒤 종료하는 docker 스텁을 만든다."""
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    calls_file = tmp_path / "docker-calls.txt"
    lines_file = tmp_path / "docker-lines.txt"
    lines_file.write_text(lines, encoding="utf-8")
    docker = stub_bin / "docker"
    docker.write_text(
        """#!/usr/bin/env bash
set -eu
: "${DOCKER_STUB_CALLS_FILE:?}"
: "${DOCKER_STUB_LINES_FILE:?}"
printf '%s\\n' "$@" > "${DOCKER_STUB_CALLS_FILE}"
cat "${DOCKER_STUB_LINES_FILE}"
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    return stub_bin, calls_file


def _run(script: Path, args: tuple[str, ...], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """무한 루프에 들어가지 않는 dispatch·설정 검증 사례를 실행한다."""
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=script.parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _follow_environment(stub_bin: Path, calls_file: Path, lines_file: Path) -> dict[str, str]:
    """두 번째 attach를 막고 PATH 스텁만 통해 docker를 호출하게 한다."""
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{stub_bin}{os.pathsep}{env['PATH']}",
            "DOCKER_STUB_CALLS_FILE": str(calls_file),
            "DOCKER_STUB_LINES_FILE": str(lines_file),
            "QB_FOLLOW_RECONNECT_SEC": "300",
            "QB_WORKER_CONTAINER": WORKER_CONTAINER,
        }
    )
    return env


def _wait_for_detached(log_file: Path, proc: subprocess.Popen[str]) -> None:
    """sleep 시간 대신 detached 마커가 실제 기록될 때까지 폴링한다."""
    deadline = time.monotonic() + POLL_LIMIT_SECONDS
    while time.monotonic() < deadline:
        if log_file.is_file() and "=== [follow] detached " in log_file.read_text(encoding="utf-8"):
            return
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            pytest.fail(f"follower가 detached 전 종료됐다 (rc={proc.returncode}): {stderr}")
        time.sleep(POLL_INTERVAL_SECONDS)
    pytest.fail(f"{POLL_LIMIT_SECONDS}초 안에 detached 마커가 기록되지 않았다: {log_file}")


def _terminate(proc: subprocess.Popen[str]) -> None:
    """테스트가 띄운 무한 follower를 SIGTERM 후 회수해 좀비를 남기지 않는다."""
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
        pytest.fail("SIGTERM 뒤에도 follower 프로세스가 종료되지 않았다")


def _run_follow_once(tmp_path: Path, script: Path, lines: str, env: dict[str, str]) -> tuple[Path, Path]:
    """한 번 attach한 뒤 detached 마커를 관측하고 프로세스를 회수한다."""
    stub_bin, calls_file = _write_docker_stub(tmp_path, lines)
    lines_file = tmp_path / "docker-lines.txt"
    follow_env = _follow_environment(stub_bin, calls_file, lines_file)
    follow_env.update(env)
    log_file = tmp_path / ".soak" / "logs" / "worker-follow.log"
    proc = subprocess.Popen(
        ["bash", str(script), "run"],
        cwd=tmp_path,
        env=follow_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_detached(log_file, proc)
    finally:
        _terminate(proc)
    return log_file, calls_file


def _assert_docker_call(calls_file: Path) -> list[str]:
    """음성 조건만이 아니라 실제 docker 호출까지 함께 증명한다."""
    assert calls_file.is_file(), "docker 스텁 호출 기록이 없다"
    args = calls_file.read_text(encoding="utf-8").splitlines()
    assert args[0] == "logs"
    assert args[-1] == WORKER_CONTAINER
    return args


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("QB_FOLLOW_MAX_BYTES", "abc"),
        ("QB_FOLLOW_KEEP", "0"),
        ("QB_FOLLOW_KEEP", "x"),
    ],
)
def test_invalid_config_is_rejected_before_creating_log_dir(
    tmp_path: Path,
    name: str,
    value: str,
) -> None:
    script = _fake_repo(tmp_path)
    env = os.environ.copy()
    env[name] = value

    result = _run(script, ("run",), env)

    assert result.returncode == 1
    assert name in result.stderr
    assert not (tmp_path / ".soak" / "logs").exists()


@pytest.mark.parametrize(
    "args",
    [
        ("run", "x"),
        ("--status", "x"),
        ("--help", "x"),
        (),
        ("unknown",),
    ],
)
def test_dispatch_rejects_extra_missing_and_unknown_arguments(tmp_path: Path, args: tuple[str, ...]) -> None:
    script = _fake_repo(tmp_path)

    result = _run(script, args, os.environ.copy())

    assert result.returncode == 1
    if not args:
        assert "사용:" in result.stderr


@pytest.mark.parametrize(
    ("cursor", "expected_since"),
    [
        (None, None),
        ("not-a-time", None),
        ("2026-08-20T01:02:03Z", "2026-08-20T01:02:03Z"),
    ],
)
def test_cursor_is_passed_to_docker_only_when_valid(
    tmp_path: Path,
    cursor: str | None,
    expected_since: str | None,
) -> None:
    script = _fake_repo(tmp_path)
    if cursor is not None:
        cursor_file = tmp_path / ".soak" / "logs" / ".follow-cursor"
        cursor_file.parent.mkdir(parents=True)
        cursor_file.write_text(f"{cursor}\n", encoding="utf-8")

    _, calls_file = _run_follow_once(tmp_path, script, "", {})

    args = _assert_docker_call(calls_file)
    if expected_since is None:
        assert "--since" not in args
    else:
        since_index = args.index("--since")
        assert args[since_index + 1] == expected_since


@pytest.mark.parametrize(
    ("lines", "expected_cursor"),
    [
        (
            "2026-08-20T01:02:03Z first log\n2026-08-20T01:02:04Z final log\n",
            "2026-08-20T01:02:04Z",
        ),
        ("first log without timestamp\nsecond log without timestamp\n", None),
    ],
)
def test_cursor_advances_only_from_timestamped_log_lines(
    tmp_path: Path,
    lines: str,
    expected_cursor: str | None,
) -> None:
    script = _fake_repo(tmp_path)

    _, calls_file = _run_follow_once(tmp_path, script, lines, {})

    _assert_docker_call(calls_file)
    cursor_file = tmp_path / ".soak" / "logs" / ".follow-cursor"
    if expected_cursor is None:
        assert not cursor_file.exists()
    else:
        assert cursor_file.read_text(encoding="utf-8") == f"{expected_cursor}\n"


def test_rotation_keeps_only_configured_generations_before_attach(tmp_path: Path) -> None:
    script = _fake_repo(tmp_path)
    logs = tmp_path / ".soak" / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "worker-follow.log"
    active_generation = "active-before-rotation\n" + ("x" * 250)
    log_file.write_text(active_generation, encoding="utf-8")
    for index in range(1, 4):
        (logs / f"worker-follow.log.{index}").write_text(
            f"old-generation-{index}\n",
            encoding="utf-8",
        )

    rotated_log, calls_file = _run_follow_once(
        tmp_path,
        script,
        "",
        {"QB_FOLLOW_MAX_BYTES": "200", "QB_FOLLOW_KEEP": "3"},
    )

    _assert_docker_call(calls_file)
    assert (logs / "worker-follow.log.1").read_text(encoding="utf-8") == active_generation
    assert (logs / "worker-follow.log.3").read_text(encoding="utf-8") == "old-generation-2\n"
    assert not (logs / "worker-follow.log.4").exists()
    assert "=== [follow] rotated " in rotated_log.read_text(encoding="utf-8")
