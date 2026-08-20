"""DB 백업 상태 점검의 설치본 신선도와 파일 보관 출력을 검증한다."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "db-backup.sh"
UNIT_NAME = "dev.quantbridge.db-backup"
ALARM_UNIT = "dev.quantbridge.db-backup-alarm"


def run_status(
    tmp_path: Path, xdg: Path, backup_dir: Path
) -> subprocess.CompletedProcess[str]:
    """실제 스크립트의 `--status`만 격리 경로로 실행한다."""
    env = {
        **os.environ,
        "XDG_CONFIG_HOME": str(xdg),
        "QB_BACKUP_DIR": str(backup_dir),
    }
    return subprocess.run(
        ["bash", str(SCRIPT), "--status"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        cwd=tmp_path,
        check=False,
    )


def _unit_dir(xdg: Path) -> Path:
    """`--install`이 만들 systemd user 유닛 디렉터리를 계산한다."""
    return xdg / "systemd" / "user"


def _write_backup_unit(xdg: Path, executable: Path, *, has_run_suffix: bool = True) -> None:
    """설치 유닛의 ExecStart 계약을 수동으로 만든다."""
    suffix = " run" if has_run_suffix else ""
    unit_path = _unit_dir(xdg) / f"{UNIT_NAME}.service"
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(
        f"[Service]\nExecStart=/bin/bash {executable}{suffix}\n", encoding="utf-8"
    )


def _write_alarm_unit(xdg: Path) -> None:
    """신선도 판정에 필요한 알람 유닛 존재만 만든다."""
    unit_path = _unit_dir(xdg) / f"{ALARM_UNIT}.service"
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text("[Service]\nExecStart=/bin/true\n", encoding="utf-8")


def _write_dump(backup_dir: Path, name: str, *, meta: str | None = None) -> Path:
    """`--status`가 세는 이름 규약의 비어 있지 않은 덤프를 만든다."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    dump = backup_dir / name
    dump.write_text("backup", encoding="utf-8")
    if meta is not None:
        (backup_dir / f"{name}.meta").write_text(meta, encoding="utf-8")
    return dump


def _prepare_healthy_status(tmp_path: Path) -> tuple[Path, Path]:
    """신선도 외 실패원을 제거한 정상 유닛·백업 파일 쌍을 만든다."""
    xdg = tmp_path / "xdg"
    backup_dir = tmp_path / "backups"
    _write_backup_unit(xdg, SCRIPT)
    _write_alarm_unit(xdg)
    _write_dump(backup_dir, "quantbridge-20260821T000000Z.dump")
    return xdg, backup_dir


def test_status_fails_when_backup_unit_is_missing(tmp_path: Path) -> None:
    """주 서비스 유닛이 없으면 설치본 신선도는 실패다."""
    xdg = tmp_path / "xdg"
    backup_dir = tmp_path / "backups"
    _write_dump(backup_dir, "quantbridge-20260821T000000Z.dump")

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 1
    assert "설치된 유닛이 없다" in result.stdout


def test_status_fails_when_execstart_target_is_missing(tmp_path: Path) -> None:
    """사라진 경로가 남은 유닛은 rc=127 사망 가능성을 실패로 알린다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)
    missing_script = tmp_path / "moved" / "db-backup.sh"
    _write_backup_unit(xdg, missing_script)

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 1
    assert "ExecStart 가 없는 파일을 가리킨다" in result.stdout
    assert "rc=127 로 죽는다" in result.stdout


def test_status_fails_when_execstart_targets_another_existing_file(tmp_path: Path) -> None:
    """다른 실재 파일은 설치본과 현재본 경로를 함께 보여 주며 실패한다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)
    stale_script = tmp_path / "old" / "db-backup.sh"
    stale_script.parent.mkdir()
    stale_script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    _write_backup_unit(xdg, stale_script)

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 1
    assert "ExecStart 가 이 파일이 아니다" in result.stdout
    assert f"설치본: {stale_script}" in result.stdout
    assert f"현재본: {SCRIPT}" in result.stdout


def test_status_succeeds_with_current_units_and_backup(tmp_path: Path) -> None:
    """현재 스크립트·알람 유닛·덤프가 모두 있으면 상태 점검은 성공한다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 0, result.stdout
    assert f"ExecStart = {SCRIPT}" in result.stdout
    assert "실패 알림 유닛 있음" in result.stdout
    assert "보관 1개" in result.stdout


def test_status_fails_when_alarm_unit_is_missing(tmp_path: Path) -> None:
    """정상 ExecStart라도 알람 유닛이 없으면 조용한 사망 위험으로 실패한다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)
    (_unit_dir(xdg) / f"{ALARM_UNIT}.service").unlink()

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 1
    assert "실패 알림 유닛이 없다" in result.stdout
    assert "백업이 죽어도 조용하다" in result.stdout


def test_status_treats_execstart_without_run_suffix_as_missing_unit(tmp_path: Path) -> None:
    """` run` 접미가 빠진 유닛은 추출되지 않아 설치 부재로 실패한다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)
    _write_backup_unit(xdg, SCRIPT, has_run_suffix=False)

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 1
    assert "설치된 유닛이 없다" in result.stdout


def test_status_fails_when_backup_directory_is_missing(tmp_path: Path) -> None:
    """유닛이 정상이더라도 백업 디렉터리가 없으면 실패한다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)
    for entry in backup_dir.iterdir():
        entry.unlink()
    backup_dir.rmdir()

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 1
    assert "디렉터리가 없다" in result.stdout


def test_status_fails_when_backup_directory_has_no_dump(tmp_path: Path) -> None:
    """빈 백업 디렉터리는 복원 가능한 사본이 없으므로 실패한다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)
    for entry in backup_dir.iterdir():
        entry.unlink()

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 1
    assert "백업 파일이 하나도 없다" in result.stdout


def test_status_prints_latest_dump_count_and_indented_metadata(tmp_path: Path) -> None:
    """가장 최근 덤프와 그 메타데이터를 보관 개수와 함께 출력한다."""
    xdg, backup_dir = _prepare_healthy_status(tmp_path)
    older_dump = _write_dump(backup_dir, "quantbridge-20260820T000000Z.dump")
    newest_dump = _write_dump(
        backup_dir,
        "quantbridge-20260821T000000Z.dump",
        meta="finished_at=2026-08-21T00:00:00Z\n",
    )
    os.utime(older_dump, (1_000_000_000, 1_000_000_000))
    os.utime(newest_dump, (1_000_000_100, 1_000_000_100))

    result = run_status(tmp_path, xdg, backup_dir)

    assert result.returncode == 0, result.stdout
    assert "보관 2개" in result.stdout
    assert f"최근: {newest_dump}" in result.stdout
    assert "        finished_at=2026-08-21T00:00:00Z" in result.stdout
