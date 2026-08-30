"""`soak-stack.sh` 의 **워커 이미지 신선도** 판정을 고정한다.

★왜 이 판정이 있나 — 2026-08-30 실측: 서버 워커 이미지가 3주간 낡아 `openai` 가 없었고
제거된 Clerk 시절 패키지를 아직 갖고 있었다. `pin` 은 `.soak/src` 만 바꾸고 의존성은
이미지에 구워져 있는데, compose 4서비스에 `image:` 태그가 없고 `up` 은 `--build` 를
안 쓰므로 **재빌드하는 주체가 없다.** 그 드리프트는 감사 중 우연히 걸렸다.

★**3값을 재는 것이 이 파일의 핵심이다** — `same` / `stale` / **`unknown`**.
「이미지를 못 읽었다」를 「동일하다」로 접으면 낡은 이미지를 최신이라 말하게 된다.
`test_missing_image_is_unknown_not_same` 이 그 접힘을 막는다.

실제 docker 를 절대 부르지 않는다 — PATH 의 `docker` 스텁만 부른다.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "soak-stack.sh"

REPO_LOCK_BODY = "version = 1\nrequires-python = '>=3.12'\n"
# 같은 내용을 이미지도 갖고 있으면 sha256 이 같다. 값을 하드코딩하지 않는다 —
# 스텁이 레포 파일을 그대로 해싱하게 해서 「같음」을 **계산으로** 만든다.


def _fake_repo(tmp_path: Path, *, repo_lock: str | None = REPO_LOCK_BODY) -> Path:
    """대상 스크립트를 가짜 레포에 두고 `apps/api/uv.lock` 만 심는다."""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "soak-stack.sh"
    shutil.copy2(REAL, script)

    api = tmp_path / "apps" / "api"
    api.mkdir(parents=True)
    if repo_lock is not None:
        (api / "uv.lock").write_text(repo_lock, encoding="utf-8")
    return script


def _write_docker_stub(tmp_path: Path, *, image_lock: str | None) -> Path:
    """`docker run … sha256sum /app/uv.lock` 만 답하는 스텁.

    `image_lock` 이 None 이면 이미지가 없는 상황(비어 있는 stdout + rc≠0)을 흉내낸다.
    """
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    lock_file = tmp_path / "image-uv.lock"
    if image_lock is not None:
        lock_file.write_text(image_lock, encoding="utf-8")

    (stub_bin / "docker").write_text(
        f"""#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "${{DOCKER_STUB_CALLS_FILE:?}}"

if [ "$1" = "run" ]; then
  if [ -f "{lock_file}" ]; then
    # 실제 이미지 안의 `sha256sum /app/uv.lock` 출력 형태를 그대로 흉내낸다.
    if command -v sha256sum > /dev/null 2>&1; then
      sha256sum "{lock_file}" | cut -d' ' -f1 | sed 's|$|  /app/uv.lock|'
    else
      shasum -a 256 "{lock_file}" | cut -d' ' -f1 | sed 's|$|  /app/uv.lock|'
    fi
    exit 0
  fi
  printf 'Unable to find image\\n' >&2
  exit 125
fi

# status 의 나머지 축(mount/psql)은 이 파일의 관심사가 아니다 — 조용히 빈 값.
exit 0
""",
        encoding="utf-8",
    )
    (stub_bin / "docker").chmod(0o755)
    return stub_bin


def _run(
    script: Path, stub_bin: Path, tmp_path: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    calls = tmp_path / "docker-calls.txt"
    calls.touch()
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        env={
            "PATH": f"{stub_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(tmp_path),
            "DOCKER_STUB_CALLS_FILE": str(calls),
        },
        check=False,
    )


# --------------------------------------------------------------- 판정 3값


def test_identical_lock_reports_same(tmp_path: Path) -> None:
    """이미지와 레포의 `uv.lock` 이 같으면 `same` 이다."""
    script = _fake_repo(tmp_path)
    stub = _write_docker_stub(tmp_path, image_lock=REPO_LOCK_BODY)

    result = _run(script, stub, tmp_path, "status")

    assert "이미지 의존성: 레포 uv.lock 과 동일" in result.stdout
    assert "낡았다" not in result.stdout


def test_different_lock_reports_stale_with_rebuild_command(tmp_path: Path) -> None:
    """내용이 다르면 `stale` 이고, **재빌드 명령을 함께 찍는다**.

    ★경고만 하고 방법을 안 알려주면 사람은 그 경고를 무시한다. 재빌드 커맨드가
    출력에 있는지까지 잰다 — 이 판정의 값은 「알려주는 것」이 아니라 「고치게 하는 것」이다.
    """
    script = _fake_repo(tmp_path)
    stub = _write_docker_stub(tmp_path, image_lock="version = 1\n# 다른 내용\n")

    result = _run(script, stub, tmp_path, "status")

    assert "이미지 의존성: ★낡았다" in result.stdout
    assert (
        "build backend-worker backend-ws-stream backend-optimizer-heavy backend-beat"
        in result.stdout
    )


def test_missing_image_is_unknown_not_same(tmp_path: Path) -> None:
    """★이미지를 못 읽으면 `unknown` 이다 — 절대 `same` 이 아니다.

    이 접힘이 이 판정의 유일한 치명적 오답이다. 「못 봤다」를 「동일하다」로 접으면
    낡은 이미지를 최신이라 보고하고, 그 보고를 믿은 사람이 재빌드를 건너뛴다.
    """
    script = _fake_repo(tmp_path)
    stub = _write_docker_stub(tmp_path, image_lock=None)

    result = _run(script, stub, tmp_path, "status")

    assert "측정 못 함" in result.stdout
    assert "이것은 「동일하다」가 아니다" in result.stdout
    assert "레포 uv.lock 과 동일" not in result.stdout


def test_missing_repo_lock_is_unknown_not_same(tmp_path: Path) -> None:
    """레포 쪽 `uv.lock` 이 없어도 `unknown` 이다(빈 문자열끼리 같다고 접지 않는다).

    ★양쪽이 모두 빈 문자열이면 소박한 `[ "$a" = "$b" ]` 는 **참**이 된다.
    그 항진명제를 막는 것이 이 케이스다.
    """
    script = _fake_repo(tmp_path, repo_lock=None)
    stub = _write_docker_stub(tmp_path, image_lock=None)

    result = _run(script, stub, tmp_path, "status")

    assert "측정 못 함" in result.stdout
    assert "레포 uv.lock 과 동일" not in result.stdout


# --------------------------------------------------------------- 판정이 네트워크를 안 탄다


def test_freshness_probe_runs_with_network_disabled(tmp_path: Path) -> None:
    """판정용 컨테이너는 `--network none` 으로 뜬다.

    ★판정이 네트워크를 타면 네트워크 장애가 「이미지가 낡았다」로 둔갑한다.
    """
    script = _fake_repo(tmp_path)
    stub = _write_docker_stub(tmp_path, image_lock=REPO_LOCK_BODY)
    calls = tmp_path / "docker-calls.txt"

    _run(script, stub, tmp_path, "status")

    run_calls = [
        line for line in calls.read_text(encoding="utf-8").splitlines() if line.startswith("run ")
    ]
    assert run_calls, "판정이 docker run 을 부르지 않았다 — 측정 자체가 없었다"
    assert all("--network none" in call for call in run_calls)


def test_worker_image_name_is_overridable(tmp_path: Path) -> None:
    """`QB_WORKER_IMAGE` 로 이미지 이름을 바꿀 수 있다.

    compose 의 project 이름은 체크아웃 디렉터리에서 파생되므로 워크트리·격리 슬롯에서
    달라진다. 그 경우에도 판정이 엉뚱한 이미지를 재지 않도록 seam 을 둔다.
    """
    script = _fake_repo(tmp_path)
    stub = _write_docker_stub(tmp_path, image_lock=REPO_LOCK_BODY)
    calls = tmp_path / "docker-calls.txt"
    calls.touch()

    subprocess.run(
        ["bash", str(script), "status"],
        capture_output=True,
        text=True,
        env={
            "PATH": f"{stub}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(tmp_path),
            "DOCKER_STUB_CALLS_FILE": str(calls),
            "QB_WORKER_IMAGE": "custom-worker-image",
        },
        check=False,
    )

    assert "custom-worker-image" in calls.read_text(encoding="utf-8")


@pytest.mark.parametrize("subcommand", ["status"])
def test_status_prints_the_freshness_section(tmp_path: Path, subcommand: str) -> None:
    """섹션 제목이 있어야 사람이 그 줄을 찾는다."""
    script = _fake_repo(tmp_path)
    stub = _write_docker_stub(tmp_path, image_lock=REPO_LOCK_BODY)

    result = _run(script, stub, tmp_path, subcommand)

    assert "── 워커 이미지 신선도 ──" in result.stdout
