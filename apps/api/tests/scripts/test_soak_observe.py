"""`soak-observe.sh` 인자 계약과 fail-closed 종료 코드를 고정한다.

실제 레포에서 실행하면 `.soak/session`을 덮고 Docker 데몬을 건드린다. 모든 사례는 대상
스크립트를 `tmp_path` 가짜 레포로 복사하고, PATH의 `docker` 스텁만 통해 실행한다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REAL = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "soak-observe.sh"
SESSION_ID = "39731d57-f3ec-45c4-b4e1-db304c72692e"
T0 = "2026-08-20 00:00:00+00"


def _fake_repo(tmp_path: Path) -> Path:
    """대상 스크립트를 복사해 레포의 `.soak/` 앵커를 격리한다."""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    copied = scripts / "soak-observe.sh"
    shutil.copy2(REAL, copied)
    return copied


def _write_docker_stub(tmp_path: Path, mode: str) -> Path:
    """T0·`q()`의 Docker 호출을 결정론적으로 응답한다."""
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    docker = stub_bin / "docker"

    scripts = {
        "anchor_failure": """#!/usr/bin/env bash
echo 'database unreachable' >&2
exit 1
""",
        "anchor_empty": """#!/usr/bin/env bash
exit 0
""",
        "q_failure_after_t0": """#!/usr/bin/env bash
calls_file="${DOCKER_STUB_CALLS_FILE:?}"
if [ -s "${calls_file}" ]; then
  printf 'q query failed\\n' >&2
  exit 1
fi
printf 'T0\\n' >> "${calls_file}"
printf '2026-08-20 00:00:00+00\\n'
""",
        "success": """#!/usr/bin/env bash
printf '2026-08-20 00:00:00+00\\n'
""",
    }
    docker.write_text(scripts[mode], encoding="utf-8")
    docker.chmod(0o755)
    return stub_bin


def _write_curl_stub(
    tmp_path: Path,
    stub_bin: Path,
    body: str,
    *,
    returncode: int = 0,
) -> dict[str, str]:
    """URL 지표 취득을 실제 네트워크 없이 본문·종료 코드로 고정한다."""
    body_file = tmp_path / "curl-body.txt"
    body_file.write_text(body, encoding="utf-8")
    curl = stub_bin / "curl"
    curl.write_text(
        """#!/usr/bin/env bash
if [ -n "${CURL_STUB_BODY_FILE:-}" ]; then
  cat "${CURL_STUB_BODY_FILE}"
fi
exit "${CURL_STUB_RETURN_CODE:-0}"
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    return {
        "CURL_STUB_BODY_FILE": str(body_file),
        "CURL_STUB_RETURN_CODE": str(returncode),
    }


def _env(tmp_path: Path, stub_bin: Path, **overrides: str) -> dict[str, str]:
    """실제 Docker 대신 PATH 스텁을 쓰고, DB 컨테이너 이름도 고정한다."""
    environment = {
        **os.environ,
        "PATH": f"{stub_bin}:{os.environ['PATH']}",
        "QB_DB_CONTAINER": "qb-test-db",
        "DOCKER_STUB_CALLS_FILE": str(tmp_path / "docker-calls"),
    }
    environment.update(overrides)
    return environment


def _url_metrics_environment(
    tmp_path: Path,
    stub_bin: Path,
    body: str,
    *,
    curl_returncode: int = 0,
) -> dict[str, str]:
    """URL/curl 스텁과 실재 metrics 디렉터리로 성공 경로의 전제를 맞춘다."""
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    return _env(
        tmp_path,
        stub_bin,
        QB_METRICS_DIR=str(metrics_dir),
        QB_METRICS_URL="http://stub/metrics",
        **_write_curl_stub(
            tmp_path,
            stub_bin,
            body,
            returncode=curl_returncode,
        ),
    )


def _run(script: Path, environment: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """Bash로 가짜 레포의 복사본만 실행한다."""
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def _write_session(script: Path) -> None:
    """DB 없이 fail-closed 앵커 분기까지 도달할 최소 세션 파일을 만든다."""
    state_dir = script.parents[2] / ".soak"
    state_dir.mkdir()
    (state_dir / "session").write_text(f"SESSION_ID={SESSION_ID}\n", encoding="utf-8")


def _write_previous_snapshot(script: Path, body: str) -> Path:
    """현재 실행과 충돌하지 않는 과거 counter 스냅샷을 가짜 레포에 둔다."""
    snapshot = script.parents[2] / ".soak" / "snap-20000101T000000Z.txt"
    snapshot.write_text(body, encoding="utf-8")
    return snapshot


def test_unknown_argument_returns_usage_error(tmp_path: Path) -> None:
    """알 수 없는 인자는 관측 실패가 아니라 사용법 오류(64)다."""
    script = _fake_repo(tmp_path)
    environment = _env(tmp_path, _write_docker_stub(tmp_path, "success"))

    result = _run(script, environment, "--unknown")

    assert result.returncode == 64
    assert "unknown arg" in result.stderr


def test_baseline_without_session_returns_usage_error(tmp_path: Path) -> None:
    """`--baseline`은 세션 UUID 없이 앵커를 만들지 않는다."""
    script = _fake_repo(tmp_path)
    environment = _env(tmp_path, _write_docker_stub(tmp_path, "success"))

    result = _run(script, environment, "--baseline")

    assert result.returncode == 64
    assert "--session <uuid> 가 필요하다" in result.stderr


def test_baseline_writes_session_anchor_in_the_fake_repo(tmp_path: Path) -> None:
    """baseline 앵커는 실제 레포가 아닌 가짜 레포 `.soak/session`에만 남는다."""
    script = _fake_repo(tmp_path)
    environment = _env(tmp_path, _write_docker_stub(tmp_path, "success"))

    result = _run(script, environment, "--baseline", "--session", SESSION_ID)

    assert result.returncode == 3, "지표 경로가 없으므로 baseline 뒤 관측은 fail-closed다"
    assert (tmp_path / ".soak" / "session").read_text(encoding="utf-8") == (
        f"SESSION_ID={SESSION_ID}\n"
    )


def test_missing_anchor_is_measurement_unavailable(tmp_path: Path) -> None:
    """앵커가 없으면 정상으로 진행하지 않고 정확히 3을 반환한다."""
    script = _fake_repo(tmp_path)
    environment = _env(tmp_path, _write_docker_stub(tmp_path, "success"))

    result = _run(script, environment)

    assert result.returncode == 3
    assert "UNKNOWN" in result.stderr
    assert "--baseline --session <uuid>" in result.stderr


def test_anchor_lookup_failure_is_measurement_unavailable(tmp_path: Path) -> None:
    """T0 Docker 실패는 DB에 세션이 없는 경우와 다른 fail-closed 분기다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    environment = _env(tmp_path, _write_docker_stub(tmp_path, "anchor_failure"))

    result = _run(script, environment)

    assert result.returncode == 3
    assert "UNKNOWN — 세션 앵커 조회 실패: database unreachable" in result.stderr


def test_missing_anchor_session_is_measurement_unavailable(tmp_path: Path) -> None:
    """T0 조회가 성공해도 빈 결과는 DB에 없는 세션으로 정확히 구분한다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    environment = _env(tmp_path, _write_docker_stub(tmp_path, "anchor_empty"))

    result = _run(script, environment)

    assert result.returncode == 3
    assert f"UNKNOWN — 세션 {SESSION_ID} 가 DB 에 없다" in result.stderr


def test_query_failure_after_t0_is_reported_as_unknown(tmp_path: Path) -> None:
    """`q()`가 실패해도 요약 UNKNOWN을 남기고 3으로 종결한다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    environment = _env(tmp_path, _write_docker_stub(tmp_path, "q_failure_after_t0"))

    result = _run(script, environment)

    assert result.returncode == 3
    assert (tmp_path / "docker-calls").read_text(encoding="utf-8") == "T0\n"
    assert "UNKNOWN — psql 실패: q query failed" in result.stdout
    assert "일부 조회가 실패했다" in result.stdout


def test_successful_queries_and_metrics_return_zero(tmp_path: Path) -> None:
    """양성 대조 — 첫 스냅샷도 실제 series를 기록하고 전량 성공한다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(
        tmp_path,
        stub_bin,
        "qb_live_signal_evaluated_total 1\n",
    )

    result = _run(script, environment)

    assert result.returncode == 0, result.stderr
    assert "첫 스냅샷" in result.stdout
    assert "1 series" in result.stdout
    assert "✓ 전 항목 조회 성공" in result.stdout
    snapshots = list((tmp_path / ".soak").glob("snap-*.txt"))
    assert len(snapshots) == 1
    assert snapshots[0].read_text(encoding="utf-8") == "qb_live_signal_evaluated_total 1\n"


def test_counter_increase_reports_signed_delta(tmp_path: Path) -> None:
    """같은 series의 증가는 절대값이 아니라 부호 있는 차분으로만 보인다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    _write_previous_snapshot(script, "qb_live_signal_evaluated_total 5\n")
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(
        tmp_path,
        stub_bin,
        "qb_live_signal_evaluated_total 8\n",
    )

    result = _run(script, environment)

    assert result.returncode == 0, result.stderr
    assert "Δ" in result.stdout
    assert "+3" in result.stdout
    assert "qb_live_signal_evaluated_total  : 5 -> 8" in result.stdout


def test_counter_new_series_is_not_treated_as_delta_from_zero(tmp_path: Path) -> None:
    """출생일이 다른 series는 0에서 오른 값이 아니라 NEW다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    _write_previous_snapshot(script, "qb_live_signal_evaluated_total 5\n")
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(
        tmp_path,
        stub_bin,
        "qb_live_signal_dispatch_total 3\nqb_live_signal_evaluated_total 5\n",
    )

    result = _run(script, environment)

    assert result.returncode == 0, result.stderr
    assert "NEW      qb_live_signal_dispatch_total  = 3" in result.stdout
    assert "after-0" not in result.stdout
    assert "Δ" not in result.stdout


def test_counter_missing_series_warns_snapshot_loss(tmp_path: Path) -> None:
    """이전에는 있던 series가 사라지면 MISSING과 유실 경고를 남긴다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    _write_previous_snapshot(
        script,
        "qb_live_signal_dispatch_total 4\nqb_live_signal_evaluated_total 5\n",
    )
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(
        tmp_path,
        stub_bin,
        "qb_live_signal_evaluated_total 5\n",
    )

    result = _run(script, environment)

    assert result.returncode == 0, result.stderr
    assert "MISSING  qb_live_signal_dispatch_total  (이전 4)" in result.stdout
    assert "스냅샷 유실 의심" in result.stdout


def test_unchanged_counter_requests_session_liveness_check(tmp_path: Path) -> None:
    """차분이 없으면 정상 단정 대신 세션 생존 확인을 요청한다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    _write_previous_snapshot(script, "qb_live_signal_evaluated_total 5\n")
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(
        tmp_path,
        stub_bin,
        "qb_live_signal_evaluated_total 5\n",
    )

    result = _run(script, environment)

    assert result.returncode == 0, result.stderr
    assert "변화 없음" in result.stdout
    assert "세션 생존을 먼저 의심해라" in result.stdout


def test_metrics_scrape_failure_is_unknown_and_returns_three(tmp_path: Path) -> None:
    """curl 실패는 series 0건이 아니라 UNKNOWN으로 fail-closed 한다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(
        tmp_path,
        stub_bin,
        "ignored\n",
        curl_returncode=22,
    )

    result = _run(script, environment)

    assert result.returncode == 3
    assert "UNKNOWN — http://stub/metrics 스크레이프 실패" in result.stdout
    assert "일부 조회가 실패했다" in result.stdout


def test_metrics_with_no_matching_series_is_not_unknown(tmp_path: Path) -> None:
    """성공한 취득의 0 series는 표본 없음이지 스크레이프 실패가 아니다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(
        tmp_path,
        stub_bin,
        "process_cpu_seconds_total 1\n",
    )

    result = _run(script, environment)

    assert result.returncode == 0, result.stderr
    assert "첫 스냅샷" in result.stdout
    assert "0 series" in result.stdout
    assert "UNKNOWN" not in result.stdout
    assert "✓ 전 항목 조회 성공" in result.stdout
    snapshots = list((tmp_path / ".soak").glob("snap-*.txt"))
    assert len(snapshots) == 1
    assert snapshots[0].read_text(encoding="utf-8") == ""


def test_empty_metrics_body_is_unknown_and_returns_three(tmp_path: Path) -> None:
    """curl 성공이어도 빈 본문은 관측 불가이므로 fail-closed 한다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    stub_bin = _write_docker_stub(tmp_path, "success")
    environment = _url_metrics_environment(tmp_path, stub_bin, "")

    result = _run(script, environment)

    assert result.returncode == 3
    assert "UNKNOWN — http://stub/metrics 스크레이프 실패" in result.stdout


def test_direct_metrics_source_is_labelled_when_directory_is_unavailable(tmp_path: Path) -> None:
    """URL 미지정 UNKNOWN은 직독 경로를 명시해 잘못된 URL 추적을 막는다."""
    script = _fake_repo(tmp_path)
    _write_session(script)
    missing_metrics_dir = tmp_path / "missing-metrics"
    environment = _env(
        tmp_path,
        _write_docker_stub(tmp_path, "success"),
        QB_METRICS_DIR=str(missing_metrics_dir),
    )

    result = _run(script, environment)

    assert result.returncode == 3
    assert f"UNKNOWN — {missing_metrics_dir} (직독) 스크레이프 실패" in result.stdout
