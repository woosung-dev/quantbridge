"""mise shim PATH 고정 함수의 실패·성공 계약을 검증한다."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "lib" / "mise-shim-path.sh"
_BASH = Path("/bin/bash")
_SCRIPT = (
    'set -uo pipefail; . "$1"; qb_pin_tool_path > "$2" 2> "$3"; '
    'rc=$?; printf "%s\\n%s\\n" "$rc" "$PATH"'
)


def run_shim_path(
    tmp_path: Path,
    *,
    home: Path,
    mise_data_dir: Path | None,
    path: str,
) -> tuple[int, str, str, str]:
    """실행자 설치를 배제한 셸에서 함수 결과와 PATH 부작용을 분리해 읽는다."""
    out = tmp_path / "function.stdout"
    err = tmp_path / "function.stderr"
    env = {"HOME": str(home), "PATH": path}
    if mise_data_dir is not None:
        env["MISE_DATA_DIR"] = str(mise_data_dir)

    result = subprocess.run(
        [str(_BASH), "-c", _SCRIPT, "x", str(LIB), str(out), str(err)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )

    assert result.returncode == 0
    rc, path_after, trailing = result.stdout.split("\n", 2)
    assert trailing == ""
    return int(rc), path_after, out.read_text(encoding="utf-8"), err.read_text(encoding="utf-8")


def test_missing_shims_returns_one_without_changing_path(tmp_path: Path) -> None:
    """shim 디렉터리 부재는 2줄 진단과 rc=1만 남기고 PATH를 보존한다."""
    home = tmp_path / "home"
    data_dir = tmp_path / "mise-data"
    original_path = str(tmp_path / "original-path")

    rc, path_after, stdout, stderr = run_shim_path(
        tmp_path,
        home=home,
        mise_data_dir=data_dir,
        path=original_path,
    )

    assert rc == 1
    assert path_after == original_path
    assert stdout == ""
    assert stderr.splitlines() == [
        f"⚠ mise shim 디렉터리가 없다: {data_dir / 'shims'}",
        "  도구 버전이 핀(mise.toml)이 아니라 이 셸의 PATH 로 결정된다 — 결과를 CI 와 비교하지 마라.",
    ]


def test_existing_shims_are_prepended_silently(tmp_path: Path) -> None:
    """존재하는 shim 디렉터리는 PATH 첫 항목이 되고 함수는 조용히 성공한다."""
    home = tmp_path / "home"
    data_dir = tmp_path / "mise-data"
    shims = data_dir / "shims"
    shims.mkdir(parents=True)
    original_path = str(tmp_path / "original-path")

    rc, path_after, stdout, stderr = run_shim_path(
        tmp_path,
        home=home,
        mise_data_dir=data_dir,
        path=original_path,
    )

    assert rc == 0
    assert path_after.split(":", 1)[0] == str(shims)
    assert stdout == ""
    assert stderr == ""


def test_existing_shims_are_prepended_even_when_already_in_path(tmp_path: Path) -> None:
    """shim이 PATH 중간에 있어도 낡은 도구보다 앞으로 다시 붙인다."""
    home = tmp_path / "home"
    data_dir = tmp_path / "mise-data"
    shims = data_dir / "shims"
    old_tools = tmp_path / "old-tools"
    remainder = tmp_path / "remainder"
    shims.mkdir(parents=True)
    old_tools.mkdir()
    remainder.mkdir()
    original_path = ":".join((str(old_tools), str(shims), str(remainder)))

    rc, path_after, stdout, stderr = run_shim_path(
        tmp_path,
        home=home,
        mise_data_dir=data_dir,
        path=original_path,
    )

    assert rc == 0
    assert path_after.split(":", 1)[0] == str(shims)
    assert stdout == ""
    assert stderr == ""


def test_mise_data_dir_takes_precedence_and_home_is_the_fallback(tmp_path: Path) -> None:
    """MISE_DATA_DIR을 우선하고, 없으면 HOME 아래 mise shim을 사용한다."""
    home = tmp_path / "home"
    data_dir = tmp_path / "mise-data"
    data_shims = data_dir / "shims"
    data_shims.mkdir(parents=True)
    original_path = str(tmp_path / "original-path")

    data_rc, data_path, data_stdout, data_stderr = run_shim_path(
        tmp_path,
        home=home,
        mise_data_dir=data_dir,
        path=original_path,
    )

    home_shims = home / ".local" / "share" / "mise" / "shims"
    home_shims.mkdir(parents=True)
    home_rc, home_path, home_stdout, home_stderr = run_shim_path(
        tmp_path,
        home=home,
        mise_data_dir=None,
        path=original_path,
    )

    assert data_rc == 0
    assert data_path.split(":", 1)[0] == str(data_shims)
    assert data_stdout == ""
    assert data_stderr == ""
    assert home_rc == 0
    assert home_path.split(":", 1)[0] == str(home_shims)
    assert home_stdout == ""
    assert home_stderr == ""


def test_pinning_does_not_execute_mise(tmp_path: Path) -> None:
    """성공 경로에서도 PATH의 mise 스텁은 호출하지 않는다."""
    home = tmp_path / "home"
    data_dir = tmp_path / "mise-data"
    shims = data_dir / "shims"
    shims.mkdir(parents=True)
    old_tools = tmp_path / "old-tools"
    old_tools.mkdir()
    marker = tmp_path / "mise-was-called"
    mise_stub = old_tools / "mise"
    mise_stub.write_text(
        f"#!/bin/sh\n: > {shlex.quote(str(marker))}\n",
        encoding="utf-8",
    )
    mise_stub.chmod(0o755)

    rc, path_after, stdout, stderr = run_shim_path(
        tmp_path,
        home=home,
        mise_data_dir=data_dir,
        path=str(old_tools),
    )

    assert rc == 0
    assert path_after.split(":", 1)[0] == str(shims)
    assert stdout == ""
    assert stderr == ""
    assert not marker.exists()


@pytest.mark.xfail(
    strict=True,
    reason="[BL-791] 내용물 미검증 — fail 정책 결정 전이라 현재는 rc=0",
)
def test_empty_shims_dir_is_rejected(tmp_path: Path) -> None:
    """BL-791: 빈 shim 디렉터리는 현재 성공하므로 향후 정책 변경을 strict xfail로 고정한다."""
    home = tmp_path / "home"
    data_dir = tmp_path / "mise-data"
    (data_dir / "shims").mkdir(parents=True)

    rc, _, _, _ = run_shim_path(
        tmp_path,
        home=home,
        mise_data_dir=data_dir,
        path=str(tmp_path / "original-path"),
    )

    assert rc == 1
