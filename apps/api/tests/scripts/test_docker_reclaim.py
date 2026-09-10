"""`tools/scripts/docker-reclaim.sh` 의 안전 계약을 고정한다 — 이 스크립트가 틀리면 **남의 롤백 태그**가 지워진다.

가짜 `docker` 를 PATH 앞에 놓고 스크립트가 무엇을 `rmi` 하려 했는지만 본다. 잰 것은 넷이다:
⑴ 저장소당 KEEP 세대 보호 ⑵ 컨테이너가 쓰는 태그 보호 ⑶ 접두사 밖(타 프로젝트) 무접촉
⑷ `rmi` 실패를 숨기지 않는다(rc=1). 종전 런북 한 줄은 ⑷ 를 `2>/dev/null` 로 어겼고 서버에
정책(3세대)보다 많은 4벌이 남아 있었다(2026-09-10 실측).
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "docker-reclaim.sh"

# `docker images` 순서 = 생성 시각 내림차순(최신 먼저). 스크립트는 그 순서에 의존한다.
IMAGES = [
    ("quantbridge-frontend", "n1"),
    ("quantbridge-frontend", "n2"),
    ("quantbridge-frontend", "n3"),
    ("quantbridge-frontend", "old4"),
    ("quantbridge-frontend", "old5"),
    ("quantbridge-backend", "b1"),
    ("quantbridge-backend", "b2"),
    ("quantbridge-backend", "b3"),
    ("quantbridge-backend", "bold4"),
    ("truewords-backend", "t1"),
    ("truewords-backend", "t2"),
    ("truewords-backend", "t3"),
    ("truewords-backend", "t4"),
    ("kairos-api", "k1"),
    ("kairos-api", "k2"),
    ("kairos-api", "k3"),
    ("kairos-api", "k4"),
]

FAKE_DOCKER = r"""#!/usr/bin/env bash
# 가짜 docker — 호출을 $FAKE_LOG 에 적고, images/ps 는 픽스처를 낸다.
printf '%s\n' "$*" >> "$FAKE_LOG"
case "$1 $2" in
  "images --format")
    # $4 = 저장소 패턴 (예: quantbridge-*). 접두사 매칭만 흉내 낸다.
    pat="${4%\*}"
    while IFS=$'\t' read -r repo tag; do
      [ -n "$repo" ] || continue
      case "$repo" in "$pat"*) printf '%s\t%s\n' "$repo" "$tag" ;; esac
    done < "$FAKE_IMAGES"
    ;;
  "ps -a") cat "$FAKE_PS" ;;
  "rmi "*)
    for f in $FAKE_RMI_FAIL; do
      [ "$f" = "$2" ] && { echo "Error: conflict: unable to remove $2" >&2; exit 1; }
    done
    ;;
  "builder prune") ;;
  "system df") echo "Build Cache 1.7GB reclaimable=1.7GB" ;;
esac
exit 0
"""


def run(
    tmp_path: Path,
    *args: str,
    images: list[tuple[str, str]] = IMAGES,
    in_use: tuple[str, ...] = (),
    rmi_fail: tuple[str, ...] = (),
    env_extra: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "docker"
    fake.write_text(FAKE_DOCKER)
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    images_f = tmp_path / "images.tsv"
    images_f.write_text("".join(f"{r}\t{t}\n" for r, t in images))
    ps_f = tmp_path / "ps.txt"
    ps_f.write_text("".join(f"{ref}\n" for ref in in_use))
    log_f = tmp_path / "calls.log"
    log_f.write_text("")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_IMAGES": str(images_f),
        "FAKE_PS": str(ps_f),
        "FAKE_LOG": str(log_f),
        "FAKE_RMI_FAIL": " ".join(rmi_fail),
        "HOME": str(tmp_path),
        **(env_extra or {}),
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    calls = log_f.read_text().splitlines()
    return proc, calls


def rmi_targets(calls: list[str]) -> list[str]:
    return [c.split(" ", 1)[1] for c in calls if c.startswith("rmi ")]


def test_script_exists_and_is_executable() -> None:
    assert SCRIPT.is_file(), f"{SCRIPT} 가 없다"
    assert os.access(SCRIPT, os.X_OK), (
        "실행 비트가 없다 — systemd ExecStart 가 bash 로 부르지만 사람도 직접 친다"
    )


def test_dry_run_is_default_and_removes_nothing(tmp_path: Path) -> None:
    """인자 없이 부르면 dry-run 이다 — 후보를 인쇄만 하고 rmi·prune 을 한 번도 안 부른다."""
    proc, calls = run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert rmi_targets(calls) == []
    assert not any(c.startswith("builder prune") for c in calls)
    assert "quantbridge-frontend:old4" in proc.stdout
    assert "dry-run" in proc.stdout


def test_confirm_keeps_three_per_repo_and_prunes_builder(tmp_path: Path) -> None:
    """⑴ 저장소마다 최신 3세대는 남고 그 밖만 지운다. builder prune 은 until 필터를 단다."""
    proc, calls = run(tmp_path, "--confirm")
    assert proc.returncode == 0, proc.stderr
    assert sorted(rmi_targets(calls)) == sorted(
        ["quantbridge-frontend:old4", "quantbridge-frontend:old5", "quantbridge-backend:bold4"]
    )
    assert "builder prune -f --filter until=168h" in calls


def test_never_touches_other_projects(tmp_path: Path) -> None:
    """⑶ truewords·kairos 는 4벌씩 있어도 rmi 인자로 가지 않는다 — 그쪽 롤백 경로다."""
    proc, calls = run(tmp_path, "--confirm")
    assert proc.returncode == 0, proc.stderr
    assert not any(ref.startswith(("truewords-", "kairos-")) for ref in rmi_targets(calls))


def test_in_use_tag_is_protected_regardless_of_generation(tmp_path: Path) -> None:
    """⑵ 4번째 세대라도 컨테이너가 쓰고 있으면 지우지 않는다(롤백 후 오래 머문 태그가 그렇다)."""
    proc, calls = run(
        tmp_path, "--confirm", in_use=("quantbridge-frontend:old4", "quantbridge-redis")
    )
    assert proc.returncode == 0, proc.stderr
    assert "quantbridge-frontend:old4" not in rmi_targets(calls)
    assert "quantbridge-frontend:old5" in rmi_targets(calls)
    assert "보호(컨테이너 사용 중): quantbridge-frontend:old4" in proc.stderr


def test_rmi_failure_is_not_hidden(tmp_path: Path) -> None:
    """⑷ rmi 하나가 실패하면 나머지는 계속하되 rc=1 로 끝난다 — 종전 `2>/dev/null` 이 어긴 계약."""
    proc, calls = run(tmp_path, "--confirm", rmi_fail=("quantbridge-frontend:old4",))
    assert proc.returncode == 1
    assert "rmi 실패: quantbridge-frontend:old4" in proc.stderr
    assert "quantbridge-frontend:old5" in rmi_targets(calls), (
        "실패 뒤에도 나머지 후보는 계속 처리한다"
    )


def test_keep_env_is_honored(tmp_path: Path) -> None:
    proc, calls = run(tmp_path, "--confirm", env_extra={"QB_RECLAIM_KEEP": "1"})
    assert proc.returncode == 0, proc.stderr
    assert "quantbridge-frontend:n2" in rmi_targets(calls)
    assert "quantbridge-frontend:n1" not in rmi_targets(calls)


@pytest.mark.parametrize("keep", ["0", "abc"])
def test_keep_must_be_positive_integer(tmp_path: Path, keep: str) -> None:
    """KEEP=0 은 실행 중 태그까지 후보로 만든다 — 기동 전에 거부한다."""
    proc, calls = run(tmp_path, "--confirm", env_extra={"QB_RECLAIM_KEEP": keep})
    assert proc.returncode == 1
    assert rmi_targets(calls) == []


def test_status_lists_candidates_without_removing(tmp_path: Path) -> None:
    proc, calls = run(tmp_path, "--status")
    assert proc.returncode == 0, proc.stderr
    assert rmi_targets(calls) == []
    assert "quantbridge-frontend:old4" in proc.stdout
    assert "설치본: 없음" in proc.stdout
