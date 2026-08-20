"""디스크 경보의 발화 조건이 상태 전이를 보존하는지 검증한다."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

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


def _run_dry_check(tmp_path: Path, pct: int) -> subprocess.CompletedProcess[str]:
    """격리된 환경에서 한 번의 dry-run 판정을 실행한다."""
    stub_dir = _stub_bin(tmp_path, pct)
    env = {
        **os.environ,
        "PATH": f"{stub_dir}:{os.environ['PATH']}",
        "QB_DISK_TARGET": "/",
        "QB_DISK_WARN_PCT": "80",
        "QB_DISK_STATE": str(tmp_path / "state" / "disk-guard.state"),
        "QB_SOAK_ENV_FILE": str(tmp_path / "env.local"),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg"),
    }
    result = subprocess.run(
        [str(SCRIPT), "--dry-run"],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
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
