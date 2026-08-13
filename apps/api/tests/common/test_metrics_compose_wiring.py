"""BL-506 compose 배선 테스트(Docker/DB 의존 없음)."""

from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).parents[4]
_MAKEFILE = _ROOT / "Makefile"
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


def test_makefile_wipes_metrics_only_for_full_stack_starts() -> None:
    """U8: 부분 watch 재기동은 살아 있는 mmap writer 파일을 지우지 않는다."""
    rules = {
        line.partition(":")[0]: line.partition(":")[2].split()
        for line in _MAKEFILE.read_text().splitlines()
        if line.startswith(("up:", "up-isolated:", "up-isolated-build:", "up-isolated-watch:"))
        and ":=" not in line
    }

    assert all(
        "metrics-wipe" in rules[target] for target in ("up", "up-isolated", "up-isolated-build")
    )
    assert "metrics-wipe" not in rules["up-isolated-watch"]
    assert "metrics-prepare" in rules["up-isolated-watch"]


def test_metrics_wipe_fails_closed_and_checks_only_metric_writers() -> None:
    """V5: ps 오류는 안전측 skip, writer 네 서비스만 wipe gate로 사용한다."""
    makefile = _MAKEFILE.read_text()
    recipe = makefile[makefile.index("metrics-wipe:") : makefile.index("# === 기본 모드")]
    services = next(
        line.partition(":=")[2].split()
        for line in makefile.splitlines()
        if line.startswith("METRICS_WRITER_SERVICES :=")
    )

    assert services == list(_SERVICES)
    assert "ps -q $(METRICS_WRITER_SERVICES)" in recipe
    assert "status=$$?" in recipe
    assert "[ $$status -ne 0 ]" in recipe
    assert "compose ps failed" in recipe
    assert "metric writers running" in recipe
    assert "no metric writers running" in recipe
