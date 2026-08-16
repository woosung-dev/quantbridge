"""BL-506 compose 배선 테스트(Docker/DB 의존 없음)."""

from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).parents[4]
# ★2026-08-16 [ADR-036] — 종전 `Makefile` 자리다. 기동 명령은 `mise.toml` task 로,
#   metrics wipe 의 fail-closed 판정은 `tools/scripts/metrics-wipe.sh` 로 옮겼다.
#   불변식(전체 스택 기동만 wipe · 부분 watch 재기동은 wipe 금지 · ps 오류는 안전측 skip)은
#   그대로다 — 아래 두 테스트는 **대상만** 바꿔 같은 것을 잰다.
_MISE_TOML = _ROOT / "mise.toml"
_WIPE_SH = _ROOT / "tools" / "scripts" / "metrics-wipe.sh"
_SERVICES = (
    "backend-worker",
    "backend-ws-stream",
    "backend-optimizer-heavy",
    "backend-beat",
)


def _load_compose(path: Path) -> dict[str, object]:
    yaml.SafeLoader.add_constructor(
        "!override", lambda loader, node: loader.construct_sequence(node)
    )
    return yaml.load(path.read_text(), Loader=yaml.SafeLoader)


def _metrics_mount(service: dict[str, object]) -> str | None:
    volumes = service.get("volumes", [])
    return next((volume for volume in volumes if str(volume).endswith(":/metrics")), None)


def test_isolated_volume_overrides_retain_metrics_bind() -> None:
    """T10: 모든 isolated volume override가 base metrics mount를 유지한다."""
    base = _load_compose(_ROOT / "infra" / "compose" / "docker-compose.yml")
    isolated = _load_compose(_ROOT / "infra" / "compose" / "docker-compose.isolated.yml")
    base_services = base["services"]
    isolated_services = isolated["services"]

    for name in _SERVICES:
        base_mount = _metrics_mount(base_services[name])
        isolated_mount = _metrics_mount(isolated_services[name])
        assert base_mount is not None
        assert isolated_mount == base_mount


def test_worker_roles_and_metrics_directory_are_wired() -> None:
    """T11: 모든 writer 컨테이너가 /metrics와 서로 다른 안전한 role을 쓴다."""
    compose = _load_compose(_ROOT / "infra" / "compose" / "docker-compose.yml")
    services = compose["services"]
    roles = []

    for name in _SERVICES:
        environment = services[name]["environment"]
        assert environment["PROMETHEUS_MULTIPROC_DIR"] == "/metrics"
        role = environment["QB_METRICS_ROLE"]
        assert "_" not in role
        roles.append(role)

    assert len(roles) == len(set(roles))


def _task_body(name: str) -> str:
    """`mise.toml` 의 `[tasks.<name>]` 블록 본문을 돌려준다.

    ★섹션 헤더로 자르는 이유 — task 는 순서가 보장되지 않으므로 "다음 `[` 까지" 로만 자른다.
    블록을 못 찾으면 **빈 문자열이 아니라 예외**다. 빈 문자열을 돌려주면 아래 `not in` 단언이
    전부 참이 되어 검사기가 무증거가 된다(이 레포가 반복해서 밟은 모양이다).
    """
    text = _MISE_TOML.read_text()
    header = f"[tasks.{name}]"
    start = text.index(header) + len(header)
    nxt = text.find("\n[", start)
    return text[start:] if nxt == -1 else text[start:nxt]


def test_metrics_wipe_only_on_full_stack_starts() -> None:
    """U8: 부분 watch 재기동은 살아 있는 mmap writer 파일을 지우지 않는다.

    ★[ADR-036] 이후 대상이 Makefile 선행 타깃 → mise task 본문으로 바뀌었다. 재는 것은 같다.
    """
    for task in ("up", "up-isolated", "up-isolated-build"):
        assert "metrics-wipe.sh" in _task_body(task), f"{task} 가 metrics wipe 를 안 부른다"

    watch = _task_body("up-isolated-watch")
    assert "metrics-wipe.sh" not in watch, "부분 재기동이 wipe 를 부르면 지표가 무음 손실된다"
    assert "metrics-prepare" in watch


def test_metrics_wipe_fails_closed_and_checks_only_metric_writers() -> None:
    """V5: ps 오류는 안전측 skip, writer 네 서비스만 wipe gate로 사용한다."""
    wipe = _WIPE_SH.read_text()
    services = next(
        line.partition("=")[2].strip().strip('"').split()
        for line in wipe.splitlines()
        if line.startswith("WRITERS=")
    )

    assert services == list(_SERVICES)
    assert "ps -q $WRITERS" in wipe
    assert "status=$?" in wipe
    assert '[ "$status" -ne 0 ]' in wipe
    assert "compose ps failed" in wipe
    assert "metric writers running" in wipe
    assert "no metric writers running" in wipe
    # ★가드가 wipe **안에도** 있어야 한다 — 이 스크립트는 단독 호출이 가능하고,
    #   워크트리에서 `docker compose ps` 는 다른 프로젝트를 봐서 writer 를 0개로 센다.
    assert "assert-main-checkout.sh" in wipe
