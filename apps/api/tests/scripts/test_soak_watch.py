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


def _write_stubs(tmp_path: Path) -> tuple[Path, Path]:
    """macOS에도 같은 경로를 타도록 `timeout`·날짜·알림 캡처기를 둔다."""
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    timeout = stub_bin / "timeout"
    timeout.write_text(
        "#!/usr/bin/env bash\n"
        "shift\n"
        "exec \"$@\"\n",
        encoding="utf-8",
    )
    timeout.chmod(0o755)
    date = stub_bin / "date"
    date.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' '{TODAY}'\n", encoding="utf-8")
    date.chmod(0o755)

    notify = tmp_path / "notify-stub.sh"
    notify.write_text(
        "#!/usr/bin/env bash\n"
        "cat > \"${QB_TEST_NOTIFY_BODY:?}\"\n",
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


def _run(
    tmp_path: Path,
    output: str,
    *,
    gate_returncode: int = 0,
    args: tuple[str, ...] = ("--dry-run",),
) -> subprocess.CompletedProcess[str]:
    """실제 소크·게이트·텔레그램에 닿지 않는 감시 1회를 실행한다."""
    script = _fake_repo(tmp_path)
    gate_output = _write_gate(tmp_path, output, gate_returncode)
    stub_bin, notify = _write_stubs(tmp_path)
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
    assert (tmp_path / "gate-calls").read_text(encoding="utf-8") == "called\n"
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
