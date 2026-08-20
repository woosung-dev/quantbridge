"""소크 감시자의 지문·발화 판단이 가짜 게이트 출력만으로 유지되는지 검증한다."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "soak-watch.sh"
NOTIFY_LIB = REAL.parent / "lib" / "notify-telegram.sh"
TODAY = "2026-08-21"
C5_OK = "⑴=✓ ⑵=✓"


def _fake_repo(tmp_path: Path) -> Path:
    """대상과 가짜 게이트를 격리된 레포 구조에 둔다."""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    copied = scripts / "soak-watch.sh"
    shutil.copy2(REAL, copied)
    return copied


def _gate_output(
    *,
    verdict: str = "PASS",
    disq: int = 0,
    windows: int = 2,
    c5: str = C5_OK,
    has_c1: bool = True,
) -> str:
    """대상 `sed` 식이 읽는 5개 앵커와 BL-003 꼬리를 만든다."""
    c1 = "  ✓ C1 24h 창 3개\n" if has_c1 else ""
    return (
        f"{c1}"
        f"판정: {verdict}\n"
        f"  ✓ C3 실격 사건  {disq}건\n"
        f"  귀속 창 {windows}개: 가짜 창\n"
        f"  ✓ C5 측정 무결  {c5}\n"
        "══ [BL-003] 가짜 게이트 본문\n"
    )


def _write_gate(tmp_path: Path, output: str, returncode: int = 0) -> Path:
    """호출 기록을 남기고 고정된 출력·종료 코드를 내는 가짜 게이트를 만든다."""
    gate_output = tmp_path / "gate-output.txt"
    gate_output.write_text(output, encoding="utf-8")
    gate = tmp_path / "tools" / "scripts" / "soak-gate.sh"
    gate.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'called\\n' >> \"${QB_TEST_GATE_CALLS:?}\"\n"
        "cat \"${QB_TEST_GATE_OUTPUT:?}\"\n"
        f"exit {returncode}\n",
        encoding="utf-8",
    )
    gate.chmod(0o755)
    return gate_output


def _write_stubs(
    tmp_path: Path,
    *,
    stub_date: bool = True,
    notify_returncode: int = 0,
) -> tuple[Path, Path]:
    """격리 실행에 필요한 `timeout`·선택적 날짜·알림 명령을 둔다."""
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir(exist_ok=True)
    timeout = stub_bin / "timeout"
    timeout.write_text(
        "#!/usr/bin/env bash\n"
        "shift\n"
        "exec \"$@\"\n",
        encoding="utf-8",
    )
    timeout.chmod(0o755)
    if stub_date:
        date = stub_bin / "date"
        date.write_text(
            f"#!/usr/bin/env bash\nprintf '%s\\n' '{TODAY}'\n",
            encoding="utf-8",
        )
        date.chmod(0o755)

    notify = tmp_path / "notify-stub.sh"
    if notify_returncode:
        notify.write_text(
            f"#!/usr/bin/env bash\nexit {notify_returncode}\n",
            encoding="utf-8",
        )
    else:
        notify.write_text(
            "#!/usr/bin/env bash\n"
            "cat >> \"${QB_TEST_NOTIFY_BODY:?}\"\n",
            encoding="utf-8",
        )
    notify.chmod(0o755)
    return stub_bin, notify


def _write_state(
    tmp_path: Path,
    fingerprint: str,
    disq: int,
    heartbeat_date: str = TODAY,
) -> None:
    """이전 감시 결과를 명시해 변화·증가·무발화 갈래를 분리한다."""
    state_file = tmp_path / "state" / "soak-watch.state"
    state_file.parent.mkdir(exist_ok=True)
    state_file.write_text(
        "FINGERPRINT=" + fingerprint + "\n"
        f"DISQ={disq}\n"
        f"HEARTBEAT_DATE={heartbeat_date}\n",
        encoding="utf-8",
    )


def _unit_dir(tmp_path: Path) -> Path:
    """`XDG_CONFIG_HOME` 아래의 격리된 systemd user 유닛 디렉터리를 돌려준다."""
    return tmp_path / "xdg-config" / "systemd" / "user"


def _write_watch_unit(tmp_path: Path, execstart: Path) -> None:
    """`_install`이 굽는 watch 유닛의 ExecStart 형식으로 손수 쓴다."""
    unit_dir = _unit_dir(tmp_path)
    unit_dir.mkdir(parents=True, exist_ok=True)
    (unit_dir / "dev.quantbridge.soak-watch.service").write_text(
        "[Unit]\n"
        "Description=QuantBridge soak watch (게이트 1회 호출 + 지문 변화 시 텔레그램)\n"
        "OnFailure=dev.quantbridge.soak-watch-alarm.service\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"WorkingDirectory={tmp_path}\n"
        "Environment=PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin\n"
        f"ExecStart=/bin/bash {execstart}\n",
        encoding="utf-8",
    )


def _write_alarm_unit(tmp_path: Path, env_file: Path) -> None:
    """`_install`과 같은 `. "<env>"` alarm ExecStart 형식으로 손수 쓴다."""
    unit_dir = _unit_dir(tmp_path)
    unit_dir.mkdir(parents=True, exist_ok=True)
    (unit_dir / "dev.quantbridge.soak-watch-alarm.service").write_text(
        "[Unit]\n"
        "Description=QuantBridge soak watch 실패 알림 (감시자 자신이 죽었을 때)\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        "Environment=PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin\n"
        "ExecStart=/bin/bash -c 'set -a; . "
        f'"{env_file}"; '
        "set +a; exec curl --silent --fail --output /dev/null --max-time 15 "
        '--data-urlencode "chat_id=$${TELEGRAM_CHAT_ID}" '
        '--data-urlencode "text=🔴 soak-watch.service 가 실패했다 — 소크 알림이 끊겼다. '
        'journalctl --user -u dev.quantbridge.soak-watch.service -n 20" '
        '"https://api.telegram.org/bot$${TELEGRAM_BOT_TOKEN}/sendMessage"\'\n',
        encoding="utf-8",
    )


def _run_status(tmp_path: Path, script: Path) -> subprocess.CompletedProcess[str]:
    """systemctl을 대체하지 않고 `--status`의 설치본 신선도만 실행한다."""
    credential_file = tmp_path / "fake.env"
    credential_file.write_text(
        "TELEGRAM_BOT_TOKEN=fake\nTELEGRAM_CHAT_ID=fake\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
        "QB_SOAK_WATCH_STATE": str(tmp_path / "state" / "soak-watch.state"),
        "QB_SOAK_ENV_FILE": str(credential_file),
        "QB_NOTIFY_LIB": str(NOTIFY_LIB),
    }
    return subprocess.run(
        ["bash", str(script), "--status"],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )


def _run(
    tmp_path: Path,
    output: str,
    *,
    gate_returncode: int = 0,
    args: tuple[str, ...] = ("--dry-run",),
    stub_date: bool = True,
    notify_returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    """실제 소크·게이트·텔레그램에 닿지 않는 감시 1회를 실행한다."""
    call_log = tmp_path / "gate-calls"
    previous_calls = call_log.read_text(encoding="utf-8") if call_log.exists() else ""
    script = _fake_repo(tmp_path)
    gate_output = _write_gate(tmp_path, output, gate_returncode)
    stub_bin, notify = _write_stubs(
        tmp_path,
        stub_date=stub_date,
        notify_returncode=notify_returncode,
    )
    credential_file = tmp_path / "fake.env"
    credential_file.write_text("TELEGRAM_BOT_TOKEN=fake\nTELEGRAM_CHAT_ID=fake\n", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{stub_bin}:{os.environ['PATH']}",
        "QB_SOAK_WATCH_STATE": str(tmp_path / "state" / "soak-watch.state"),
        "QB_SOAK_ENV_FILE": str(credential_file),
        "QB_SOAK_NOTIFY_CMD": str(notify),
        "QB_NOTIFY_LIB": str(NOTIFY_LIB),
        "QB_SOAK_GATE_TIMEOUT": "1",
        "QB_TEST_GATE_CALLS": str(tmp_path / "gate-calls"),
        "QB_TEST_GATE_OUTPUT": str(gate_output),
        "QB_TEST_NOTIFY_BODY": str(tmp_path / "notify-body"),
    }
    result = subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    assert call_log.read_text(encoding="utf-8") == previous_calls + "called\n"
    return result


def test_first_dry_run_reports_start_fingerprint_without_writing_state(tmp_path: Path) -> None:
    """첫 dry-run은 앵커 지문과 감시 시작을 내되 상태를 남기지 않는다."""
    result = _run(tmp_path, _gate_output())

    assert result.returncode == 0, result.stderr
    assert "감시 시작" in result.stdout
    assert f"PASS|0|2|{C5_OK}" in result.stdout
    assert not (tmp_path / "state" / "soak-watch.state").exists()


def test_missing_c1_anchor_is_crash_not_fail(tmp_path: Path) -> None:
    """C1 앵커가 없으면 PASS 출력이어도 게이트 크래시로 분류한다."""
    result = _run(tmp_path, _gate_output(has_c1=False))

    assert result.returncode == 0, result.stderr
    assert "게이트 크래시" in result.stdout
    assert "CRASH" in result.stdout
    assert "[소크] FAIL" not in result.stdout
    assert "판정 FAIL" not in result.stdout


@pytest.mark.parametrize(
    ("output", "gate_returncode", "expected_fingerprint"),
    [
        (_gate_output(has_c1=False), 0, "CRASH"),
        (_gate_output(), 1, f"PASS|0|2|{C5_OK}"),
    ],
    ids=("rc-zero-without-c1-is-crash", "rc-one-with-c1-is-not-crash"),
)
def test_exit_code_does_not_classify_gate_crash(
    tmp_path: Path,
    output: str,
    gate_returncode: int,
    expected_fingerprint: str,
) -> None:
    """종료 코드와 C1 앵커의 반대 대조로 크래시 판별자를 고정한다."""
    result = _run(tmp_path, output, gate_returncode=gate_returncode)

    assert result.returncode == 0, result.stderr
    assert expected_fingerprint in result.stdout
    if expected_fingerprint == "CRASH":
        assert "게이트 크래시" in result.stdout
    else:
        assert "게이트 크래시" not in result.stdout


def test_fail_verdict_reports_fail_reason(tmp_path: Path) -> None:
    """정상 앵커의 FAIL은 크래시가 아니라 판정 FAIL 사유를 낸다."""
    result = _run(tmp_path, _gate_output(verdict="FAIL"))

    assert result.returncode == 0, result.stderr
    assert "판정 FAIL — 실격 사건이 났다" in result.stdout
    assert "[소크] FAIL" in result.stdout
    assert "게이트 크래시" not in result.stdout


def test_disqualification_increase_reports_delta_and_previous_value(tmp_path: Path) -> None:
    """실격 수가 증가하면 증가량과 이전·현재 값을 함께 보고한다."""
    _write_state(tmp_path, f"PASS|1|2|{C5_OK}", disq=1)
    result = _run(tmp_path, _gate_output(disq=3))

    assert result.returncode == 0, result.stderr
    assert "실격 +2 (1 → 3)" in result.stdout


@pytest.mark.parametrize("disq", (1, 0), ids=("same", "decrease"))
def test_disqualification_same_or_decrease_does_not_report_delta(
    tmp_path: Path, disq: int
) -> None:
    """실격이 같거나 줄면 변화가 없을 때 실격 증가 알림도 없다."""
    fingerprint = f"PASS|{disq}|2|{C5_OK}"
    _write_state(tmp_path, fingerprint, disq=1)
    result = _run(tmp_path, _gate_output(disq=disq))

    assert result.returncode == 0, result.stderr
    assert "실격 +" not in result.stdout


@pytest.mark.parametrize(
    ("output", "expected_reason"),
    [
        (_gate_output(windows=0), "활성 귀속 창 0"),
        (_gate_output(c5="⑴=✗ ⑵=✓"), "C5 측정 무결 위반"),
    ],
    ids=("zero-windows", "c5-integrity-failure"),
)
def test_zero_windows_and_c5_failure_each_report_reason(
    tmp_path: Path, output: str, expected_reason: str
) -> None:
    """창 부재와 C5 무결 위반은 서로 독립된 발화 축이다."""
    result = _run(tmp_path, output)

    assert result.returncode == 0, result.stderr
    assert expected_reason in result.stdout


def test_unchanged_fingerprint_with_today_heartbeat_is_silent(tmp_path: Path) -> None:
    """오늘 이미 알려진 같은 지문은 dry-run에서도 무발화 갈래를 탄다."""
    _write_state(tmp_path, f"PASS|0|2|{C5_OK}", disq=0)
    result = _run(tmp_path, _gate_output())

    assert result.returncode == 0, result.stderr
    assert "── [dry-run] 무발화" in result.stdout
    assert "보냈을 알림" not in result.stdout


def test_notify_seam_receives_notification_body_on_non_dry_run(tmp_path: Path) -> None:
    """실제 모드에서는 주입 seam이 본문을 stdin으로 받아 첫 줄부터 제목을 보존한다."""
    result = _run(tmp_path, _gate_output(), args=())

    notify_body = (tmp_path / "notify-body").read_text(encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert notify_body.splitlines()[0] == "🟠 [소크] 상태 변화"


def test_status_fails_when_watch_unit_is_missing(tmp_path: Path) -> None:
    """watch 유닛 부재는 타이머 조회 결과와 무관하게 실패로 판정한다."""
    script = _fake_repo(tmp_path)

    result = _run_status(tmp_path, script)

    assert result.returncode == 1, result.stderr
    assert "설치된 유닛이 없다" in result.stdout


def test_status_fails_when_execstart_points_to_missing_file(tmp_path: Path) -> None:
    """[BL-737]처럼 삭제된 ExecStart는 rc=127 진단으로 고정한다."""
    script = _fake_repo(tmp_path)
    missing_script = tmp_path / "old-layout" / "soak-watch.sh"
    alarm_env = tmp_path / "alarm.env"
    alarm_env.write_text("TELEGRAM_BOT_TOKEN=fake\n", encoding="utf-8")
    _write_watch_unit(tmp_path, missing_script)
    _write_alarm_unit(tmp_path, alarm_env)

    result = _run_status(tmp_path, script)

    assert result.returncode == 1, result.stderr
    assert "ExecStart 가 없는 파일을 가리킨다" in result.stdout
    assert "rc=127 로 죽는다" in result.stdout


def test_status_shows_both_paths_when_execstart_is_another_file(tmp_path: Path) -> None:
    """실재하지만 다른 설치본이면 재설치에 필요한 두 경로를 함께 보인다."""
    script = _fake_repo(tmp_path)
    installed_script = tmp_path / "old-layout" / "soak-watch.sh"
    installed_script.parent.mkdir()
    installed_script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    alarm_env = tmp_path / "alarm.env"
    alarm_env.write_text("TELEGRAM_BOT_TOKEN=fake\n", encoding="utf-8")
    _write_watch_unit(tmp_path, installed_script)
    _write_alarm_unit(tmp_path, alarm_env)

    result = _run_status(tmp_path, script)

    assert result.returncode == 1, result.stderr
    assert "ExecStart 가 이 파일이 아니다" in result.stdout
    assert f"설치본: {installed_script}" in result.stdout
    assert f"현재본: {script}" in result.stdout


def test_status_accepts_current_execstart_with_alarm_and_existing_env(tmp_path: Path) -> None:
    """양성 대조: 현재 스크립트·알람 유닛·env가 모두 있으면 최신이다."""
    script = _fake_repo(tmp_path)
    alarm_env = tmp_path / "alarm.env"
    alarm_env.write_text("TELEGRAM_BOT_TOKEN=fake\n", encoding="utf-8")
    _write_watch_unit(tmp_path, script)
    _write_alarm_unit(tmp_path, alarm_env)

    result = _run_status(tmp_path, script)

    assert result.returncode == 0, result.stderr
    assert f"✓ ExecStart = {script}" in result.stdout
    assert f"✓ 실패 알림 유닛 · env = {alarm_env}" in result.stdout


def test_status_fails_when_alarm_unit_is_missing(tmp_path: Path) -> None:
    """정상 watch에도 알람 유닛이 없으면 감시자 사망은 조용해진다."""
    script = _fake_repo(tmp_path)
    _write_watch_unit(tmp_path, script)

    result = _run_status(tmp_path, script)

    assert result.returncode == 1, result.stderr
    assert f"✓ ExecStart = {script}" in result.stdout
    assert "watch 가 죽어도 조용하다" in result.stdout


def test_status_fails_when_alarm_env_file_is_missing(tmp_path: Path) -> None:
    """알람 ExecStart를 읽어도 env 경로가 없으면 실패로 판정한다."""
    script = _fake_repo(tmp_path)
    missing_env = tmp_path / "missing-alarm.env"
    _write_watch_unit(tmp_path, script)
    _write_alarm_unit(tmp_path, missing_env)

    result = _run_status(tmp_path, script)

    assert result.returncode == 1, result.stderr
    assert "실패 알림 유닛의 env 파일이 없다" in result.stdout
    assert str(missing_env) in result.stdout


def test_successful_change_advances_heartbeat_date_and_silences_second_run(
    tmp_path: Path,
) -> None:
    """변화 알림도 실제로 나간 날을 기록해 다음 주기의 heartbeat를 막는다."""
    fingerprint = f"PASS|0|2|{C5_OK}"

    first = _run(tmp_path, _gate_output(), args=(), stub_date=False)

    state_file = tmp_path / "state" / "soak-watch.state"
    first_capture = (tmp_path / "notify-body").read_text(encoding="utf-8")
    state_lines = state_file.read_text(encoding="utf-8").splitlines()
    assert first.returncode == 0, first.stderr
    assert first_capture.splitlines()[0] == "🟠 [소크] 상태 변화"
    assert len(state_lines) == 3
    assert state_lines[:2] == [f"FINGERPRINT={fingerprint}", "DISQ=0"]
    assert state_lines[2].startswith("HEARTBEAT_DATE=")
    assert state_lines[2] != "HEARTBEAT_DATE="

    second = _run(tmp_path, _gate_output(), args=(), stub_date=False)

    assert second.returncode == 0, second.stderr
    assert (tmp_path / "notify-body").read_text(encoding="utf-8") == first_capture


def test_heartbeat_is_once_per_day_with_real_shell_date(tmp_path: Path) -> None:
    """같은 지문의 heartbeat는 실제 셸 날짜로 기록한 뒤 그날 한 번만 발화한다."""
    fingerprint = f"PASS|0|2|{C5_OK}"
    _write_state(tmp_path, fingerprint, disq=0, heartbeat_date="")

    first = _run(tmp_path, _gate_output(), args=(), stub_date=False)

    first_capture = (tmp_path / "notify-body").read_text(encoding="utf-8")
    assert first.returncode == 0, first.stderr
    assert first_capture.splitlines()[0] == "🟢 [소크] heartbeat"

    second = _run(tmp_path, _gate_output(), args=(), stub_date=False)

    assert second.returncode == 0, second.stderr
    assert (tmp_path / "notify-body").read_text(encoding="utf-8") == first_capture


def test_failed_notification_keeps_heartbeat_date_for_a_successful_retry(tmp_path: Path) -> None:
    """전송 실패일은 날짜를 전진시키지 않아 같은 지문도 다음 실행에 재발화한다."""
    fingerprint = f"PASS|0|2|{C5_OK}"
    _write_state(tmp_path, fingerprint, disq=0, heartbeat_date="1970-01-01")

    failed = _run(
        tmp_path,
        _gate_output(),
        args=(),
        stub_date=False,
        notify_returncode=1,
    )

    state_file = tmp_path / "state" / "soak-watch.state"
    assert failed.returncode == 1
    assert "HEARTBEAT_DATE=1970-01-01" in state_file.read_text(encoding="utf-8")

    retried = _run(tmp_path, _gate_output(), args=(), stub_date=False)

    notify_body = (tmp_path / "notify-body").read_text(encoding="utf-8")
    assert retried.returncode == 0, retried.stderr
    assert notify_body.splitlines()[0] == "🟢 [소크] heartbeat"


def test_past_heartbeat_date_emits_heartbeat_without_a_date_stub(tmp_path: Path) -> None:
    """리터럴 과거 날짜는 시계와 관계없이 같은 지문의 heartbeat를 발화한다."""
    fingerprint = f"PASS|0|2|{C5_OK}"
    _write_state(tmp_path, fingerprint, disq=0, heartbeat_date="1970-01-01")

    result = _run(tmp_path, _gate_output(), args=(), stub_date=False)

    notify_body = (tmp_path / "notify-body").read_text(encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert notify_body.splitlines()[0] == "🟢 [소크] heartbeat"
