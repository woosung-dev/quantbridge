"""`tools/scripts/deploy.sh` 의 계약을 고정한다 — 이 스크립트가 틀리면 매매 워커가 잘못된 순서로 죽거나,
DDL 승인 규칙이 조용히 우회되거나, 실격이 난 위에 새 코드가 얹힌다.

가짜 docker·git·uv·systemctl·curl 을 PATH 앞에 두고 **호출 순서와 rc** 만 본다. 잰 것:
⑴ 24h 자동 사망 ≥1 이면 rc 2 + 아무것도 안 바꾼다  ⑵ DDL 불일치면 rc 2  ⑶ 롤링 순서 beat→optimizer→worker→ws-stream
⑷ 한 서비스 up 실패 = 그 자리에서 멈추고 rc 1(다음 서비스 안 건드림)  ⑸ import probe 실패면 API 를 재시작하지 않는다
⑹ --dry-run 은 판정만 하고 부작용 0  ⑺ 자동 사망 어휘가 `SessionDeactivationReason` 과 어긋나지 않는다.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

from src.trading.models import SessionDeactivationReason

REPO = Path(__file__).resolve().parents[4]
SCRIPT = REPO / "tools" / "scripts" / "deploy.sh"

FAKE_DOCKER = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_LOG"
case "$1" in
  pull) [ "${FAKE_PULL_FAIL:-}" = 1 ] && exit 1; exit 0 ;;
  exec)
    # … psql … -Atc <SQL>
    sql="${@: -1}"
    case "$sql" in
      *alembic_version*) echo "${FAKE_DB_REV}" ;;
      *count\(\*\)*) echo "${FAKE_DEATHS}" ;;
    esac
    exit 0 ;;
  run) echo "${FAKE_HEAD} (head)"; exit 0 ;;
  inspect)
    case "$*" in
      *State.Status*) echo running ;;
      *Config.Image*) echo "ghcr.io/woosung-dev/quantbridge-backend:sha-running" ;;
    esac
    exit 0 ;;
  compose)
    case "$*" in
      *" up -d --no-deps --no-build "*)
        svc="${@: -1}"
        [ "$svc" = "${FAKE_UP_FAIL:-}" ] && exit 1
        ;;
    esac
    exit 0 ;;
  images) exit 0 ;;
  ps) exit 0 ;;
  builder) exit 0 ;;
  system) exit 0 ;;
esac
exit 0
"""

FAKE_GIT = r"""#!/usr/bin/env bash
printf 'git %s\n' "$*" >> "$FAKE_LOG"
case "$*" in
  *"branch --show-current"*) echo "${FAKE_BRANCH:-main}" ;;
  *"rev-parse --short HEAD"*) echo abc1234 ;;
esac
exit 0
"""

FAKE_LOGGER = r"""#!/usr/bin/env bash
printf '%s %s\n' "$(basename "$0")" "$*" >> "$FAKE_LOG"
exit 0
"""

FAKE_API_PYTHON = r"""#!/usr/bin/env bash
printf 'api-python %s\n' "$*" >> "$FAKE_LOG"
exit "${FAKE_PROBE_RC:-0}"
"""

FAKE_NOTIFY = r"""#!/usr/bin/env bash
cat >> "$FAKE_NOTIFY_BODY"
echo >> "$FAKE_NOTIFY_BODY"
exit 0
"""


def _write_exec(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def run(
    tmp_path: Path,
    *args: str,
    deaths: str = "0",
    db_rev: str = "r1",
    head: str = "r1",
    branch: str = "main",
    up_fail: str = "",
    probe_rc: str = "0",
    env_extra: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[str], str, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _write_exec(bin_dir / "docker", FAKE_DOCKER)
    _write_exec(bin_dir / "git", FAKE_GIT)
    for name in ("uv", "systemctl", "curl"):
        _write_exec(bin_dir / name, FAKE_LOGGER)
    api_python = _write_exec(tmp_path / "api-python", FAKE_API_PYTHON)
    notify = _write_exec(tmp_path / "notify", FAKE_NOTIFY)

    root = tmp_path / "root"
    (root / "apps" / "api").mkdir(parents=True, exist_ok=True)
    (root / "infra" / "compose").mkdir(parents=True, exist_ok=True)
    env_file = root / "apps" / "api" / ".env.local"
    env_file.write_text("TELEGRAM_BOT_TOKEN=t\nTELEGRAM_CHAT_ID=c\n")
    log = tmp_path / "calls.log"
    log.write_text("")
    body = tmp_path / "notify-body"
    body.write_text("")

    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_LOG": str(log),
        "FAKE_DEATHS": deaths,
        "FAKE_DB_REV": db_rev,
        "FAKE_HEAD": head,
        "FAKE_BRANCH": branch,
        "FAKE_UP_FAIL": up_fail,
        "FAKE_PROBE_RC": probe_rc,
        "FAKE_NOTIFY_BODY": str(body),
        "QB_DEPLOY_ROOT": str(root),
        "QB_NOTIFY_ENV_FILE": str(env_file),
        "QB_DEPLOY_API_PYTHON": str(api_python),
        "QB_DEPLOY_NOTIFY_CMD": str(notify),
        "HOME": str(tmp_path),
        **(env_extra or {}),
    }
    env.pop("QB_DEPLOY_FORCE", None) if not (env_extra and "QB_DEPLOY_FORCE" in env_extra) else None
    proc = subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    return proc, log.read_text().splitlines(), body.read_text(), root


def _ups(calls: list[str]) -> list[str]:
    """롤링 up 호출만 서비스 이름으로 뽑는다(순서 보존)."""
    return [c.rsplit(" ", 1)[1] for c in calls if " up -d --no-deps --no-build " in c]


def test_script_exists_and_is_executable() -> None:
    assert SCRIPT.is_file()
    assert os.access(SCRIPT, os.X_OK)


def test_dry_run_judges_but_changes_nothing(tmp_path: Path) -> None:
    proc, calls, body, root = run(tmp_path, "--dry-run", "0123456789abcdef")
    assert proc.returncode == 0, proc.stderr
    assert "pull -q ghcr.io/woosung-dev/quantbridge-backend:sha-0123456" in calls, (
        "판정 전에 이미지를 당긴다"
    )
    assert _ups(calls) == []
    assert not any(c.startswith("systemctl") for c in calls)
    assert not any(c.startswith("git pull") for c in calls)
    assert not (root / ".env").exists()
    assert body == ""


def test_auto_death_in_last_24h_blocks_with_rc2(tmp_path: Path) -> None:
    proc, calls, body, root = run(tmp_path, "0123456789abcdef", deaths="2")
    assert proc.returncode == 2
    assert _ups(calls) == []
    assert not (root / ".env").exists()
    assert "막힘" in body and "자동 사망 2건" in body


def test_force_bypasses_auto_death_check(tmp_path: Path) -> None:
    proc, calls, _, _ = run(
        tmp_path, "0123456789abcdef", deaths="2", env_extra={"QB_DEPLOY_FORCE": "1"}
    )
    assert proc.returncode == 0, proc.stderr
    assert len(_ups(calls)) == 4


def test_ddl_mismatch_blocks_with_rc2(tmp_path: Path) -> None:
    proc, calls, body, _ = run(tmp_path, "0123456789abcdef", db_rev="r1", head="r2")
    assert proc.returncode == 2
    assert _ups(calls) == []
    assert "DDL 필요" in body and "r1" in body and "r2" in body


def test_happy_path_rolls_in_order_then_fe_then_api(tmp_path: Path) -> None:
    proc, calls, body, root = run(tmp_path, "0123456789abcdef")
    assert proc.returncode == 0, proc.stderr
    assert _ups(calls) == [
        "backend-beat",
        "backend-optimizer-heavy",
        "backend-worker",
        "backend-ws-stream",
    ]
    joined = "\n".join(calls)
    i_last_worker = joined.index("backend-ws-stream")
    i_fe = joined.index("-p quantbridge-fe up -d --no-build")
    i_probe = joined.index("api-python -c import src.main")
    i_restart = joined.index("systemctl --user restart quantbridge-api.service")
    i_health = joined.index("curl -fsS")
    assert i_last_worker < i_fe < i_probe < i_restart < i_health, (
        "워커 → FE → probe → 재시작 → health 순서"
    )
    assert any(c.endswith("pull -q --ff-only origin main") for c in calls)
    env = (root / ".env").read_text()
    assert "QB_BACKEND_TAG=sha-0123456" in env and "QB_FRONTEND_TAG=sha-0123456" in env
    assert "✅ deploy sha-0123456 완료" in body


def test_service_up_failure_stops_there_with_rc1(tmp_path: Path) -> None:
    proc, calls, body, _ = run(tmp_path, "0123456789abcdef", up_fail="backend-worker")
    assert proc.returncode == 1
    assert _ups(calls) == ["backend-beat", "backend-optimizer-heavy", "backend-worker"], (
        "실패한 다음은 안 건드린다"
    )
    assert not any(c.startswith("systemctl") for c in calls)
    assert "🔴" in body and "backend-worker up" in body


def test_import_probe_failure_does_not_restart_api(tmp_path: Path) -> None:
    proc, calls, body, _ = run(tmp_path, "0123456789abcdef", probe_rc="1")
    assert proc.returncode == 1
    assert not any("systemctl --user restart" in c for c in calls), "옛 API 를 살려 둔다"
    assert "import probe" in body


def test_refuses_non_main_checkout(tmp_path: Path) -> None:
    proc, calls, _, _ = run(tmp_path, "0123456789abcdef", branch="feat/x")
    assert proc.returncode == 1
    assert _ups(calls) == []


def test_auto_death_vocabulary_matches_the_enum() -> None:
    """어휘 정본은 `SessionDeactivationReason` 이다 — 행정 사유 둘만 빼고 전부 실격이어야 한다."""
    text = SCRIPT.read_text()
    m = re.search(r'^AUTO_DEATH_REASONS="(.+)"$', text, re.M)
    assert m, "deploy.sh 에 AUTO_DEATH_REASONS 가 없다"
    in_script = {v.strip("'") for v in m.group(1).split(",")}
    administrative = {"user_stopped", "account_deleted"}
    in_enum = {r.value for r in SessionDeactivationReason} - administrative
    assert in_script == in_enum, (
        f"script-enum={in_script - in_enum} enum-script={in_enum - in_script}"
    )
