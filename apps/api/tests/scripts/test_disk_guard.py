"""디스크 경보의 발화 조건이 상태 전이를 보존하는지 검증한다."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "disk-guard.sh"
TODAY = "2026-08-20"


def _stub_bin(
    tmp_path: Path,
    pct: int,
    avail_kb: int = 10485760,
    today: str = TODAY,
) -> Path:
    """`df`와 `date`를 갈아끼운 PATH 디렉터리를 만든다."""
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir(exist_ok=True)
    (stub_dir / "df").write_text(
        "#!/bin/sh\n"
        "echo 'Filesystem 1024-blocks Used Available Capacity Mounted-on'\n"
        f"echo '/dev/sda1 104857600 1 {avail_kb} {pct}% /'\n",
        encoding="utf-8",
    )
    (stub_dir / "date").write_text(
        f"#!/bin/sh\nprintf '%s\\n' '{today}'\n", encoding="utf-8"
    )
    for stub in ("df", "date"):
        (stub_dir / stub).chmod(0o755)
    return stub_dir


def _write_state(tmp_path: Path, level: str, notified_date: str) -> None:
    """이전 점검 상태를 직접 만든다. dry-run은 상태를 쓰지 않는다."""
    state_file = tmp_path / "state" / "disk-guard.state"
    state_file.parent.mkdir()
    state_file.write_text(
        f"LEVEL={level}\nNOTIFIED_DATE={notified_date}\n", encoding="utf-8"
    )


def _write_notify_stub(tmp_path: Path) -> Path:
    """stdin 본문을 남기고 지정한 종료 코드로 끝나는 알림 주입 명령을 만든다."""
    notify_stub = tmp_path / "notify-stub.sh"
    notify_stub.write_text(
        "#!/bin/sh\n"
        "while IFS= read -r line; do\n"
        "  printf '%s\\n' \"$line\"\n"
        "done > \"${QB_TEST_NOTIFY_BODY}\"\n"
        "exit \"${QB_TEST_NOTIFY_EXIT}\"\n",
        encoding="utf-8",
    )
    notify_stub.chmod(0o755)
    return notify_stub


def _run_check(
    tmp_path: Path,
    pct: int,
    *,
    args: tuple[str, ...] = (),
    df_stub: str | None = None,
    notify_exit: int = 0,
    stub_systemctl: bool = False,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """기존 df/date 스텁 환경에서 disk-guard 한 번을 실행한다."""
    stub_dir = _stub_bin(tmp_path, pct)
    if df_stub is not None:
        (stub_dir / "df").write_text(df_stub, encoding="utf-8")
        (stub_dir / "df").chmod(0o755)
    if stub_systemctl:
        (stub_dir / "systemctl").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (stub_dir / "systemctl").chmod(0o755)

    notify_stub = _write_notify_stub(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{stub_dir}:{os.environ['PATH']}",
        "QB_DISK_TARGET": "/",
        "QB_DISK_WARN_PCT": "80",
        "QB_DISK_STATE": str(tmp_path / "state" / "disk-guard.state"),
        "QB_DISK_NOTIFY_CMD": str(notify_stub),
        "QB_SOAK_ENV_FILE": str(tmp_path / "env.local"),
        "QB_TEST_NOTIFY_BODY": str(tmp_path / "notify-body"),
        "QB_TEST_NOTIFY_EXIT": str(notify_exit),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg"),
    }
    if env_overrides is not None:
        env.update(env_overrides)

    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )


def _run_dry_check(tmp_path: Path, pct: int) -> subprocess.CompletedProcess[str]:
    """격리된 환경에서 한 번의 dry-run 판정을 실행한다."""
    result = _run_check(tmp_path, pct, args=("--dry-run",))
    assert result.returncode == 0, result.stderr
    return result


def test_ok_to_warn_transition_fires(tmp_path: Path) -> None:
    """상태가 없던 OK에서 WARN으로 바뀌면 즉시 경보한다."""
    result = _run_dry_check(tmp_path, pct=85)

    assert "── [dry-run] 보냈을 알림 ──" in result.stdout
    assert "🟠" in result.stdout
    assert "임계 80% 를 넘었다" in result.stdout
    assert "85%" in result.stdout


def test_warn_same_day_is_silent(tmp_path: Path) -> None:
    """WARN이 같은 날 이어지면 중복 경보하지 않는다."""
    _write_state(tmp_path, level="WARN", notified_date=TODAY)
    result = _run_dry_check(tmp_path, pct=85)

    assert "── [dry-run] 무발화" in result.stdout
    assert "보냈을 알림" not in result.stdout


def test_warn_other_day_refires(tmp_path: Path) -> None:
    """WARN이 다음 날까지 이어지면 하루 한 번 재고지한다."""
    _write_state(tmp_path, level="WARN", notified_date="1970-01-01")
    result = _run_dry_check(tmp_path, pct=85)

    assert "── [dry-run] 보냈을 알림 ──" in result.stdout
    assert "재고지" in result.stdout
    assert "85%" in result.stdout


def test_warn_to_ok_transition_fires_recovery(tmp_path: Path) -> None:
    """WARN에서 OK로 회복한 전이는 알림을 남긴다."""
    _write_state(tmp_path, level="WARN", notified_date=TODAY)
    result = _run_dry_check(tmp_path, pct=10)

    assert "── [dry-run] 보냈을 알림 ──" in result.stdout
    assert "🟢" in result.stdout
    assert "회복" in result.stdout
    assert "10%" in result.stdout


def test_ok_remains_silent(tmp_path: Path) -> None:
    """OK가 이어질 때는 heartbeat를 보내지 않는다."""
    _write_state(tmp_path, level="OK", notified_date=TODAY)
    result = _run_dry_check(tmp_path, pct=10)

    assert "── [dry-run] 무발화" in result.stdout
    assert "보냈을 알림" not in result.stdout


def test_warn_threshold_boundary_fires(tmp_path: Path) -> None:
    """사용률이 임계와 같아도 -ge 비교로 WARN이 된다."""
    result = _run_dry_check(tmp_path, pct=80)

    assert "── [dry-run] 보냈을 알림 ──" in result.stdout
    assert "🟠" in result.stdout
    assert "80%" in result.stdout


def test_below_warn_threshold_is_ok(tmp_path: Path) -> None:
    """임계 바로 아래 사용률은 OK 유지로 무발화다."""
    _write_state(tmp_path, level="OK", notified_date=TODAY)
    result = _run_dry_check(tmp_path, pct=79)

    assert "── [dry-run] 무발화 (OK 79% · 임계 80%) ──" in result.stdout
    assert "보냈을 알림" not in result.stdout


def test_dry_run_warn_does_not_write_state(tmp_path: Path) -> None:
    """dry-run WARN 전이는 알림 판단만 하고 상태 파일을 만들지 않는다."""
    result = _run_dry_check(tmp_path, pct=85)

    assert "보냈을 알림" in result.stdout
    assert not (tmp_path / "state" / "disk-guard.state").exists()


def test_notify_success_writes_warn_state_and_body(tmp_path: Path) -> None:
    """실제 WARN 전이는 주입 알림 성공 후 오늘 날짜로 상태를 저장한다."""
    result = _run_check(tmp_path, pct=85)

    state_file = tmp_path / "state" / "disk-guard.state"
    notify_body = tmp_path / "notify-body"
    assert result.returncode == 0, result.stderr
    assert "🟠 [디스크]" in notify_body.read_text(encoding="utf-8")
    assert state_file.read_text(encoding="utf-8") == f"LEVEL=WARN\nNOTIFIED_DATE={TODAY}\n"


def test_notify_failure_returns_one_but_preserves_notified_date(tmp_path: Path) -> None:
    """알림 실패는 WARN 상태만 저장하고 성공 날짜를 거짓으로 갱신하지 않는다."""
    _write_state(tmp_path, level="OK", notified_date="1970-01-01")
    result = _run_check(tmp_path, pct=85, notify_exit=1)

    state_file = tmp_path / "state" / "disk-guard.state"
    assert result.returncode == 1
    assert "🟠 [디스크]" in (tmp_path / "notify-body").read_text(encoding="utf-8")
    assert state_file.read_text(encoding="utf-8") == "LEVEL=WARN\nNOTIFIED_DATE=1970-01-01\n"


def test_non_firing_ok_check_writes_ok_state(tmp_path: Path) -> None:
    """OK 유지에는 알림이 없어도 마지막 상태를 저장한다."""
    result = _run_check(tmp_path, pct=10)

    state_file = tmp_path / "state" / "disk-guard.state"
    assert result.returncode == 0, result.stderr
    assert state_file.read_text(encoding="utf-8") == "LEVEL=OK\nNOTIFIED_DATE=\n"
    assert not (tmp_path / "notify-body").exists()


@pytest.mark.parametrize(
    "df_stub",
    [
        "#!/bin/sh\nexit 0\n",
        "#!/bin/sh\n"
        "echo 'Filesystem 1024-blocks Used Available Capacity Mounted-on'\n"
        "echo '/dev/sda1 104857600 1 10485760 invalid% /'\n",
    ],
)
def test_df_parse_failure_returns_one(tmp_path: Path, df_stub: str) -> None:
    """빈 df 출력과 숫자가 아닌 사용률은 감시자 실패로 처리한다."""
    result = _run_check(tmp_path, pct=10, df_stub=df_stub)

    assert result.returncode == 1
    assert "df 판독 실패" in result.stderr


def test_non_numeric_warn_threshold_returns_one(tmp_path: Path) -> None:
    """임계값이 숫자가 아니면 판정 전에 실패한다."""
    result = _run_check(
        tmp_path,
        pct=10,
        env_overrides={"QB_DISK_WARN_PCT": "eighty"},
    )

    assert result.returncode == 1
    assert "숫자가 아니다" in result.stderr


def test_unknown_argument_fails_and_help_succeeds(tmp_path: Path) -> None:
    """허용하지 않은 인자는 거부하고 help는 사용법만 성공으로 끝낸다."""
    unknown = _run_check(tmp_path, pct=10, args=("--unknown",))
    help_result = _run_check(tmp_path, pct=10, args=("--help",))

    assert unknown.returncode == 1
    assert "알 수 없는 인자" in unknown.stderr
    assert help_result.returncode == 0
    assert "사용:" in help_result.stdout


def test_status_fails_when_primary_unit_is_missing(tmp_path: Path) -> None:
    """설치된 주 유닛이 없으면 status는 신선도 실패를 반환한다."""
    result = _run_check(tmp_path, pct=10, args=("--status",), stub_systemctl=True)

    assert result.returncode == 1
    assert "설치된 유닛이 없다" in result.stdout


def test_status_fails_when_exec_start_is_stale(tmp_path: Path) -> None:
    """옛 절대경로가 유닛에 남으면 타이머가 살아도 status는 실패한다."""
    unit_dir = tmp_path / "xdg" / "systemd" / "user"
    unit_dir.mkdir(parents=True)
    env_file = tmp_path / "env.local"
    env_file.write_text("", encoding="utf-8")
    (unit_dir / "dev.quantbridge.disk-guard.service").write_text(
        "ExecStart=/bin/bash /엉뚱한/경로/disk-guard.sh\n", encoding="utf-8"
    )
    (unit_dir / "dev.quantbridge.disk-guard-alarm.service").write_text(
        f"ExecStart=/bin/bash -c 'set -a; . \"{env_file}\"; set +a'\n",
        encoding="utf-8",
    )

    result = _run_check(tmp_path, pct=10, args=("--status",), stub_systemctl=True)

    assert result.returncode == 1
    assert "ExecStart 가 이 파일이 아니다" in result.stdout


def test_status_succeeds_when_units_are_current(tmp_path: Path) -> None:
    """두 유닛과 실패 알림 env가 현재 설치본과 맞으면 신선도는 성공한다."""
    unit_dir = tmp_path / "xdg" / "systemd" / "user"
    unit_dir.mkdir(parents=True)
    env_file = tmp_path / "env.local"
    env_file.write_text("", encoding="utf-8")
    (unit_dir / "dev.quantbridge.disk-guard.service").write_text(
        f"ExecStart=/bin/bash {SCRIPT}\n", encoding="utf-8"
    )
    (unit_dir / "dev.quantbridge.disk-guard-alarm.service").write_text(
        f"ExecStart=/bin/bash -c 'set -a; . \"{env_file}\"; set +a'\n",
        encoding="utf-8",
    )

    result = _run_check(tmp_path, pct=10, args=("--status",), stub_systemctl=True)

    assert result.returncode == 0, result.stdout
    assert f"ExecStart = {SCRIPT}" in result.stdout
    assert "실패 알림 유닛 · env" in result.stdout
