"""soak-restart의 스택 탐침 fail-closed 계약을 고정한다.

실제 소크 스택을 건드리지 않는다. 모든 사례는 대상 스크립트를 ``tmp_path`` 가짜 레포로
복사하고, 형제 스크립트와 Docker를 PATH 스텁으로 대체한다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "soak-restart.sh"


def _fake_repo(tmp_path: Path) -> tuple[Path, Path]:
    """대상과 형제를 가짜 레포에 두고 soak-stack 호출 원장을 준비한다."""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "soak-restart.sh"
    shutil.copy2(REAL, script)

    calls = tmp_path / "soak-stack-calls.log"
    soak_stack = scripts / "soak-stack.sh"
    soak_stack.write_text(
        """#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "${SOAK_STACK_CALLS_FILE:?}"
if [ "${1:-}" = "ps" ]; then
  exit "${SOAK_STACK_PS_RC:-0}"
fi
exit "${SOAK_STACK_OTHER_RC:-0}"
""",
        encoding="utf-8",
    )
    soak_stack.chmod(0o755)

    assert_main = scripts / "assert-main-checkout.sh"
    assert_main.write_text(
        """#!/usr/bin/env bash
exit "${ASSERT_MAIN_RC:-0}"
""",
        encoding="utf-8",
    )
    assert_main.chmod(0o755)
    return script, calls


def _docker_stub(tmp_path: Path) -> Path:
    """원장 조회가 실제 소크 DB에 닿지 않도록 Docker를 항상 실패시킨다."""
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    docker = stub_dir / "docker"
    docker.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    docker.chmod(0o755)
    return stub_dir


def _env(
    tmp_path: Path,
    calls: Path,
    *,
    ps_rc: int = 0,
    assert_main_rc: int = 0,
) -> dict[str, str]:
    """가짜 형제·Docker만 쓰도록 subprocess 환경을 조립한다."""
    stub_dir = _docker_stub(tmp_path)
    return {
        **os.environ,
        "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}",
        "SOAK_STACK_CALLS_FILE": str(calls),
        "SOAK_STACK_PS_RC": str(ps_rc),
        "ASSERT_MAIN_RC": str(assert_main_rc),
    }


def _run(script: Path, environment: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """가짜 레포에 복사한 대상만 Bash로 실행한다."""
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def _calls(calls: Path) -> list[str]:
    """호출이 없으면 파일 부재 자체를 보존한다."""
    if not calls.exists():
        return []
    return calls.read_text(encoding="utf-8").splitlines()


def test_ps_measurement_failure_stops_before_any_stack_action(tmp_path: Path) -> None:
    """ps rc=2는 완전 down으로 접지 않고 rc=2로 fail-closed 한다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(script, _env(tmp_path, calls, ps_rc=2))

    assert result.returncode == 2
    assert "측정하지 못했다" in result.stderr
    assert _calls(calls) == ["ps"]


def test_running_stack_dry_run_describes_down_pin_up_without_executing(tmp_path: Path) -> None:
    """ps rc=0 갈래는 ⑷ 순서를 보이되 dry-run에서는 ps 외 호출이 없다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(script, _env(tmp_path, calls, ps_rc=0))

    assert result.returncode == 0
    assert "스택 생존: 살아 있다" in result.stdout
    assert "⑷ 는 down → pin → up" in result.stdout
    assert _calls(calls) == ["ps"]


def test_down_stack_dry_run_describes_preflight_without_executing(tmp_path: Path) -> None:
    """ps rc=1 갈래는 pin·up 선행과 ⑷ 건너뛰기를 보이되 집행하지 않는다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(script, _env(tmp_path, calls, ps_rc=1))

    assert result.returncode == 0
    assert "스택 생존: **완전 down**" in result.stdout
    assert "⑷ 는 건너뛴다" in result.stdout
    assert _calls(calls) == ["ps"]


def test_confirm_checks_main_checkout_before_stack_probe(tmp_path: Path) -> None:
    """--confirm은 워크트리 거부 시 soak-stack을 한 번도 부르지 않는다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(script, _env(tmp_path, calls, assert_main_rc=1), "--confirm")

    assert result.returncode == 2
    assert not calls.exists()


def test_strategy_id_without_value_is_usage_error(tmp_path: Path) -> None:
    """값 없는 --strategy-id는 스택 탐침 전에 인자 오류로 끝난다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(script, _env(tmp_path, calls), "--strategy-id")

    assert result.returncode == 2
    assert "--strategy-id 에 값이 없다" in result.stderr
    assert not calls.exists()


def test_unknown_argument_is_usage_error(tmp_path: Path) -> None:
    """알 수 없는 인자는 스택 탐침 전에 명시적으로 거부한다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(script, _env(tmp_path, calls), "--not-an-option")

    assert result.returncode == 2
    assert "알 수 없는 인자" in result.stderr
    assert not calls.exists()


@pytest.mark.parametrize(
    ("args", "assert_main_rc", "expected_rc", "expected_calls"),
    [
        (("--dry-run", "--confirm"), 1, 2, []),
        (("--confirm", "--dry-run"), 1, 0, ["ps"]),
    ],
)
def test_last_execution_mode_flag_wins(
    tmp_path: Path,
    args: tuple[str, str],
    assert_main_rc: int,
    expected_rc: int,
    expected_calls: list[str],
) -> None:
    """--dry-run과 --confirm을 함께 주면 뒤 플래그가 순차 파싱 결과를 결정한다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(
        script,
        _env(tmp_path, calls, assert_main_rc=assert_main_rc),
        *args,
    )

    assert result.returncode == expected_rc
    assert _calls(calls) == expected_calls


@pytest.mark.xfail(
    strict=True,
    reason="--help의 sed -n '2,40p' 범위가 34행 헤더 뒤 실행 코드를 출력한다",
)
def test_help_does_not_print_shell_code_after_header(tmp_path: Path) -> None:
    """현재 드리프트: 도움말은 헤더 범위만 출력해야 한다."""
    script, calls = _fake_repo(tmp_path)

    result = _run(script, _env(tmp_path, calls), "--help")

    assert result.returncode == 0
    assert "set -uo pipefail" not in result.stdout
    assert not calls.exists()
